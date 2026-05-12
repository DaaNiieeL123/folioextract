from __future__ import annotations

import importlib.util
from pathlib import Path
from threading import Event, Lock
from unittest.mock import patch

import backend.server as server
import backend.app.application.conversion_use_case as use_case_module
from fastapi import UploadFile as FastApiUploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from backend.app.infrastructure.config.settings import AppSettings
from backend.app.domain.entities import BatchConversionOutcome
from backend.app.domain.errors import ValidationError
from backend.app.infrastructure.dynamic_factory import DynamicConverterFactory
from backend.app.infrastructure.di.container import AppContainer
from backend.app.infrastructure.job_store import FileJobStore
from backend.app.infrastructure.observability.metrics import InMemoryMetrics
from backend.app.infrastructure.observability.structured_logger import StructuredJobLogger
from backend.app.application.batch_service import BatchService


class FakeUseCase:
    def __init__(self):
        self.called = False

    def convert_batch(self, sources, output_dir, extension, on_progress=None, job_context=None, should_cancel=None):
        self.called = True
        total = len(sources)
        for index, source in enumerate(sources, start=1):
            if on_progress:
                on_progress(index, total, source.name, False, None, str(output_dir / f"{source.stem}{extension}"))
        return BatchConversionOutcome(
            job_id="job_test",
            total=total,
            successes=total,
            errors=0,
            elapsed_ms=10.0,
            status="completed",
        )


class FakeBatchService:
    def __init__(self, fail: bool = False):
        self.last_job_context = None
        self.fail = fail

    def convert_batch_async(
        self,
        sources,
        output_dir,
        extension,
        on_progress=None,
        on_complete=None,
        on_started=None,
        job_context=None,
        should_cancel=None,
    ):
        self.last_job_context = job_context
        total = len(sources)
        if on_started:
            on_started()
        for index, source in enumerate(sources, start=1):
            if on_progress:
                if self.fail:
                    on_progress(index, total, source.name, True, "forced_error", None)
                else:
                    on_progress(index, total, source.name, False, None, str(output_dir / f"{source.stem}{extension}"))
        if on_complete:
            if self.fail:
                on_complete(0, total, "failed")
            else:
                on_complete(total, 0, "completed")


def test_batch_service_uses_application_use_case(tmp_path: Path):
    completed = Event()
    stats = {}
    progress_events = []

    use_case = FakeUseCase()
    service = BatchService(use_case=use_case)

    sources = [tmp_path / "a.pdf", tmp_path / "b.pdf"]

    def on_progress(current, total, filename, is_error, error_msg, output_path):
        progress_events.append((current, total, filename, is_error, error_msg, output_path))

    def on_complete(successes, errors, status):
        stats["successes"] = successes
        stats["errors"] = errors
        stats["status"] = status
        completed.set()

    service.convert_batch_async(
        sources=sources,
        output_dir=tmp_path,
        extension=".md",
        on_progress=on_progress,
        on_complete=on_complete,
    )

    assert completed.wait(timeout=2), "Batch did not complete in expected time"
    assert use_case.called is True
    assert stats == {"successes": 2, "errors": 0, "status": "completed"}
    assert len(progress_events) == 2


def _build_test_app(monkeypatch, tmp_path: Path, *, fail: bool = False):
    fake_service = FakeBatchService(fail=fail)

    def fake_build_runtime():
        app_dir = tmp_path / ".folioextract"
        app_dir.mkdir(parents=True, exist_ok=True)
        settings_file = app_dir / "settings.json"
        settings = AppSettings()
        container = AppContainer(settings=settings)
        runtime = server.RuntimeState(
            event_broker=server.JobEventBroker(),
            job_store=FileJobStore(app_dir / "jobs_history_test.json"),
        )
        return app_dir, settings_file, settings, container, fake_service, runtime

    monkeypatch.setattr(server, "_build_runtime", fake_build_runtime)
    return server.create_app(), fake_service


def test_api_convert_validation(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient  # type: ignore[reportMissingImports]

    app, _ = _build_test_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post("/api/convert", json={"paths": [], "output_dir": "", "extension": ".md"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_settings_endpoint_normalizes_output_dir(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient  # type: ignore[reportMissingImports]

    app, _ = _build_test_app(monkeypatch, tmp_path)
    client = TestClient(app)

    raw_dir = str(Path("~") / "folio-settings")
    expected_dir = str(Path(raw_dir).expanduser().resolve(strict=False))

    update_response = client.post(
        "/api/settings",
        json={"theme": "System", "last_output_dir": raw_dir},
    )
    assert update_response.status_code == 200
    assert update_response.json()["last_output_dir"] == expected_dir

    get_response = client.get("/api/settings")
    assert get_response.status_code == 200
    assert get_response.json()["last_output_dir"] == expected_dir


def test_sse_progress_stream(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient  # type: ignore[reportMissingImports]

    app, fake_service = _build_test_app(monkeypatch, tmp_path)
    client = TestClient(app)

    convert_response = client.post(
        "/api/convert",
        json={
            "paths": [str(tmp_path / "one.pdf")],
            "output_dir": str(tmp_path),
            "extension": ".md",
        },
    )
    assert convert_response.status_code == 200
    payload = convert_response.json()
    assert payload.get("job_id")
    assert fake_service.last_job_context is not None

    sse_response = client.get(f"/api/jobs/{payload['job_id']}/progress")
    assert sse_response.status_code == 200
    body = sse_response.text
    assert "event: progress" in body
    assert "event: complete" in body

    jobs_response = client.get("/api/jobs")
    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()
    assert jobs_payload["jobs"]
    assert jobs_payload["jobs"][0]["status"] == "completed"

    detail_response = client.get(f"/api/jobs/{payload['job_id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["job"]["job_id"] == payload["job_id"]


def test_upload_convert_starts_job(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient  # type: ignore[reportMissingImports]

    if importlib.util.find_spec("multipart") is None:
        return

    app, fake_service = _build_test_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/convert/upload",
        data={"output_dir": str(tmp_path), "extension": ".md"},
        files=[("files", ("one.pdf", b"%PDF-1.4 fake", "application/pdf"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("job_id")
    assert fake_service.last_job_context is not None


def test_upload_item_detection_accepts_fastapi_and_starlette_uploads():
    fastapi_item = FastApiUploadFile(file=open(__file__, "rb"), filename="fastapi.pdf")
    starlette_item = StarletteUploadFile(file=open(__file__, "rb"), filename="starlette.pdf")

    try:
        assert server._is_upload_item(fastapi_item) is True
        assert server._is_upload_item(starlette_item) is True
        assert server._is_upload_item("not-a-file") is False
    finally:
        fastapi_item.file.close()
        starlette_item.file.close()


def test_upload_convert_without_multipart_returns_validation_error(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient  # type: ignore[reportMissingImports]

    app, _ = _build_test_app(monkeypatch, tmp_path)
    client = TestClient(app)

    monkeypatch.setattr(server, "_ensure_multipart_support", lambda: (_ for _ in ()).throw(ValidationError("missing_multipart")))

    response = client.post("/api/convert/upload")

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "missing_multipart"


def test_retry_job_creates_new_job(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient  # type: ignore[reportMissingImports]

    app, fake_service = _build_test_app(monkeypatch, tmp_path, fail=True)
    client = TestClient(app)
    source_file = tmp_path / "one.pdf"
    source_file.write_bytes(b"%PDF-1.4 fake")

    convert_response = client.post(
        "/api/convert",
        json={
            "paths": [str(source_file)],
            "output_dir": str(tmp_path),
            "extension": ".md",
        },
    )
    failed_job_id = convert_response.json()["job_id"]
    _ = client.get(f"/api/jobs/{failed_job_id}/progress")

    fake_service.fail = False
    retry_response = client.post(f"/api/jobs/{failed_job_id}/retry")

    assert retry_response.status_code == 200
    assert retry_response.json()["job_id"] != failed_job_id


def test_jobs_status_failed_when_all_items_fail(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient  # type: ignore[reportMissingImports]

    app, _ = _build_test_app(monkeypatch, tmp_path, fail=True)
    client = TestClient(app)

    convert_response = client.post(
        "/api/convert",
        json={
            "paths": [str(tmp_path / "one.pdf")],
            "output_dir": str(tmp_path),
            "extension": ".md",
        },
    )
    assert convert_response.status_code == 200
    payload = convert_response.json()

    _ = client.get(f"/api/jobs/{payload['job_id']}/progress")
    detail_response = client.get(f"/api/jobs/{payload['job_id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["job"]["status"] == "failed"


def test_sse_progress_is_scoped_to_requested_job(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient  # type: ignore[reportMissingImports]

    app, _ = _build_test_app(monkeypatch, tmp_path)
    client = TestClient(app)

    first_response = client.post(
        "/api/convert",
        json={
            "paths": [str(tmp_path / "one.pdf")],
            "output_dir": str(tmp_path),
            "extension": ".md",
        },
    )
    second_response = client.post(
        "/api/convert",
        json={
            "paths": [str(tmp_path / "two.pdf")],
            "output_dir": str(tmp_path),
            "extension": ".txt",
        },
    )

    first_job_id = first_response.json()["job_id"]
    second_job_id = second_response.json()["job_id"]

    first_stream = client.get(f"/api/jobs/{first_job_id}/progress")
    second_stream = client.get(f"/api/jobs/{second_job_id}/progress")

    assert first_stream.status_code == 200
    assert second_stream.status_code == 200
    assert first_job_id in first_stream.text
    assert second_job_id not in first_stream.text
    assert second_job_id in second_stream.text
    assert first_job_id not in second_stream.text


def test_batch_service_limits_parallel_batches(tmp_path: Path):
    active = {"count": 0, "max_seen": 0}
    guard = Lock()
    first_started = Event()
    allow_first_finish = Event()
    second_started = Event()
    completed = Event()
    completion_calls = {"count": 0}

    class BlockingUseCase:
        def convert_batch(self, sources, output_dir, extension, on_progress=None, job_context=None, should_cancel=None):
            with guard:
                active["count"] += 1
                active["max_seen"] = max(active["max_seen"], active["count"])

            if not first_started.is_set():
                first_started.set()
                allow_first_finish.wait(timeout=2)
            else:
                second_started.set()

            total = len(sources)
            for index, source in enumerate(sources, start=1):
                if on_progress:
                    on_progress(index, total, source.name, False, None, str(output_dir / f"{source.stem}{extension}"))

            with guard:
                active["count"] -= 1

            return BatchConversionOutcome(
                job_id="job_test",
                total=total,
                successes=total,
                errors=0,
                elapsed_ms=10.0,
                status="completed",
            )

    service = BatchService(use_case=BlockingUseCase(), max_concurrent_batches=1)

    def on_complete(*_args):
        completion_calls["count"] += 1
        if completion_calls["count"] == 2:
            completed.set()

    service.convert_batch_async(
        sources=[tmp_path / "one.pdf"],
        output_dir=tmp_path,
        extension=".md",
        on_complete=on_complete,
    )
    assert first_started.wait(timeout=2)

    service.convert_batch_async(
        sources=[tmp_path / "two.pdf"],
        output_dir=tmp_path,
        extension=".md",
        on_started=second_started.set,
        on_complete=on_complete,
    )

    assert second_started.wait(timeout=0.2) is False
    allow_first_finish.set()
    assert completed.wait(timeout=2)
    assert active["max_seen"] == 1


class _ImmediateFuture:
    def __init__(self, value):
        self._value = value

    def result(self):
        return self._value

    def cancel(self):
        return False


class _ImmediateExecutor:
    def __init__(self):
        self._futures = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args, **kwargs):
        value = fn(*args, **kwargs)
        future = _ImmediateFuture(value)
        self._futures.append(future)
        return future


def test_conversion_use_case_retries_once(tmp_path: Path):
    metrics = InMemoryMetrics()
    logger = StructuredJobLogger("test-logger")
    factory = DynamicConverterFactory()

    attempts = {"count": 0}

    def fake_runner(source, destination, extension):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return use_case_module.ConversionResult(success=False, output_path=None, error="temp_fail")
        return use_case_module.ConversionResult(success=True, output_path=destination, error=None)

    use_case = use_case_module.ConversionUseCase(
        factory=factory,
        metrics=metrics,
        logger=logger,
        max_retries=1,
        executor_factory=lambda _: _ImmediateExecutor(),
    )

    with patch.object(use_case_module, "_run_conversion_process", side_effect=fake_runner), patch.object(
        use_case_module,
        "wait",
        side_effect=lambda futures, timeout=None, return_when=None: (set(futures), set()),
    ):
        outcome = use_case.convert_batch(
            sources=[tmp_path / "retry.pdf"],
            output_dir=tmp_path,
            extension=".md",
        )

    assert attempts["count"] == 2
    assert outcome.successes == 1
    assert outcome.errors == 0


