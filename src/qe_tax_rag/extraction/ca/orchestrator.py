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
    # TODO: Implement
    return {
        "total_files": 0,
        "processed_files": 0,
        "failed_files": [],
        "total_rules": 0,
        "stats": {"perfect_matches": 0, "auto_corrected": 0, "manual_review": 0},
        "manual_review_count": 0,
    }
