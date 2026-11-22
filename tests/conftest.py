"""Test fixtures and synthetic PDF generation utilities."""

import io
from pathlib import Path

import pymupdf
import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def sample_text_pdf(tmp_path: Path) -> Path:
    """Generate a clean 2-page text PDF with headings, paragraphs, and metadata."""
    pdf_path = tmp_path / "sample_text.pdf"
    doc = pymupdf.open()

    # Page 1
    page1 = doc.new_page(width=595, height=842)  # A4
    page1.insert_text(
        pymupdf.Point(50, 80),
        "Document Intelligence System Overview",
        fontsize=18,
    )
    page1.insert_text(
        pymupdf.Point(50, 120),
        "This is an automated pipeline for extracting structured information from documents.",
        fontsize=11,
    )
    page1.insert_text(
        pymupdf.Point(50, 150),
        "It supports native text extraction, layout detection, and OCR fallback when necessary.",
        fontsize=11,
    )

    # Page 2
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text(pymupdf.Point(50, 80), "Technical Specifications", fontsize=16)
    page2.insert_text(
        pymupdf.Point(50, 120),
        "The system processes documents sequentially to ensure predictable memory usage.",
        fontsize=11,
    )

    doc.set_metadata(
        {
            "title": "Document Intelligence Specification",
            "author": "Engineering Team",
            "creationDate": "D:20261122120000",
        }
    )
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_scanned_pdf(tmp_path: Path) -> Path:
    """Generate a scanned-style PDF containing an image of text but no native text layer."""
    pdf_path = tmp_path / "sample_scanned.pdf"

    # Create synthetic scanned image
    img = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 50), "Scanned Invoice #88492 Total: $450.00", fill=(0, 0, 0))

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_data = img_bytes.getvalue()

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    # Insert image without any text layer
    page.insert_image(pymupdf.Rect(50, 50, 450, 250), stream=img_data)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_encrypted_pdf(tmp_path: Path) -> Path:
    """Generate a password-protected PDF."""
    pdf_path = tmp_path / "sample_encrypted.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(pymupdf.Point(50, 50), "Confidential Secret Content", fontsize=12)

    # Save with encryption owner & user password
    perm = int(
        pymupdf.PDF_PERM_ACCESSIBILITY
        | pymupdf.PDF_PERM_PRINT
        | pymupdf.PDF_PERM_COPY
        | pymupdf.PDF_PERM_ANNOTATE
    )
    doc.save(
        str(pdf_path),
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="secret_owner",
        user_pw="secret_pass",
        permissions=perm,
    )
    doc.close()
    return pdf_path


@pytest.fixture
def sample_corrupt_pdf(tmp_path: Path) -> Path:
    """Generate a file with an invalid PDF header."""
    pdf_path = tmp_path / "sample_corrupt.pdf"
    pdf_path.write_bytes(b"NOT_A_REAL_PDF_HEADER_DATA_1234567890")
    return pdf_path


@pytest.fixture
def sample_empty_pdf(tmp_path: Path) -> Path:
    """Generate an empty 0-byte file with .pdf extension."""
    pdf_path = tmp_path / "sample_empty.pdf"
    pdf_path.write_bytes(b"")
    return pdf_path
