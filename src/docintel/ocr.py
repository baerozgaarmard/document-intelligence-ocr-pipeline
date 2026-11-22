"""OCR adapter layer supporting Tesseract and controlled test fakes."""

import shutil
from typing import Protocol

import pytesseract
from PIL import Image

from docintel.config import settings
from docintel.exceptions import OcrUnavailableError
from docintel.models import BlockType, BoundingBox, TextBlock


class OcrEngine(Protocol):
    """Protocol for pluggable optical character recognition backends."""

    def is_available(self) -> bool: ...

    def extract_text(self, image: Image.Image, page_number: int) -> tuple[str, list[TextBlock]]: ...


class TesseractOcrEngine:
    """Tesseract implementation with health check and bounding-box extraction."""

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        self.cmd = tesseract_cmd or settings.tesseract_cmd or shutil.which("tesseract")
        if self.cmd:
            pytesseract.pytesseract.tesseract_cmd = self.cmd

    def is_available(self) -> bool:
        if not self.cmd:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text(self, image: Image.Image, page_number: int) -> tuple[str, list[TextBlock]]:
        if not self.is_available():
            raise OcrUnavailableError(
                "Tesseract binary not found. Install Tesseract and ensure it is on PATH "
                "or configure DOCINTEL_TESSERACT_CMD."
            )

        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        full_text = pytesseract.image_to_string(image).strip()

        blocks: list[TextBlock] = []
        n_boxes = len(data.get("text", []))

        current_block_num = -1
        current_text_parts: list[str] = []
        current_bbox: list[float] | None = None
        confidences: list[float] = []

        for i in range(n_boxes):
            word = data["text"][i].strip()
            conf = float(data["conf"][i])
            if not word or conf < 0:
                continue

            block_num = data["block_num"][i]
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]

            if block_num != current_block_num:
                if current_text_parts and current_bbox:
                    avg_conf = sum(confidences) / len(confidences) / 100.0 if confidences else 0.8
                    blocks.append(
                        TextBlock(
                            block_id=f"p{page_number}-b{len(blocks)}",
                            type=BlockType.PARAGRAPH,
                            text=" ".join(current_text_parts),
                            bbox=BoundingBox(
                                x0=current_bbox[0],
                                y0=current_bbox[1],
                                x1=current_bbox[2],
                                y1=current_bbox[3],
                            ),
                            confidence=round(avg_conf, 3),
                        )
                    )
                current_block_num = block_num
                current_text_parts = [word]
                current_bbox = [float(x), float(y), float(x + w), float(y + h)]
                confidences = [conf]
            else:
                current_text_parts.append(word)
                confidences.append(conf)
                if current_bbox:
                    current_bbox[2] = max(current_bbox[2], float(x + w))
                    current_bbox[3] = max(current_bbox[3], float(y + h))

        if current_text_parts and current_bbox:
            avg_conf = sum(confidences) / len(confidences) / 100.0 if confidences else 0.8
            blocks.append(
                TextBlock(
                    block_id=f"p{page_number}-b{len(blocks)}",
                    type=BlockType.PARAGRAPH,
                    text=" ".join(current_text_parts),
                    bbox=BoundingBox(
                        x0=current_bbox[0],
                        y0=current_bbox[1],
                        x1=current_bbox[2],
                        y1=current_bbox[3],
                    ),
                    confidence=round(avg_conf, 3),
                )
            )

        return full_text, blocks


class FakeOcrEngine:
    """Deterministic in-memory fake OCR engine for test isolation and CI."""

    def __init__(
        self, canned_text: str = "Synthesized OCR Content", available: bool = True
    ) -> None:
        self.canned_text = canned_text
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def extract_text(self, image: Image.Image, page_number: int) -> tuple[str, list[TextBlock]]:
        if not self.available:
            raise OcrUnavailableError("Configured Fake OCR is set to unavailable for testing.")

        block = TextBlock(
            block_id=f"p{page_number}-b0",
            type=BlockType.PARAGRAPH,
            text=self.canned_text,
            bbox=BoundingBox(x0=50.0, y0=50.0, x1=400.0, y1=100.0),
            confidence=0.98,
        )
        return self.canned_text, [block]
