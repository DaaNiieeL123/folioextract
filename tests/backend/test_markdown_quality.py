from backend.app.infrastructure.conversion.markdown_quality import enhance_markdown_structure


def test_markdown_quality_adds_numeric_headings_and_single_table_separator():
    raw = """1 Introduccion
• item uno
| Col A | Col B |
| val1 | val2 |
| val3 | val4 |
"""
    result = enhance_markdown_structure(raw)

    assert "## 1 Introduccion" in result
    assert "- item uno" in result
    assert result.count("| --- | --- |") == 1


def test_markdown_quality_preserves_existing_heading():
    raw = "# Titulo Principal\n\nContenido"
    result = enhance_markdown_structure(raw)
    assert result.startswith("# Titulo Principal")


def test_markdown_quality_does_not_inject_synthetic_toc():
    raw = """# Documento

## Seccion Uno
Texto

## Seccion Dos
Texto
"""
    result = enhance_markdown_structure(raw)

    assert "## Tabla de contenido" not in result
    assert "## Seccion Uno" in result
    assert "## Seccion Dos" in result


def test_markdown_quality_preserves_existing_index_lines():
    raw = """Índice

1. Seccion Uno................................ 3
1.1 Subseccion................................ 4
"""
    result = enhance_markdown_structure(raw)

    assert "Índice" in result
    assert "1. Seccion Uno................................ 3" in result
    assert "1.1 Subseccion................................ 4" in result
    assert "#page-" not in result


def test_markdown_quality_merges_split_table_continuation():
    raw = """| SMART | Definicion | Objetivo |
| --- | --- | --- |
| Alcanzable | Texto | Se lograra mediante un dashboard web que|

| Col1 | Col2 | permita la visualizacion |
| --- | --- | --- |
| Realista | Texto | Continuacion |
"""
    result = enhance_markdown_structure(raw)

    assert "| Col1 | Col2 | permita la visualizacion |" not in result
    assert result.count("| --- | --- | --- |") == 1
    assert "dashboard web que" in result
    assert "permita la visualizacion" in result


def test_markdown_quality_merges_table_blocks_across_image_break():
    raw = """| A | B | C |
| --- | --- | --- |
| 1 | 2 | 3 |

![](page.png)

| 4 | 5 | Col3 |
| --- | --- | --- |
| 6 | 7 | 8 |
"""
    result = enhance_markdown_structure(raw)

    assert "![](page.png)" not in result
    assert result.count("| --- | --- | --- |") == 1
    assert "|4|5||" in result or "| 4 | 5 |  |" in result
    assert "| 6 | 7 | 8 |" in result
