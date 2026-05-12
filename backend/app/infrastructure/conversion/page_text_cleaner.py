from __future__ import annotations

from collections import Counter


def _page_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def strip_repeated_edge_lines(
    page_texts: list[str],
    *,
    edge_window: int = 3,
    min_repetition: int = 3,
) -> list[str]:
    """Remove page-edge lines that repeat across many pages, such as headers and footers."""
    pages = [_page_lines(text) for text in page_texts]
    if not pages:
        return []

    edge_counter: Counter[str] = Counter()
    for lines in pages:
        edge_candidates = lines[:edge_window] + lines[-edge_window:]
        for line in set(edge_candidates):
            if 2 <= len(line) <= 120:
                edge_counter[line] += 1

    repeated = {line for line, count in edge_counter.items() if count >= min_repetition}
    if not repeated:
        return page_texts

    cleaned_pages: list[str] = []
    for lines in pages:
        start = 0
        end = len(lines)
        while start < end and lines[start] in repeated:
            start += 1
        while end > start and lines[end - 1] in repeated:
            end -= 1
        cleaned_pages.append("\n".join(lines[start:end]).strip())

    return cleaned_pages
