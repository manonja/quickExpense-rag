"""
Grounded adjudication and self-correction for HTML-to-YAML extraction pipeline.

This module implements the core intelligence of the Mixture-of-Experts (MoE) pipeline.
It merges results from two expert parsers (classic HTML parser and LLM parser),
identifies discrepancies, and uses Gemini Pro to resolve conflicts with full audit trail.

Key Features:
- Triage algorithm: categorizes rules into perfect matches, conflicts, and orphans
- Trust classic parser for perfect matches (deterministic source of truth)
- Grounded LLM adjudication with full HTML context for evidence-based decisions
- Comprehensive error handling: all failures lead to manual review, not crashes
- Structured logging for audit trail with reasoning and citations

Usage:
    from qe_tax_rag.extraction.ca.adjudicator import adjudicate

    resolved_rules, manual_items, stats = adjudicate(
        classic_rules=classic_parser_output,
        llm_rules=llm_parser_output,
        source_html_content=html_content,
        source_file="t4002-5.html",
    )
"""

import logging
import re
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from src.qe_tax_rag.extraction.ca.schema import ExtractedRule

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================


class TriageResult(NamedTuple):
    """
    Results from the triage phase of adjudication.

    Categorizes rules into three groups based on comparison between
    classic and LLM parser outputs.
    """

    perfect_matches: list[ExtractedRule]
    """Rules where both parsers produced identical normalized output."""

    conflicts: list[tuple[ExtractedRule, ExtractedRule]]
    """Rules where parsers disagree (classic_rule, llm_rule)."""

    orphans: list[ExtractedRule]
    """Rules found by only one parser."""


class ManualReviewItem(BaseModel):
    """
    Represents a failed adjudication requiring manual review.

    When the LLM adjudicator cannot resolve a conflict or orphan
    (due to API failures, validation errors, or insufficient evidence),
    this structure captures all relevant information for human review.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    rule_number: int = Field(description="Rule number requiring review")
    discrepancy_type: str = Field(description="CONFLICT or ORPHAN")
    failure_reason: str = Field(description="Why adjudication failed")
    source_file: str = Field(description="Source HTML filename")
    timestamp: str = Field(description="ISO 8601 timestamp of failure")

    # For conflicts: both versions
    classic_version: dict[str, object] | None = Field(
        default=None, description="Classic parser version"
    )
    llm_version: dict[str, object] | None = Field(
        default=None, description="LLM parser version"
    )

    # For orphans: single version
    orphan_version: dict[str, object] | None = Field(
        default=None, description="Orphan rule data"
    )
    found_by: str | None = Field(
        default=None, description="Which parser found orphan (classic/llm)"
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _normalize_rule_for_comparison(rule: ExtractedRule) -> dict[str, str | list[str]]:
    """
    Normalize a rule for comparison between parsers.

    Normalization ensures that rules are compared semantically, not textually.
    This prevents false conflicts from whitespace differences or ordering variations.

    Args:
        rule: The ExtractedRule to normalize

    Returns:
        Dictionary with normalized fields: title, content, applies_to

    Example:
        >>> rule = ExtractedRule(
        ...     rule_number=8523,
        ...     title="  Meals  ",
        ...     content="You can\\n\\n  deduct  the cost",
        ...     applies_to=[ApplicabilityType.FISHING, ApplicabilityType.BUSINESS],
        ...     ...
        ... )
        >>> normalized = _normalize_rule_for_comparison(rule)
        >>> normalized["title"]
        'Meals'
        >>> normalized["content"]
        'You can deduct the cost'
        >>> normalized["applies_to"]
        ['business', 'fishing']
    """
    # Normalize content: collapse all consecutive whitespace to single space
    normalized_content = re.sub(r"\s+", " ", rule.content).strip()

    return {
        "title": rule.title.strip(),
        "content": normalized_content,
        # Sort applies_to to handle different orderings
        "applies_to": sorted([item.value for item in rule.applies_to]),
    }
