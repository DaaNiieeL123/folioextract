import os
import subprocess
import sys
from threading import Event, Lock

from fastapi import FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from starlette.datastructures import UploadFile as StarletteUploadFile
import asyncio
import importlib.util
from pathlib import Path
import json
import shutil
import tempfile
from dataclasses import dataclass
from dataclasses import field
from time import perf_counter

from backend.app.api.schemas import ConversionRequest, OpenPathRequest, SelectFolderRequest, SettingsData
from backend.app.infrastructure.config.settings import AppSettings
from backend.app.domain.entities import ConversionJobContext
from backend.app.domain.errors import AppError, InfrastructureError, ValidationError
from backend.app.infrastructure.di.container import AppContainer
from backend.app.infrastructure.job_store import FileJobStore
from backend.app.application.batch_service import BatchService
from backend.app.infrastructure.common.logger import logger
from backend.app.infrastructure.common.file_helpers import get_unique_filename


@dataclass
class JobEventStream:
    items: list[dict] = field(default_factory=list)
    completed: bool = False
    wait_event: asyncio.Event = field(default_factory=asyncio.Event)


class JobEventBroker:
    def __init__(self):
        self._streams: dict[str, JobEventStream] = {}
        self._lock = Lock()

    def ensure_job(self, job_id: str) -> None:
        with self._lock:
            self._streams.setdefault(job_id, JobEventStream())

    def publish(self, job_id: str, item: dict) -> None:
        with self._lock:
            stream = self._streams.setdefault(job_id, JobEventStream())
            stream.items.append(item)
            if item["type"] == "complete":
                stream.completed = True
            wait_event = stream.wait_event
            stream.wait_event = asyncio.Event()
        wait_event.set()

    async def iterate(self, job_id: str):
        index = 0
        while True:
            with self._lock:
                stream = self._streams.get(job_id)
                if stream is None:
                    return
                pending_items = list(stream.items[index:])
                is_completed = stream.completed
                wait_event = stream.wait_event

            for item in pending_items:
                index += 1
                yield item
                if item["type"] == "complete":
                    return

            if is_completed:
                return

            await wait_event.wait()


@dataclass
class RuntimeState:
    event_broker: JobEventBroker
    job_store: FileJobStore
    state_lock: Lock = field(default_factory=Lock)
    running_job_ids: set[str] = field(default_factory=set)
    started_at: dict[str, float] = field(default_factory=dict)
    cancel_events: dict[str, Event] = field(default_factory=dict)


def _resolve_app_dir() -> Path:
    configured_dir = os.environ.get("FOLIOEXTRACT_HOME", "").strip()
    candidates = []
    if configured_dir:
        candidates.append(Path(configured_dir).expanduser())
    candidates.append(Path.home() / ".folioextract")
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        candidates.append(Path(local_app_data) / "FolioExtract")
    candidates.append(Path(tempfile.gettempdir()) / "FolioExtract")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            continue

    raise InfrastructureError("No se pudo preparar el directorio de datos de FolioExtract")


def _build_runtime() -> tuple[Path, Path, AppSettings, AppContainer, BatchService, RuntimeState]:
    app_dir = _resolve_app_dir()
    settings_file = app_dir / "settings.json"
    settings = AppSettings.load(settings_file)
    container = AppContainer(settings=settings)
    batch_service = BatchService(use_case=container.conversion_use_case, container=container)
    job_store = FileJobStore(app_dir / "jobs_history.json")
    recovered_jobs = job_store.mark_interrupted_unfinished()
    if recovered_jobs:
        logger.info("jobs_marked_interrupted", extra={"event": "jobs_marked_interrupted", "count": recovered_jobs})
    runtime = RuntimeState(event_broker=JobEventBroker(), job_store=job_store)
    return app_dir, settings_file, settings, container, batch_service, runtime


def _normalize_output_dir(raw_path: str) -> Path:
    normalized = Path(raw_path).expanduser().resolve(strict=False)
    return normalized


def _settings_payload(settings: AppSettings) -> SettingsData:
    last_output_dir = ""
    if settings.last_output_dir.strip():
        try:
            last_output_dir = str(_normalize_output_dir(settings.last_output_dir))
        except Exception:
            last_output_dir = settings.last_output_dir
    return SettingsData(theme=settings.theme, last_output_dir=last_output_dir)


def _ensure_multipart_support() -> None:
    if importlib.util.find_spec("multipart") is None:
        raise ValidationError("La conversion por upload requiere instalar python-multipart")


def _is_upload_item(value: object) -> bool:
    return isinstance(value, (UploadFile, StarletteUploadFile))


def _open_path_in_os(target: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(target))
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
        return
    subprocess.Popen(["xdg-open", str(target)])


def _select_folder_in_os(initial_path: str | None = None) -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise InfrastructureError(f"No se pudo abrir el selector de carpetas: {exc}") from exc

    root = tk.Tk()
    root.withdraw()

    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    dialog_kwargs = {"parent": root, "title": "Selecciona una carpeta de salida"}
    if initial_path:
        candidate = Path(initial_path).expanduser().resolve(strict=False)
        if candidate.exists() and candidate.is_dir():
            dialog_kwargs["initialdir"] = str(candidate)

    try:
        selected = filedialog.askdirectory(**dialog_kwargs)
    finally:
        root.destroy()

    return str(selected or "")


def create_app() -> FastAPI:
    app_dir, settings_file, settings, container, batch_service, runtime = _build_runtime()
    app = FastAPI(title="FolioExtract API", version="3.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception):
        logger.error("unhandled_api_exception", extra={"event": "unhandled_api_exception", "error": str(exc)})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "Unexpected server error",
                }
            },
        )

    @app.get("/api/settings", response_model=SettingsData)
    def get_settings():
        return _settings_payload(settings)

    @app.post("/api/settings", response_model=SettingsData)
    def update_settings(data: SettingsData):
        settings.theme = data.theme
        if data.last_output_dir.strip():
            try:
                settings.last_output_dir = str(_normalize_output_dir(data.last_output_dir))
            except Exception:
                raise ValidationError("No se pudo normalizar el directorio de destino")
        else:
            settings.last_output_dir = ""
        settings.save(settings_file)
        return _settings_payload(settings)

    @app.get("/api/health")
    def health_check():
        with runtime.state_lock:
            running_job_ids = sorted(runtime.running_job_ids)
        return {
            "status": "ok",
            "backend_ready": True,
            "running_jobs": running_job_ids,
            "running_jobs_count": len(running_job_ids),
        }

    @app.get("/api/metrics")
    def get_metrics():
        return container.metrics.snapshot()

    @app.get("/api/jobs")
    def list_jobs(limit: int = 20):
        return {"jobs": runtime.job_store.list_jobs(limit=max(1, min(limit, 100)))}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        job = runtime.job_store.get_job(job_id)
        if job is None:
            raise ValidationError("Job no encontrado")
        return {"job": job}

    async def _start_conversion(
        *,
        source_paths: list[Path],
        output_dir_raw: str,
        extension: str,
        job: ConversionJobContext | None = None,
        cleanup_dir: Path | None = None,
    ):
        if not source_paths:
            raise ValidationError("Debes seleccionar al menos un PDF")
        if not output_dir_raw:
            raise ValidationError("Debes seleccionar un directorio de destino")

        try:
            out_dir = _normalize_output_dir(output_dir_raw)
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            raise ValidationError("No se pudo preparar el directorio de destino")

        try:
            container.converter_factory.create(extension)
        except Exception as exc:
            logger.error(
                "converter_validation_failed",
                extra={
                    "event": "converter_validation_failed",
                    "converter": extension,
                    "error": str(exc),
                },
            )
            raise ValidationError("Formato de salida no soportado")

        job = job or ConversionJobContext()
        runtime.event_broker.ensure_job(job.job_id)
        settings.last_output_dir = str(out_dir)
        settings.save(settings_file)
        loop = asyncio.get_running_loop()

        runtime.job_store.create_job(
            job_id=job.job_id,
            total=len(source_paths),
            extension=extension,
            output_dir=str(out_dir),
            files=[path.name for path in source_paths],
            source_paths=[str(path) for path in source_paths],
            status="queued",
        )
        with runtime.state_lock:
            runtime.cancel_events[job.job_id] = Event()

        def _started_cb():
            runtime.job_store.mark_running(job_id=job.job_id)
            with runtime.state_lock:
                runtime.running_job_ids.add(job.job_id)
                runtime.started_at[job.job_id] = perf_counter()

        def _should_cancel() -> bool:
            with runtime.state_lock:
                cancel_event = runtime.cancel_events.get(job.job_id)
            return cancel_event.is_set() if cancel_event is not None else False

        def _progress_cb(current, total, fname, is_err, err_msg, output_path):
            msg = {
                "job_id": job.job_id,
                "current": current,
                "total": total,
                "filename": fname,
                "is_error": is_err,
                "error_msg": err_msg or "",
                "output_path": output_path or "",
            }
            runtime.job_store.update_progress(
                job_id=job.job_id,
                current=current,
                filename=fname,
                is_error=is_err,
                error_msg=err_msg,
                output_path=output_path,
            )
            loop.call_soon_threadsafe(runtime.event_broker.publish, job.job_id, {"type": "progress", "data": msg})

        def _complete_cb(successes, errors, final_status):
            msg = {"job_id": job.job_id, "successes": successes, "errors": errors, "status": final_status}
            with runtime.state_lock:
                runtime.running_job_ids.discard(job.job_id)
                started_at = runtime.started_at.pop(job.job_id, perf_counter())
                runtime.cancel_events.pop(job.job_id, None)
            elapsed_ms = (perf_counter() - started_at) * 1000
            runtime.job_store.complete_job(
                job_id=job.job_id,
                successes=successes,
                errors=errors,
                elapsed_ms=elapsed_ms,
                status=final_status,
            )
            loop.call_soon_threadsafe(runtime.event_broker.publish, job.job_id, {"type": "complete", "data": msg})

        batch_service.convert_batch_async(
            sources=source_paths,
            output_dir=out_dir,
            extension=extension,
            on_started=_started_cb,
            on_progress=_progress_cb,
            on_complete=_complete_cb,
            job_context=job,
            should_cancel=_should_cancel,
        )
        return {"message": "Conversion started in background", "job_id": job.job_id}

    @app.post("/api/convert")
    async def start_conversion(req: ConversionRequest):
        return await _start_conversion(
            source_paths=[Path(p) for p in req.paths],
            output_dir_raw=req.output_dir,
            extension=req.extension,
        )

    @app.post("/api/convert/upload")
    async def start_upload_conversion(request: Request):
        _ensure_multipart_support()
        try:
            form = await request.form()
        except (RuntimeError, AssertionError) as exc:
            raise ValidationError("La conversion por upload requiere instalar python-multipart") from exc

        output_dir = str(form.get("output_dir") or "")
        extension = str(form.get("extension") or "")
        files = [item for item in form.getlist("files") if _is_upload_item(item)]

        if not files:
            raise ValidationError("Debes seleccionar al menos un PDF")

        job = ConversionJobContext()
        upload_root = app_dir / "temp_jobs" / job.job_id
        input_dir = upload_root / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        source_paths: list[Path] = []
        try:
            for uploaded in files:
                filename = Path(uploaded.filename or "").name
                if not filename.lower().endswith(".pdf"):
                    continue

                target = get_unique_filename(input_dir / filename)
                with target.open("wb") as buffer:
                    shutil.copyfileobj(uploaded.file, buffer)
                source_paths.append(target)

            if not source_paths:
                raise ValidationError("Debes seleccionar al menos un PDF valido")

            return await _start_conversion(
                source_paths=source_paths,
                output_dir_raw=output_dir,
                extension=extension,
                job=job,
                cleanup_dir=upload_root,
            )
        except Exception:
            shutil.rmtree(upload_root, ignore_errors=True)
            raise
        finally:
            for uploaded in files:
                await uploaded.close()

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        job = runtime.job_store.get_job(job_id)
        if job is None:
            raise ValidationError("Job no encontrado")
        if job.get("status") in {"completed", "failed", "canceled", "interrupted"}:
            return {"message": "El job ya habia finalizado", "job_id": job_id}

        runtime.job_store.request_cancel(job_id=job_id)
        with runtime.state_lock:
            cancel_event = runtime.cancel_events.get(job_id)
        if cancel_event is not None:
            cancel_event.set()
        return {"message": "Cancelacion solicitada", "job_id": job_id}

    @app.post("/api/jobs/{job_id}/retry")
    async def retry_job(job_id: str):
        job = runtime.job_store.get_job(job_id)
        if job is None:
            raise ValidationError("Job no encontrado")
        if job.get("status") in {"queued", "running"}:
            raise ValidationError("No puedes reintentar un job en progreso")

        source_paths = [Path(raw) for raw in runtime.job_store.get_retryable_sources(job_id)]
        existing_sources = [path for path in source_paths if path.exists()]
        if not existing_sources:
            raise ValidationError("No hay archivos disponibles para reintentar")

        return await _start_conversion(
            source_paths=existing_sources,
            output_dir_raw=str(job.get("output_dir") or ""),
            extension=str(job.get("extension") or ""),
        )

    @app.post("/api/system/open")
    def open_system_path(data: OpenPathRequest):
        target = Path(data.path).expanduser().resolve(strict=False)
        if not target.exists():
            raise ValidationError("La ruta solicitada no existe")
        try:
            _open_path_in_os(target)
        except Exception as exc:
            raise InfrastructureError(f"No se pudo abrir la ruta solicitada: {exc}") from exc
        return {"message": "Ruta abierta", "path": str(target)}

    @app.post("/api/system/select-folder")
    def select_system_folder(data: SelectFolderRequest):
        selected_path = _select_folder_in_os(data.initial_path)
        if not selected_path:
            return {"message": "Seleccion cancelada", "path": ""}
        return {"message": "Carpeta seleccionada", "path": str(_normalize_output_dir(selected_path))}

    @app.get("/api/jobs/{job_id}/progress")
    async def sse_progress(job_id: str):
        job = runtime.job_store.get_job(job_id)
        if job is None:
            raise ValidationError("Job no encontrado")

        async def event_generator():
            emitted = False
            async for item in runtime.event_broker.iterate(job_id):
                emitted = True
                yield {"event": item["type"], "data": json.dumps(item["data"])}
            if not emitted and job.get("status") != "running":
                yield {
                    "event": "complete",
                    "data": json.dumps(
                        {
                            "job_id": job_id,
                            "successes": int(job.get("successes", 0)),
                            "errors": int(job.get("errors", 0)),
                        }
                    ),
                }

        return EventSourceResponse(event_generator())

    return app


app = create_app()
