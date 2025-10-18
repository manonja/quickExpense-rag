"""
Classic rule-based HTML parser for CRA tax documents.

This parser serves as the "classic" expert in the Mixture-of-Experts extraction
pipeline. It uses BeautifulSoup and rule-based logic to extract line-numbered
expense rules from CRA T4002 HTML documents.

Extraction scope: Only h3 tags matching "Line XXXX –" pattern.
"""

import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from .exceptions import ParserError
from .schema import ApplicabilityType, ExpertSource, ExtractedRule

logger = logging.getLogger(__name__)

# Icon alt text to ApplicabilityType mapping
ICON_MAPPING = {
    "business icon": ApplicabilityType.BUSINESS,
    "farm icon": ApplicabilityType.FARMING,
    "fish icon": ApplicabilityType.FISHING,
}


def parse(html_path: str) -> list[ExtractedRule]:
    """
    Parse HTML file to extract line-numbered tax rules.

    Extracts only h3 tags matching "Line XXXX –" pattern using rule-based
    BeautifulSoup parsing. Resilient to individual rule failures - skips
    malformed rules with logged warnings.

    Uses robust sibling-based content collection to handle varied HTML
    structures. Extracts context fields (chapter, section, anchor_id) for
    navigation and debugging.

    Args:
        html_path: Absolute path to HTML file.

    Returns:
        List of ExtractedRule objects with expert_source=CLASSIC.
        Returns empty list if no line-numbered rules found (e.g., CCA chapters).

    Raises:
        ParserError: If file cannot be read.

    Example:
        >>> rules = parse("/path/to/t4002-5.html")
        >>> len(rules)
        127
        >>> rules[0].rule_number
        8523
        >>> rules[0].title
        'Meals and entertainment'

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

    # Extract global chapter from h1
    h1_tag = soup.find("h1")
    chapter = h1_tag.get_text(strip=True) if h1_tag else "Unknown Chapter"

    # Find all h3 tags matching "Line XXXX –" pattern using function
    def is_line_rule(tag: Tag) -> bool:
        if tag.name != "h3":
            return False
        text = tag.get_text(strip=True)
        return re.match(r"^\s*Line \d+ –", text) is not None

    rule_headers = soup.find_all(is_line_rule)

    if not rule_headers:
        logger.warning(
            f"No line-numbered rules found in {source_file}. "
            "This file may contain different content (e.g., CCA sections, introductory chapters)."
        )
        return []

    extracted_rules: list[ExtractedRule] = []

    for header in rule_headers:
        try:
            # Extract rule_number and title from header text
            header_text = header.get_text(strip=True)
            # Remove any img tag remnants from header_text for clean parsing
            clean_header = re.sub(r"<img[^>]*>", "", header_text)
            match = re.search(r"Line (\d+) –\s*(.+)", clean_header)
            if not match:
                logger.warning(f"Skipping h3 with unparseable format: '{header_text}'")
                continue

            rule_number = int(match.group(1))
            title = match.group(2).strip()

            # Extract applies_to from img tags within h3
            applies_to = _extract_applies_to(header)

            # Extract section from previous h2 sibling (Zen's lookback pattern)
            section_tag = header.find_previous_sibling("h2")
            section = section_tag.get_text(strip=True) if section_tag else None

            # Extract anchor_id from <a> tag within h3
            anchor_tag = header.find("a")
            anchor_id = anchor_tag.get("id") if anchor_tag else None

            # Collect content from subsequent siblings (Zen's robust pattern)
            content_parts = []
            for sibling in header.find_next_siblings():
                if sibling.name == "h3":
                    break
                if sibling.name in ["p", "ul", "ol"]:
                    content_parts.append(sibling.get_text(strip=True))

            if not content_parts:
                logger.warning(
                    f"Skipping Line {rule_number} ('{title}'): no content found"
                )
                continue

            # Normalize content (max 2 consecutive newlines)
            raw_content = "\n\n".join(content_parts)
            content = re.sub(r"\n{3,}", "\n\n", raw_content).strip()

            # Create ExtractedRule
            rule = ExtractedRule(
                rule_number=rule_number,
                title=title,
                content=content,
                applies_to=applies_to,
                source_citation=f"Line {rule_number}",
                chapter=chapter,
                section=section,
                source_file=source_file,
                expert_source=ExpertSource.CLASSIC,
                anchor_id=anchor_id,
                confidence_score=1.0,  # Deterministic parser
            )
            extracted_rules.append(rule)

        except Exception as e:
            logger.warning(
                f"Skipping malformed rule '{header.get_text(strip=True)}': {e}"
            )
            continue

    return extracted_rules


def _extract_applies_to(header_tag: Tag) -> list[ApplicabilityType]:
    """
    Extract applicability types from img tags within header.

    Maps icon alt text to ApplicabilityType enum values. Handles multiple
    icons gracefully, returning a list of unique applicability types.

    Args:
        header_tag: BeautifulSoup h3 tag element.

    Returns:
        List of ApplicabilityType enums. Empty list if no icons found.

    Example:
        >>> header = soup.find("h3")
        >>> applies_to = _extract_applies_to(header)
        >>> applies_to
        [ApplicabilityType.BUSINESS, ApplicabilityType.FARMING]

    """
    applies_to = []
    img_tags = header_tag.find_all("img")

    for img in img_tags:
        alt_text = img.get("alt", "").strip().lower()
        if alt_text in ICON_MAPPING:
            applicability_type = ICON_MAPPING[alt_text]
            if applicability_type not in applies_to:
                applies_to.append(applicability_type)

    return applies_to
