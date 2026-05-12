"""
Quality-aware text extraction strategy pipeline.

Architecture: Strategy Pattern — converters delegate to a pipeline of 
ExtractionStrategy objects. The pipeline tries each in order and returns
the first result that passes the quality threshold.

SOLID compliance:
- S: Each strategy has one job (extract text with a specific method)
- O: Add new strategies without modifying existing converters
- L: All strategies are substitutable implementations of BaseExtractionStrategy
- I: Thin interface — just text_from_page(page, pdf_path, page_num)
- D: Converters depend on abstract BaseExtractionStrategy, not concrete classes
"""
from __future__ import annotations
import re
from abc import ABC, abstractmethod
from pathlib import Path


class BaseExtractionStrategy(ABC):
    """Abstract contract for a single PDF text extraction strategy."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def text_from_page(self, pdf_path: Path, page_num: int) -> str:
        """Extract text from a single page. Returns empty string on failure."""
        ...


class QualityChecker:
    """
    Heuristic quality scorer for extracted text.
    Detects common extraction artefacts:
      - Long runs without spaces (fused words)
      - Suspiciously low space-to-char ratio
    Returns 0.0 (terrible) to 1.0 (perfect).
    """
    MIN_QUALITY = 0.65   # below this → try next strategy

    @staticmethod
    def score(text: str) -> float:
        if not text or len(text) < 50:
            return 1.0   # too short to judge

        words = text.split()
        if not words:
            return 0.0

        # 1. Space ratio (should be ~15-25% of chars in normal prose)
        space_ratio = text.count(' ') / len(text)
        space_score = min(space_ratio / 0.15, 1.0)

        # 2. Fused-word ratio (words that are suspiciously long with no spaces)
        long_tokens = sum(1 for w in words if len(w) > 20)
        fusion_score = max(0.0, 1.0 - (long_tokens / max(len(words), 1)) * 3)

        return (space_score * 0.4 + fusion_score * 0.6)

    @classmethod
    def is_good_enough(cls, text: str) -> bool:
        return cls.score(text) >= cls.MIN_QUALITY


# ─── Concrete Strategies ──────────────────────────────────────────────────────

class PdfPlumberStrategy(BaseExtractionStrategy):
    """
    Primary strategy: pdfplumber with layout-aware extraction.
    Best for: justified text, multi-column, tables.
    """
    @property
    def name(self) -> str:
        return "pdfplumber"

    def text_from_page(self, pdf_path: Path, page_num: int) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                page = pdf.pages[page_num]
                return page.extract_text(
                    x_tolerance=3,
                    y_tolerance=3,
                    layout=True,
                    x_density=7.25,
                    y_density=13,
                ) or ""
        except Exception:
            return ""


class PyMuPDFWordsStrategy(BaseExtractionStrategy):
    """
    Fallback strategy: PyMuPDF get_text("words") sorted by Y→X.
    Best for: simple single-column documents.
    """
    @property
    def name(self) -> str:
        return "pymupdf_words"

    def text_from_page(self, pdf_path: Path, page_num: int) -> str:
        try:
            import fitz
            from backend.app.infrastructure.conversion.text_cleaner import page_to_clean_text
            doc = fitz.open(str(pdf_path))
            page = doc.load_page(page_num)
            text = page_to_clean_text(page)
            doc.close()
            return text
        except Exception:
            return ""


class OcrRenderStrategy(BaseExtractionStrategy):
    """
    Deep fallback: renders page as image and uses EasyOCR (ML-based).
    Handles: scanned PDFs, image-based text, severely fused glyph encodings.
    Lazy-imports easyocr to avoid heavy startup cost.
    """
    _reader = None   # Singleton — model loads once

    @property
    def name(self) -> str:
        return "easyocr_ml"

    def text_from_page(self, pdf_path: Path, page_num: int) -> str:
        try:
            import fitz
            import numpy as np

            # Render page to RGB image at 2x DPI for better OCR accuracy
            doc = fitz.open(str(pdf_path))
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2, 2)         # 2× zoom → 144 DPI
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)
            img_array = img_array.reshape(pix.height, pix.width, 3)
            doc.close()

            # Lazy-load EasyOCR reader (downloads model on first use)
            if OcrRenderStrategy._reader is None:
                import easyocr
                OcrRenderStrategy._reader = easyocr.Reader(
                    ['es', 'en'],
                    gpu=False,
                    verbose=False
                )

            results = OcrRenderStrategy._reader.readtext(img_array, detail=0, paragraph=True)
            return '\n'.join(results)
        except Exception:
            return ""


class ExtractionPipeline:
    """
    Orchestrates multiple strategies with quality-gated fallback.
    Tries strategies in order; returns first result above quality threshold.
    If all strategies fail quality check, returns the best one seen.
    """
    DEFAULT_STRATEGIES: list[BaseExtractionStrategy] = [
        PdfPlumberStrategy(),
        PyMuPDFWordsStrategy(),
        OcrRenderStrategy(),     # Deep Learning: CRNN+CTC via EasyOCR (scanned PDFs)
    ]

    def __init__(self, strategies: list[BaseExtractionStrategy] | None = None):
        self._strategies = strategies or self.DEFAULT_STRATEGIES

    def extract_page(self, pdf_path: Path, page_num: int) -> tuple[str, str]:
        """
        Returns (text, strategy_name_used).
        """
        best_text = ""
        best_score = -1.0
        best_strategy = "none"

        for strategy in self._strategies:
            text = strategy.text_from_page(pdf_path, page_num)
            if not text:
                continue

            score = QualityChecker.score(text)
            if score > best_score:
                best_score = score
                best_text = text
                best_strategy = strategy.name

            if QualityChecker.is_good_enough(text):
                return text, strategy.name   # Good enough → stop early

        return best_text, best_strategy

    def extract_full_document(self, pdf_path: Path, num_pages: int) -> list[tuple[str, str]]:
        """Returns list of (page_text, strategy_used) for all pages."""
        return [self.extract_page(pdf_path, i) for i in range(num_pages)]


