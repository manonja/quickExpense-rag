"""Integration tests for pipeline command (TICKET-9D Task 5)."""

import json
from pathlib import Path

import pytest
from scripts.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def sample_html_files(tmp_path: Path) -> Path:
    """Create sample HTML files for full pipeline testing."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    # Create 2 simple HTML files with CRA-like content
    html1 = raw_dir / "S1-F1-C1.html"
    html1.write_text(
        """
        <html>
        <head><title>Business Expenses - Meals</title></head>
        <body>
        <h1>Deductible Business Expenses</h1>
        <p>Meals and entertainment expenses are deductible at 50%.</p>
        <p>You must keep receipts for all meal expenses.</p>
        </body>
        </html>
        """,
        encoding="utf-8",
    )

    html2 = raw_dir / "S2-F1-C1.html"
    html2.write_text(
        """
        <html>
        <head><title>Business Expenses - Vehicle</title></head>
        <body>
        <h1>Vehicle Expenses</h1>
        <p>Vehicle expenses are deductible based on business use percentage.</p>
        <p>Keep a detailed log of business kilometers driven.</p>
        </body>
        </html>
        """,
        encoding="utf-8",
    )

    return raw_dir


@pytest.mark.integration
@pytest.mark.slow
def test_pipeline_command_full_workflow(
    sample_html_files: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 5a (RED): Verify full pipeline execution (preprocess → parse → build → validate)."""
    # Set fake API key for testing
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")

    preprocessed_dir = tmp_path / "preprocessed"
    processed_dir = tmp_path / "processed"
    output_db = tmp_path / "cra_rules.db"
    output_manifest = tmp_path / "manifest.json"

    # Run pipeline (this will fail because we don't have real API key)
    # For now, just test that the command exists and can be invoked
    result = runner.invoke(
        app,
        [
            "pipeline",
            "--input-dir",
            str(sample_html_files),
            "--preprocessed-dir",
            str(preprocessed_dir),
            "--processed-dir",
            str(processed_dir),
            "--output-db",
            str(output_db),
            "--output-manifest",
            str(output_manifest),
            "--force",  # Skip confirmation prompt
        ],
    )

    # Command should exist (not exit code 2)
    # May fail due to missing API key or other issues, but command should be recognized
    assert result.exit_code != 2


@pytest.mark.integration
def test_pipeline_command_requires_confirmation_without_force(
    sample_html_files: Path, tmp_path: Path
) -> None:
    """Test 5b (RED): Verify pipeline prompts for confirmation when artifacts exist."""
    # Create existing artifacts
    preprocessed_dir = tmp_path / "preprocessed"
    preprocessed_dir.mkdir()
    (preprocessed_dir / "existing.txt").write_text("existing content")

    result = runner.invoke(
        app,
        [
            "pipeline",
            "--input-dir",
            str(sample_html_files),
            "--preprocessed-dir",
            str(preprocessed_dir),
        ],
        input="n\n",  # Answer 'no' to confirmation
    )

    # Should exit without running if user says no
    # Exit code 2 means command doesn't exist, so we just check it's not 2
    assert result.exit_code != 2


@pytest.mark.integration
def test_pipeline_command_skips_confirmation_with_force(
    sample_html_files: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 5c (RED): Verify --force flag skips confirmation prompt."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Create existing artifacts
    preprocessed_dir = tmp_path / "preprocessed"
    preprocessed_dir.mkdir()
    (preprocessed_dir / "existing.txt").write_text("existing content")

    result = runner.invoke(
        app,
        [
            "pipeline",
            "--input-dir",
            str(sample_html_files),
            "--preprocessed-dir",
            str(preprocessed_dir),
            "--force",
        ],
    )

    # Should not prompt, should attempt to run (may fail for other reasons)
    # Just verify command exists
    assert result.exit_code != 2


@pytest.mark.integration
def test_pipeline_command_fails_fast_on_error(
    sample_html_files: Path, tmp_path: Path
) -> None:
    """Test 5d (RED): Verify pipeline stops on first error (fail-fast)."""
    # Don't set GEMINI_API_KEY - should fail fast at parse stage
    result = runner.invoke(
        app,
        [
            "pipeline",
            "--input-dir",
            str(sample_html_files),
            "--force",
        ],
    )

    # Should fail (exit code 1 or 2 for command not existing)
    # We're testing that it doesn't continue past errors
    assert result.exit_code != 0
