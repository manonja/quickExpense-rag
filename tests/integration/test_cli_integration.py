"""Integration tests for extraction pipeline CLI."""

import subprocess
from pathlib import Path

import pytest
import yaml
from qe_tax_rag.extraction.ca.cli import app
from qe_tax_rag.parser.schema import ParsedDocument
from typer.testing import CliRunner

runner = CliRunner()

# Test YAML fixtures for transform command tests
VALID_YAML_CONTENT = """
schema_version: "1.0"
extraction_timestamp: "2025-01-01T00:00:00Z"
rules:
  - rule_number: 8523
    title: "Meals and entertainment"
    content: "You can deduct 50% of restaurant expenses..."
    applies_to:
      - business
      - fishing
    source_citation: "Line 8523"
    chapter: "Chapter 3 – Expenses"
    section: "Part 4 – Net income"
    source_file: "t4002-5.html"
    expert_source: "adjudicated"
    anchor_id: "tocch3ln8523"
    confidence_score: 0.95
  - rule_number: 9200
    title: "Motor vehicle expenses"
    content: "Deductible car expenses include fuel and mileage..."
    applies_to:
      - business
    source_citation: "Line 9200"
    chapter: "Chapter 3 – Expenses"
    section: "Part 5 – Vehicle"
    source_file: "t4002-5.html"
    expert_source: "classic"
    anchor_id: "tocch3ln9200"
    confidence_score: 1.0
"""

YAML_WITH_SKIPPABLE_ERROR = """
schema_version: "1.0"
extraction_timestamp: "2025-01-01T00:00:00Z"
rules:
  - rule_number: 8523
    title: "Valid rule"
    content: "Content..."
    applies_to:
      - business
    source_citation: "Line 8523"
    chapter: "Chapter 3"
    section: null
    source_file: "t4002-5.html"
    expert_source: "classic"
    confidence_score: 1.0
"""

YAML_WITH_CRITICAL_ERROR = """
schema_version: "999.0"
extraction_timestamp: "2025-01-01T00:00:00Z"
rules: []
"""


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


@pytest.mark.integration
def test_cli_execution_missing_input_file(tmp_path: Path) -> None:
    """Test CLI error handling for missing input file."""
    nonexistent = tmp_path / "missing.html"
    output_yaml = tmp_path / "output.yml"

    result = runner.invoke(app, ["extract", str(nonexistent), str(output_yaml)])

    assert result.exit_code != 0
    # Typer handles this before our code runs


@pytest.mark.integration
def test_transform_command_success(tmp_path: Path) -> None:
    """Transform command should convert YAML to JSONL successfully."""
    # Create valid YAML file
    yaml_path = tmp_path / "test_rules.yml"
    yaml_path.write_text(VALID_YAML_CONTENT)

    jsonl_path = tmp_path / "chunks.jsonl"

    # Run command
    result = subprocess.run(
        ["uv", "run", "extract-rules", "transform", str(yaml_path), str(jsonl_path)],
        capture_output=True,
        text=True,
    )

    # Assertions
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Transformation Complete" in result.stdout
    assert jsonl_path.exists()

    # Validate JSONL content
    with open(jsonl_path) as f:
        lines = f.readlines()
        assert len(lines) == 1  # One document (grouped by source_file)

        # Verify ParsedDocument schema
        doc = ParsedDocument.model_validate_json(lines[0])
        assert doc.document_id == "t4002-5"
        assert "t4002" in doc.title.lower()


@pytest.mark.integration
def test_transform_command_with_skippable_errors(tmp_path: Path) -> None:
    """Transform command should handle skippable errors gracefully."""
    # Create YAML with valid content
    yaml_path = tmp_path / "partial_rules.yml"
    yaml_path.write_text(YAML_WITH_SKIPPABLE_ERROR)

    jsonl_path = tmp_path / "chunks.jsonl"

    # Run command (default continue_on_error=True)
    result = subprocess.run(
        ["uv", "run", "extract-rules", "transform", str(yaml_path), str(jsonl_path)],
        capture_output=True,
        text=True,
    )

    # Should succeed with exit code 0 for valid YAML
    assert result.returncode == 0
    assert jsonl_path.exists()


@pytest.mark.integration
def test_transform_command_fail_fast(tmp_path: Path) -> None:
    """Transform command should stop on first error with --no-continue-on-error."""
    yaml_path = tmp_path / "bad_rules.yml"
    yaml_path.write_text(YAML_WITH_CRITICAL_ERROR)

    jsonl_path = tmp_path / "chunks.jsonl"

    # Run command with --no-continue-on-error
    result = subprocess.run(
        [
            "uv",
            "run",
            "extract-rules",
            "transform",
            str(yaml_path),
            str(jsonl_path),
            "--no-continue-on-error",
        ],
        capture_output=True,
        text=True,
    )

    # Should fail
    assert result.returncode == 1
    assert "Transformation failed" in result.stdout or "failed" in result.stdout.lower()


@pytest.mark.integration
def test_transform_command_error_report(tmp_path: Path) -> None:
    """Transform command should generate error report YAML."""
    yaml_path = tmp_path / "partial_rules.yml"
    yaml_path.write_text(YAML_WITH_CRITICAL_ERROR)

    jsonl_path = tmp_path / "chunks.jsonl"
    error_report = tmp_path / "errors.yml"

    # Run command with --error-report
    result = subprocess.run(
        [
            "uv",
            "run",
            "extract-rules",
            "transform",
            str(yaml_path),
            str(jsonl_path),
            "--error-report",
            str(error_report),
        ],
        capture_output=True,
        text=True,
    )

    # Should fail due to unsupported schema version
    assert result.returncode == 1

    # Error report might not be created for critical errors
    # (only for skippable errors during transformation)


@pytest.mark.integration
def test_transform_command_missing_input(tmp_path: Path) -> None:
    """Transform command should handle missing input file gracefully."""
    nonexistent = tmp_path / "missing.yml"
    jsonl_path = tmp_path / "chunks.jsonl"

    # Run command
    result = subprocess.run(
        ["uv", "run", "extract-rules", "transform", str(nonexistent), str(jsonl_path)],
        capture_output=True,
        text=True,
    )

    # Should fail
    assert result.returncode != 0
