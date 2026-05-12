from backend.app.infrastructure.conversion.base_converter import BaseConverter
from backend.app.infrastructure.conversion.converter_factory import ConverterFactory, register_all_converters


class DynamicConverterFactory:
    """Infrastructure adapter for converter creation with dynamic registration."""

    def __init__(self):
        register_all_converters()

    def create(self, extension: str) -> BaseConverter:
        return ConverterFactory.create(extension)


