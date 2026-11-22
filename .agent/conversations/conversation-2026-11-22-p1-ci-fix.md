# Engineering Session Log - CI Fix: document-intelligence-ocr-pipeline

- **Date:** 2026-11-22
- **Issue:** GitHub Actions CI failure on `astral-sh/setup-uv@v3` with `enable-cache: true` due to missing `uv.lock`.
- **Resolution:**
  1. Generated reproducible `uv.lock` via `uv lock`.
  2. Updated `.github/workflows/ci.yml` to `setup-uv@v5` and streamlined dependency installation with `uv sync --extra dev` and `uv run`.
  3. Verified tests locally (19/19 passed) and formatting/linting clean.
