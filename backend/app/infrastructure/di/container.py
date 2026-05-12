from __future__ import annotations

from backend.app.infrastructure.config.settings import AppSettings
from backend.app.application.conversion_use_case import ConversionUseCase
from backend.app.infrastructure.dynamic_factory import DynamicConverterFactory
from backend.app.infrastructure.observability.metrics import InMemoryMetrics
from backend.app.infrastructure.observability.structured_logger import StructuredJobLogger


class AppContainer:
    """Simple DI container for explicit dependency wiring."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.metrics = InMemoryMetrics()
        self.job_logger = StructuredJobLogger()
        self.converter_factory = DynamicConverterFactory()
        self.conversion_use_case = ConversionUseCase(
            factory=self.converter_factory,
            metrics=self.metrics,
            logger=self.job_logger,
            max_retries=1,
        )


