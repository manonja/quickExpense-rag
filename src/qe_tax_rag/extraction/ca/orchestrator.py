"""
Pipeline orchestrator for HTML-to-YAML extraction.

This module provides the core business logic for the extraction pipeline,
coordinating file discovery, parsing, adjudication, and YAML generation.
Designed to be testable without CLI framework dependencies.
"""

import logging
from pathlib import Path
from typing import Any

from src.qe_tax_rag.extraction.ca.adjudicator import ManualReviewItem, adjudicate
from src.qe_tax_rag.extraction.ca.classic_parser import parse as classic_parse
from src.qe_tax_rag.extraction.ca.exceptions import PipelineError
from src.qe_tax_rag.extraction.ca.llm_parser import parse as llm_parse
from src.qe_tax_rag.extraction.ca.schema import ExtractedRule
from src.qe_tax_rag.extraction.ca.yaml_generator import generate

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
        YAMLGenerationError: If YAML generation fails
    """
    logger.info(f"Starting extraction pipeline for {input_path}")

    # Step 1: File discovery
    html_files = _discover_html_files(input_path)

    # Step 2: Pre-flight checks (create output directories)
    _preflight_checks(output_yaml, manual_review_yaml)

    # Step 3: Process files
    all_resolved_rules: list[ExtractedRule] = []
    all_manual_review_items: list[ManualReviewItem] = []
    failed_files: list[tuple[str, str]] = []
    stats = {"perfect_matches": 0, "auto_corrected": 0, "manual_review": 0}

    for html_file in html_files:
        try:
            # Read HTML content for adjudicator
            html_content = html_file.read_text(encoding="utf-8")

            # Parse with both parsers
            classic_rules = classic_parse(str(html_file))
            llm_rules = llm_parse(str(html_file))

            # Adjudicate
            resolved_rules, manual_items, file_stats = adjudicate(
                classic_rules=classic_rules,
                llm_rules=llm_rules,
                source_html_content=html_content,
                source_file=html_file.name,
            )

            # Accumulate results
            all_resolved_rules.extend(resolved_rules)
            all_manual_review_items.extend(manual_items)

            # Accumulate stats
            stats["perfect_matches"] += file_stats["perfect_matches"]
            stats["auto_corrected"] += file_stats["auto_corrected"]
            stats["manual_review"] += file_stats["manual_review"]

            logger.info(
                f"Processed {html_file.name}: {len(resolved_rules)} rules extracted"
            )

        except PipelineError as e:
            # Expected pipeline errors (parser/adjudicator failures)
            error_msg = f"{type(e).__name__}: {e}"
            failed_files.append((html_file.name, error_msg))
            logger.error(f"Failed to process {html_file.name}: {error_msg}")
        except Exception as e:  # noqa: BLE001
            # Unexpected errors
            error_msg = f"Unexpected error: {type(e).__name__}: {e}"
            failed_files.append((html_file.name, error_msg))
            logger.exception(f"Unexpected error processing {html_file.name}")

    # Step 4: Generate YAML files (unless dry run)
    if not dry_run:
        # Generate main YAML
        logger.info(f"Generating main YAML with {len(all_resolved_rules)} rules...")
        generate(rules=all_resolved_rules, output_path=str(output_yaml))

        # Generate manual review YAML (only if items exist)
        if all_manual_review_items:
            logger.info(
                f"Generating manual review YAML with {len(all_manual_review_items)} items..."
            )
            # Convert ManualReviewItem to dict for YAML generation
            # Note: generate() expects list[ExtractedRule], but manual review items
            # need different handling. For now, we'll use a workaround.
            # TODO: Consider creating a separate function for manual review YAML
            import yaml

            manual_review_yaml.parent.mkdir(parents=True, exist_ok=True)
            with open(manual_review_yaml, "w", encoding="utf-8") as f:
                yaml.dump(
                    [item.model_dump() for item in all_manual_review_items],
                    f,
                    sort_keys=False,
                    default_flow_style=False,
                    allow_unicode=True,
                )
            logger.info(f"Manual review YAML written to {manual_review_yaml}")

    # Step 5: Return summary
    processed_files = len(html_files) - len(failed_files)

    return {
        "total_files": len(html_files),
        "processed_files": processed_files,
        "failed_files": failed_files,
        "total_rules": len(all_resolved_rules),
        "stats": stats,
        "manual_review_count": len(all_manual_review_items),
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


def _preflight_checks(output_yaml: Path, manual_review_yaml: Path) -> None:
    """
    Perform pre-flight checks and directory creation.

    Args:
        output_yaml: Path for output YAML file
        manual_review_yaml: Path for manual review YAML file

    Raises:
        PermissionError: If output directories aren't writable
    """
    # Create output directories
    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    manual_review_yaml.parent.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Pre-flight checks complete: directories created")
