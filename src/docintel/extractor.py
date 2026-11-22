"""PDF extraction core: native text parsing, layout analysis, table extraction, and OCR triggering."""

import io
from pathlib import Path

import pymupdf
from PIL import Image

from docintel.config import settings
from docintel.exceptions import (
    CorruptPdfError,
    DocIntelError,
    EmptyPdfError,
    EncryptedPdfError,
    FileTooLargeError,
    OcrUnavailableError,
)
from docintel.models import (
    BlockType,
    BoundingBox,
    DocumentInfo,
    DocumentMetadata,
    ExtractionMethod,
    PageOutput,
    Table,
    TextBlock,
)
from docintel.ocr import OcrEngine, TesseractOcrEngine


class PdfDocumentExtractor:
    """Extracts structured content from PDF streams or files using PyMuPDF and OCR."""

    def __init__(
        self,
        ocr_engine: OcrEngine | None = None,
        max_upload_size_bytes: int | None = None,
    ) -> None:
        self.ocr_engine = ocr_engine or TesseractOcrEngine()
        self.max_upload_size_bytes = (
            max_upload_size_bytes
            if max_upload_size_bytes is not None
            else settings.max_upload_size_bytes
        )

    def extract(
        self,
        source: bytes | Path | str,
        filename: str = "document.pdf",
        document_id: str = "doc_1",
    ) -> tuple[DocumentInfo, list[PageOutput], list[str]]:
        raw_bytes = self._read_and_validate_bytes(source)
        doc_warnings: list[str] = []

        try:
            doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
        except Exception as exc:
            raise CorruptPdfError(f"Failed to parse PDF file header or stream: {exc}") from exc

        try:
            if doc.is_encrypted:
                # Attempt decryption with empty password; if locked, raise error
                if not doc.authenticate(""):
                    raise EncryptedPdfError(
                        f"PDF '{filename}' is password protected and cannot be decrypted."
                    )

            page_count = len(doc)
            if page_count == 0:
                raise EmptyPdfError(f"PDF '{filename}' contains 0 pages.")

            # Extract document metadata
            raw_meta = doc.metadata or {}
            meta = DocumentMetadata(
                title=raw_meta.get("title") or None,
                author=raw_meta.get("author") or None,
                created_at=raw_meta.get("creationDate") or None,
                producer=raw_meta.get("producer") or None,
            )
            doc_info = DocumentInfo(
                document_id=document_id,
                filename=filename,
                page_count=page_count,
                metadata=meta,
            )

            pages_output: list[PageOutput] = []

            for page_idx in range(page_count):
                page = doc[page_idx]
                page_num = page_idx + 1
                page_output = self._process_page(page, page_num)
                pages_output.append(page_output)

            return doc_info, pages_output, doc_warnings

        finally:
            doc.close()

    def _read_and_validate_bytes(self, source: bytes | Path | str) -> bytes:
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                raise DocIntelError(f"Source file not found: {path}")
            raw_bytes = path.read_bytes()
        elif isinstance(source, bytes):
            raw_bytes = source
        else:
            raise DocIntelError(f"Unsupported source type: {type(source)}")

        if len(raw_bytes) == 0:
            raise EmptyPdfError("Supplied document is 0 bytes.")

        if len(raw_bytes) > self.max_upload_size_bytes:
            raise FileTooLargeError(
                f"Document size {len(raw_bytes)} bytes exceeds maximum allowed "
                f"{self.max_upload_size_bytes} bytes."
            )

        # Basic PDF header check
        if not raw_bytes.startswith(b"%PDF-"):
            raise CorruptPdfError("Invalid PDF signature: missing '%PDF-' header prefix.")

        return raw_bytes

    def _process_page(self, page: pymupdf.Page, page_num: int) -> PageOutput:
        rect = page.rect
        width = float(rect.width)
        height = float(rect.height)
        page_warnings: list[str] = []

        # 1. Native text and structured blocks
        native_blocks, native_text = self._extract_native_blocks(page, page_num)
        tables = self._extract_tables(page, page_num)

        # 2. Check if OCR is required
        image_list = page.get_images()
        needs_ocr = len(native_text.strip()) < settings.ocr_char_threshold and (
            len(image_list) > 0 or len(native_text.strip()) == 0
        )

        extraction_method = ExtractionMethod.NATIVE_TEXT
        final_blocks = native_blocks
        final_text = native_text

        if needs_ocr:
            try:
                ocr_text, ocr_blocks = self._ocr_page(page, page_num)
                if ocr_text:
                    final_text = ocr_text
                    final_blocks = ocr_blocks
                    extraction_method = ExtractionMethod.OCR
                else:
                    page_warnings.append("OCR executed but yielded no textual content.")
            except OcrUnavailableError as err:
                page_warnings.append(
                    f"OCR required for page {page_num} but unavailable: {err.message}"
                )
            except Exception as exc:
                page_warnings.append(f"OCR extraction failed on page {page_num}: {exc}")

        return PageOutput(
            page_number=page_num,
            extraction_method=extraction_method,
            text=final_text,
            blocks=final_blocks,
            tables=tables,
            warnings=page_warnings,
            width=width,
            height=height,
        )

    def _extract_native_blocks(
        self, page: pymupdf.Page, page_num: int
    ) -> tuple[list[TextBlock], str]:
        blocks: list[TextBlock] = []
        page_dict = page.get_text("dict")
        text_lines: list[str] = []

        for b_idx, b in enumerate(page_dict.get("blocks", [])):
            if b.get("type") != 0:  # 0 indicates text block
                continue

            block_text_parts: list[str] = []
            font_sizes: list[float] = []

            for line in b.get("lines", []):
                line_parts: list[str] = []
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    if span_text.strip():
                        line_parts.append(span_text)
                        font_sizes.append(float(span.get("size", 10.0)))
                if line_parts:
                    block_text_parts.append(" ".join(line_parts))

            combined_text = "\n".join(block_text_parts).strip()
            if not combined_text:
                continue

            avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 10.0
            is_heading = avg_font_size >= 14.0 or (
                avg_font_size >= 12.0
                and len(combined_text) < 80
                and not combined_text.endswith(".")
            )

            bbox = b.get("bbox")
            bounding_box = (
                BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3])
                if bbox and len(bbox) == 4
                else None
            )

            blocks.append(
                TextBlock(
                    block_id=f"p{page_num}-b{b_idx}",
                    type=BlockType.HEADING if is_heading else BlockType.PARAGRAPH,
                    text=combined_text,
                    bbox=bounding_box,
                    confidence=1.0,
                    font_size=round(avg_font_size, 2),
                )
            )
            text_lines.append(combined_text)

        full_text = "\n\n".join(text_lines)
        return blocks, full_text

    def _extract_tables(self, page: pymupdf.Page, page_num: int) -> list[Table]:
        tables: list[Table] = []
        try:
            detected = page.find_tables()
            for t_idx, tab in enumerate(detected):
                raw_rows = tab.extract()
                clean_rows: list[list[str]] = []
                for r in raw_rows:
                    clean_rows.append([str(c or "").strip() for c in r])

                bbox = None
                if tab.bbox and len(tab.bbox) == 4:
                    bbox = BoundingBox(
                        x0=float(tab.bbox[0]),
                        y0=float(tab.bbox[1]),
                        x1=float(tab.bbox[2]),
                        y1=float(tab.bbox[3]),
                    )

                headers = clean_rows[0] if clean_rows else None
                tables.append(
                    Table(
                        table_id=f"p{page_num}-t{t_idx}",
                        rows=clean_rows,
                        headers=headers,
                        bbox=bbox,
                    )
                )
        except Exception:
            # Table detection fallback: ignore if unsupported or fails on specific page
            pass
        return tables

    def _ocr_page(self, page: pymupdf.Page, page_num: int) -> tuple[str, list[TextBlock]]:
        pix = page.get_pixmap(dpi=settings.ocr_dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return self.ocr_engine.extract_text(img, page_num)
