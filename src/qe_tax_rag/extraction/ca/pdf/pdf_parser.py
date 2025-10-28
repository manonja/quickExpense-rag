"""
PDF content extraction and structuring using pdfplumber and LLM.

This module extracts content from PDF semantic sections and structures it
using an LLM (Gemini). It handles both text and table extraction.
"""

import hashlib
import logging
from pathlib import Path

import pdfplumber
import yaml

from qe_tax_rag.extraction.ca.models import ContentType, ExtractedContent
from qe_tax_rag.extraction.ca.pdf.structure_detector import SemanticSection

logger = logging.getLogger(__name__)


def extract_section_content(
    pdf_path: Path,
    section: SemanticSection,
) -> tuple[str, list[dict]]:
    """
    Extract raw text and tables from a PDF section using pdfplumber.

    Args:
        pdf_path: Path to PDF file
        section: SemanticSection with page range to extract

    Returns:
        Tuple of (consolidated_text, tables)
        - consolidated_text: All text from the section pages
        - tables: List of table data (each table is list of row dicts)

    Example:
        >>> text, tables = extract_section_content(
        ...     Path("T4002.pdf"), SemanticSection("Chapter 3", (38, 68))
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
    """
    Build detailed LLM prompt for content structuring.

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

    # Check for text truncation and log warning
    MAX_CHARS = 50000
    if len(text) > MAX_CHARS:
        logger.warning(
            f"Truncating text for section '{section.full_title}' "
            f"from {len(text)} to {MAX_CHARS} characters. "
            f"Consider subdividing this section further."
        )
        text_for_prompt = text[:MAX_CHARS]
    else:
        text_for_prompt = text

    return f"""You are extracting structured content from "{section.full_title}"
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
5. Output MUST be valid YAML (more robust than JSON for large responses)

{table_summary}

Section content:
---
{text_for_prompt}
---

Return YAML ONLY (no markdown code fences, no explanation).
IMPORTANT: For multiline text, use the pipe (|) block scalar indicator.

Example format:
- type: RULE
  text: |
    Line 8523 – Meals and entertainment

    You can deduct 50% of food, beverage, and entertainment expenses...
  page_number: 42
  applies_to: [business, farming]

- type: PRINCIPLE
  text: |
    See Chapter 4 for capital cost allowance rules.
  page_number: 43
  applies_to: [business, farming, fishing]

- type: DEFINITION
  text: |
    Capital cost allowance (CCA) – A tax deduction for the cost of depreciable property.
  page_number: 44
  applies_to: [business, farming, fishing]
"""


def parse_llm_response(
    response: str,
    section: SemanticSection,
    tables: list[dict],
) -> list[ExtractedContent]:
    """
    Parse LLM YAML response into ExtractedContent objects.

    Args:
        response: Raw LLM response (should be YAML list)
        section: SemanticSection for metadata
        tables: Extracted tables for TABLE content type

    Returns:
        List of ExtractedContent objects

    Raises:
        ValueError: If response is not valid YAML or missing required fields

    """
    # Strip markdown code fences if present (common LLM behavior)
    cleaned_response = response.strip()
    if cleaned_response.startswith("```yaml"):
        cleaned_response = cleaned_response.removeprefix("```yaml").strip()
    if cleaned_response.startswith("```"):
        cleaned_response = cleaned_response.removeprefix("```").strip()
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response.removesuffix("```").strip()

    try:
        items = yaml.safe_load(cleaned_response)
    except yaml.YAMLError as e:
        msg = f"Failed to parse LLM response as YAML: {e}"
        raise ValueError(msg) from e

    if not isinstance(items, list):
        msg = f"Expected YAML list, got {type(items)}"
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

        # Build citation_id using content hash for global uniqueness
        # This prevents duplicates when multiple sections cover the same page
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:8]
        citation_id = f"T4002-P{page_number}-{content_hash}"

        # Handle TABLE content type specially
        table_data = None
        if content_type_enum == ContentType.TABLE and tables:
            # Find matching table by page number
            matching_tables = [t for t in tables if t["page_number"] == page_number]
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
    """
    Extract and structure content from a PDF section.

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

    logger.info(f"Successfully extracted {len(extracted)} items from {section.title}")
    return extracted
