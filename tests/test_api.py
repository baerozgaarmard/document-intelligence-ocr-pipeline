"""REST API endpoint tests using FastAPI TestClient."""

from pathlib import Path

from fastapi.testclient import TestClient

from docintel.api import app, pipeline
from docintel.ocr import FakeOcrEngine

# Inject fake OCR engine for deterministic API tests
pipeline.extractor.ocr_engine = FakeOcrEngine()
client = TestClient(app)


def test_api_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_api_schema() -> None:
    response = client.get("/v1/schema")
    assert response.status_code == 200
    data = response.json()
    assert "properties" in data
    assert "schema_version" in data["properties"]


def test_api_process_document_success(sample_text_pdf: Path) -> None:
    with open(sample_text_pdf, "rb") as f:
        response = client.post(
            "/v1/documents",
            files={"file": (sample_text_pdf.name, f, "application/pdf")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["schema_version"] == "1.0.0"
    assert data["document"]["filename"] == sample_text_pdf.name
    assert data["document"]["page_count"] == 2
    assert len(data["pages"]) == 2

    # Verify retrieval endpoint
    doc_id = data["document"]["document_id"]
    get_resp = client.get(f"/v1/documents/{doc_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["job_id"] == doc_id
    assert get_data["document_output"]["document"]["document_id"] == doc_id


def test_api_rejects_non_pdf() -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("test.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400
    assert "only '.pdf'" in response.json()["detail"]


def test_api_rejects_corrupt_pdf(sample_corrupt_pdf: Path) -> None:
    with open(sample_corrupt_pdf, "rb") as f:
        response = client.post(
            "/v1/documents",
            files={"file": (sample_corrupt_pdf.name, f, "application/pdf")},
        )
    assert response.status_code == 400
    assert "Invalid PDF" in response.json()["detail"]


def test_api_rejects_empty_pdf(sample_empty_pdf: Path) -> None:
    with open(sample_empty_pdf, "rb") as f:
        response = client.post(
            "/v1/documents",
            files={"file": (sample_empty_pdf.name, f, "application/pdf")},
        )
    assert response.status_code == 400
    assert "0 bytes" in response.json()["detail"]


def test_api_rejects_encrypted_pdf(sample_encrypted_pdf: Path) -> None:
    with open(sample_encrypted_pdf, "rb") as f:
        response = client.post(
            "/v1/documents",
            files={"file": (sample_encrypted_pdf.name, f, "application/pdf")},
        )
    assert response.status_code == 400
    assert "password protected" in response.json()["detail"]


def test_api_not_found_document() -> None:
    response = client.get("/v1/documents/non_existent_id")
    assert response.status_code == 404
