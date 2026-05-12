import re


_COMMON_EXTRACTION_FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bDefni\s*ición\b", re.IGNORECASE), "Definición"),
    (re.compile(r"\bEspecífco\b", re.IGNORECASE), "Específico"),
    (re.compile(r"\bfrmas\b", re.IGNORECASE), "firmas"),
    (re.compile(r"\bclasifcación\b", re.IGNORECASE), "clasificación"),
    (re.compile(r"\bfujo\b", re.IGNORECASE), "flujo"),
    (re.compile(r"\bfnal\b", re.IGNORECASE), "final"),
    (re.compile(r"\butlizar\b", re.IGNORECASE), "utilizar"),
]


def repair_common_extraction_typos(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in _COMMON_EXTRACTION_FIXES:
        text = pattern.sub(replacement, text)
    return text


def clean_text(text: str) -> str:
    """Elimina artefactos Unicode invisibles y normaliza espacios/saltos."""
    if not text:
        return text

    for ch in ('\u200b', '\u200c', '\u200d', '\ufeff'):
        text = text.replace(ch, '')

    text = re.sub(r'\xa0', ' ', text)       # non-breaking space -> normal
    text = re.sub(r' {2,}', ' ', text)      # espacios múltiples -> uno
    
    # Trim lines first, so lines with only spaces become empty lines
    text = '\n'.join(line.strip() for line in text.splitlines())
    # Then collapse consecutive empty lines
    text = re.sub(r'\n{3,}', '\n\n', text)  # 3+ saltos -> 2

    text = repair_common_extraction_typos(text)
    return text.strip()


def page_to_clean_text(page) -> str:
    """
    Extrae texto con espacios reales, orden de lectura Y→X y detección de párrafos.

    - get_text("words") provee tokens a nivel glifo: espacio garantizado.
    - Se agrupan palabras por fila (tolerancia 4px en Y).
    - Dentro de cada fila, se detectan columnas por saltos de X grandes
      (gap > PAGE_WIDTH * 0.15) para separar texto flotante lateral.
    - Párrafos detectados por salto vertical > 1.8× interlineado mediano.
    """
    page_rect = page.rect
    page_width = page_rect.width or 595   # A4 fallback

    # Cada word: (x0, y0, x1, y1, "texto", block_no, line_no, word_no)
    words = page.get_text("words")
    if not words:
        return ""

    # ─── 1. Agrupar palabras por fila con tolerancia de 4px ───────────────
    ROW_TOLERANCE = 4
    row_map: dict = {}   # round_y → [(x0, text)]

    for w in words:
        x0, y0, _, _, text, *_ = w
        row_key = round(y0 / ROW_TOLERANCE) * ROW_TOLERANCE
        row_map.setdefault(row_key, []).append((x0, text))

    # ─── 2. Ordenar filas top-to-bottom ───────────────────────────────────
    sorted_rows = sorted(row_map.items())   # sort by y

    # ─── 3. Dentro de cada fila: ordenar por X y manejar columnas/gaps ────
    COL_GAP_RATIO = 0.15   # gap > 15% del ancho de página → nueva columna

    text_lines = []
    for _y, word_list in sorted_rows:
        word_list.sort(key=lambda w: w[0])    # left-to-right

        # Detectar saltos de columna grande dentro de la fila
        line_parts = []
        current_part = [word_list[0][1]]

        for i in range(1, len(word_list)):
            prev_x1 = word_list[i-1][0]
            curr_x0 = word_list[i][0]
            gap = curr_x0 - prev_x1
            if gap > page_width * COL_GAP_RATIO:
                # Salto de columna → terminar parte actual
                line_parts.append(' '.join(current_part))
                current_part = []
            current_part.append(word_list[i][1])

        line_parts.append(' '.join(current_part))
        # Separar partes por espacio simple (columnas → flujo de texto)
        text_lines.append('  '.join(p for p in line_parts if p))

    # ─── 4. Detectar párrafos por salto vertical ──────────────────────────
    ys = [y for y, _ in sorted_rows]
    paragraphs: list[str] = []
    current_para = [text_lines[0]]

    if len(ys) > 1:
        diffs = [ys[i+1] - ys[i] for i in range(len(ys)-1) if ys[i+1] - ys[i] > 0]
        median_diff = sorted(diffs)[len(diffs)//2] if diffs else 12
        para_threshold = median_diff * 1.8
    else:
        para_threshold = 20

    for i in range(1, len(text_lines)):
        gap = ys[i] - ys[i-1]
        if gap > para_threshold:
            paragraphs.append('\n'.join(current_para))
            current_para = []
        current_para.append(text_lines[i])

    if current_para:
        paragraphs.append('\n'.join(current_para))

    raw = '\n\n'.join(paragraphs)
    return clean_text(raw)


