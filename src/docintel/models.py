"""Pydantic data models defining the stable 1.0.0 JSON schema contract."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class BlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST_ITEM = "list_item"
    UNKNOWN = "unknown"


class ExtractionMethod(StrEnum):
    NATIVE_TEXT = "native_text"
    OCR = "ocr"
    HYBRID = "hybrid"


class ProcessingStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class TextBlock(BaseModel):
    block_id: str
    type: BlockType = BlockType.PARAGRAPH
    text: str
    bbox: BoundingBox | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    font_size: float | None = None


class Table(BaseModel):
    table_id: str
    rows: list[list[str]] = Field(default_factory=list)
    headers: list[str] | None = None
    bbox: BoundingBox | None = None


class PageOutput(BaseModel):
    page_number: int = Field(ge=1)
    extraction_method: ExtractionMethod
    text: str
    blocks: list[TextBlock] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    width: float | None = None
    height: float | None = None


class DocumentMetadata(BaseModel):
    title: str | None = None
    author: str | None = None
    created_at: str | None = None
    producer: str | None = None


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    page_count: int = Field(ge=0)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class ProcessingSummary(BaseModel):
    status: ProcessingStatus
    duration_ms: float = Field(ge=0.0)
    pages_processed: int = Field(ge=0)
    ocr_page_count: int = Field(ge=0)


class DocumentOutput(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document: DocumentInfo
    pages: list[PageOutput] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing: ProcessingSummary


class JobStatusResponse(BaseModel):
    job_id: str
    status: ProcessingStatus
    created_at: str
    document_output: DocumentOutput | None = None
    error: str | None = None
