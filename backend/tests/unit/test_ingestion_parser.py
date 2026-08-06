from pathlib import Path

import pytest
from pypdf import PdfWriter

from src.modules.ingestion.parser import extract_text


def test_extracts_text_from_valid_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _write_minimal_text_pdf(pdf_path, "Article 1: Cars must have four wheels.")

    text = extract_text(str(pdf_path))

    assert "Article 1" in text
    assert "four wheels" in text


def test_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "does-not-exist.pdf"

    with pytest.raises(FileNotFoundError):
        extract_text(str(missing_path))


def test_raises_for_corrupted_file(tmp_path):
    corrupted_path = tmp_path / "corrupted.pdf"
    corrupted_path.write_bytes(b"not a real pdf file")

    with pytest.raises(ValueError):
        extract_text(str(corrupted_path))


def test_raises_for_pdf_with_no_extractable_text(tmp_path):
    blank_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(blank_path, "wb") as f:
        writer.write(f)

    with pytest.raises(ValueError):
        extract_text(str(blank_path))


def _write_minimal_text_pdf(path: Path, text: str) -> None:
    # Build a minimal single-page PDF with a real content stream containing
    # a Tj text-show operator, so pypdf's extract_text() finds real text
    # without depending on an external PDF-generation library.
    content = f"BT /F1 12 Tf 50 150 Td ({text}) Tj ET".encode()
    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 200 200] /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
        + content
        + b"\nendstream"
    )

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode()

    path.write_bytes(pdf)
