"""Document intelligence processing pipeline orchestrating extraction, validation, and batch jobs."""

import time
import uuid
from collections.abc import Generator
from pathlib import Path

from docintel.exceptions import DocIntelError
from docintel.extractor import PdfDocumentExtractor
from docintel.models import (
    DocumentInfo,
    DocumentMetadata,
    DocumentOutput,
    ExtractionMethod,
    ProcessingStatus,
    ProcessingSummary,
)
from docintel.ocr import OcrEngine


class DocumentProcessingPipeline:
    """Orchestrates PDF ingestion, structured extraction, validation, and performance metrics."""

    def __init__(self, ocr_engine: OcrEngine | None = None) -> None:
        self.extractor = PdfDocumentExtractor(ocr_engine=ocr_engine)

    def process_document(
        self,
        source: bytes | Path | str,
        filename: str = "document.pdf",
        document_id: str | None = None,
    ) -> DocumentOutput:
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        try:
            doc_info, pages, doc_warnings = self.extractor.extract(
                source=source,
                filename=filename,
                document_id=doc_id,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            ocr_count = sum(1 for p in pages if p.extraction_method == ExtractionMethod.OCR)
            all_warnings = list(doc_warnings)
            for p in pages:
                all_warnings.extend(p.warnings)

            status = ProcessingStatus.COMPLETED
            if any("failed" in w.lower() for w in all_warnings):
                status = ProcessingStatus.PARTIAL

            summary = ProcessingSummary(
                status=status,
                duration_ms=round(duration_ms, 2),
                pages_processed=len(pages),
                ocr_page_count=ocr_count,
            )

            return DocumentOutput(
                schema_version="1.0.0",
                document=doc_info,
                pages=pages,
                warnings=all_warnings,
                processing=summary,
            )

        except DocIntelError:
            # Re-raise known domain errors for callers/API to handle
            raise
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Unexpected processing failure: {exc}"
            summary = ProcessingSummary(
                status=ProcessingStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                pages_processed=0,
                ocr_page_count=0,
            )
            return DocumentOutput(
                schema_version="1.0.0",
                document=DocumentInfo(
                    document_id=doc_id,
                    filename=filename,
                    page_count=0,
                    metadata=DocumentMetadata(),
                ),
                pages=[],
                warnings=[error_msg],
                processing=summary,
            )

    def process_batch(
        self,
        input_paths: list[Path],
        output_dir: Path | None = None,
    ) -> Generator[DocumentOutput, None, None]:
        """Stream batch documents sequentially to ensure bounded memory consumption."""
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

        for path in input_paths:
            try:
                output = self.process_document(source=path, filename=path.name)
                if output_dir:
                    out_file = output_dir / f"{path.stem}.json"
                    out_file.write_text(output.model_dump_json(indent=2), encoding="utf-8")
                yield output
            except Exception as exc:
                # In batch mode, record failure output rather than aborting whole batch
                err_output = DocumentOutput(
                    schema_version="1.0.0",
                    document=DocumentInfo(
                        document_id=f"doc_{uuid.uuid4().hex[:12]}",
                        filename=path.name,
                        page_count=0,
                    ),
                    pages=[],
                    warnings=[f"Batch processing failed for {path.name}: {exc}"],
                    processing=ProcessingSummary(
                        status=ProcessingStatus.FAILED,
                        duration_ms=0.0,
                        pages_processed=0,
                        ocr_page_count=0,
                    ),
                )
                if output_dir:
                    out_file = output_dir / f"{path.stem}.error.json"
                    out_file.write_text(err_output.model_dump_json(indent=2), encoding="utf-8")
                yield err_output
