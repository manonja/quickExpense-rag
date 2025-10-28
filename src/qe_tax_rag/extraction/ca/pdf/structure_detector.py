"""Lightweight structure detection for PDF documents using font metadata.

This module provides simple, deterministic extraction of document structure
(chapters, sections) by analyzing font properties. No LLM calls are made during
structure detection - only local PDF parsing.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemanticSection:
    """Represents a semantic section of a PDF document.

    A semantic section is a logical unit of the document (e.g., a chapter,
    appendix, or major section) with natural boundaries determined by
    heading patterns and font metadata.

    Attributes:
        title: Section title extracted from heading (e.g., "Chapter 3 – Expenses")
        page_range: Tuple of (start_page, end_page) inclusive, 1-indexed
    """

    title: str
    page_range: tuple[int, int]

    def __post_init__(self) -> None:
        """Validate section data."""
        if self.page_range[0] > self.page_range[1]:
            msg = f"Invalid page range: start ({self.page_range[0]}) > end ({self.page_range[1]})"
            raise ValueError(msg)
        if self.page_range[0] < 1:
            msg = f"Page numbers must be >= 1, got {self.page_range[0]}"
            raise ValueError(msg)


def discover_sections(
    pdf_path: Path,
    min_heading_size: float = 15.4,
    heading_pattern: str = r"Chapter \d+",
) -> list[SemanticSection]:
    """Discover semantic sections in a PDF using font-based heading detection.

    This function performs a fast, local analysis of the PDF's visual structure
    to identify chapter/section boundaries. It does not use any LLM calls.

    Algorithm:
    1. Scan all pages for text blocks with font metadata
    2. Identify headings using font size threshold and regex pattern
    3. Build section list where each section spans from one heading to the next

    Args:
        pdf_path: Path to PDF file
        min_heading_size: Minimum font size (in points) to consider as heading
        heading_pattern: Regex pattern to match chapter/section titles

    Returns:
        List of SemanticSection objects representing the document structure.
        The first section always starts at page 1, even if no heading is found there.

    Example:
        >>> sections = discover_sections(Path("T4002.pdf"))
        >>> len(sections)
        18
        >>> sections[0]
        SemanticSection(title="Chapter 1 – General information", page_range=(10, 37))
    """
    logger.info(f"Discovering sections in {pdf_path.name}")

    # Open PDF and extract headings
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    headings: list[tuple[int, str]] = []  # (page_number, heading_text)

    for page_num in range(total_pages):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            # Only process text blocks
            if block["type"] != 0:  # 0 = text, 1 = image
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_size = span.get("size", 0)
                    text = span.get("text", "").strip()

                    # Check if this looks like a heading
                    if font_size >= min_heading_size and text:
                        if re.search(heading_pattern, text):
                            # Convert 0-indexed page to 1-indexed
                            headings.append((page_num + 1, text))
                            logger.debug(
                                f"Found heading on page {page_num + 1}: {text} (size: {font_size:.1f}pt)"
                            )
                            break  # Only take first match per line

    doc.close()

    # Build sections from headings
    sections: list[SemanticSection] = []

    if not headings:
        # No headings found - treat entire document as one section
        logger.warning(
            f"No headings found in {pdf_path.name}. Treating as single section."
        )
        return [SemanticSection(title="Full Document", page_range=(1, total_pages))]

    # Create sections between consecutive headings
    for i, (page_num, heading_text) in enumerate(headings):
        # Determine end page: one page before next heading, or last page
        if i + 1 < len(headings):
            end_page = headings[i + 1][0] - 1
        else:
            end_page = total_pages

        # Handle edge case: heading is on last page
        if page_num > end_page:
            end_page = total_pages

        sections.append(
            SemanticSection(title=heading_text, page_range=(page_num, end_page))
        )

    # If first heading doesn't start at page 1, create intro section
    if headings[0][0] > 1:
        intro = SemanticSection(
            title="Introduction", page_range=(1, headings[0][0] - 1)
        )
        sections.insert(0, intro)

    logger.info(
        f"Discovered {len(sections)} semantic sections covering {total_pages} pages"
    )
    return sections
