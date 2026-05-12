import os
import re
import shutil
from pathlib import Path

from backend.app.infrastructure.common.file_helpers import ensure_dir
from backend.app.infrastructure.conversion.base_converter import BaseConverter, ConversionResult
from backend.app.infrastructure.conversion.exceptions import ConversionError, CorruptedPdfError
from backend.app.infrastructure.conversion.structured_pdf_extractor import try_docling_markdown


def _sanitize_path_fragment(value: str, *, fallback: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return sanitized or fallback


def _looks_like_image_export_failure(error: Exception) -> bool:
    message = str(error).lower()
    return all(marker in message for marker in ("cannot open file", ".png")) or (
        "no such file or directory" in message and ".png" in message
    )


def _markdown_covers_pdf_toc(md_text: str, toc_entries) -> bool:
    if not toc_entries:
        return True

    from backend.app.infrastructure.conversion.pdf_toc import normalize_lookup

    normalized_md = normalize_lookup(md_text)
    titled_entries = [entry for entry in toc_entries if getattr(entry, "title", "").strip()]
    if not titled_entries:
        return True

    tail_entries = titled_entries[-6:] if len(titled_entries) >= 6 else titled_entries
    matched = 0
    for entry in tail_entries:
        if normalize_lookup(entry.title) in normalized_md:
            matched += 1

    return matched >= max(1, len(tail_entries) - 1)

class MarkdownConverter(BaseConverter):
    @property
    def extension(self) -> str:
        return ".md"

    @property
    def display_name(self) -> str:
        return ".md (Markdown avanzado para IA)"

    def convert(self, source: Path, destination: Path) -> ConversionResult:
        from backend.app.infrastructure.common.logger import logger
        from backend.app.infrastructure.conversion.markdown_quality import enhance_markdown_structure
        from backend.app.infrastructure.conversion.md_fusion_repair import repair_fused_words
        from backend.app.infrastructure.conversion.pdf_toc import extract_pdf_toc_entries
        from backend.app.infrastructure.conversion.text_cleaner import clean_text
        import fitz
        import pymupdf4llm

        source = source.resolve()
        destination = destination.resolve()

        if not source.exists():
            raise CorruptedPdfError(f"El archivo no existe: {source}")
            
        try:
            document = fitz.open(str(source))
            num_pages = len(document)
            document.close()
        except Exception as e:
            raise CorruptedPdfError(f"No se pudo abrir el archivo PDF: {str(e)}")

        out_dir = destination.parent
        name_without_ext = destination.stem
        safe_image_name = _sanitize_path_fragment(f"{name_without_ext}_imagenes", fallback="imagenes")
        images_dir = out_dir / safe_image_name
        safe_source_stem = _sanitize_path_fragment(source.stem, fallback="documento")
        temp_source_path: Path | None = None
        toc_entries = extract_pdf_toc_entries(source)

        old_cwd = os.getcwd()
        try:
            ensure_dir(out_dir)
            docling_result = try_docling_markdown(
                source,
                destination,
                images_dir=images_dir,
            )
            if docling_result is not None:
                md_text = clean_text(docling_result.markdown)
                md_text = repair_fused_words(md_text, source)
                md_text = enhance_markdown_structure(md_text, toc_entries=toc_entries)
                if not _markdown_covers_pdf_toc(md_text, toc_entries):
                    logger.warning(
                        "docling_markdown_incomplete_falling_back",
                        extra={
                            "event": "docling_markdown_incomplete_falling_back",
                            "file": source.name,
                            "converter": ".md",
                        },
                    )
                else:
                    with open(destination, "w", encoding="utf-8") as f:
                        f.write(md_text)
                    return ConversionResult(
                        success=True,
                        output_path=destination,
                        pages_processed=docling_result.pages_processed,
                    )

            # pymupdf4llm usa el directorio actual y deriva nombres de imagen
            # desde el nombre del PDF; copiamos el origen a un nombre temporal
            # estable para evitar fallos con caracteres como "[" o "]".
            temp_source_path = out_dir / f"{safe_source_stem}{source.suffix.lower()}"
            shutil.copy2(source, temp_source_path)
            temp_source_ref = str(temp_source_path)

            os.chdir(str(out_dir))
            ensure_dir(images_dir)
            if hasattr(pymupdf4llm, "use_layout"):
                pymupdf4llm.use_layout(False)
            elif hasattr(pymupdf4llm, "_use_layout"):
                pymupdf4llm._use_layout = False

            try:
                md_text = pymupdf4llm.to_markdown(
                    doc=temp_source_ref,
                    write_images=True,
                    image_path=images_dir.name,
                    image_format="png",
                    margins=(0, 50, 0, 50),
                    dpi=220,
                )
            except Exception as image_error:
                if not _looks_like_image_export_failure(image_error):
                    raise
                logger.error(
                    "markdown_image_export_failed_retrying_without_images",
                    extra={
                        "event": "markdown_image_export_failed_retrying_without_images",
                        "file": source.name,
                        "converter": ".md",
                        "error": str(image_error),
                    },
                )
                md_text = pymupdf4llm.to_markdown(
                    doc=temp_source_ref,
                    write_images=False,
                    image_format="png",
                    margins=(0, 50, 0, 50),
                    dpi=220,
                )
            
            # 1. Clean invisible Unicode characters (U+200B, etc.)
            md_text = clean_text(md_text)
            
            # 2. Repair fused words using pdfplumber geometric word list as reference
            md_text = repair_fused_words(md_text, source)

            # 3. Markdown formatting only; no synthetic TOC or injected sections.
            md_text = enhance_markdown_structure(md_text, toc_entries=toc_entries)
            
            with open(destination, "w", encoding="utf-8") as f:
                f.write(f"{md_text}")
                
            return ConversionResult(success=True, output_path=destination, pages_processed=num_pages)
        except Exception as e:
            raise ConversionError(f"Error al convertir a Markdown: {str(e)}")
        finally:
            os.chdir(old_cwd)
            if temp_source_path is not None:
                try:
                    temp_source_path.unlink(missing_ok=True)
                except OSError:
                    pass


