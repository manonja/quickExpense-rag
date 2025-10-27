"""PDF page extractor for coverage validation.

Extracts text from PDF pages using pdfplumber in a single pass (no subprocess overhead).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pdfplumber

from scripts.pdf_coverage.normalizer import (
    normalize_text,
    remove_header_footer_patterns,
)

logger = logging.getLogger(__name__)


def extract_pdf_pages(
    pdf_path: str | Path,
    remove_headers: bool = True,
) -> dict[int, str]:
    """Extract text from all PDF pages in single pass.

    Uses pdfplumber to extract text from each page, optionally removes
    common header/footer patterns, and applies text normalization.

    Args:
        pdf_path: Path to PDF file
        remove_headers: If True, remove common header/footer patterns

    Returns:
        Dictionary mapping page numbers (1-indexed) to normalized text

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If PDF extraction fails

    Examples:
        >>> pages = extract_pdf_pages("document.pdf")
        >>> print(f"Extracted {len(pages)} pages")
        Extracted 113 pages

        >>> print(pages[1][:50])
        'chapter 1 - introduction this guide...'

    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    logger.info(f"Extracting text from PDF: {pdf_path}")

    pdf_pages: dict[int, str] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"PDF has {total_pages} pages")

            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract raw text
                raw_text = page.extract_text() or ""

                # Optional: Remove headers/footers
                if remove_headers:
                    raw_text = remove_header_footer_patterns(raw_text)

                # Normalize text
                normalized_text = normalize_text(raw_text)

                pdf_pages[page_num] = normalized_text

                # Log progress every 10 pages
                if page_num % 10 == 0:
                    logger.info(f"Processed {page_num}/{total_pages} pages...")

            logger.info(f"Extraction complete: {total_pages} pages")

    except Exception as e:
        raise ValueError(f"Failed to extract PDF text: {e}") from e

    return pdf_pages


def get_page_count(pdf_path: str | Path) -> int:
    """Get total page count from PDF.

    Lightweight metadata read without extracting text.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Total number of pages

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If PDF parsing fails

    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception as e:
        raise ValueError(f"Failed to get PDF page count: {e}") from e
