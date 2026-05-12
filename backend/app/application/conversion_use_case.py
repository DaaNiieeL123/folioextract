from __future__ import annotations

import os
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from collections import deque
from pathlib import Path
from time import perf_counter
from typing import Callable, Optional

from backend.app.infrastructure.conversion.base_converter import ConversionResult
from backend.app.infrastructure.conversion.converter_factory import register_all_converters
from backend.app.domain.entities import BatchConversionOutcome, ConversionJobContext, FileConversionOutcome
from backend.app.domain.errors import ValidationError
from backend.app.domain.ports import ConverterFactoryPort, JobLoggerPort, MetricsPort
from backend.app.infrastructure.common.file_helpers import get_unique_filename


ProgressCallback = Callable[[int, int, str, bool, Optional[str], Optional[str]], None]


def _run_conversion_process(source: Path, destination: Path, extension: str) -> ConversionResult:
    register_all_converters()
    from backend.app.infrastructure.conversion.converter_factory import ConverterFactory

    try:
        converter = ConverterFactory.create(extension)
        return converter.convert(source, destination)
    except Exception as exc:
        return ConversionResult(success=False, output_path=None, error=str(exc))


class ConversionUseCase:
    """Application layer orchestration for batch conversion."""

    def __init__(
        self,
        factory: ConverterFactoryPort,
        metrics: MetricsPort,
        logger: JobLoggerPort,
        max_retries: int = 1,
        executor_factory: Optional[Callable[[int], ProcessPoolExecutor]] = None,
    ):
        self._factory = factory
        self._metrics = metrics
        self._logger = logger
        self._max_retries = max(0, max_retries)
        self._executor_factory = executor_factory or (lambda workers: ProcessPoolExecutor(max_workers=workers))

    def _resolve_workers(self, extension: str, total: int) -> int:
        cpu_count = os.cpu_count() or 4
        normalized = extension.lower()
        max_by_format = {
            ".txt": 1,
            ".docx": 2,
            ".md": 3,
        }.get(normalized, 2)
        cpu_safe_limit = max(1, min(4, cpu_count // 2 if cpu_count > 2 else 1))
        return max(1, min(total, max_by_format, cpu_safe_limit))

    @staticmethod
    def _submit_job(executor: ProcessPoolExecutor, meta: dict) -> object:
        future = executor.submit(
            _run_conversion_process,
            meta["source"],
            meta["destination"],
            meta["extension"],
        )
        meta["future"] = future
        return future

    def convert_batch(
        self,
        sources: list[Path],
        output_dir: Path,
        extension: str,
        on_progress: Optional[ProgressCallback] = None,
        job_context: Optional[ConversionJobContext] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> BatchConversionOutcome:
        if not sources:
            raise ValidationError("La lista de archivos no puede estar vacia")

        if not extension:
            raise ValidationError("La extension de salida es requerida")

        normalized_extension = extension if extension.startswith(".") else f".{extension}"
        normalized_extension = normalized_extension.lower()

        # Validation by construction: fail fast if extension is not registered.
        self._factory.create(normalized_extension)

        job = job_context or ConversionJobContext()
        batch_started = perf_counter()
        total = len(sources)
        successes = 0
        errors = 0
        processed = 0
        canceled = False

        self._logger.info(
            "batch_started",
            job=job,
            converter=normalized_extension,
            total=total,
            output_dir=str(output_dir),
        )

        local_workers = self._resolve_workers(normalized_extension, total)
        self._logger.info(
            "batch_workers_resolved",
            job=job,
            converter=normalized_extension,
            workers=local_workers,
            total=total,
        )

        with self._executor_factory(local_workers) as executor:
            pending_queue = deque()
            futures = {}

            for source in sources:
                base_name = f"{source.stem}_convertido{normalized_extension}"
                destination = get_unique_filename(output_dir / base_name)
                pending_queue.append(
                    {
                        "source": source,
                        "destination": destination,
                        "extension": normalized_extension,
                        "attempt": 0,
                        "started_at": perf_counter(),
                    }
                )

            while pending_queue and len(futures) < local_workers:
                meta = pending_queue.popleft()
                future = self._submit_job(executor, meta)
                futures[future] = meta

            while futures:
                if should_cancel and should_cancel():
                    canceled = True
                    for future in list(futures.keys()):
                        future.cancel()
                    futures.clear()
                    break

                done, _ = wait(list(futures.keys()), timeout=0.2, return_when=FIRST_COMPLETED)
                if not done:
                    continue

                for future in done:
                    meta = futures.pop(future)
                    source = meta["source"]
                    destination = meta["destination"]
                    attempt = int(meta["attempt"])
                    started_at = float(meta["started_at"])

                    try:
                        result = future.result()
                    except Exception as exc:
                        result = ConversionResult(success=False, output_path=None, error=str(exc))

                    if (not result.success) and attempt < self._max_retries and not (should_cancel and should_cancel()):
                        retry_attempt = attempt + 1
                        self._logger.info(
                            "file_retry_scheduled",
                            job=job,
                            file_name=source.name,
                            converter=normalized_extension,
                            retry=retry_attempt,
                            max_retries=self._max_retries,
                        )
                        retry_meta = {
                            "source": source,
                            "destination": destination,
                            "extension": normalized_extension,
                            "attempt": retry_attempt,
                            "started_at": started_at,
                        }
                        retry_future = self._submit_job(executor, retry_meta)
                        futures[retry_future] = retry_meta
                        continue

                    processed += 1
                    try:
                        success = bool(result.success)
                        if success:
                            successes += 1
                        else:
                            errors += 1

                        duration_ms = (perf_counter() - started_at) * 1000
                        error_msg = result.error
                        if error_msg and attempt > 0:
                            error_msg = f"{error_msg} (retries={attempt})"

                        outcome = FileConversionOutcome(
                            source=source,
                            destination=destination,
                            filename=source.name,
                            converter=normalized_extension,
                            success=success,
                            duration_ms=duration_ms,
                            error=error_msg,
                        )
                        self._metrics.observe_conversion(
                            converter=outcome.converter,
                            duration_ms=outcome.duration_ms,
                            success=outcome.success,
                        )
                        if outcome.success:
                            self._logger.info(
                                "file_converted",
                                job=job,
                                file_name=outcome.filename,
                                converter=outcome.converter,
                                duration_ms=round(outcome.duration_ms, 2),
                                retries=attempt,
                            )
                        else:
                            self._logger.error(
                                "file_conversion_failed",
                                job=job,
                                file_name=outcome.filename,
                                converter=outcome.converter,
                                error=outcome.error or "unknown_error",
                                retries=attempt,
                            )

                        if on_progress:
                            on_progress(
                                processed,
                                total,
                                source.name,
                                not success,
                                outcome.error,
                                str(outcome.destination) if outcome.success else None,
                            )
                    except Exception as exc:
                        errors += 1
                        self._logger.error(
                            "file_conversion_exception",
                            job=job,
                            file_name=source.name,
                            converter=normalized_extension,
                            error=str(exc),
                        )
                        if on_progress:
                            on_progress(processed, total, source.name, True, str(exc), None)

                    while pending_queue and len(futures) < local_workers and not (should_cancel and should_cancel()):
                        next_meta = pending_queue.popleft()
                        next_future = self._submit_job(executor, next_meta)
                        futures[next_future] = next_meta

        elapsed_ms = (perf_counter() - batch_started) * 1000
        self._metrics.observe_batch(total=total, elapsed_ms=elapsed_ms)

        final_status = "canceled" if canceled else ("failed" if successes == 0 and errors > 0 else "completed")

        self._logger.info(
            "batch_finished",
            job=job,
            converter=normalized_extension,
            total=total,
            successes=successes,
            errors=errors,
            elapsed_ms=round(elapsed_ms, 2),
            status=final_status,
        )

        return BatchConversionOutcome(
            job_id=job.job_id,
            total=total,
            successes=successes,
            errors=errors,
            elapsed_ms=elapsed_ms,
            status=final_status,
        )


