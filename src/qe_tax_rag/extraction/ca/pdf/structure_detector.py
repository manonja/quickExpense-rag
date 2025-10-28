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
        parent_title: Optional parent section title for hierarchical structure
            (e.g., subsection "Fiscal period" has parent "Chapter 1 – General information")
    """

    title: str
    page_range: tuple[int, int]
    parent_title: str | None = None

    def __post_init__(self) -> None:
        """Validate section data."""
        if self.page_range[0] > self.page_range[1]:
            msg = f"Invalid page range: start ({self.page_range[0]}) > end ({self.page_range[1]})"
            raise ValueError(msg)
        if self.page_range[0] < 1:
            msg = f"Page numbers must be >= 1, got {self.page_range[0]}"
            raise ValueError(msg)

    @property
    def full_title(self) -> str:
        """Return the fully qualified title including parent context.

        Returns:
            If parent_title exists: "Parent Title: Subsection Title"
            Otherwise: "Section Title"

        Example:
            >>> section = SemanticSection("Fiscal period", (10, 13), "Chapter 1")
            >>> section.full_title
            "Chapter 1: Fiscal period"
        """
        if self.parent_title:
            return f"{self.parent_title}: {self.title}"
        return self.title


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


def discover_subsections(
    doc: fitz.Document,
    parent_section: SemanticSection,
    min_heading_size: float = 13.0,
    max_heading_size: float = 15.0,
) -> list[SemanticSection]:
    """Discover subsections within a parent section's page range.

    This function performs fine-grained structure detection within a larger
    section (e.g., chapter) to identify subsection boundaries. It uses font
    size heuristics to find intermediate-level headings.

    Algorithm:
    1. Scan pages within parent section's range
    2. Identify subsection headings using font size thresholds
    3. Build subsection list where each subsection spans from one heading to the next
    4. Handle intro content before first subheading

    Args:
        doc: Open PyMuPDF document handle
        parent_section: The parent SemanticSection to subdivide
        min_heading_size: Minimum font size (in points) for subsection headings
        max_heading_size: Maximum font size (in points) for subsection headings

    Returns:
        List of SemanticSection objects representing subsections within the parent.
        Empty list if no subsections are found (process parent as a whole).
        Each subsection has parent_title set to parent_section.title.

    Example:
        >>> doc = fitz.open("T4002.pdf")
        >>> chapter1 = SemanticSection("Chapter 1 – General information", (10, 23))
        >>> subsections = discover_subsections(doc, chapter1)
        >>> len(subsections)
        4
        >>> subsections[0].full_title
        "Chapter 1 – General information: Fiscal period"
    """
    logger.debug(
        f"Discovering subsections in {parent_section.title} "
        f"(pages {parent_section.page_range[0]}-{parent_section.page_range[1]})"
    )

    subheadings: list[tuple[int, str]] = []  # (page_number, heading_text)
    start_page, end_page = parent_section.page_range
    total_pages = len(doc)

    # Scan parent section's page range
    for page_num in range(start_page - 1, min(end_page, total_pages)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            # Only process text blocks
            if block["type"] != 0:  # 0 = text, 1 = image
                continue

            for line in block.get("lines", []):
                # Heuristic: subsection headings are typically single-span lines
                if len(line.get("spans", [])) != 1:
                    continue

                span = line["spans"][0]
                font_size = span.get("size", 0)
                text = span.get("text", "").strip()

                # Check if this looks like a subsection heading
                if min_heading_size <= font_size <= max_heading_size and text:
                    # Convert 0-indexed page to 1-indexed
                    subheadings.append((page_num + 1, text))
                    logger.debug(
                        f"Found subsection heading on page {page_num + 1}: {text} "
                        f"(size: {font_size:.1f}pt)"
                    )
                    break  # Only take first match per line

    # No subsections found - return empty list
    if not subheadings:
        logger.debug(f"No subsections found in {parent_section.title}")
        return []

    # Build subsections from subheadings
    subsections: list[SemanticSection] = []

    for i, (page_num, heading_text) in enumerate(subheadings):
        # Determine end page: one page before next subheading, or parent's end page
        if i + 1 < len(subheadings):
            sub_end_page = subheadings[i + 1][0] - 1
        else:
            sub_end_page = end_page

        # Handle edge case: subheading is on last page of parent
        if page_num > sub_end_page:
            sub_end_page = end_page

        subsections.append(
            SemanticSection(
                title=heading_text,
                page_range=(page_num, sub_end_page),
                parent_title=parent_section.title,
            )
        )

    # Check if content exists before the first subheading
    if subheadings and subheadings[0][0] > start_page:
        # Create an intro subsection for content before first subheading
        intro_subsection = SemanticSection(
            title=f"{parent_section.title} (Introduction)",
            page_range=(start_page, subheadings[0][0] - 1),
            parent_title=parent_section.title,
        )
        subsections.insert(0, intro_subsection)

    logger.debug(
        f"Discovered {len(subsections)} subsections in {parent_section.title}"
    )
    return subsections
