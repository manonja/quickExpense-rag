"""Text normalization utilities for PDF coverage validation.

Normalizes text from both PDF pages and YAML corpus to enable accurate
fuzzy matching despite formatting differences.
"""

import re


def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching.

    Applies aggressive normalization to handle formatting differences between
    PDF extraction (pdfplumber) and YAML structured data.

    Transformations:
    - Convert to lowercase
    - Remove HTML entities (&nbsp;, &mdash;, etc.)
    - Collapse multiple whitespace to single space
    - Strip leading/trailing whitespace

    Args:
        text: Raw text to normalize

    Returns:
        Normalized text suitable for fuzzy matching

    Examples:
        >>> normalize_text("Line 9600 – Other income")
        'line 9600 - other income'

        >>> normalize_text("  Multiple   spaces  ")
        'multiple spaces'

        >>> normalize_text("Test&nbsp;&mdash;&nbsp;Test")
        'test - test'

    """
    # Lowercase
    text = text.lower()

    # Remove common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&mdash;", "-")
    text = text.replace("&ndash;", "-")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")

    # Collapse whitespace (spaces, tabs, newlines) to single space
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace
    return text.strip()


def serialize_table_row(row: dict[str, str]) -> str:
    """Convert table row dict to order-independent string.

    Tables extracted from PDF (pdfplumber) may have columns in different
    order than YAML structured data. This function creates a normalized
    representation by sorting key-value pairs.

    Args:
        row: Table row as dictionary (column_name -> cell_value)

    Returns:
        Order-independent string representation

    Examples:
        >>> serialize_table_row({"Class No.": "10", "Property": "Chain-saws"})
        'Class No.: 10 Property: Chain-saws'

        >>> serialize_table_row({"Property": "Chain-saws", "Class No.": "10"})
        'Class No.: 10 Property: Chain-saws'

    Note:
        Both examples return the same string (sorted by key) despite
        different input order.

    """
    # Create key-value strings
    parts = [f"{k}: {v}" for k, v in row.items()]

    # Sort for order independence
    return " ".join(sorted(parts))


def remove_header_footer_patterns(text: str) -> str:
    """Remove common PDF header/footer patterns.

    Optional preprocessing step to reduce noise from page headers/footers
    that are not present in YAML corpus.

    Common patterns:
    - "T4002 Business and Professional Income 2023"
    - "Page N"
    - "canada.ca/taxes"
    - "Chapter N –"

    Args:
        text: Raw PDF page text

    Returns:
        Text with header/footer patterns removed

    Examples:
        >>> remove_header_footer_patterns("T4002 Business Income 2023\\nContent here")
        'Content here'

        >>> remove_header_footer_patterns("Content\\nPage 42")
        'Content'

    """
    # Remove T4002 header line
    text = re.sub(r"T4002\s+Business.*?20\d{2}", "", text, flags=re.IGNORECASE)

    # Remove "Page N" footers
    text = re.sub(r"Page\s+\d+", "", text, flags=re.IGNORECASE)

    # Remove canada.ca URLs
    text = re.sub(r"canada\.ca/\S+", "", text, flags=re.IGNORECASE)

    # Remove standalone chapter markers
    text = re.sub(r"^Chapter\s+\d+\s*[–-]?\s*$", "", text, flags=re.MULTILINE)

    # Collapse whitespace after removals
    text = re.sub(r"\s+", " ", text)

    return text.strip()
