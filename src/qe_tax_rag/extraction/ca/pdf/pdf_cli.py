"""CLI for PDF extraction using lightweight semantic chunking.

This module provides a simple command-line interface to extract structured
content from PDF files using the two-pass approach:
1. Structure discovery (local, no LLM)
2. Content extraction (one LLM call per semantic section)
"""

import logging
import sys
from pathlib import Path

from qe_tax_rag.extraction.ca.pdf.llm_client import call_gemini
from qe_tax_rag.extraction.ca.pdf.pdf_parser import parse_section
from qe_tax_rag.extraction.ca.pdf.structure_detector import discover_sections
from qe_tax_rag.extraction.ca.yaml_generator import generate

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

    # Pass 1: Discover structure (local, fast)
    logger.info("Pass 1: Discovering document structure...")
    all_sections = discover_sections(pdf_path)
    logger.info(f"Discovered {len(all_sections)} semantic sections")

    # Filter sections by page range if specified
    if start_page or end_page:
        start = start_page or 1
        end = end_page or float("inf")
        sections = [
            s
            for s in all_sections
            if s.page_range[0] >= start and s.page_range[1] <= end
        ]
        logger.info(
            f"Filtered to {len(sections)} sections in page range {start}-{end}"
        )
    else:
        sections = all_sections

    # Pass 2: Extract content (LLM per section)
    logger.info("Pass 2: Extracting and structuring content...")
    all_content = []
    failed_sections = []

    for i, section in enumerate(sections, 1):
        logger.info(
            f"Processing section {i}/{len(sections)}: {section.title} "
            f"(pages {section.page_range[0]}-{section.page_range[1]})"
        )

        try:
            # Parse section with Gemini
            chunks = parse_section(
                pdf_path=pdf_path,
                section=section,
                llm_call_func=call_gemini,
            )
            all_content.extend(chunks)
            logger.info(f"Extracted {len(chunks)} items from {section.title}")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            failed_sections.append((section.title, error_msg))
            logger.error(f"Failed to process {section.title}: {error_msg}")
            # Continue processing other sections

    # Generate YAML
    if all_content:
        logger.info(f"Generating YAML with {len(all_content)} items...")
        generate(content=all_content, output_path=output_yaml)
        logger.info(f"YAML written to {output_yaml}")
    else:
        logger.warning("No content extracted, skipping YAML generation")

    # Return stats
    stats = {
        "total_sections": len(sections),
        "total_chunks": len(all_content),
        "api_calls": len(sections) - len(failed_sections),  # Successful calls only
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
