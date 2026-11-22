"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("DOCINTEL_HOST", "127.0.0.1")
    port: int = int(os.getenv("DOCINTEL_PORT", "8000"))
    max_upload_size_bytes: int = int(
        os.getenv("DOCINTEL_MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024))
    )
    ocr_char_threshold: int = int(os.getenv("DOCINTEL_OCR_CHAR_THRESHOLD", "50"))
    ocr_dpi: int = int(os.getenv("DOCINTEL_OCR_DPI", "300"))
    tesseract_cmd: str | None = os.getenv("DOCINTEL_TESSERACT_CMD")
    storage_dir: Path = Path(os.getenv("DOCINTEL_STORAGE_DIR", "./storage"))


settings = Settings()
