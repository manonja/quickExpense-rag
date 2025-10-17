"""Integration tests for extraction pipeline CLI."""

from pathlib import Path

import pytest
from qe_tax_rag.extraction.ca.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.mark.integration
def test_cli_imports() -> None:
    """Verify CLI module and app can be imported."""
    assert app is not None


@pytest.mark.integration
def test_cli_help_command() -> None:
    """Test that --help displays usage information."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Extract tax rules" in result.stdout
    assert "INPUT_PATH" in result.stdout
    assert "OUTPUT_YAML" in result.stdout


@pytest.mark.integration
def test_cli_execution_missing_input_file(tmp_path: Path) -> None:
    """Test CLI error handling for missing input file."""
    nonexistent = tmp_path / "missing.html"
    output_yaml = tmp_path / "output.yml"

    result = runner.invoke(app, [str(nonexistent), str(output_yaml)])

    assert result.exit_code != 0
    # Typer handles this before our code runs
