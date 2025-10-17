"""
Pipeline orchestrator for HTML-to-YAML extraction.

This module provides the core business logic for the extraction pipeline,
coordinating file discovery, parsing, adjudication, and YAML generation.
Designed to be testable without CLI framework dependencies.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def run_extraction(
    input_path: Path,
    output_yaml: Path,
    manual_review_yaml: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Execute the HTML-to-YAML extraction pipeline.

    Args:
        input_path: Path to HTML file or directory of HTML files
        output_yaml: Path for output YAML file
        manual_review_yaml: Path for manual review YAML file
        dry_run: If True, skip YAML file generation

    Returns:
        Dictionary with keys:
        - total_files: Total HTML files discovered
        - processed_files: Successfully processed files
        - failed_files: List of (filename, error_message) tuples
        - total_rules: Total rules extracted
        - stats: Adjudication statistics
        - manual_review_count: Items requiring manual review

    Raises:
        ValueError: If input_path doesn't exist or no HTML files found
        PermissionError: If output directories aren't writable
    """
    logger.info(f"Starting extraction pipeline for {input_path}")

    # Step 1: File discovery
    html_files = _discover_html_files(input_path)

    # TODO: Implement processing logic

    return {
        "total_files": len(html_files),
        "processed_files": 0,
        "failed_files": [],
        "total_rules": 0,
        "stats": {"perfect_matches": 0, "auto_corrected": 0, "manual_review": 0},
        "manual_review_count": 0,
    }


def _discover_html_files(input_path: Path) -> list[Path]:
    """
    Discover HTML files from input path.

    Args:
        input_path: Path to single file or directory

    Returns:
        Sorted list of HTML file paths

    Raises:
        ValueError: If path doesn't exist or no HTML files found
    """
    if not input_path.exists():
        raise ValueError(f"Input path does not exist: {input_path}")

    if input_path.is_file():
        if input_path.suffix.lower() != ".html":
            raise ValueError(f"Input file is not an HTML file: {input_path}")
        return [input_path]

    if input_path.is_dir():
        html_files = sorted(input_path.glob("*.html"))
        if not html_files:
            raise ValueError(f"No HTML files found in directory: {input_path}")
        logger.info(f"Discovered {len(html_files)} HTML files")
        return html_files

    raise ValueError(f"Input path is neither file nor directory: {input_path}")
