"""CLI for PDF extraction using lightweight semantic chunking.

This module provides a simple command-line interface to extract structured
content from PDF files using the two-pass approach:
1. Structure discovery (local, no LLM)
2. Content extraction (one LLM call per semantic section)
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
import yaml

from qe_tax_rag.extraction.ca.pdf.llm_client import call_gemini
from qe_tax_rag.extraction.ca.pdf.pdf_parser import parse_section
from qe_tax_rag.extraction.ca.pdf.structure_detector import (
    discover_sections,
    discover_subsections,
)

logger = logging.getLogger(__name__)


def extract_pdf(
    pdf_path: Path,
    output_yaml: Path,
    start_page: int | None = None,
    end_page: int | None = None,
) -> dict:
    """Extract PDF content to YAML using semantic chunking.

    Args:
        pdf_path: Path to PDF file
        output_yaml: Path for output YAML file
        start_page: Optional starting page (1-indexed, for testing)
        end_page: Optional ending page (1-indexed, for testing)

    Returns:
        Dictionary with extraction statistics:
        - total_sections: Number of semantic sections discovered
        - total_chunks: Total ExtractedContent items
        - api_calls: Number of LLM API calls made
        - failed_sections: List of (section_title, error_message) tuples

    Example:
        >>> stats = extract_pdf(
        ...     Path("T4002.pdf"),
        ...     Path("output.yml")
        ... )
        >>> stats['api_calls']
        7
    """
    logger.info(f"Starting PDF extraction from {pdf_path.name}")

    # Pass 1: Discover top-level structure (local, fast)
    logger.info("Pass 1: Discovering document chapters...")
    all_chapters = discover_sections(pdf_path)
    logger.info(f"Discovered {len(all_chapters)} chapters")

    # Filter chapters by page range if specified
    if start_page or end_page:
        start = start_page or 1
        end = end_page or float("inf")
        chapters_to_process = [
            s
            for s in all_chapters
            if s.page_range[0] >= start and s.page_range[1] <= end
        ]
        logger.info(
            f"Filtered to {len(chapters_to_process)} chapters in page range {start}-{end}"
        )
    else:
        chapters_to_process = all_chapters

    # Pass 1.5: Discover subsections within chapters (hierarchical detection)
    logger.info("Pass 1.5: Discovering subsections within chapters...")
    doc = fitz.open(pdf_path)
    processing_units = []

    for chapter in chapters_to_process:
        subsections = discover_subsections(doc, chapter)
        if subsections:
            processing_units.extend(subsections)
            logger.info(
                f"Found {len(subsections)} subsections in '{chapter.title}'"
            )
        else:
            # If no subsections, process the entire chapter as one unit
            processing_units.append(chapter)
            logger.info(
                f"No subsections in '{chapter.title}', processing as a whole"
            )

    doc.close()

    logger.info(
        f"Total processing units: {len(processing_units)} "
        f"(chapters + subsections)"
    )

    # Pass 2: Extract content (LLM per subsection or chapter)
    logger.info("Pass 2: Extracting and structuring content...")
    all_content = []
    failed_sections = []

    for i, unit in enumerate(processing_units, 1):
        logger.info(
            f"Processing unit {i}/{len(processing_units)}: {unit.full_title} "
            f"(pages {unit.page_range[0]}-{unit.page_range[1]})"
        )

        try:
            # Parse unit with Gemini
            chunks = parse_section(
                pdf_path=pdf_path,
                section=unit,
                llm_call_func=call_gemini,
            )
            all_content.extend(chunks)
            logger.info(f"Extracted {len(chunks)} items from {unit.full_title}")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            failed_sections.append((unit.full_title, error_msg))
            logger.error(f"Failed to process {unit.full_title}: {error_msg}")
            # Continue processing other units

    # Generate YAML
    if all_content:
        logger.info(f"Generating YAML with {len(all_content)} items...")

        # Create parent directories
        output_yaml.parent.mkdir(parents=True, exist_ok=True)

        # Create metadata wrapper
        output_data = {
            "schema_version": "1.0",
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "source_file": pdf_path.name,
            "content": json.loads(
                json.dumps([item.model_dump() for item in all_content], default=str)
            ),
        }

        # Write YAML
        with output_yaml.open("w", encoding="utf-8") as f:
            yaml.dump(output_data, f, default_flow_style=False, width=88)

        logger.info(f"YAML written to {output_yaml}")
    else:
        logger.warning("No content extracted, skipping YAML generation")

    # Return stats
    stats = {
        "total_sections": len(processing_units),
        "total_chunks": len(all_content),
        "api_calls": len(processing_units) - len(failed_sections),  # Successful calls only
        "failed_sections": failed_sections,
    }

    logger.info(f"Extraction complete: {stats}")
    return stats


def main() -> int:
    """CLI entry point.

    Usage:
        uv run extract-pdf input.pdf output.yml
        uv run extract-pdf input.pdf output.yml --start-page 10 --end-page 20

    Returns:
        Exit code (0 for success, 1 for error)
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract structured content from PDF using semantic chunking"
    )
    parser.add_argument("pdf_path", type=Path, help="Path to PDF file")
    parser.add_argument("output_yaml", type=Path, help="Path for output YAML file")
    parser.add_argument(
        "--start-page",
        type=int,
        help="Starting page number (1-indexed, for testing)",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        help="Ending page number (1-indexed, for testing)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Validate inputs
    if not args.pdf_path.exists():
        logger.error(f"PDF file not found: {args.pdf_path}")
        return 1

    # Run extraction
    try:
        stats = extract_pdf(
            pdf_path=args.pdf_path,
            output_yaml=args.output_yaml,
            start_page=args.start_page,
            end_page=args.end_page,
        )

        # Print summary
        print(f"\nExtraction Summary:")
        print(f"  Sections processed: {stats['total_sections']}")
        print(f"  Content items extracted: {stats['total_chunks']}")
        print(f"  LLM API calls: {stats['api_calls']}")

        if stats["failed_sections"]:
            print(f"\nFailed sections ({len(stats['failed_sections'])}):")
            for title, error in stats["failed_sections"]:
                print(f"  - {title}: {error}")
            return 1

        print(f"\nYAML written to: {args.output_yaml}")
        return 0

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
