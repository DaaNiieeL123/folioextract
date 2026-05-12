from pathlib import Path

from backend.app.infrastructure.conversion.structured_pdf_extractor import (
    DoclingStructuredExtractor,
    _has_unresolved_docling_images,
    try_docling_markdown,
    try_docling_text,
)


def test_structured_pdf_extractor_detects_unresolved_image_placeholders(tmp_path: Path):
    assert _has_unresolved_docling_images("texto\n<!-- image -->\n", None) is True

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "image-1.png").write_bytes(b"png")
    assert _has_unresolved_docling_images("texto\n<!-- image -->\n", artifacts_dir) is False
    assert _has_unresolved_docling_images("texto sin imagen", artifacts_dir) is False


def test_try_docling_markdown_returns_none_on_failure(monkeypatch, tmp_path: Path):
    def _boom(*args, **kwargs):
        raise RuntimeError("fallo")

    monkeypatch.setattr(DoclingStructuredExtractor, "export_markdown", _boom)

    result = try_docling_markdown(tmp_path / "input.pdf", tmp_path / "out.md")

    assert result is None


def test_try_docling_text_returns_none_on_failure(monkeypatch, tmp_path: Path):
    def _boom(*args, **kwargs):
        raise RuntimeError("fallo")

    monkeypatch.setattr(DoclingStructuredExtractor, "export_text", _boom)

    result = try_docling_text(tmp_path / "input.pdf")

    assert result is None
