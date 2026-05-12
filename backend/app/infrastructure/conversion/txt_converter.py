import pdfplumber
import fitz
from pathlib import Path
from backend.app.infrastructure.conversion.base_converter import BaseConverter, ConversionResult
from backend.app.infrastructure.conversion.exceptions import CorruptedPdfError, ConversionError
from backend.app.infrastructure.conversion.text_cleaner import clean_text
from backend.app.infrastructure.conversion.extraction_pipeline import ExtractionPipeline
from backend.app.infrastructure.conversion.page_text_cleaner import strip_repeated_edge_lines
from backend.app.infrastructure.conversion.plain_text_formatter import normalize_plain_text
from backend.app.infrastructure.conversion.structured_pdf_extractor import try_docling_text


class TxtConverter(BaseConverter):
    """
    Convierte PDF a texto plano usando el pipeline de extracción inteligente.
    
    Orden de estrategias:
      1. pdfplumber (layout-aware, mejor para texto justificado)
      2. PyMuPDF words (fallback geométrico rápido)
      3. EasyOCR ML (fallback pesado: PDFs escaneados o glifos corruptos)
    
    La selección de estrategia es automática basada en un quality score.
    """

    _pipeline = ExtractionPipeline()   # Singleton — compartido entre conversiones

    @property
    def extension(self) -> str:
        return ".txt"

    @property
    def display_name(self) -> str:
        return ".txt (Texto plano sin formato)"

    def convert(self, source: Path, destination: Path) -> ConversionResult:
        if not source.exists():
            raise CorruptedPdfError(f"El archivo no existe: {source}")

        try:
            doc = fitz.open(str(source))
            num_pages = len(doc)
            doc.close()
        except Exception as e:
            raise CorruptedPdfError(f"No se pudo abrir el PDF: {str(e)}")

        try:
            docling_result = try_docling_text(source)
            if docling_result is not None:
                text = normalize_plain_text(clean_text(docling_result.text))
                with open(destination, "w", encoding="utf-8") as f:
                    f.write(text)
                    if not text.endswith("\n"):
                        f.write("\n")
                return ConversionResult(
                    success=True,
                    output_path=destination,
                    pages_processed=docling_result.pages_processed
                )

            # The pipeline extracts text using various strategies, including pdfplumber.
            # The `pages_data` already contains the extracted text for each page.
            pages_data = self._pipeline.extract_full_document(source, num_pages)
            cleaned_pages = [clean_text(text) for text, _strategy in pages_data]
            cleaned_pages = strip_repeated_edge_lines(cleaned_pages)

            with open(destination, "w", encoding="utf-8") as f:
                for page_num, text in enumerate(cleaned_pages):
                    text = normalize_plain_text(text)
                    if page_num > 0:
                        f.write("\n\n")
                    f.write(text)
                    if not text.endswith("\n"):
                        f.write("\n")

            return ConversionResult(
                success=True,
                output_path=destination,
                pages_processed=num_pages
            )
        except Exception as e:
            raise ConversionError(f"Error al escribir el archivo TXT: {str(e)}")


