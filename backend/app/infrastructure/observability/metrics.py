from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class _Counters:
    total_files: int = 0
    total_batches: int = 0
    successful_files: int = 0
    failed_files: int = 0
    conversion_time_ms: float = 0.0
    batch_time_ms: float = 0.0


class InMemoryMetrics:
    """Simple in-memory metrics, enough for local observability."""

    def __init__(self):
        self._counters = _Counters()
        self._lock = Lock()

    def observe_conversion(self, converter: str, duration_ms: float, success: bool) -> None:
        with self._lock:
            self._counters.total_files += 1
            self._counters.conversion_time_ms += max(duration_ms, 0)
            if success:
                self._counters.successful_files += 1
            else:
                self._counters.failed_files += 1

    def observe_batch(self, total: int, elapsed_ms: float) -> None:
        with self._lock:
            self._counters.total_batches += 1
            self._counters.batch_time_ms += max(elapsed_ms, 0)

    def snapshot(self) -> dict:
        with self._lock:
            files = self._counters.total_files
            batches = self._counters.total_batches
            avg_file_ms = (self._counters.conversion_time_ms / files) if files else 0.0
            avg_batch_ms = (self._counters.batch_time_ms / batches) if batches else 0.0
            throughput_files_per_sec = 1000.0 / avg_file_ms if avg_file_ms > 0 else 0.0
            error_rate = (self._counters.failed_files / files) if files else 0.0

            return {
                "total_files": files,
                "total_batches": batches,
                "successful_files": self._counters.successful_files,
                "failed_files": self._counters.failed_files,
                "avg_file_ms": round(avg_file_ms, 2),
                "avg_batch_ms": round(avg_batch_ms, 2),
                "throughput_files_per_sec": round(throughput_files_per_sec, 2),
                "error_rate": round(error_rate, 4),
            }


