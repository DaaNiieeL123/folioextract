from pathlib import Path
from typing import Protocol, Optional

from backend.app.infrastructure.conversion.base_converter import BaseConverter, ConversionResult
from .entities import ConversionJobContext


class ConverterFactoryPort(Protocol):
    def create(self, extension: str) -> BaseConverter:
        ...


class MetricsPort(Protocol):
    def observe_conversion(self, converter: str, duration_ms: float, success: bool) -> None:
        ...

    def observe_batch(self, total: int, elapsed_ms: float) -> None:
        ...

    def snapshot(self) -> dict:
        ...


class JobLoggerPort(Protocol):
    def info(self, message: str, *, job: ConversionJobContext, file_name: Optional[str] = None, converter: Optional[str] = None, **extra: object) -> None:
        ...

    def error(self, message: str, *, job: ConversionJobContext, file_name: Optional[str] = None, converter: Optional[str] = None, **extra: object) -> None:
        ...


