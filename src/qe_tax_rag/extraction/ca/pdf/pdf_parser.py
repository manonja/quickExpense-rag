"""PDF content extraction and structuring using pdfplumber and LLM.

This module extracts content from PDF semantic sections and structures it
using an LLM (Gemini). It handles both text and table extraction.
"""

import json
import logging
from pathlib import Path

import pdfplumber

from qe_tax_rag.extraction.ca.models import ContentType, ExtractedContent
from qe_tax_rag.extraction.ca.pdf.structure_detector import SemanticSection

logger = logging.getLogger(__name__)


def extract_section_content(
    pdf_path: Path,
    section: SemanticSection,
) -> tuple[str, list[dict]]:
    """Extract raw text and tables from a PDF section using pdfplumber.

    Args:
        pdf_path: Path to PDF file
        section: SemanticSection with page range to extract

    Returns:
        Tuple of (consolidated_text, tables)
        - consolidated_text: All text from the section pages
        - tables: List of table data (each table is list of row dicts)

    Example:
        >>> text, tables = extract_section_content(
        ...     Path("T4002.pdf"),
        ...     SemanticSection("Chapter 3", (38, 68))
        ... )
        >>> len(text)
        15234
        >>> len(tables)
        3
    """
    logger.info(
        f"Extracting content from {section.title} "
        f"(pages {section.page_range[0]}-{section.page_range[1]})"
    )

    text_blocks: list[str] = []
    tables: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        # Extract from page range (convert 1-indexed to 0-indexed)
        start_idx = section.page_range[0] - 1
        end_idx = section.page_range[1]  # pdfplumber slicing is exclusive on end

        for page_num, page in enumerate(
            pdf.pages[start_idx:end_idx], start=section.page_range[0]
        ):
            # Extract text
            page_text = page.extract_text()
            if page_text:
                text_blocks.append(f"--- Page {page_num} ---\n{page_text}")

            # Extract tables
            page_tables = page.extract_tables()
            for table_idx, table in enumerate(page_tables):
                if table and len(table) > 1:  # Has headers + rows
                    # Convert to list of dicts (filter None values)
                    headers = [h or f"Column{i}" for i, h in enumerate(table[0])]
                    rows = []
                    for row in table[1:]:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                row_dict[header] = row[i] or ""
                        rows.append(row_dict)

                    tables.append(
                        {
                            "page_number": page_num,
                            "table_index": table_idx,
                            "headers": headers,
                            "rows": rows,
                        }
                    )

    consolidated_text = "\n\n".join(text_blocks)
    logger.debug(
        f"Extracted {len(consolidated_text)} chars of text and {len(tables)} tables"
    )

    return consolidated_text, tables


def build_llm_prompt(
    section: SemanticSection,
    text: str,
    tables: list[dict],
) -> str:
    """Build detailed LLM prompt for content structuring.

    Args:
        section: SemanticSection being processed
        text: Consolidated text from section
        tables: Extracted tables metadata

    Returns:
        Formatted prompt string for LLM
    """
    table_summary = ""
    if tables:
        table_summary = f"\n\nThe section contains {len(tables)} table(s):\n"
        for i, table in enumerate(tables, 1):
            table_summary += (
                f"- Table {i}: Page {table['page_number']}, "
                f"columns: {', '.join(table['headers'])}\n"
            )

    return f"""You are extracting structured content from "{section.title}"
(pages {section.page_range[0]}-{section.page_range[1]}) of the T4002 CRA Business Expenses Guide.

Extract ALL instances of these content types:
- RULE: Tax rules with line numbers (e.g., "Line 8523 – Meals and entertainment")
- PRINCIPLE: Cross-references to other sections/forms (e.g., "See Chapter 4 for...")
- DEFINITION: Glossary terms and definitions
- FORMULA: Calculation methods and examples with numbers
- TABLE: Reference to structured data (tables are extracted separately)
- EXAMPLE: Illustrative cases showing how to apply rules

For each item, provide:
- type: One of [RULE, PRINCIPLE, DEFINITION, FORMULA, TABLE, EXAMPLE]
- text: Full text content (complete sentences/paragraphs)
- page_number: Specific page where this item appears (must be within {section.page_range[0]}-{section.page_range[1]})
- applies_to: Array of business types this applies to ["business", "farming", "fishing"]
  (default to ["business", "farming", "fishing"] if unclear)

CRITICAL RULES:
1. Extract EVERY distinct piece of content - be comprehensive
2. For RULE type: Include the line number in the text (e.g., "Line 8523")
3. For TABLE type: Just note "Table from page X" - don't duplicate table data
4. page_number MUST be an integer within the section's page range
5. Output MUST be valid JSON array

{table_summary}

Section content:
---
{text[:50000]}  # Limit to ~50k chars to avoid token limits
---

Return JSON array ONLY (no markdown, no explanation):
[
  {{
    "type": "RULE",
    "text": "Line 8523 – Meals and entertainment\\n\\nYou can deduct...",
    "page_number": 42,
    "applies_to": ["business", "farming"]
  }},
  ...
]"""


def parse_llm_response(
    response: str,
    section: SemanticSection,
    tables: list[dict],
) -> list[ExtractedContent]:
    """Parse LLM JSON response into ExtractedContent objects.

    Args:
        response: Raw LLM response (should be JSON array)
        section: SemanticSection for metadata
        tables: Extracted tables for TABLE content type

    Returns:
        List of ExtractedContent objects

    Raises:
        ValueError: If response is not valid JSON or missing required fields
    """
    # Strip markdown code fences if present (common LLM behavior)
    cleaned_response = response.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response.removeprefix("```json").strip()
    if cleaned_response.startswith("```"):
        cleaned_response = cleaned_response.removeprefix("```").strip()
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response.removesuffix("```").strip()

    try:
        items = json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        msg = f"Failed to parse LLM response as JSON: {e}"
        raise ValueError(msg) from e

    if not isinstance(items, list):
        msg = f"Expected JSON array, got {type(items)}"
        raise ValueError(msg)

    extracted: list[ExtractedContent] = []
    table_counter = 0

    for idx, item in enumerate(items):
        # Validate required fields
        if not isinstance(item, dict):
            logger.warning(f"Skipping non-dict item at index {idx}: {item}")
            continue

        content_type = item.get("type")
        text = item.get("text")
        page_number = item.get("page_number")

        if not all([content_type, text, page_number]):
            logger.warning(f"Skipping incomplete item at index {idx}: {item}")
            continue

        # Validate content type
        try:
            content_type_enum = ContentType(content_type)
        except ValueError:
            logger.warning(f"Invalid content type '{content_type}' at index {idx}")
            continue

        # Validate page number
        if not isinstance(page_number, int) or not (
            section.page_range[0] <= page_number <= section.page_range[1]
        ):
            logger.warning(
                f"Invalid page_number {page_number} for section "
                f"{section.page_range} at index {idx}"
            )
            continue

        # Build citation_id
        citation_id = f"T4002-P{page_number}-ITEM{idx + 1}"

        # Handle TABLE content type specially
        table_data = None
        if content_type_enum == ContentType.TABLE and tables:
            # Find matching table by page number
            matching_tables = [
                t for t in tables if t["page_number"] == page_number
            ]
            if matching_tables:
                # Use first matching table's data
                table_data = matching_tables[table_counter % len(matching_tables)][
                    "rows"
                ]
                table_counter += 1

        # Get applies_to (default to all if not specified)
        applies_to = item.get("applies_to", ["business", "farming", "fishing"])

        extracted.append(
            ExtractedContent(
                citation_id=citation_id,
                content_type=content_type_enum,
                text=text,
                source_file="T4002-Business-Expenses-Guide.pdf",
                anchor_id=None,  # PDF doesn't have HTML anchors
                references=[],  # Could extract LINE-XXXX references later
                table_data=table_data,
                page_number=page_number,
                section_title=section.title,
            )
        )

    logger.info(f"Parsed {len(extracted)} content items from LLM response")
    return extracted


def parse_section(
    pdf_path: Path,
    section: SemanticSection,
    llm_call_func: callable,
) -> list[ExtractedContent]:
    """Extract and structure content from a PDF section.

    This is the main entry point that orchestrates:
    1. Raw content extraction (text + tables)
    2. LLM prompt generation
    3. LLM API call
    4. Response parsing into ExtractedContent

    Args:
        pdf_path: Path to PDF file
        section: SemanticSection to process
        llm_call_func: Function to call LLM (signature: str -> str)
            Takes prompt string, returns JSON response string

    Returns:
        List of ExtractedContent objects with full lineage

    Example:
        >>> def my_llm_call(prompt: str) -> str:
        ...     # Call Gemini, OpenAI, etc.
        ...     return gemini_client.generate(prompt)
        >>>
        >>> section = SemanticSection("Chapter 3", (38, 68))
        >>> content = parse_section(Path("T4002.pdf"), section, my_llm_call)
        >>> len(content)
        42
    """
    logger.info(f"Parsing section: {section.title}")

    # Step 1: Extract raw content
    text, tables = extract_section_content(pdf_path, section)

    # Step 2: Build prompt
    prompt = build_llm_prompt(section, text, tables)

    # Step 3: Call LLM
    logger.info(f"Calling LLM for {section.title}")
    try:
        response = llm_call_func(prompt)
    except Exception as e:
        logger.error(f"LLM call failed for {section.title}: {e}")
        raise

    # Step 4: Parse response
    try:
        extracted = parse_llm_response(response, section, tables)
    except ValueError as e:
        logger.error(f"Failed to parse LLM response for {section.title}: {e}")
        logger.debug(f"Raw response: {response[:500]}")
        raise

    logger.info(
        f"Successfully extracted {len(extracted)} items from {section.title}"
    )
    return extracted
