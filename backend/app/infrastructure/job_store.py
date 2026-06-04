from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from time import time
from typing import Any

_logger = logging.getLogger("FolioExtract")


class FileJobStore:
    """Simple file-based persistence for conversion jobs."""

    def __init__(self, file_path: Path):
        self._path = file_path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_all([])

    def create_job(
        self,
        *,
        job_id: str,
        total: int,
        extension: str,
        output_dir: str,
        files: list[str],
        source_paths: list[str] | None = None,
        status: str = "running",
    ) -> None:
        with self._lock:
            jobs = self._read_all()
            normalized_sources = source_paths or files
            file_items = [
                {
                    "filename": file_name,
                    "source_path": normalized_sources[index] if index < len(normalized_sources) else file_name,
                    "output_path": None,
                    "status": "pending",
                    "error": None,
                }
                for index, file_name in enumerate(files)
            ]
            jobs.insert(
                0,
                {
                    "job_id": job_id,
                    "status": status,
                    "total": total,
                    "processed": 0,
                    "successes": 0,
                    "errors": 0,
                    "extension": extension,
                    "output_dir": output_dir,
                    "files": files,
                    "source_paths": normalized_sources,
                    "file_items": file_items,
                    "started_at": time(),
                    "finished_at": None,
                    "last_file": None,
                    "last_error": None,
                    "elapsed_ms": None,
                },
            )
            self._write_all(jobs)

    def mark_running(self, *, job_id: str) -> None:
        with self._lock:
            jobs = self._read_all()
            job = self._find_job(jobs, job_id)
            if job is None:
                return
            job["status"] = "running"
            self._write_all(jobs)

    def mark_interrupted_unfinished(self) -> int:
        with self._lock:
            jobs = self._read_all()
            changed = 0
            for job in jobs:
                if job.get("status") not in {"queued", "running"}:
                    continue
                job["status"] = "interrupted"
                job["finished_at"] = time()
                file_items = job.get("file_items") or []
                for item in file_items:
                    if item.get("status") == "pending":
                        item["status"] = "interrupted"
                        if not item.get("error"):
                            item["error"] = "job_interrupted"
                changed += 1
            if changed:
                self._write_all(jobs)
            return changed

    def request_cancel(self, *, job_id: str) -> None:
        with self._lock:
            jobs = self._read_all()
            job = self._find_job(jobs, job_id)
            if job is None:
                return
            if job.get("status") in {"queued", "running"}:
                job["cancel_requested"] = True
                self._write_all(jobs)

    def update_progress(
        self,
        *,
        job_id: str,
        current: int,
        filename: str,
        is_error: bool,
        error_msg: str | None,
        output_path: str | None = None,
    ) -> None:
        with self._lock:
            jobs = self._read_all()
            job = self._find_job(jobs, job_id)
            if job is None:
                return
            job["processed"] = current
            job["last_file"] = filename
            file_items = job.get("file_items") or []
            for item in file_items:
                if item.get("filename") == filename:
                    item["status"] = "failed" if is_error else "completed"
                    item["error"] = (error_msg or "unknown_error") if is_error else None
                    item["output_path"] = output_path
                    break
            if is_error:
                job["errors"] = int(job.get("errors", 0)) + 1
                job["last_error"] = error_msg or "unknown_error"
            else:
                job["successes"] = int(job.get("successes", 0)) + 1
            self._write_all(jobs)

    def complete_job(self, *, job_id: str, successes: int, errors: int, elapsed_ms: float, status: str = "completed") -> None:
        with self._lock:
            jobs = self._read_all()
            job = self._find_job(jobs, job_id)
            if job is None:
                return
            job["status"] = status
            job["successes"] = successes
            job["errors"] = errors
            job["processed"] = successes + errors
            job["elapsed_ms"] = round(elapsed_ms, 2)
            job["finished_at"] = time()
            file_items = job.get("file_items") or []
            for item in file_items:
                if item.get("status") == "pending":
                    if status == "failed":
                        item["status"] = "failed"
                        if not item.get("error"):
                            item["error"] = "not_processed"
                    elif status == "canceled":
                        item["status"] = "canceled"
                        if not item.get("error"):
                            item["error"] = "job_canceled"
                    elif status == "interrupted":
                        item["status"] = "interrupted"
                        if not item.get("error"):
                            item["error"] = "job_interrupted"
                    else:
                        item["status"] = "completed"
            job["cancel_requested"] = False
            self._write_all(jobs)

    def get_retryable_sources(self, job_id: str) -> list[str]:
        with self._lock:
            jobs = self._read_all()
            job = self._find_job(jobs, job_id)
            if job is None:
                return []
            file_items = job.get("file_items") or []
            retryable_statuses = {"failed", "pending", "canceled", "interrupted"}
            return [
                str(item.get("source_path"))
                for item in file_items
                if item.get("status") in retryable_statuses and item.get("source_path")
            ]

    def list_jobs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return self._read_all()[:limit]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            jobs = self._read_all()
            return self._find_job(jobs, job_id)

    def _find_job(self, jobs: list[dict[str, Any]], job_id: str) -> dict[str, Any] | None:
        for job in jobs:
            if job.get("job_id") == job_id:
                return job
        return None

    def _read_all(self) -> list[dict[str, Any]]:
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            return []
        except Exception as exc:
            _logger.warning("Failed to read jobs from %s: %s", self._path, exc)
            return []

    def _write_all(self, jobs: list[dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(jobs, ensure_ascii=True, indent=2), encoding="utf-8")
