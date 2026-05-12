import pytest
from unittest.mock import patch

from backend.app.infrastructure.conversion.converter_factory import ConverterFactory, register_all_converters
from backend.app.infrastructure.conversion.exceptions import UnsupportedFormatError
from backend.app.infrastructure.conversion.md_converter import MarkdownConverter
from backend.app.infrastructure.conversion.txt_converter import TxtConverter
from backend.app.infrastructure.conversion.docx_converter import DocxConverter

def test_factory_registration():
    register_all_converters()
    converter = ConverterFactory.create(".md")
    assert isinstance(converter, MarkdownConverter)
    assert converter.extension == ".md"


def test_factory_normalizes_extension_without_dot():
    register_all_converters()
    converter = ConverterFactory.create("md")
    assert isinstance(converter, MarkdownConverter)


def test_factory_normalizes_extension_case_insensitive():
    register_all_converters()
    converter = ConverterFactory.create(".MD")
    assert isinstance(converter, MarkdownConverter)

def test_factory_unsupported_format():
    with pytest.raises(UnsupportedFormatError):
        ConverterFactory.create(".unknown")


def test_factory_known_modules_still_register_when_pkgutil_fails():
    ConverterFactory._registry = {}
    ConverterFactory._autodiscovered = False

    with patch("backend.app.infrastructure.conversion.converter_factory.pkgutil.iter_modules", side_effect=RuntimeError("frozen-build")):
        assert isinstance(ConverterFactory.create(".md"), MarkdownConverter)
        assert isinstance(ConverterFactory.create(".txt"), TxtConverter)
        assert isinstance(ConverterFactory.create(".docx"), DocxConverter)


