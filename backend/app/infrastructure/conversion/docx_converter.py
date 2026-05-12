from pathlib import Path
import os
import shutil
import subprocess
import tempfile

import fitz

from backend.app.infrastructure.conversion.base_converter import BaseConverter, ConversionResult
from backend.app.infrastructure.conversion.docx_quality import (
    apply_docx_page_geometry,
    align_docx_toc_pages_with_preview,
    detect_pdf_page_profiles,
    compact_comment_guidelines,
    compact_trailing_body_whitespace,
    validate_docx_content,
)
from backend.app.infrastructure.conversion.exceptions import ConversionError, CorruptedPdfError


class DocxConverter(BaseConverter):
    """
    Convierte PDF a DOCX priorizando fidelidad real.

    En Windows, si Microsoft Word esta instalado, se intenta primero la
    conversion nativa de Word, que suele acercarse mucho mas al resultado
    que espera el usuario en documentos tipo Google Docs / Adobe.

    Si Word no esta disponible o falla, se usa pdf2docx como respaldo.
    """

    @property
    def extension(self) -> str:
        return ".docx"

    @property
    def display_name(self) -> str:
        return ".docx (Editable con alta fidelidad)"

    @staticmethod
    def _powershell_executable() -> str | None:
        return shutil.which("powershell") or shutil.which("pwsh")

    @staticmethod
    def _word_installed() -> bool:
        candidates = [
            Path(r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"),
            Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE"),
            Path(r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE"),
            Path(r"C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE"),
        ]
        return any(candidate.exists() for candidate in candidates)

    @staticmethod
    def _ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _convert_with_word_automation(self, source: Path, destination: Path) -> tuple[bool, str]:
        if os.name != "nt":
            return False, "Word automation solo esta disponible en Windows."

        powershell = self._powershell_executable()
        if not powershell:
            return False, "No se encontro PowerShell."

        if not self._word_installed():
            return False, "No se encontro Microsoft Word instalado."

        source_path = str(source.resolve())
        destination_path = str(destination.resolve())

        script = f"""
$ErrorActionPreference = 'Stop'
$source = {self._ps_quote(source_path)}
$destination = {self._ps_quote(destination_path)}
$word = $null
$document = $null
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($source)
    $document.SaveAs2($destination, 16)
    $document.Close($false)
    $document = $null
    Write-Output 'OK'
}}
finally {{
    if ($document -ne $null) {{
        try {{ $document.Close($false) }} catch {{ }}
    }}
    if ($word -ne $null) {{
        try {{ $word.Quit() }} catch {{ }}
    }}
}}
""".strip()

        result = subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=240,
        )

        if result.returncode == 0 and destination.exists():
            return True, "Conversion nativa de Word completada."

        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or "Word no genero un archivo de salida."
        return False, details

    def _export_docx_preview_with_word(self, source: Path, destination: Path) -> tuple[bool, str]:
        if os.name != "nt":
            return False, "Word automation solo esta disponible en Windows."

        powershell = self._powershell_executable()
        if not powershell:
            return False, "No se encontro PowerShell."

        if not self._word_installed():
            return False, "No se encontro Microsoft Word instalado."

        source_path = str(source.resolve())
        destination_path = str(destination.resolve())

        script = f"""
$ErrorActionPreference = 'Stop'
$source = {self._ps_quote(source_path)}
$destination = {self._ps_quote(destination_path)}
$word = $null
$document = $null
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($source, $false, $true)
    $document.ExportAsFixedFormat($destination, 17)
    $document.Close($false)
    $document = $null
    Write-Output 'OK'
}}
finally {{
    if ($document -ne $null) {{
        try {{ $document.Close($false) }} catch {{ }}
    }}
    if ($word -ne $null) {{
        try {{ $word.Quit() }} catch {{ }}
    }}
}}
""".strip()

        result = subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=240,
        )

        if result.returncode == 0 and destination.exists():
            return True, "Preview export completado."

        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or "Word no genero un preview PDF."
        return False, details

    @staticmethod
    def _count_pdf_pages(path: Path) -> int:
        pdf = fitz.open(str(path))
        try:
            return len(pdf)
        finally:
            pdf.close()

    def _refine_wordnative_pagination(self, source_pdf: Path, destination_docx: Path) -> None:
        source_pages = self._count_pdf_pages(source_pdf)
        if source_pages <= 1:
            return

        preview_path: Path | None = None
        try:
            for _ in range(2):
                with tempfile.NamedTemporaryFile(
                    suffix=".preview.pdf",
                    prefix=f"{destination_docx.stem}_",
                    dir=str(destination_docx.parent),
                    delete=False,
                ) as tmp_file:
                    preview_path = Path(tmp_file.name)

                exported, _ = self._export_docx_preview_with_word(destination_docx, preview_path)
                if not exported or not preview_path.exists():
                    break

                preview_pages = self._count_pdf_pages(preview_path)
                if preview_pages >= source_pages:
                    break

                inserted = align_docx_toc_pages_with_preview(destination_docx, source_pdf, preview_path)
                if inserted <= 0:
                    break

                try:
                    preview_path.unlink(missing_ok=True)
                except Exception:
                    pass
                preview_path = None
        finally:
            if preview_path is not None:
                try:
                    preview_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def _convert_with_pdf2docx_fallback(self, source: Path, destination: Path, page_sizes_pt: list[tuple[float, float]]) -> None:
        from pdf2docx import Converter as Pdf2DocxConverter

        converter = Pdf2DocxConverter(str(source))
        try:
            converter.convert(
                str(destination),
                start=0,
                end=None,
                quiet=True,
            )
        finally:
            converter.close()

        apply_docx_page_geometry(destination, page_sizes_pt=page_sizes_pt)

    def convert(self, source: Path, destination: Path) -> ConversionResult:
        try:
            if not source.exists():
                raise CorruptedPdfError(f"El archivo no existe: {source}")

            try:
                pdf = fitz.open(str(source))
                num_pages = len(pdf)
                if num_pages == 0:
                    raise CorruptedPdfError("El PDF no contiene paginas.")
                page_sizes_pt = [
                    (float(pdf.load_page(page_num).rect.width), float(pdf.load_page(page_num).rect.height))
                    for page_num in range(num_pages)
                ]
                page_profiles = detect_pdf_page_profiles(page_sizes_pt)
            except CorruptedPdfError:
                raise
            except Exception as exc:
                raise CorruptedPdfError(f"No se pudo abrir el PDF: {exc}") from exc
            finally:
                try:
                    pdf.close()
                except Exception:
                    pass

            converted_with_word, _word_message = self._convert_with_word_automation(source, destination)
            if not converted_with_word:
                normalized_page_sizes_pt = [
                    (profile.normalized_width_pt, profile.normalized_height_pt)
                    for profile in page_profiles
                ]
                self._convert_with_pdf2docx_fallback(destination=destination, source=source, page_sizes_pt=normalized_page_sizes_pt)
            else:
                compact_comment_guidelines(destination)
                compact_trailing_body_whitespace(destination)
                self._refine_wordnative_pagination(source, destination)

            validate_docx_content(destination)

            return ConversionResult(
                success=True,
                output_path=destination,
                pages_processed=num_pages,
            )
        except CorruptedPdfError:
            raise
        except Exception as exc:
            raise ConversionError(f"Error al convertir a DOCX: {exc}") from exc
