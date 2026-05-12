from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import fitz

from backend.app.infrastructure.common.file_helpers import ensure_dir
from backend.app.infrastructure.common.logger import logger
from backend.app.infrastructure.conversion.plain_text_formatter import markdown_to_plain_text


@dataclass(slots=True)
class StructuredPdfTextResult:
    text: str
    pages_processed: int
    engine: str


@dataclass(slots=True)
class StructuredPdfMarkdownResult:
    markdown: str
    pages_processed: int
    engine: str
    images_exported: bool


def _count_pdf_pages(source: Path) -> int:
    pdf = fitz.open(str(source))
    try:
        return len(pdf)
    finally:
        pdf.close()


def _has_unresolved_docling_images(markdown: str, artifacts_dir: Path | None) -> bool:
    placeholder_count = markdown.count("<!-- image -->")
    if placeholder_count == 0:
        return False
    if artifacts_dir is None or not artifacts_dir.exists():
        return True
    return not any(path.is_file() for path in artifacts_dir.rglob("*"))


def _extract_pdf_visual_markdown_images(source: Path, images_dir: Path) -> list[str]:
    image_paths: list[str] = []
    pdf = fitz.open(str(source))
    try:
        for page_index, page in enumerate(pdf, start=1):
            image_blocks = [
                block
                for block in page.get_text("dict")["blocks"]
                if block.get("type") == 1 and block.get("image")
            ]
            content_blocks = []
            for block in image_blocks:
                x0, y0, x1, y1 = [float(v) for v in block["bbox"]]
                width = x1 - x0
                height = y1 - y0
                if width >= page.rect.width * 0.9 and height <= 40:
                    continue
                content_blocks.append((x0, y0, x1, y1))

            if not content_blocks:
                continue

            x0 = min(block[0] for block in content_blocks)
            y0 = min(block[1] for block in content_blocks)
            x1 = max(block[2] for block in content_blocks)
            y1 = max(block[3] for block in content_blocks)
            clip = fitz.Rect(x0, y0, x1, y1)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
            image_name = f"page-{page_index:03d}.png"
            image_path = images_dir / image_name
            pix.save(str(image_path))
            image_paths.append(image_name)
    finally:
        pdf.close()

    return image_paths


def _resolve_docling_image_placeholders(markdown: str, source: Path, images_dir: Path) -> str:
    placeholder_count = markdown.count("<!-- image -->")
    if placeholder_count == 0:
        return markdown

    ensure_dir(images_dir)
    image_names = _extract_pdf_visual_markdown_images(source, images_dir)
    if not image_names:
        raise ValueError("Docling dejo placeholders de imagen y no se pudieron reconstruir desde el PDF.")

    replacements = [f"![]({images_dir.name}/{name})" for name in image_names]
    while len(replacements) < placeholder_count:
        replacements.append(replacements[-1])

    resolved = markdown
    for replacement in replacements[:placeholder_count]:
        resolved = resolved.replace("<!-- image -->", replacement, 1)
    return resolved


class DoclingStructuredExtractor:
    _converter = None

    @classmethod
    def _get_converter(cls):
        if cls._converter is None:
            from docling.document_converter import DocumentConverter

            cls._converter = DocumentConverter()
        return cls._converter

    @classmethod
    def _convert(cls, source: Path):
        converter = cls._get_converter()
        return converter.convert(str(source.resolve()))

    @classmethod
    def export_markdown(
        cls,
        source: Path,
        destination: Path,
        *,
        images_dir: Path | None = None,
    ) -> StructuredPdfMarkdownResult:
        from docling_core.types.doc import ImageRefMode

        num_pages = _count_pdf_pages(source)
        conversion = cls._convert(source)

        ensure_dir(destination.parent)
        if images_dir is not None:
            if images_dir.exists():
                shutil.rmtree(images_dir, ignore_errors=True)
            ensure_dir(images_dir)
            conversion.document.save_as_markdown(
                destination,
                artifacts_dir=images_dir,
                image_mode=ImageRefMode.REFERENCED,
            )
            markdown = destination.read_text(encoding="utf-8")
            if _has_unresolved_docling_images(markdown, images_dir):
                markdown = _resolve_docling_image_placeholders(markdown, source, images_dir)
                destination.write_text(markdown, encoding="utf-8")
        else:
            markdown = conversion.document.export_to_markdown()
            destination.write_text(markdown, encoding="utf-8")

        unresolved_images = _has_unresolved_docling_images(markdown, images_dir)
        if unresolved_images:
            raise ValueError("Docling dejo placeholders de imagen sin resolver.")

        return StructuredPdfMarkdownResult(
            markdown=markdown,
            pages_processed=num_pages,
            engine="docling",
            images_exported=images_dir is not None and any(path.is_file() for path in images_dir.rglob("*")),
        )

    @classmethod
    def export_text(cls, source: Path) -> StructuredPdfTextResult:
        num_pages = _count_pdf_pages(source)
        conversion = cls._convert(source)
        markdown = conversion.document.export_to_markdown(image_placeholder="")
        from backend.app.infrastructure.conversion.markdown_quality import enhance_markdown_structure
        from backend.app.infrastructure.conversion.pdf_toc import extract_pdf_toc_entries

        markdown = enhance_markdown_structure(markdown, toc_entries=extract_pdf_toc_entries(source))
        text = markdown_to_plain_text(markdown)
        if not text.strip():
            raise ValueError("Docling no devolvio texto util.")

        return StructuredPdfTextResult(
            text=text,
            pages_processed=num_pages,
            engine="docling",
        )


def try_docling_markdown(
    source: Path,
    destination: Path,
    *,
    images_dir: Path | None = None,
) -> StructuredPdfMarkdownResult | None:
    try:
        return DoclingStructuredExtractor.export_markdown(source, destination, images_dir=images_dir)
    except Exception as exc:
        logger.warning(
            "docling_markdown_unavailable",
            extra={
                "event": "docling_markdown_unavailable",
                "file": source.name,
                "error": str(exc),
            },
        )
        return None


def try_docling_text(source: Path) -> StructuredPdfTextResult | None:
    try:
        return DoclingStructuredExtractor.export_text(source)
    except Exception as exc:
        logger.warning(
            "docling_text_unavailable",
            extra={
                "event": "docling_text_unavailable",
                "file": source.name,
                "error": str(exc),
            },
        )
        return None
