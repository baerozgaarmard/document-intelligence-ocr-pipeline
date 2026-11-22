# Engineering Session Log - Project 1: document-intelligence-ocr-pipeline

- **Date:** 2026-11-22
- **Goal:** Implement production-grade PDF document extraction pipeline with layout analysis, OCR triggering, CLI, REST API, and test suite.

## Key Decisions Made
1. **Extraction Engine**: Implemented `PdfDocumentExtractor` leveraging PyMuPDF (`fitz`) for native text, bounding box coordinates, and table detection.
2. **Pluggable OCR**: Created `OcrEngine` protocol with `TesseractOcrEngine` (production) and `FakeOcrEngine` (deterministic test suite).
3. **Threshold-based OCR Trigger**: Automatically detects scanned/image-heavy pages when native character count is below configured threshold (`DOCINTEL_OCR_CHAR_THRESHOLD`).
4. **Stable Schema Contract**: Implemented Pydantic v2 `DocumentOutput` contract with version `1.0.0`, bounding boxes, block classifications, and processing metadata.
5. **Safety and Boundary Defenses**: Added strict defenses against encrypted, corrupt, oversized, and empty documents with custom typed exceptions.

## Verification
- 19 automated unit & integration tests passing (`pytest -v`).
- Zero linting or formatting errors (`ruff check .`, `ruff format --check .`).
