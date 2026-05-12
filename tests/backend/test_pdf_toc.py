from backend.app.infrastructure.conversion.pdf_toc import TocEntry, clean_toc_title, filter_visible_toc_entries


def test_pdf_toc_clean_title_restores_spaces():
    assert clean_toc_title("1.1.Valor") == "1.1. Valor"
    assert clean_toc_title("2.Enunciado de la Práctica") == "2. Enunciado de la Práctica"
    assert clean_toc_title("A.Métricas del sistema") == "A. Métricas del sistema"


def test_pdf_toc_filters_entries_before_visible_index():
    entries = [
        TocEntry(level=1, title="Portada", page=1),
        TocEntry(level=1, title="Introduccion", page=2),
        TocEntry(level=1, title="Marco", page=3),
    ]

    filtered = filter_visible_toc_entries(entries, index_page=2)

    assert filtered == [TocEntry(level=1, title="Marco", page=3)]
