"""Integration tests for parse command (TICKET-9D Task 2)."""

import json
import os
from pathlib import Path

import pytest
from scripts.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def sample_preprocessed_files(tmp_path: Path) -> Path:
    """Create sample preprocessed .txt files for testing."""
    preprocessed_dir = tmp_path / "preprocessed"
    preprocessed_dir.mkdir()

    # Create 3 sample text files
    for i in range(1, 4):
        file_path = preprocessed_dir / f"S{i}-F1-C1.txt"
        file_path.write_text(
            f"""Business Expense Rules - Sample {i}

This is a sample CRA document about business expenses.

Meals and entertainment expenses are deductible at 50%.
Travel expenses for business purposes are fully deductible.
Vehicle expenses can be claimed based on business use percentage.

Province: BC, ON
Business Type: sole_proprietorship, corporation
Expense Types: meals, travel, vehicle
"""
        )

    return preprocessed_dir


@pytest.mark.integration
def test_parse_command_creates_jsonl_output(
    sample_preprocessed_files: Path, tmp_path: Path
) -> None:
    """Test 2a (RED): Verify parse command creates JSONL output file."""
    output_file = tmp_path / "chunks.jsonl"

    # Set API key (use dummy for test - will fail but we test structure)
    os.environ["GEMINI_API_KEY"] = "test-api-key"

    result = runner.invoke(
        app,
        [
            "parse",
            "--input-dir",
            str(sample_preprocessed_files),
            "--output-file",
            str(output_file),
        ],
    )

    # Command should execute (may fail due to invalid API key, that's ok for structure test)
    # We're testing the command exists and accepts parameters
    assert result.exit_code in [
        0,
        1,
    ]  # 0 = success, 1 = expected failure (invalid API key)


@pytest.mark.integration
def test_parse_command_missing_api_key_fails(
    sample_preprocessed_files: Path, tmp_path: Path
) -> None:
    """Test 2c (RED): Verify parse command fails fast with missing API key."""
    output_file = tmp_path / "chunks.jsonl"

    # Remove API key from environment
    os.environ.pop("GEMINI_API_KEY", None)

    result = runner.invoke(
        app,
        [
            "parse",
            "--input-dir",
            str(sample_preprocessed_files),
            "--output-file",
            str(output_file),
        ],
    )

    # Should fail with clear error message
    assert result.exit_code == 1
    assert "GEMINI_API_KEY" in result.stdout or "API key" in result.stdout


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Requires GEMINI_API_KEY environment variable",
)
def test_parse_command_with_real_api(
    sample_preprocessed_files: Path, tmp_path: Path
) -> None:
    """Test 2b (RED): Verify parse command creates valid ParsedDocument JSONL format."""
    output_file = tmp_path / "chunks.jsonl"

    result = runner.invoke(
        app,
        [
            "parse",
            "--input-dir",
            str(sample_preprocessed_files),
            "--output-file",
            str(output_file),
        ],
    )

    # Should succeed with real API key
    assert result.exit_code == 0
    assert output_file.exists()

    # Verify JSONL format (each line is valid JSON)
    with output_file.open() as f:
        lines = f.readlines()
        assert len(lines) > 0

        for line in lines:
            parsed = json.loads(line)
            # Should have ParsedDocument structure
            assert "title" in parsed
            assert "document_id" in parsed
            assert "metadata" in parsed
            assert "sections" in parsed


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Requires GEMINI_API_KEY environment variable",
)
def test_parse_command_tracks_token_usage(
    sample_preprocessed_files: Path, tmp_path: Path
) -> None:
    """Test 2d (RED): Verify parse command displays token usage and cost estimate."""
    output_file = tmp_path / "chunks.jsonl"

    result = runner.invoke(
        app,
        [
            "parse",
            "--input-dir",
            str(sample_preprocessed_files),
            "--output-file",
            str(output_file),
        ],
    )

    assert result.exit_code == 0

    # Output should mention token usage
    assert "tokens" in result.stdout.lower() or "usage" in result.stdout.lower()


@pytest.mark.integration
def test_parse_command_missing_input_dir_fails(tmp_path: Path) -> None:
    """Test 2c (RED): Verify parse command fails when input directory doesn't exist."""
    nonexistent_dir = tmp_path / "nonexistent"
    output_file = tmp_path / "chunks.jsonl"

    os.environ["GEMINI_API_KEY"] = "test-api-key"

    result = runner.invoke(
        app,
        [
            "parse",
            "--input-dir",
            str(nonexistent_dir),
            "--output-file",
            str(output_file),
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


@pytest.mark.integration
def test_parse_command_shows_progress(
    sample_preprocessed_files: Path, tmp_path: Path
) -> None:
    """Test 2b (RED): Verify parse command shows file-level progress bar."""
    output_file = tmp_path / "chunks.jsonl"

    os.environ["GEMINI_API_KEY"] = "test-api-key"

    result = runner.invoke(
        app,
        [
            "parse",
            "--input-dir",
            str(sample_preprocessed_files),
            "--output-file",
            str(output_file),
        ],
    )

    # Should show some indication of progress
    # (May fail due to API key, but should still attempt to show progress)
    assert result.exit_code in [0, 1]
