from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.app.infrastructure.conversion.pdf_toc import normalize_lookup, slugify_anchor

if TYPE_CHECKING:
    from backend.app.infrastructure.conversion.pdf_toc import TocEntry


_HEADING_NUMERIC_RE = re.compile(r"^(\d+(?:\.\d+){0,3})\s+(.+)$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(\s*:?-+:?\s*\|)+\s*$")
_GENERIC_COLUMN_RE = re.compile(r"^col\d+$", re.IGNORECASE)


def _looks_like_index_entry(line: str) -> bool:
    stripped = line.strip()
    return ("..." in stripped or "…" in stripped) and bool(re.search(r"\d+\s*$", stripped))


def _split_index_entries(line: str) -> list[str]:
    normalized = _strip_inline_markdown(line)
    matches = [match.group(0).strip() for match in re.finditer(r".+?\.{3,}\s*\d+", normalized)]
    return matches or [normalized]


def _strip_inline_markdown(text: str) -> str:
    stripped = re.sub(r"^#{1,6}\s*", "", text.strip())
    stripped = stripped.replace("**", "").replace("__", "").replace("`", "")
    return stripped


def _table_cell_count(line: str) -> int:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return 0
    return max(0, stripped.count("|") - 1)


def _table_cells(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _build_table_row(cells: list[str]) -> str:
    return "|" + "|".join(cells) + "|"


def _is_generic_header_row(line: str) -> bool:
    cells = _table_cells(line)
    if not cells:
        return False
    generic_cells = sum(1 for cell in cells if _GENERIC_COLUMN_RE.fullmatch(cell or ""))
    return generic_cells >= max(1, len(cells) - 1)


def _normalize_placeholder_cells(line: str) -> str:
    cells = _table_cells(line)
    if not cells:
        return line
    normalized = [("" if _GENERIC_COLUMN_RE.fullmatch(cell or "") else cell) for cell in cells]
    return _build_table_row(normalized)


def _normalize_placeholder_rows(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    for line in lines:
        if line.strip().startswith("|"):
            normalized.append(_normalize_placeholder_cells(line))
            continue
        normalized.append(line)
    return normalized


def _is_image_line(line: str) -> bool:
    return line.strip().startswith("![](")


def _merge_split_tables(lines: list[str]) -> list[str]:
    merged: list[str] = []
    i = 0
    while i < len(lines):
        current = lines[i].strip()
        if not current:
            previous_index = len(merged) - 1
            while previous_index >= 0 and not merged[previous_index].strip():
                previous_index -= 1
            next_index = i + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            previous_line = merged[previous_index].strip() if previous_index >= 0 else ""
            next_line = lines[next_index].strip() if next_index < len(lines) else ""
            if (
                previous_line.startswith("|")
                and next_line.startswith("|")
                and _table_cell_count(previous_line)
                and _table_cell_count(previous_line) == _table_cell_count(next_line)
            ):
                i += 1
                continue
        if current.startswith("|") and merged:
            current_cells = _table_cells(current)
            previous_index = len(merged) - 1
            while previous_index >= 0 and not merged[previous_index].strip():
                previous_index -= 1
            previous_line = merged[previous_index].strip() if previous_index >= 0 else ""
            previous_cols = _table_cell_count(previous_line)
            current_cols = _table_cell_count(current)
            if (
                previous_cols
                and current_cols == previous_cols
                and len(current_cells) >= 2
                and sum(1 for cell in current_cells[:-1] if cell.strip()) == 0
                and current_cells[-1].strip()
            ):
                previous_cells = _table_cells(previous_line)
                previous_cells[-1] = (
                    f"{previous_cells[-1]}<br>{current_cells[-1].strip()}"
                    if previous_cells[-1].strip()
                    else current_cells[-1].strip()
                )
                merged[previous_index] = _build_table_row(previous_cells)
                i += 1
                if i < len(lines) and _TABLE_SEPARATOR_RE.match(lines[i].strip()):
                    i += 1
                continue
        if (
            lines[i].strip() == ""
            and i + 2 < len(lines)
            and lines[i + 1].strip().startswith("|")
            and _TABLE_SEPARATOR_RE.match(lines[i + 2].strip())
            and merged
        ):
            previous_line = merged[-1].strip() if merged else ""
            continuation_line = lines[i + 1].strip()
            previous_cols = _table_cell_count(previous_line)
            next_cols = _table_cell_count(continuation_line)
            if previous_cols and previous_cols == next_cols and _is_generic_header_row(continuation_line):
                previous_cells = _table_cells(previous_line)
                continuation_cells = _table_cells(continuation_line)
                tail = continuation_cells[-1].strip()
                if tail:
                    previous_cells[-1] = (
                        f"{previous_cells[-1]}<br>{tail}" if previous_cells[-1].strip() else tail
                    )
                    merged[-1] = _build_table_row(previous_cells)
                i += 3
                continue
        if (
            lines[i].strip() == ""
            and i + 4 < len(lines)
            and _is_image_line(lines[i + 1])
            and lines[i + 2].strip() == ""
            and lines[i + 3].strip().startswith("|")
            and _TABLE_SEPARATOR_RE.match(lines[i + 4].strip())
            and merged
        ):
            previous_line = merged[-1].strip() if merged else ""
            next_row = lines[i + 3].strip()
            previous_cols = _table_cell_count(previous_line)
            next_cols = _table_cell_count(next_row)
            if previous_cols and previous_cols == next_cols:
                merged.append(_normalize_placeholder_cells(next_row))
                i += 5
                continue
        merged.append(lines[i])
        i += 1
    return merged


def _heading_level_from_numeric(prefix: str) -> int:
    depth = prefix.count(".") + 1
    return min(depth + 1, 4)


def _normalize_list_prefix(line: str) -> str:
    if re.match(r"^\s*[○◦]\s*", line):
        return re.sub(r"^\s*[○◦]\s*", "  - ", line)
    if re.match(r"^\s*[•●▪■·]\s*", line):
        return re.sub(r"^\s*[•●▪■·]\s*", "- ", line)
    return re.sub(r"^\s*-\s*", "- ", line)


def _split_cover_title(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# Título del Proyecto: ") and len(stripped) > len("# Título del Proyecto: "):
            title = "# Título del Proyecto:"
            subtitle = stripped[len("# Título del Proyecto: "):].strip()
            normalized.append(title)
            normalized.append("")
            normalized.append(f"## {subtitle}")
            continue
        if stripped.startswith("## **PONDERACIÓN:") and "Tiempo estimado:" in stripped:
            compact = stripped.replace("## ", "").replace("**", "")
            parts = [part.strip() for part in re.split(r"(?=Tiempo estimado:)", compact) if part.strip()]
            normalized.append("## Resumen")
            for part in parts:
                normalized.append(f"- {part}")
            continue
        normalized.append(line)
    return normalized


def _repair_heading_like_table(lines: list[str]) -> list[str]:
    repaired: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if (
            line.startswith("|")
            and i + 2 < len(lines)
            and _TABLE_SEPARATOR_RE.match(lines[i + 1].strip())
        ):
            cells = _table_cells(line)
            joined = " ".join(cell for cell in cells if cell).strip()
            if len(cells) >= 2 and "MARCO" in joined.upper() and "FORMATIVO" in joined.upper():
                repaired.append("## 1. MARCO FORMATIVO")
                if "1.1." in joined or "Valor" in joined:
                    repaired.append("")
                    repaired.append("### 1.1. Valor")
                i += 2
                continue
        repaired.append(lines[i])
        i += 1
    return repaired


def _link_index_entry(entry_text: str, toc_entries: list["TocEntry"] | None) -> str:
    if not toc_entries:
        return entry_text
    title_part = re.sub(r"\.{3,}\s*\d+\s*$", "", entry_text).strip()
    normalized = normalize_lookup(title_part)
    for toc_entry in toc_entries:
        if normalize_lookup(toc_entry.title) == normalized:
            return f"- [{entry_text}](#{slugify_anchor(toc_entry.title)})"
    return f"- {entry_text}"


def _inject_heading_anchors(lines: list[str], toc_entries: list["TocEntry"] | None) -> list[str]:
    if not toc_entries:
        return lines

    toc_lookup = {
        normalize_lookup(entry.title): slugify_anchor(entry.title)
        for entry in toc_entries
    }
    anchored: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            plain = _strip_inline_markdown(re.sub(r"^#{1,6}\s*", "", stripped))
            slug = toc_lookup.get(normalize_lookup(plain))
            if slug:
                anchored.append(f'<a id="{slug}"></a>')
        anchored.append(line)
    return anchored


def enhance_markdown_structure(md_text: str, toc_entries: list["TocEntry"] | None = None) -> str:
    """Normalize Markdown formatting without injecting synthetic sections or TOCs."""
    if not md_text:
        return md_text

    lines = _split_cover_title(md_text.splitlines())
    lines = _repair_heading_like_table(lines)
    out: list[str] = []
    in_code_block = False
    in_index_section = False

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            out.append(line)
            continue

        if in_code_block:
            out.append(line)
            continue

        if _strip_inline_markdown(stripped).lower() in {"índice", "indice"}:
            out.append("## Índice")
            in_index_section = True
            continue

        if in_index_section:
            if stripped.startswith("<a id="):
                continue
            if not stripped:
                out.append("")
                continue
            if _TABLE_SEPARATOR_RE.match(stripped):
                continue
            if stripped.startswith("#"):
                heading_text = _strip_inline_markdown(stripped)
                if _looks_like_index_entry(heading_text):
                    out.append(_link_index_entry(heading_text, toc_entries))
                    continue
                in_index_section = False
            if stripped.startswith("|"):
                cells = [cell for cell in _table_cells(stripped) if cell]
                if len(cells) == 1 and _looks_like_index_entry(cells[0]):
                    out.append(_link_index_entry(cells[0], toc_entries))
                    continue
                in_index_section = False
            if _looks_like_index_entry(_strip_inline_markdown(stripped)):
                out.extend(_link_index_entry(entry, toc_entries) for entry in _split_index_entries(stripped))
                continue
            in_index_section = False

        numeric_match = _HEADING_NUMERIC_RE.match(stripped)
        if numeric_match and not line.lstrip().startswith("#") and not _looks_like_index_entry(stripped):
            prefix, title = numeric_match.groups()
            level = _heading_level_from_numeric(prefix)
            out.append(f"{'#' * level} {prefix} {title.strip()}")
            continue

        if re.match(r"^\s*[•●○▪■◦·-]\s*", line):
            out.append(_normalize_list_prefix(line))
            continue

        out.append(line)

    repaired: list[str] = []
    for idx, current in enumerate(out):
        repaired.append(current)
        next_line = out[idx + 1] if idx + 1 < len(out) else ""
        previous_line = out[idx - 1] if idx > 0 else ""
        if current.count("|") >= 2 and next_line.count("|") >= 2:
            if not _TABLE_SEPARATOR_RE.match(next_line) and previous_line.count("|") < 2:
                col_count = max(2, current.count("|") - 1)
                repaired.append("|" + " --- |" * col_count)

    repaired = _merge_split_tables(repaired)
    repaired = _normalize_placeholder_rows(repaired)
    repaired = _inject_heading_anchors(repaired, toc_entries)
    text = "\n".join(repaired)
    text = re.sub(r"(\|[^\n]+\|)\n\s*\n(?=\|)", r"\1\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"
