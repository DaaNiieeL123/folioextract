from backend.app.infrastructure.conversion.plain_text_formatter import normalize_plain_text


def test_plain_text_formatter_fixes_hyphenated_breaks_and_spacing():
    raw = "Docu-\nmento   con  ruido\n\nLinea 2"
    result = normalize_plain_text(raw)

    assert "Documento con ruido" in result
    assert "  " not in result


def test_plain_text_formatter_keeps_numbered_list_lines():
    raw = "1) item uno\n2) item dos\n\nParrafo\ncontinuado"
    result = normalize_plain_text(raw)

    assert "1) item uno" in result
    assert "2) item dos" in result
    assert "Parrafo continuado" in result


def test_plain_text_formatter_splits_inline_bullet_markers():
    raw = "●primer punto ●segundo punto\n\nTexto\ncontinuado"
    result = normalize_plain_text(raw)

    assert "- primer punto" in result
    assert "- segundo punto" in result
    assert "Texto continuado" in result


def test_plain_text_formatter_preserves_dense_structured_layout():
    raw = "Tema\nDescripción\nCumple\n(Sí/No)\n\nFila 1\nFila 2\nFila 3\nFila 4\nFila 5\nFila 6"
    result = normalize_plain_text(raw)

    assert "Tema\nDescripción\nCumple" in result
    assert "Fila 1\nFila 2" in result
