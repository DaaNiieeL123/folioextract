from __future__ import annotations

import json
import logging
import sys
from typing import Optional

from backend.app.domain.entities import ConversionJobContext


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("job_id", "file", "converter", "event", "error", "elapsed_ms", "total", "successes", "errors", "output_dir", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=True)


class StructuredJobLogger:
    def __init__(self, name: str = "FolioExtract"):
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            self._logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JsonFormatter())
            self._logger.addHandler(handler)

    def info(
        self,
        message: str,
        *,
        job: ConversionJobContext,
        file_name: Optional[str] = None,
        converter: Optional[str] = None,
        **extra: object,
    ) -> None:
        self._logger.info(message, extra={"event": message, "job_id": job.job_id, "file": file_name, "converter": converter, **extra})

    def error(
        self,
        message: str,
        *,
        job: ConversionJobContext,
        file_name: Optional[str] = None,
        converter: Optional[str] = None,
        **extra: object,
    ) -> None:
        self._logger.error(message, extra={"event": message, "job_id": job.job_id, "file": file_name, "converter": converter, **extra})


