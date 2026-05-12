import importlib
import inspect
import pkgutil
from typing import Dict, Type

from backend.app.infrastructure.common.logger import logger
from backend.app.infrastructure.conversion.base_converter import BaseConverter
from backend.app.infrastructure.conversion.exceptions import UnsupportedFormatError


KNOWN_CONVERTER_MODULES = (
    "backend.app.infrastructure.conversion.md_converter",
    "backend.app.infrastructure.conversion.txt_converter",
    "backend.app.infrastructure.conversion.docx_converter",
)


class ConverterFactory:
    _registry: Dict[str, Type[BaseConverter]] = {}
    _autodiscovered = False

    @staticmethod
    def _normalize_extension(extension: str) -> str:
        normalized = extension.strip().lower()
        if not normalized:
            return normalized
        return normalized if normalized.startswith(".") else f".{normalized}"

    @classmethod
    def register(cls, converter_cls: Type[BaseConverter]) -> None:
        instance = converter_cls()
        cls._registry[cls._normalize_extension(instance.extension)] = converter_cls

    @classmethod
    def register_module(cls, module_name: str) -> int:
        module = importlib.import_module(module_name)
        registered = 0
        for _, member in inspect.getmembers(module, inspect.isclass):
            if member is BaseConverter:
                continue
            if issubclass(member, BaseConverter):
                cls.register(member)
                registered += 1
        return registered

    @classmethod
    def _register_known_converters(cls) -> int:
        # Keep these imports explicit so frozen builds include the built-in converters.
        registered = 0

        try:
            from backend.app.infrastructure.conversion.md_converter import MarkdownConverter

            cls.register(MarkdownConverter)
            registered += 1
        except Exception as exc:
            logger.error(
                "converter_import_failed",
                extra={
                    "event": "converter_import_failed",
                    "converter": ".md",
                    "error": str(exc),
                },
            )

        try:
            from backend.app.infrastructure.conversion.txt_converter import TxtConverter

            cls.register(TxtConverter)
            registered += 1
        except Exception as exc:
            logger.error(
                "converter_import_failed",
                extra={
                    "event": "converter_import_failed",
                    "converter": ".txt",
                    "error": str(exc),
                },
            )

        try:
            from backend.app.infrastructure.conversion.docx_converter import DocxConverter

            cls.register(DocxConverter)
            registered += 1
        except Exception as exc:
            logger.error(
                "converter_import_failed",
                extra={
                    "event": "converter_import_failed",
                    "converter": ".docx",
                    "error": str(exc),
                },
            )

        return registered

    @classmethod
    def autodiscover(cls, package_name: str = "backend.app.infrastructure.conversion") -> int:
        if cls._autodiscovered:
            return 0
        discovered = cls._register_known_converters()

        for module_name in KNOWN_CONVERTER_MODULES:
            try:
                discovered += cls.register_module(module_name)
            except Exception as exc:
                logger.error(
                    "converter_module_registration_failed",
                    extra={
                        "event": "converter_module_registration_failed",
                        "error": f"{module_name}: {exc}",
                    },
                )
                continue

        try:
            package = importlib.import_module(package_name)
            for module in pkgutil.iter_modules(package.__path__, prefix=f"{package_name}."):
                if module.name.endswith("_converter") and module.name not in KNOWN_CONVERTER_MODULES:
                    discovered += cls.register_module(module.name)
        except Exception:
            # In frozen builds pkgutil can fail; explicit modules above remain the fallback.
            pass

        cls._autodiscovered = True
        return discovered

    @classmethod
    def create(cls, extension: str) -> BaseConverter:
        cls.autodiscover()
        normalized_extension = cls._normalize_extension(extension)
        if normalized_extension not in cls._registry:
            raise UnsupportedFormatError(f"Formato no soportado: {extension}")
        return cls._registry[normalized_extension]()
        
def register_all_converters() -> None:
    ConverterFactory.autodiscover("backend.app.infrastructure.conversion")
