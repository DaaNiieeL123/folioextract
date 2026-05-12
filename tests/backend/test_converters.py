import pytest
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from backend.app.infrastructure.conversion.docx_converter import DocxConverter
from backend.app.infrastructure.conversion.md_converter import MarkdownConverter
from backend.app.infrastructure.conversion.txt_converter import TxtConverter
from backend.app.infrastructure.conversion.exceptions import CorruptedPdfError

def test_txt_converter_missing_file(tmp_path):
    converter = TxtConverter()
    missing_pdf = tmp_path / "missing.pdf"
    dest = tmp_path / "out.txt"
    
    with pytest.raises(CorruptedPdfError):
        converter.convert(missing_pdf, dest)


def test_markdown_converter_handles_brackets_in_pdf_name_with_images(tmp_path):
    image_path = tmp_path / "sample.png"
    image = Image.new("RGB", (320, 140), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 300, 120), outline="black", width=3)
    draw.text((40, 55), "Imagen de prueba", fill="black")
    image.save(image_path)

    source = tmp_path / "[RC1]Enunciado_Practica1.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Hola mundo")
    page.insert_image(fitz.Rect(72, 120, 392, 260), filename=str(image_path))
    document.save(source)
    document.close()

    destination = tmp_path / "[RC1]Enunciado_Practica1_convertido.md"
    result = MarkdownConverter().convert(source, destination)

    assert result.success is True
    assert destination.exists()

    markdown = destination.read_text(encoding="utf-8")
    assert ".png" in markdown
    assert "convertido_imagenes" in markdown

    images_dir = tmp_path / "RC1-Enunciado_Practica1_convertido_imagenes"
    assert images_dir.exists()
    assert any(path.suffix.lower() == ".png" for path in images_dir.iterdir())


def test_docx_converter_creates_editable_docx_with_page_geometry(tmp_path):
    from docx import Document

    source = tmp_path / "sample.pdf"
    document = fitz.open()
    portrait = document.new_page(width=595, height=842)
    portrait.insert_text((72, 72), "Pagina vertical")
    landscape = document.new_page(width=842, height=595)
    landscape.insert_text((72, 72), "Pagina horizontal")
    document.save(source)
    document.close()

    destination = tmp_path / "sample_convertido.docx"
    result = DocxConverter().convert(source, destination)

    assert result.success is True
    assert result.pages_processed == 2
    assert destination.exists()

    cloned = Document(str(destination))
    assert len(cloned.sections) == 2
    assert "Pagina vertical" in "\n".join(paragraph.text for paragraph in cloned.paragraphs)
    assert cloned.sections[0].page_width < cloned.sections[0].page_height
    assert cloned.sections[1].page_width > cloned.sections[1].page_height
    assert cloned.sections[0].top_margin == 0
    assert cloned.sections[1].left_margin == 0


