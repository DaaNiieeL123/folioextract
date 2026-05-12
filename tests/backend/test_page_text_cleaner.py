from backend.app.infrastructure.conversion.page_text_cleaner import strip_repeated_edge_lines


def test_page_text_cleaner_removes_repeated_headers():
    pages = [
        "Sistemas Operativos 2\nContenido de la pagina 1",
        "Sistemas Operativos 2\nContenido de la pagina 2",
        "Sistemas Operativos 2\nContenido de la pagina 3",
    ]

    cleaned = strip_repeated_edge_lines(pages, edge_window=1, min_repetition=3)

    assert cleaned == [
        "Contenido de la pagina 1",
        "Contenido de la pagina 2",
        "Contenido de la pagina 3",
    ]
