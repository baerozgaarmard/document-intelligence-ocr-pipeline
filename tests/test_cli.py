"""CLI command tests using Typer CliRunner."""

from pathlib import Path

from typer.testing import CliRunner

from docintel.cli import app

runner = CliRunner()


def test_cli_process_and_validate(sample_text_pdf: Path, tmp_path: Path) -> None:
    output_json = tmp_path / "output.json"

    # 1. Process
    result = runner.invoke(app, ["process", str(sample_text_pdf), "--output", str(output_json)])
    assert result.exit_code == 0
    assert output_json.exists()
    assert "Successfully processed" in result.stdout

    # 2. Validate
    val_result = runner.invoke(app, ["validate", str(output_json)])
    assert val_result.exit_code == 0
    assert "Validation successful" in val_result.stdout


def test_cli_validate_corrupt_json(tmp_path: Path) -> None:
    corrupt_json = tmp_path / "corrupt.json"
    corrupt_json.write_text('{"schema_version": "0.9.0", "invalid": true}', encoding="utf-8")

    val_result = runner.invoke(app, ["validate", str(corrupt_json)])
    assert val_result.exit_code == 1
    assert "Schema validation error" in val_result.stdout
