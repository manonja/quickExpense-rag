"""Unit tests for extraction pipeline orchestrator."""

from pathlib import Path

import pytest

from src.qe_tax_rag.extraction.ca.orchestrator import run_extraction


def test_orchestrator_module_imports() -> None:
    """Verify orchestrator module and function can be imported."""
    assert callable(run_extraction)


# File Discovery Tests


@pytest.mark.unit
def test_file_discovery_single_file(tmp_path: Path) -> None:
    """Test file discovery for single HTML file."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Execute
    result = run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["total_files"] == 1


@pytest.mark.unit
def test_file_discovery_directory(tmp_path: Path) -> None:
    """Test file discovery for directory of HTML files."""
    # Setup
    (tmp_path / "file1.html").write_text("<html></html>")
    (tmp_path / "file2.html").write_text("<html></html>")
    (tmp_path / "readme.txt").write_text("not html")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Execute
    result = run_extraction(tmp_path, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["total_files"] == 2


@pytest.mark.unit
def test_file_discovery_nonexistent_path(tmp_path: Path) -> None:
    """Test error handling for nonexistent input path."""
    nonexistent = tmp_path / "does_not_exist.html"
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    with pytest.raises(ValueError, match="does not exist"):
        run_extraction(nonexistent, output_yaml, manual_yaml, dry_run=True)


@pytest.mark.unit
def test_file_discovery_empty_directory(tmp_path: Path) -> None:
    """Test error handling for directory with no HTML files."""
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    with pytest.raises(ValueError, match="No HTML files found"):
        run_extraction(tmp_path, output_yaml, manual_yaml, dry_run=True)
