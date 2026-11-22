"""Unit tests for PDF document extractor and boundary condition handlers."""

from pathlib import Path

import pytest

from docintel.exceptions import (
    CorruptPdfError,
    EmptyPdfError,
    EncryptedPdfError,
    FileTooLargeError,
)
from docintel.extractor import PdfDocumentExtractor
from docintel.models import BlockType, ExtractionMethod
from docintel.ocr import FakeOcrEngine


def test_text_pdf_extraction(sample_text_pdf: Path) -> None:
    extractor = PdfDocumentExtractor(ocr_engine=FakeOcrEngine())
    doc_info, pages, warnings = extractor.extract(sample_text_pdf, filename=sample_text_pdf.name)

    assert doc_info.page_count == 2
    assert doc_info.filename == sample_text_pdf.name
    assert doc_info.metadata.title == "Document Intelligence Specification"
    assert doc_info.metadata.author == "Engineering Team"

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[0].extraction_method == ExtractionMethod.NATIVE_TEXT
    assert "Document Intelligence System Overview" in pages[0].text
    assert any(b.type == BlockType.HEADING for b in pages[0].blocks)

    assert pages[1].page_number == 2
    assert pages[1].extraction_method == ExtractionMethod.NATIVE_TEXT
    assert "Technical Specifications" in pages[1].text


def test_scanned_pdf_triggers_ocr(sample_scanned_pdf: Path) -> None:
    fake_ocr = FakeOcrEngine(canned_text="Scanned Invoice #88492 Total: $450.00")
    extractor = PdfDocumentExtractor(ocr_engine=fake_ocr)

    doc_info, pages, warnings = extractor.extract(
        sample_scanned_pdf, filename=sample_scanned_pdf.name
    )

    assert doc_info.page_count == 1
    assert pages[0].extraction_method == ExtractionMethod.OCR
    assert "Scanned Invoice #88492" in pages[0].text
    assert len(pages[0].blocks) > 0


def test_ocr_unavailable_path(sample_scanned_pdf: Path) -> None:
    # Fake OCR engine set to unavailable
    unavailable_ocr = FakeOcrEngine(available=False)
    extractor = PdfDocumentExtractor(ocr_engine=unavailable_ocr)

    doc_info, pages, warnings = extractor.extract(
        sample_scanned_pdf, filename=sample_scanned_pdf.name
    )

    assert doc_info.page_count == 1
    # Check that warning was recorded instead of crashing
    assert len(pages[0].warnings) > 0
    assert any("unavailable" in w.lower() for w in pages[0].warnings)


def test_corrupt_pdf_raises_error(sample_corrupt_pdf: Path) -> None:
    extractor = PdfDocumentExtractor()
    with pytest.raises(CorruptPdfError) as exc_info:
        extractor.extract(sample_corrupt_pdf)
    assert "Invalid PDF signature" in str(exc_info.value)


def test_empty_pdf_raises_error(sample_empty_pdf: Path) -> None:
    extractor = PdfDocumentExtractor()
    with pytest.raises(EmptyPdfError) as exc_info:
        extractor.extract(sample_empty_pdf)
    assert "0 bytes" in str(exc_info.value)


def test_encrypted_pdf_raises_error(sample_encrypted_pdf: Path) -> None:
    extractor = PdfDocumentExtractor()
    with pytest.raises(EncryptedPdfError) as exc_info:
        extractor.extract(sample_encrypted_pdf)
    assert "password protected" in str(exc_info.value)


def test_oversized_pdf_raises_error(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.pdf"
    oversized.write_bytes(b"%PDF-" + b"0" * 2000)

    extractor = PdfDocumentExtractor(max_upload_size_bytes=1000)
    with pytest.raises(FileTooLargeError):
        extractor.extract(oversized)
