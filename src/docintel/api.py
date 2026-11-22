"""FastAPI REST application exposing document ingestion and retrieval endpoints."""

import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, File, HTTPException, UploadFile, status

from docintel import __version__
from docintel.config import settings
from docintel.exceptions import (
    CorruptPdfError,
    DocIntelError,
    EmptyPdfError,
    EncryptedPdfError,
    FileTooLargeError,
)
from docintel.models import DocumentOutput, JobStatusResponse
from docintel.pipeline import DocumentProcessingPipeline

app = FastAPI(
    title="Document Intelligence OCR Pipeline API",
    version=__version__,
    description="REST API for structured text, layout, table extraction and OCR from PDF documents.",
)

pipeline = DocumentProcessingPipeline()
# In-memory document storage for fast retrieval, backed by storage directory if needed
_DOCUMENTS_STORE: dict[str, JobStatusResponse] = {}


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Health check endpoint indicating service availability."""
    return {"status": "ok", "version": __version__}


@app.get("/v1/schema", tags=["Schema"])
def get_output_schema() -> dict:
    """Return JSON schema definition for DocumentOutput contract."""
    return DocumentOutput.model_json_schema()


@app.post(
    "/v1/documents",
    response_model=DocumentOutput,
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
)
async def process_document_upload(file: UploadFile = File(...)) -> DocumentOutput:
    """Upload and synchronously process a PDF document into structured JSON."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format: only '.pdf' documents are accepted.",
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {settings.max_upload_size_bytes} bytes.",
        )

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    try:
        output = pipeline.process_document(
            source=content,
            filename=file.filename,
            document_id=doc_id,
        )

        job_resp = JobStatusResponse(
            job_id=doc_id,
            status=output.processing.status,
            created_at=datetime.now(UTC).isoformat(),
            document_output=output,
        )
        _DOCUMENTS_STORE[doc_id] = job_resp
        return output

    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=exc.message
        ) from exc
    except (CorruptPdfError, EmptyPdfError, EncryptedPdfError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except DocIntelError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed unexpectedly: {exc}",
        ) from exc


@app.get(
    "/v1/documents/{document_id}",
    response_model=JobStatusResponse,
    tags=["Documents"],
)
def get_document_status(document_id: str) -> JobStatusResponse:
    """Retrieve processed document result by document ID."""
    if document_id not in _DOCUMENTS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' was not found.",
        )
    return _DOCUMENTS_STORE[document_id]
