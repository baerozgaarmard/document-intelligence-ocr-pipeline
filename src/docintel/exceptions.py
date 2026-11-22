"""Custom exception hierarchy for document intelligence pipeline."""


class DocIntelError(Exception):
    """Base exception for all docintel processing failures."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CorruptPdfError(DocIntelError):
    """Raised when PDF file header or xref table is invalid or unreadable."""


class EncryptedPdfError(DocIntelError):
    """Raised when PDF is password protected and cannot be decrypted."""


class EmptyPdfError(DocIntelError):
    """Raised when PDF contains 0 pages or has 0 bytes."""


class OcrUnavailableError(DocIntelError):
    """Raised when OCR is required but tesseract binary is not installed or configured."""


class FileTooLargeError(DocIntelError):
    """Raised when document file size exceeds the configured upload threshold."""
