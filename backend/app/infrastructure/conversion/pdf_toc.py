from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


_CONTROL_CHARS_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")


@dataclass(frozen=True)
class TocEntry:
    level: int
    title: str
    page: int


def clean_toc_title(title: str) -> str:
    value = _CONTROL_CHARS_RE.sub("", title or "")
    value = value.replace("\t", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"^((?:\d+\.)+\d+|\d+)\.(?=[^\d\s])", r"\1. ", value)
    value = re.sub(r"^([A-Z])\.(?=[^\s])", r"\1. ", value)
    value = re.sub(r":(?=\S)", ": ", value)
    return value.strip().strip(".")


def normalize_lookup(value: str) -> str:
    cleaned = clean_toc_title(value)
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def slugify_anchor(value: str) -> str:
    normalized = normalize_lookup(value)
    slug = normalized.replace(" ", "-")
    return slug.strip("-") or "seccion"


def find_index_page_number(source: Path) -> int | None:
    document = fitz.open(str(source))
    try:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text")
            if re.search(r"\b(índice|indice|table of contents|contents)\b", text, flags=re.IGNORECASE):
                return page_number
        return None
    finally:
        document.close()


def filter_visible_toc_entries(entries: list[TocEntry], index_page: int | None) -> list[TocEntry]:
    if index_page is None:
        return entries

    filtered = [entry for entry in entries if entry.page > index_page]
    return filtered or entries


def extract_pdf_toc_entries(source: Path) -> list[TocEntry]:
    document = fitz.open(str(source))
    try:
        entries: list[TocEntry] = []
        for level, title, page, *_rest in document.get_toc(simple=False):
            cleaned_title = clean_toc_title(str(title))
            if not cleaned_title or page <= 0:
                continue
            entries.append(TocEntry(level=int(level), title=cleaned_title, page=int(page)))
        return filter_visible_toc_entries(entries, find_index_page_number(source))
    finally:
        document.close()
