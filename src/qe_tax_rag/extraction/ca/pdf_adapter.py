"""
Adapter to convert PDF ExtractedContent to HTML-compatible ExtractedRule.

This module bridges the gap between PDF and HTML extraction pipelines by
converting PDF-specific ExtractedContent models to the ExtractedRule format
expected by the database builder.

**Rationale (Modified Option A - Pragmatic Adapter):**
- PDF extraction uses ExtractedContent (citation_id, content_type, page_number)
- HTML extraction uses ExtractedRule (rule_number, title, chapter)
- Database builder expects RuleSet with rules: list[ExtractedRule]
- This adapter enables immediate PDF-to-database conversion while preserving
  PDF-specific metadata in a dedicated field

**Design Decisions:**
1. Preserve PDF metadata (page_number, content_type, section_title) in pdf_metadata dict
2. Map citation_id → source_citation for traceability
3. Use synthetic rule_number=0 for non-RULE content
4. Set expert_source to indicate PDF adapter origin
5. Default confidence_score=1.0 (no adjudication in PDF pipeline)

**Future Migration Path:**
If we add multiple non-HTML sources, this adapter can be replaced with
Option B (Dual Pipeline Support) for cleaner schema separation.
"""

import json
import logging
import re

from qe_tax_rag.extraction.ca.models import ContentType, ExtractedContent
from qe_tax_rag.extraction.ca.schema import ApplicabilityType, ExpertSource, ExtractedRule

logger = logging.getLogger(__name__)


def _extract_rule_number_from_citation(citation_id: str) -> int:
    """
    Extract numeric rule number from PDF citation_id if possible.

    Args:
        citation_id: PDF citation ID (e.g., "T4002-P10-ITEM1" or "LINE-8523")

    Returns:
        Rule number if extractable, otherwise 0

    Examples:
        >>> _extract_rule_number_from_citation("LINE-8523")
        8523
        >>> _extract_rule_number_from_citation("T4002-P10-ITEM1")
        0
    """
    # Try LINE-XXXX pattern (if PDF content references a line number)
    if match := re.match(r"LINE-(\d+)", citation_id):
        return int(match.group(1))

    # Otherwise return 0 for non-line-numbered content
    return 0


def convert_extracted_content_to_rule(content: ExtractedContent) -> ExtractedRule:
    """
    Convert PDF ExtractedContent to HTML-compatible ExtractedRule.

    This adapter maps PDF-specific fields to the ExtractedRule schema while
    preserving all PDF metadata in a dedicated pdf_metadata field.

    Args:
        content: ExtractedContent from PDF extraction

    Returns:
        ExtractedRule compatible with database builder

    Example:
        >>> pdf_content = ExtractedContent(
        ...     citation_id="T4002-P10-ITEM1",
        ...     content_type=ContentType.DEFINITION,
        ...     text="Proceeds of disposition – the amounts you receive...",
        ...     source_file="T4002-Business-Expenses-Guide.pdf",
        ...     page_number=10,
        ...     section_title="A business and business income",
        ... )
        >>> rule = convert_extracted_content_to_rule(pdf_content)
        >>> rule.source_citation
        'T4002-P10-ITEM1'
        >>> rule.chapter
        'A business and business income'
    """
    # Extract rule number (0 for non-RULE content)
    rule_number = _extract_rule_number_from_citation(content.citation_id)

    # Map section_title to chapter (fallback to source file if missing)
    chapter = content.section_title or content.source_file

    # Generate title from content_type and section
    title = f"{content.content_type.value}: {content.section_title or 'PDF Content'}"

    # Default applies_to (all business types)
    applies_to = [
        ApplicabilityType.BUSINESS,
        ApplicabilityType.FARMING,
        ApplicabilityType.FISHING,
    ]

    # Prepare PDF-specific metadata (serialize to JSON string for lineage_stages)
    pdf_metadata = {
        "page_number": str(content.page_number) if content.page_number else None,
        "content_type": content.content_type.value,
        "original_section_title": content.section_title,
    }

    # Create ExtractedRule with PDF adapter marker
    return ExtractedRule(
        rule_number=rule_number,
        title=title,
        content=content.text,
        applies_to=applies_to,
        source_citation=content.citation_id,
        chapter=chapter,
        section=None,  # PDF doesn't have HTML-style sections
        source_file=content.source_file,
        expert_source=ExpertSource.CLASSIC,  # Use CLASSIC to avoid enum extension
        anchor_id=content.anchor_id,
        confidence_score=1.0,
        # Preserve PDF-specific metadata for traceability
        # Note: lineage_stages expects dict[str, str], so serialize metadata to JSON
        lineage_stages=[
            {
                "stage": "pdf_adapter",
                "timestamp": "",  # Will be populated by builder
                "metadata": json.dumps(pdf_metadata),
            }
        ],
    )
