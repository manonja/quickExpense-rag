"""Comprehensive unit tests for extraction pipeline orchestrator.

This file contains the complete test suite for Steps 4-8 of TICKET 6.
Tests are written following TDD approach before implementation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.qe_tax_rag.extraction.ca.exceptions import ParserError, YAMLGenerationError
from src.qe_tax_rag.extraction.ca.orchestrator import run_extraction
from src.qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
)


# Shared fixture for test rules
@pytest.fixture
def sample_rule() -> ExtractedRule:
    """Create a sample ExtractedRule for testing."""
    return ExtractedRule(
        rule_number=8523,
        title="Test Rule",
        content="Test content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id=None,
        confidence_score=1.0,
    )


# Step 4: Pre-flight Directory Creation Tests


@pytest.mark.unit
def test_preflight_creates_output_directories(tmp_path: Path) -> None:
    """Test that output directories are created if they don't exist."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    output_yaml = tmp_path / "nested" / "output" / "rules.yml"
    manual_yaml = tmp_path / "nested" / "manual.yml"

    run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    assert output_yaml.parent.exists()
    assert manual_yaml.parent.exists()


# Step 5: File Processing Loop Tests


@pytest.mark.unit
@patch("src.qe_tax_rag.extraction.ca.orchestrator.adjudicate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.llm_parse")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_processing_single_file_success(
    mock_classic: MagicMock,
    mock_llm: MagicMock,
    mock_adjudicate: MagicMock,
    tmp_path: Path,
    sample_rule: ExtractedRule,
) -> None:
    """Test successful processing of single HTML file."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><h3>Line 8523 – Test</h3><p>Content</p></html>")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Mock parser outputs
    mock_classic.return_value = [sample_rule]
    mock_llm.return_value = [sample_rule]
    mock_adjudicate.return_value = (
        [sample_rule],  # resolved_rules
        [],  # manual_review_items
        {"perfect_matches": 1, "auto_corrected": 0, "manual_review": 0},
    )

    # Execute
    result = run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["total_files"] == 1
    assert result["processed_files"] == 1
    assert result["failed_files"] == []
    assert result["total_rules"] == 1
    assert result["stats"]["perfect_matches"] == 1

    # Verify calls
    mock_classic.assert_called_once_with(str(html_file))
    mock_llm.assert_called_once_with(str(html_file))
    mock_adjudicate.assert_called_once()


@pytest.mark.unit
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_processing_handles_parser_error(
    mock_classic: MagicMock,
    tmp_path: Path,
) -> None:
    """Test graceful handling of parser errors."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html>malformed</html>")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Mock parser error
    mock_classic.side_effect = ParserError("Parse failed")

    # Execute
    result = run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["total_files"] == 1
    assert result["processed_files"] == 0
    assert len(result["failed_files"]) == 1
    assert "test.html" in result["failed_files"][0][0]
    assert "Parse failed" in result["failed_files"][0][1]


# Step 6: Statistics Accumulation Tests


@pytest.mark.unit
@patch("src.qe_tax_rag.extraction.ca.orchestrator.adjudicate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.llm_parse")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_stats_accumulation_multiple_files(
    mock_classic: MagicMock,
    mock_llm: MagicMock,
    mock_adjudicate: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that statistics are correctly accumulated across multiple files."""
    (tmp_path / "file1.html").write_text("<html></html>")
    (tmp_path / "file2.html").write_text("<html></html>")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Mock returns
    mock_classic.return_value = []
    mock_llm.return_value = []

    # File 1: 2 perfect matches, 1 auto-corrected
    # File 2: 1 perfect match, 1 manual review
    mock_adjudicate.side_effect = [
        ([], [], {"perfect_matches": 2, "auto_corrected": 1, "manual_review": 0}),
        ([], [], {"perfect_matches": 1, "auto_corrected": 0, "manual_review": 1}),
    ]

    # Execute
    result = run_extraction(tmp_path, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["stats"]["perfect_matches"] == 3
    assert result["stats"]["auto_corrected"] == 1
    assert result["stats"]["manual_review"] == 1


# Step 7: YAML Generation Integration Tests


@pytest.mark.unit
@patch("src.qe_tax_rag.extraction.ca.orchestrator.generate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.adjudicate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.llm_parse")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_yaml_generation_dry_run_skips_files(
    mock_classic: MagicMock,
    mock_llm: MagicMock,
    mock_adjudicate: MagicMock,
    mock_generate: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that dry_run=True skips YAML file generation."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    mock_classic.return_value = []
    mock_llm.return_value = []
    mock_adjudicate.return_value = (
        [],
        [],
        {"perfect_matches": 0, "auto_corrected": 0, "manual_review": 0},
    )

    # Execute
    run_extraction(html_file, tmp_path / "out.yml", tmp_path / "manual.yml", dry_run=True)

    # Assert
    mock_generate.assert_not_called()


@pytest.mark.unit
@patch("src.qe_tax_rag.extraction.ca.orchestrator.generate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.adjudicate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.llm_parse")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_yaml_generation_creates_main_file(
    mock_classic: MagicMock,
    mock_llm: MagicMock,
    mock_adjudicate: MagicMock,
    mock_generate: MagicMock,
    tmp_path: Path,
    sample_rule: ExtractedRule,
) -> None:
    """Test that main YAML file is generated when dry_run=False."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    output_yaml = tmp_path / "out.yml"
    manual_yaml = tmp_path / "manual.yml"

    mock_classic.return_value = []
    mock_llm.return_value = []
    mock_adjudicate.return_value = (
        [sample_rule],
        [],
        {"perfect_matches": 1, "auto_corrected": 0, "manual_review": 0},
    )

    # Execute
    run_extraction(html_file, output_yaml, manual_yaml, dry_run=False)

    # Assert - generate called once for main YAML (not manual review since empty)
    assert mock_generate.call_count == 1
    call_args = mock_generate.call_args
    assert call_args[1]["output_path"] == str(output_yaml)


# Step 8: Error Handling Tests


@pytest.mark.unit
@patch("src.qe_tax_rag.extraction.ca.orchestrator.generate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.adjudicate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.llm_parse")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_error_handling_yaml_generation_failure(
    mock_classic: MagicMock,
    mock_llm: MagicMock,
    mock_adjudicate: MagicMock,
    mock_generate: MagicMock,
    tmp_path: Path,
    sample_rule: ExtractedRule,
) -> None:
    """Test that YAMLGenerationError is propagated to caller."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")

    mock_classic.return_value = []
    mock_llm.return_value = []
    mock_adjudicate.return_value = (
        [sample_rule],
        [],
        {"perfect_matches": 1, "auto_corrected": 0, "manual_review": 0},
    )

    # Mock YAML generation failure
    mock_generate.side_effect = YAMLGenerationError("Disk full")

    # Execute & Assert
    with pytest.raises(YAMLGenerationError, match="Disk full"):
        run_extraction(
            html_file, tmp_path / "out.yml", tmp_path / "manual.yml", dry_run=False
        )
