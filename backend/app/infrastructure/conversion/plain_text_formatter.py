from __future__ import annotations

import re


_BULLET_MARKERS = "•●○▪■◦"
_INLINE_LIST_SPLIT_RE = re.compile(rf"\s+(?=(?:[{re.escape(_BULLET_MARKERS)}]\s*|\d+[.)]\s+|[A-Za-z][.)]\s+))")
_MARKDOWN_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*$")
_LABEL_LINE_RE = re.compile(r"^[A-ZÁÉÍÓÚÜÑa-záéíóúüñ][^:]{0,48}:\s+\S")


def _split_toc_entries(line: str) -> list[str]:
    normalized = re.sub(r"\s{2,}", " ", line.strip())
    matches = [match.group(0).strip() for match in re.finditer(r".+?\.{3,}\s*\d+", normalized)]
    return matches or [normalized]


def _looks_like_toc_line(line: str) -> bool:
    stripped = line.strip()
    return ("..." in stripped or "…" in stripped) and bool(re.search(r"\d+\s*$", stripped))


def _looks_like_structured_layout(lines: list[str]) -> bool:
    nonempty = [line.strip() for line in lines if line.strip()]
    if len(nonempty) < 8:
        return False
    avg_len = sum(len(line) for line in nonempty) / max(len(nonempty), 1)
    short_lines = sum(1 for line in nonempty if len(line) <= 45)
    heading_like = sum(
        1
        for line in nonempty
        if re.match(r"^(?:\d+(?:\.\d+)*\.?|[A-Z]\.|[A-ZÁÉÍÓÚÜÑ][^a-z]{4,}|Tema|Descripción|Área|Puntos|No\.)", line)
    )
    return avg_len <= 65 and (short_lines >= len(nonempty) * 0.45 or heading_like >= 4)


def _looks_like_labeled_line(line: str) -> bool:
    return bool(_LABEL_LINE_RE.match(line.strip()))


def _table_cells(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _convert_markdown_table_block(lines: list[str]) -> list[str]:
    rows = [_table_cells(line) for line in lines if line.strip().startswith("|")]
    rows = [row for row in rows if row and any(cell.strip("-: ") for cell in row)]
    if not rows:
        return []

    header = rows[0]
    body = rows[1:]

    if len(header) == 1 and ("..." in header[0] or "…" in header[0]):
        return [header[0], *(" ".join(cell for cell in row if cell) for row in body)]

    if len(header) >= 2 and any(cell for cell in header):
        output: list[str] = []
        for row in body:
            pairs: list[str] = []
            for index, cell in enumerate(row):
                cell = cell.replace("<br>", " ").strip()
                if not cell:
                    continue
                label = header[index] if index < len(header) else ""
                if label and label != cell:
                    pairs.append(f"{label}: {cell}")
                else:
                    pairs.append(cell)
            if pairs:
                output.extend(pairs)
                output.append("")
        if output and output[-1] == "":
            output.pop()
        return output

    return [" ".join(cell for cell in row if cell) for row in rows if any(cell for cell in row)]


def markdown_to_plain_text(text: str) -> str:
    if not text:
        return text

    text = text.replace("\r\n", "\n")
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = text.replace("<!-- image -->", "")
    text = re.sub(r"<a id=\"[^\"]+\"></a>", "", text)
    text = re.sub(r"\[([^\]]+)\]\(#.*?\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "").replace("`", "")

    source_lines = text.splitlines()
    output_lines: list[str] = []
    buffer: list[str] = []

    def flush_table() -> None:
        nonlocal buffer
        if buffer:
            output_lines.extend(_convert_markdown_table_block(buffer))
            buffer = []

    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            buffer.append(line)
            continue
        if buffer:
            if _MARKDOWN_TABLE_SEPARATOR_RE.match(stripped):
                buffer.append(line)
                continue
            flush_table()
        output_lines.append(line)

    flush_table()

    cleaned = "\n".join(output_lines)
    cleaned = cleaned.replace("<br>", "\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"


def normalize_plain_text(text: str) -> str:
    """Improve plain-text readability by fixing wraps, list markers, and noisy spacing."""
    if not text:
        return text

    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    expanded_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            expanded_lines.append("")
            continue
        if line.count(".") >= 6 and any(ch.isdigit() for ch in line):
            expanded_lines.extend(_split_toc_entries(line))
            continue
        parts = [part.strip() for part in _INLINE_LIST_SPLIT_RE.split(line.strip()) if part.strip()]
        expanded_lines.extend(parts or [line.strip()])

    preserve_layout = _looks_like_structured_layout(expanded_lines)

    if preserve_layout:
        preserved: list[str] = []
        for line in expanded_lines:
            stripped = line.strip()
            if not stripped:
                if preserved and preserved[-1] != "":
                    preserved.append("")
                continue
            if re.match(rf"^[{re.escape(_BULLET_MARKERS)}-]\s*", stripped):
                preserved.append(re.sub(rf"^[{re.escape(_BULLET_MARKERS)}-]\s*", "- ", stripped))
                continue
            preserved.append(re.sub(r"\s{2,}", " ", stripped))
        normalized = "\n".join(preserved)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", normalized)
        return normalized.strip() + "\n"

    output: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        joined = " ".join(item.strip() for item in paragraph if item.strip())
        joined = re.sub(r"\s{2,}", " ", joined).strip()
        if joined:
            output.append(joined)
        paragraph.clear()

    for line in expanded_lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            if output and output[-1] != "":
                output.append("")
            continue

        if re.match(rf"^[{re.escape(_BULLET_MARKERS)}-]\s*", stripped):
            flush_paragraph()
            output.append(re.sub(rf"^[{re.escape(_BULLET_MARKERS)}-]\s*", "- ", stripped))
            continue

        if _looks_like_labeled_line(stripped):
            flush_paragraph()
            output.append(stripped)
            continue

        if _looks_like_toc_line(stripped):
            flush_paragraph()
            output.append(stripped)
            continue

        if re.match(r"^(?:\d+|[A-Za-z])[.)]\s+", stripped):
            flush_paragraph()
            output.append(stripped)
            continue

        paragraph.append(stripped)

    flush_paragraph()

    normalized = "\n".join(output)
    final_lines: list[str] = []
    for line in normalized.splitlines():
        if _looks_like_toc_line(line):
            final_lines.extend(_split_toc_entries(line))
            continue
        final_lines.append(line)
    normalized = "\n".join(final_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", normalized)
    return normalized.strip() + "\n"
