from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Optional
import uuid


@dataclass(frozen=True)
class ConversionJobContext:
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: float = field(default_factory=perf_counter)


@dataclass(frozen=True)
class FileConversionOutcome:
    source: Path
    destination: Path
    filename: str
    converter: str
    success: bool
    duration_ms: float
    error: Optional[str] = None


@dataclass(frozen=True)
class BatchConversionOutcome:
    job_id: str
    total: int
    successes: int
    errors: int
    elapsed_ms: float
    status: str = "completed"


