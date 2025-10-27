"""
Table parser for extracting structured tabular data from CRA HTML documents.

This parser extracts HTML tables and converts them to structured list-of-dictionaries
format suitable for RAG applications. Tables are extracted with their column headers
and row data preserved.

Phase 3 Implementation: TABLE content type
"""

import logging
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from .exceptions import ParserError
from .models import ContentType, ExtractedContent

logger = logging.getLogger(__name__)


def extract_table_data(table_tag: Tag) -> list[dict[str, str]] | None:
    """
    Extract structured data from a single table element.

    Extracts column headers from <thead> and row data from <tbody>, converting
    to a list of dictionaries where each dictionary represents one row with
    column names as keys.

    Args:
        table_tag: BeautifulSoup Tag element for <table>

    Returns:
        List of row dictionaries, or None if table cannot be extracted.
        Returns None for tables without <thead> or <tbody>, or with mismatched
        column counts.

    Example:
        >>> # <table>
        >>> #   <thead><tr><th>Property</th><th>Class</th></tr></thead>
        >>> #   <tbody><tr><td>Chain-saws</td><td>10</td></tr></tbody>
        >>> # </table>
        >>> extract_table_data(table_tag)
        [{"Property": "Chain-saws", "Class": "10"}]

    Known Limitations (80/20 baseline):
        - No support for colspan/rowspan (simple grid only)
        - Nested tables extracted flat (loses hierarchy)
        - No caption/title extraction
        - Assumes consistent column counts across rows
    """
    # Extract headers from <thead>
    thead = table_tag.find("thead")
    if not thead:
        logger.debug("Skipping table without <thead>")
        return None

    headers = [th.get_text(strip=True) for th in thead.find_all("th")]
    if not headers:
        logger.debug("Skipping table with empty <thead>")
        return None

    # Extract rows from <tbody>
    tbody = table_tag.find("tbody")
    if not tbody:
        logger.debug("Skipping table without <tbody>")
        return None

    table_data: list[dict[str, str]] = []
    for row in tbody.find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]

        # Skip rows with mismatched column count (graceful degradation)
        if len(cells) != len(headers):
            logger.warning(
                f"Skipping row with {len(cells)} cells (expected {len(headers)})"
            )
            continue

        # Create row dictionary with headers as keys
        row_dict = dict(zip(headers, cells))
        table_data.append(row_dict)

    # Return None if no valid rows extracted
    if not table_data:
        logger.debug("Skipping table with no valid rows")
        return None

    return table_data


def parse(html_path: str) -> list[ExtractedContent]:
    """
    Extract tables from HTML file.

    Searches for <table> tags with <thead> and <tbody> structure, extracting
    structured data as list of dictionaries. Each table is converted to an
    ExtractedContent object with content_type=TABLE.

    Args:
        html_path: Absolute path to HTML file.

    Returns:
        List of ExtractedContent objects with content_type=TABLE.
        Returns empty list if no tables found.

    Raises:
        ParserError: If file cannot be read.

    Example:
        >>> tables = parse("/path/to/t4002-10.html")
        >>> len(tables)
        2
        >>> tables[0].content_type
        <ContentType.TABLE: 'TABLE'>
        >>> tables[0].citation_id
        't4002-10-TABLE-1'
        >>> tables[0].table_data[0]
        {'Property': 'Chain-saws', 'Class number': '10'}

    Known Limitations (80/20 baseline):
        - No support for colspan/rowspan (simple grid only)
        - Nested tables extracted flat (loses hierarchy)
        - Tables without <thead>/<tbody> skipped with warnings
        - No caption/title extraction
        - Assumes consistent column counts across rows
    """
    # Read HTML file
    try:
        html_content = Path(html_path).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise ParserError(f"HTML file not found: {html_path}") from e
    except Exception as e:
        raise ParserError(f"Failed to read HTML file {html_path}: {e}") from e

    soup = BeautifulSoup(html_content, "lxml")
    source_file = Path(html_path).name

    tables: list[ExtractedContent] = []
    seq = 1

    # Search for all <table> tags
    for table_tag in soup.find_all("table"):
        # Extract structured data from table
        table_data = extract_table_data(table_tag)

        # Skip tables that couldn't be extracted
        if table_data is None:
            continue

        try:
            # Create ExtractedContent with TABLE type
            table_content = ExtractedContent(
                citation_id=f"{Path(source_file).stem}-TABLE-{seq}",
                content_type=ContentType.TABLE,
                text=f"Table {seq} from {source_file}",
                source_file=source_file,
                anchor_id=None,
                references=[],
                table_data=table_data,
            )
            tables.append(table_content)
            seq += 1
        except Exception as e:
            # Log warning but continue processing (resilient to individual failures)
            logger.warning(f"Failed to create table {seq} from {source_file}: {e}")

    logger.info(f"Extracted {len(tables)} tables from {source_file}")
    return tables
