import threading
import os
from pathlib import Path
from typing import List, Optional, Callable
from backend.app.application.conversion_use_case import ConversionUseCase
from backend.app.domain.entities import ConversionJobContext
from backend.app.infrastructure.di.container import AppContainer
from backend.app.infrastructure.common.logger import logger

ProgressCallback = Callable[[int, int, str, bool, Optional[str], Optional[str]], None]

class BatchService:
    def __init__(
        self,
        use_case: Optional[ConversionUseCase] = None,
        container: Optional[AppContainer] = None,
        max_concurrent_batches: Optional[int] = None,
    ):
        self._use_case = use_case
        self._container = container
        cpu_count = os.cpu_count() or 4
        default_max_batches = 1 if cpu_count < 8 else 2
        self._max_concurrent_batches = max(1, max_concurrent_batches or default_max_batches)
        self._batch_slots = threading.BoundedSemaphore(self._max_concurrent_batches)
        
    def convert_batch_async(
        self,
        sources: List[Path],
        output_dir: Path,
        extension: str,
        on_progress: Optional[ProgressCallback] = None,
        on_complete: Optional[Callable[[int, int, str], None]] = None,
        on_started: Optional[Callable[[], None]] = None,
        job_context: Optional[ConversionJobContext] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> None:
        if not sources:
            if on_complete:
                on_complete(0, 0, "completed")
            return

        def _worker():
            while True:
                if should_cancel and should_cancel():
                    if on_complete:
                        on_complete(0, 0, "canceled")
                    return
                acquired_immediately = self._batch_slots.acquire(blocking=False)
                if acquired_immediately:
                    break
                logger.info(
                    "batch_waiting_for_slot",
                    extra={
                        "event": "batch_waiting_for_slot",
                        "job_id": job_context.job_id if job_context else None,
                        "max_concurrent_batches": self._max_concurrent_batches,
                    },
                )
                if self._batch_slots.acquire(timeout=0.2):
                    break
            try:
                if should_cancel and should_cancel():
                    if on_complete:
                        on_complete(0, 0, "canceled")
                    return

                if on_started:
                    on_started()

                active_use_case = self._use_case
                if active_use_case is None and self._container is not None:
                    active_use_case = self._container.conversion_use_case

                if active_use_case is None:
                    raise RuntimeError("BatchService requires a ConversionUseCase or AppContainer")

                outcome = active_use_case.convert_batch(
                    sources=sources,
                    output_dir=output_dir,
                    extension=extension,
                    on_progress=on_progress,
                    job_context=job_context,
                    should_cancel=should_cancel,
                )

                if on_complete:
                    on_complete(outcome.successes, outcome.errors, outcome.status)
            except Exception as exc:
                logger.error("batch_service_worker_failed", extra={"event": "batch_service_worker_failed", "error": str(exc)})
                if on_complete:
                    on_complete(0, len(sources), "failed")
            finally:
                self._batch_slots.release()
                
        threading.Thread(target=_worker, daemon=True).start()
