"""Unit tests for extract_rules.py refactoring (T3.3)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


@pytest.mark.unit
@patch("extract_rules.YAMLTransformer")
@patch("extract_rules.run_extraction")
def test_run_extraction_pipeline_returns_stats_and_report(
    mock_run_extraction: MagicMock,
    mock_transformer_class: MagicMock,
    tmp_path: Path,
) -> None:
    """_run_extraction_pipeline should adapt orchestrator output and return (stats, report)."""
    from extract_rules import _run_extraction_pipeline

    # Mock the return value of the canonical orchestrator (new nested structure)
    mock_run_extraction.return_value = {
        "total_files": 1,
        "processed_files": 1,
        "failed_files": [],
        "total_rules": 5,
        "stats": {"perfect_matches": 3, "auto_corrected": 1, "manual_review": 1},
        "manual_review_count": 1,
    }

    # Mock transformer
    mock_report = MagicMock()
    mock_report.successful = 5
    mock_report.total_rules = 5
    mock_report.skipped = 0
    mock_report.errors = []
    mock_transformer = MagicMock()
    mock_transformer.transform_yaml_to_jsonl.return_value = mock_report
    mock_transformer_class.return_value = mock_transformer

    # Setup test files
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

    # Assert orchestrator was called (key new assertion)
    mock_run_extraction.assert_called_once()

    # Assert output structure (adapted from orchestrator)
    assert isinstance(stats, dict)
    assert "total_rules" in stats
    assert stats["total_rules"] == 5
    assert stats["perfect_matches"] == 3
    assert report is not None  # Should have report since jsonl requested
    assert report.successful == 5

    # Verify transformer was called
    assert mock_transformer.transform_yaml_to_jsonl.called


@pytest.mark.unit
@patch("extract_rules.run_extraction")
def test_run_extraction_pipeline_without_transform(
    mock_run_extraction: MagicMock,
    tmp_path: Path,
) -> None:
    """Should work without transformation (output_jsonl=None)."""
    from extract_rules import _run_extraction_pipeline

    # Mock the return value of the canonical orchestrator (new nested structure)
    mock_run_extraction.return_value = {
        "total_files": 1,
        "processed_files": 1,
        "failed_files": [],
        "total_rules": 3,
        "stats": {"perfect_matches": 2, "auto_corrected": 1, "manual_review": 0},
        "manual_review_count": 0,
    }

    # Setup test files
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

    # Assert orchestrator was called
    mock_run_extraction.assert_called_once()

    # Assert output structure
    assert isinstance(stats, dict)
    assert "total_rules" in stats
    assert stats["total_rules"] == 3
    assert stats["perfect_matches"] == 2
    assert report is None  # Should be None when no transformation requested
