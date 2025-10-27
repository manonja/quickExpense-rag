"""
Unified content type models for Phase 2-3 extraction.

This module introduces a new content model hierarchy to support extracting
multiple content types (RULE, PRINCIPLE, TABLE, EXAMPLES, GUIDANCE) from
CRA HTML documents.

Phase 2 Implementation:
- RULE: Line-numbered expense rules (existing, from Phase 1)
- PRINCIPLE: Text referencing rules but not rule definitions

Phase 3 Implementation:
- TABLE: Structured tabular data (e.g., CCA rate tables)

Future phases will add EXAMPLES and GUIDANCE content types.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ContentType(StrEnum):
    """
    Type of content extracted from HTML.

    Discriminator for unified ExtractedContent model.

    Values:
        RULE: Line-numbered expense rule definition (e.g., "Line 9600 – Other income")
        PRINCIPLE: Text referencing rules without being a definition
            (e.g., "Complete line 9600 if...")
        TABLE: Structured tabular data (e.g., CCA rate tables)
    """

    RULE = "RULE"
    PRINCIPLE = "PRINCIPLE"
    TABLE = "TABLE"


class ExtractedContent(BaseModel):
    """
    Unified model for any extracted content.

    This model supports multiple content types through the ContentType discriminator.
    Each content type has the same base structure but different semantics:

    - RULE: Canonical line-numbered rule definition (has anchor ID)
    - PRINCIPLE: Text that references rules (no anchor ID, has references list)
    - TABLE: Structured tabular data (has table_data, no anchor ID)

    Fields:
        citation_id: Unique identifier.
            - RULE: "LINE-{number}" (e.g., "LINE-9600")
            - PRINCIPLE: "{source_file}-PRINCIPLE-{seq}" (e.g., "t4002-6-PRINCIPLE-1")
            - TABLE: "{source_file}-TABLE-{seq}" (e.g., "t4002-10-TABLE-1")
        content_type: Discriminator indicating content type
        text: Full extracted text content (descriptive text for TABLE)
        source_file: Source HTML filename (e.g., "t4002-6.html")
        anchor_id: HTML anchor ID (only for RULE content, None for PRINCIPLE/TABLE)
        references: List of LINE-XXXX references found in text
            (empty for RULE, populated for PRINCIPLE, empty for TABLE)
        table_data: Structured table data as list of row dictionaries
            (None for RULE/PRINCIPLE, populated for TABLE)

    Example (RULE):
        >>> rule = ExtractedContent(
        ...     citation_id="LINE-9600",
        ...     content_type=ContentType.RULE,
        ...     text="Other income\\n\\nInclude any other income...",
        ...     source_file="t4002-5.html",
        ...     anchor_id="tocch2ln9600",
        ...     references=[],
        ... )

    Example (PRINCIPLE):
        >>> principle = ExtractedContent(
        ...     citation_id="t4002-6-PRINCIPLE-1",
        ...     content_type=ContentType.PRINCIPLE,
        ...     text="Enter on line 9925 the total business part...",
        ...     source_file="t4002-6.html",
        ...     anchor_id=None,
        ...     references=["LINE-9925"],
        ... )

    Example (TABLE):
        >>> table = ExtractedContent(
        ...     citation_id="t4002-10-TABLE-1",
        ...     content_type=ContentType.TABLE,
        ...     text="Table 1 from t4002-10.html",
        ...     source_file="t4002-10.html",
        ...     anchor_id=None,
        ...     references=[],
        ...     table_data=[
        ...         {"Property": "Chain-saws", "Class number": "10"},
        ...         {"Property": "Computer equipment", "Class number": "45"},
        ...     ],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    citation_id: str = Field(
        description="Unique content identifier (format varies by content_type)"
    )
    content_type: ContentType = Field(
        description="Type of content (RULE, PRINCIPLE, TABLE)"
    )
    text: str = Field(description="Full extracted text content")
    source_file: str = Field(description="Source HTML filename (e.g., 't4002-6.html')")
    anchor_id: str | None = Field(
        default=None, description="HTML anchor ID (RULE only, None for PRINCIPLE/TABLE)"
    )
    references: list[str] = Field(
        default_factory=list, description="LINE-XXXX references found in text"
    )
    table_data: list[dict[str, str]] | None = Field(
        default=None,
        description="Structured table data (TABLE only, None for RULE/PRINCIPLE)",
    )
