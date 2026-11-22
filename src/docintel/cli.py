"""Command-line interface for local batch and single-file PDF document processing."""

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from docintel.models import DocumentOutput
from docintel.pipeline import DocumentProcessingPipeline

app = typer.Typer(
    name="docintel",
    help="Document Intelligence OCR Pipeline CLI for structured PDF extraction and validation.",
    add_completion=False,
)


@app.command()
def process(
    input_pdf: Path = typer.Argument(
        ..., help="Path to input PDF file to process", exists=True, dir_okay=False
    ),
    output: Path = typer.Option(
        None, "--output", "-o", help="Optional path to write structured output JSON"
    ),
) -> None:
    """Process a single PDF file and output structured JSON."""
    pipeline = DocumentProcessingPipeline()
    try:
        result = pipeline.process_document(source=input_pdf, filename=input_pdf.name)
        json_str = result.model_dump_json(indent=2)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json_str, encoding="utf-8")
            typer.echo(f"Successfully processed {input_pdf.name} -> {output}")
        else:
            typer.echo(json_str)
    except Exception as exc:
        typer.secho(f"Error processing {input_pdf}: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def validate(
    json_path: Path = typer.Argument(
        ..., help="Path to JSON file to validate against DocumentOutput schema", exists=True
    ),
) -> None:
    """Validate a JSON file against the DocumentOutput contract schema."""
    try:
        content = json_path.read_text(encoding="utf-8")
        data = json.loads(content)
        validated = DocumentOutput.model_validate(data)
        typer.secho(
            f"Validation successful: '{json_path.name}' adheres to schema {validated.schema_version} "
            f"({len(validated.pages)} pages).",
            fg=typer.colors.GREEN,
        )
    except ValidationError as err:
        typer.secho(f"Schema validation error in {json_path}:", fg=typer.colors.RED)
        typer.echo(err.json(indent=2))
        raise typer.Exit(code=1) from err
    except Exception as exc:
        typer.secho(f"Failed to read or parse {json_path}: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def batch(
    input_dir: Path = typer.Argument(
        ..., help="Directory containing PDF files", exists=True, file_okay=False
    ),
    output_dir: Path = typer.Option(
        ..., "--output-dir", "-o", help="Directory to save JSON results"
    ),
) -> None:
    """Batch process all PDF documents in an input directory."""
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        typer.secho(f"No PDF files found in {input_dir}", fg=typer.colors.YELLOW)
        return

    typer.echo(f"Found {len(pdf_files)} PDF files in {input_dir}. Beginning batch processing...")
    pipeline = DocumentProcessingPipeline()
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    for out in pipeline.process_batch(pdf_files, output_dir=output_dir):
        if out.processing.status != "failed":
            success_count += 1
            typer.echo(f" [OK] {out.document.filename} ({len(out.pages)} pages)")
        else:
            typer.secho(f" [FAIL] {out.document.filename}: {out.warnings}", fg=typer.colors.RED)

    typer.echo(f"Batch completed: {success_count}/{len(pdf_files)} succeeded.")


if __name__ == "__main__":
    app()
