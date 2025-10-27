"""
Principle parser for extracting rule references from CRA HTML documents.

This parser extracts text that references line-numbered rules but isn't a
rule definition. Principles are paragraphs or list items that mention line
numbers in instructional or cross-reference context.

Phase 2 Implementation: PRINCIPLE content type
"""

import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from .exceptions import ParserError
from .models import ContentType, ExtractedContent

logger = logging.getLogger(__name__)


def extract_line_references(text: str) -> list[str]:
    """
    Extract LINE-XXXX references from text.

    Searches for patterns like "line 9600", "Line 8523", etc. and converts
    them to canonical LINE-XXXX format.

    Args:
        text: Text to search for line references

    Returns:
        List of LINE-XXXX references (e.g., ["LINE-9600", "LINE-8523"])
        Sorted and deduplicated.

    Example:
        >>> text = "Enter on line 9925 the total. Also see line 9600."
        >>> extract_line_references(text)
        ['LINE-9600', 'LINE-9925']

    """
    # Pattern: "line" followed by whitespace and 4 digits
    # Matches: "line 9600", "Line 8523", "LINE 9270"
    pattern = r"\bline\s+(\d{4})\b"
    matches = re.findall(pattern, text, re.IGNORECASE)

    # Convert to canonical format and deduplicate
    references = sorted(set(f"LINE-{num}" for num in matches))

    return references


def is_rule_definition(tag: Tag) -> bool:
    """
    Check if tag is a rule definition (not just a reference).

    Rule definitions have anchor IDs matching pattern: id="tocch2ln9600"
    Rule references don't have anchor IDs (e.g., <span>line 9600</span>)

    This function is imported from classic_parser logic to ensure consistency.

    Args:
        tag: BeautifulSoup Tag element to check.

    Returns:
        True if tag has an anchor child with id matching "tocch\\dln\\d{4}" pattern.

    Example:
        >>> # Definition: <h3><a id="tocch2ln9600"></a>Line 9600 – Other income</h3>
        >>> is_rule_definition(definition_tag)
        True
        >>> # Reference: <p>Enter on <span>line 9600</span>...</p>
        >>> is_rule_definition(reference_tag)
        False

    """
    anchor_tag = tag.find("a")
    if not anchor_tag:
        return False
    anchor_id = anchor_tag.get("id")
    if not anchor_id:
        return False
    # Pattern: tocch{chapter}ln{4-digit line number}[optional suffix]
    # Examples: tocch2ln9600, tocch3ln8523, tocch2ln8299fshng
    return bool(re.match(r"^tocch\dln\d{4}(?:\w+)?$", anchor_id))


def parse(html_path: str) -> list[ExtractedContent]:
    """
    Extract principles (rule references) from HTML file.

    Searches <p> and <li> tags for text containing line number references
    (e.g., "Enter on line 9925..."). Excludes any tags that are rule definitions
    (i.e., where is_rule_definition() returns True).

    Args:
        html_path: Absolute path to HTML file.

    Returns:
        List of ExtractedContent objects with content_type=PRINCIPLE.
        Returns empty list if no principles found.

    Raises:
        ParserError: If file cannot be read.

    Example:
        >>> principles = parse("/path/to/t4002-6.html")
        >>> len(principles)
        42
        >>> principles[0].content_type
        <ContentType.PRINCIPLE: 'PRINCIPLE'>
        >>> principles[0].references
        ['LINE-9925']

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

    principles: list[ExtractedContent] = []
    seq = 1

    # Search <p> and <li> tags for line references
    for tag in soup.find_all(["p", "li"]):
        # Skip if this is a rule definition (e.g., h3 with anchor ID)
        if is_rule_definition(tag):
            continue

        # Extract text and look for line references
        text = tag.get_text(strip=True, separator=" ")
        references = extract_line_references(text)

        # Only create principle if text contains line references
        if references:
            try:
                principle = ExtractedContent(
                    citation_id=f"{Path(source_file).stem}-PRINCIPLE-{seq}",
                    content_type=ContentType.PRINCIPLE,
                    text=text,
                    source_file=source_file,
                    anchor_id=None,
                    references=references,
                )
                principles.append(principle)
                seq += 1
            except Exception as e:
                # Log warning but continue processing (resilient to individual failures)
                logger.warning(
                    f"Failed to create principle {seq} from {source_file}: {e}"
                )

    logger.info(f"Extracted {len(principles)} principles from {source_file}")
    return principles
