"""Integration tests for document processing pipeline and batch processing."""

from pathlib import Path

from docintel.models import DocumentOutput, ProcessingStatus
from docintel.ocr import FakeOcrEngine
from docintel.pipeline import DocumentProcessingPipeline


def test_pipeline_process_document(sample_text_pdf: Path) -> None:
    pipeline = DocumentProcessingPipeline(ocr_engine=FakeOcrEngine())
    output = pipeline.process_document(sample_text_pdf, filename=sample_text_pdf.name)

    assert isinstance(output, DocumentOutput)
    assert output.schema_version == "1.0.0"
    assert output.document.filename == sample_text_pdf.name
    assert output.document.page_count == 2
    assert output.processing.status == ProcessingStatus.COMPLETED
    assert output.processing.pages_processed == 2
    assert output.processing.duration_ms >= 0.0

    # Ensure json serialization is compliant with pydantic schema
    json_data = output.model_dump()
    assert json_data["schema_version"] == "1.0.0"
    assert len(json_data["pages"]) == 2


def test_pipeline_batch_processing(
    sample_text_pdf: Path, sample_scanned_pdf: Path, tmp_path: Path
) -> None:
    pipeline = DocumentProcessingPipeline(ocr_engine=FakeOcrEngine())
    batch_dir = tmp_path / "batch_out"

    inputs = [sample_text_pdf, sample_scanned_pdf]
    results = list(pipeline.process_batch(inputs, output_dir=batch_dir))

    assert len(results) == 2
    assert (batch_dir / f"{sample_text_pdf.stem}.json").exists()
    assert (batch_dir / f"{sample_scanned_pdf.stem}.json").exists()
