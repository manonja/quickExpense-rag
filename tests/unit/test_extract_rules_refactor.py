"""Unit tests for extract_rules.py refactoring (T3.3)."""

import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from extract_rules import _run_extraction_pipeline  # noqa: E402


@pytest.mark.unit
def test_run_extraction_pipeline_returns_stats_and_report(tmp_path: Path) -> None:
    """_run_extraction_pipeline should return (stats, report) tuple."""
    # Setup: Create minimal test HTML
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    html_file = html_dir / "test.html"
    html_file.write_text("""
    <html>
    <body>
    <h2>Line 8523</h2>
    <p>Meals and entertainment expenses...</p>
    </body>
    </html>
    """)

    output_yaml = tmp_path / "rules.yml"
    manual_yaml = tmp_path / "manual.yml"
    output_jsonl = tmp_path / "chunks.jsonl"

    # Execute
    stats, report = _run_extraction_pipeline(
        html_files=[html_file],
        output_yaml=output_yaml,
        manual_review_yaml=manual_yaml,
        output_jsonl=output_jsonl,
        verbose=False,
    )

    # Assert
    assert isinstance(stats, dict)
    assert "total_rules" in stats
    assert report is not None  # Should have report since jsonl requested
    assert output_yaml.exists()
    assert output_jsonl.exists()


@pytest.mark.unit
def test_run_extraction_pipeline_without_transform(tmp_path: Path) -> None:
    """Should work without transformation (output_jsonl=None)."""
    # Setup
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    html_file = html_dir / "test.html"
    html_file.write_text("""
    <html>
    <body>
    <h2>Line 8523</h2>
    <p>Vehicle expenses are partially deductible.</p>
    </body>
    </html>
    """)

    output_yaml = tmp_path / "rules.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Execute - no output_jsonl, so no transformation
    stats, report = _run_extraction_pipeline(
        html_files=[html_file],
        output_yaml=output_yaml,
        manual_review_yaml=manual_yaml,
        output_jsonl=None,  # Key difference: no JSONL transformation
        verbose=False,
    )

    # Assert
    assert isinstance(stats, dict)
    assert "total_rules" in stats
    assert report is None  # Should be None when no transformation requested
    assert output_yaml.exists()
