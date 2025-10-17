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


def _triage_rules(
    classic_rules: list[ExtractedRule],
    llm_rules: list[ExtractedRule],
) -> TriageResult:
    """
    Categorize rules into perfect matches, conflicts, and orphans.

    Aligns rules from both parsers by rule_number and compares normalized
    versions to determine:
    - Perfect matches: Both parsers agree → trust classic (deterministic)
    - Conflicts: Both found it, but disagree → needs adjudication
    - Orphans: Only one parser found it → needs validation

    Args:
        classic_rules: Rules extracted by classic HTML parser
        llm_rules: Rules extracted by LLM-based parser

    Returns:
        TriageResult with categorized rules

    Example:
        >>> classic = [rule1, rule2]
        >>> llm = [rule1_identical, rule3]
        >>> result = _triage_rules(classic, llm)
        >>> len(result.perfect_matches)  # rule1
        1
        >>> len(result.orphans)  # rule2 and rule3
        2
    """
    logger.info("[Adjudicator] Starting triage...")

    # Create lookup dictionaries for O(1) access
    classic_map = {r.rule_number: r for r in classic_rules}
    llm_map = {r.rule_number: r for r in llm_rules}

    # Find union of all rule numbers
    all_rule_numbers = set(classic_map.keys()) | set(llm_map.keys())

    perfect_matches: list[ExtractedRule] = []
    conflicts: list[tuple[ExtractedRule, ExtractedRule]] = []
    orphans: list[ExtractedRule] = []

    for rule_number in all_rule_numbers:
        classic_rule = classic_map.get(rule_number)
        llm_rule = llm_map.get(rule_number)

        if classic_rule and llm_rule:
            # Both parsers found this rule - compare normalized versions
            classic_normalized = _normalize_rule_for_comparison(classic_rule)
            llm_normalized = _normalize_rule_for_comparison(llm_rule)

            if classic_normalized == llm_normalized:
                # Perfect match - trust classic parser (deterministic)
                perfect_matches.append(classic_rule)
            else:
                # Conflict detected - parsers disagree
                conflicts.append((classic_rule, llm_rule))
        else:
            # Orphan - only one parser found this rule
            orphan_rule = classic_rule or llm_rule
            if orphan_rule:
                orphans.append(orphan_rule)

    logger.info(
        f"[Adjudicator] Triage complete: {len(perfect_matches)} perfect matches, "
        f"{len(conflicts)} conflicts, {len(orphans)} orphans"
    )

    return TriageResult(
        perfect_matches=perfect_matches,
        conflicts=conflicts,
        orphans=orphans,
    )


def _truncate_html_for_prompt(
    html_content: str,
    anchor_id: str | None,
) -> str:
    """
    Truncate HTML content if needed, preserving context around anchor_id.

    For large HTML files that would exceed the LLM's token limit, this function
    intelligently extracts the most relevant section:
    - If anchor_id is available: extract contextual window around the target rule
    - Otherwise: take first and last chunks

    Args:
        html_content: Full HTML content from source file
        anchor_id: Optional HTML anchor ID to locate the relevant section

    Returns:
        Full or truncated HTML content with context preserved

    Example:
        >>> large_html = "<html>..." + "x" * 500000 + "...</html>"
        >>> truncated = _truncate_html_for_prompt(large_html, "tocch3ln8523")
        >>> "[...CONTENT TRUNCATED...]" in truncated
        True
    """
    # Safe character limit (roughly <100k tokens)
    MAX_CHARS = 300_000
    CONTEXT_WINDOW_CHARS = 150_000

    if len(html_content) <= MAX_CHARS:
        return html_content

    if anchor_id:
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")
            target_tag = soup.find(id=anchor_id)

            if target_tag:
                # Find h3: either the target itself or its parent
                h3_tag = target_tag if target_tag.name == "h3" else target_tag.find_parent("h3")
                if h3_tag:
                    # Extract contextual window
                    context_parts = []

                    # Go back 2-3 siblings or until h2
                    prev_count = 0
                    for prev_sibling in h3_tag.previous_siblings:
                        if prev_sibling.name in ["h2", "h3"] and prev_count >= 1:
                            break
                        if prev_sibling.name:
                            context_parts.insert(0, str(prev_sibling))
                            prev_count += 1
                        if prev_count >= 3:
                            break

                    # Add the target h3
                    context_parts.append(str(h3_tag))

                    # Go forward until next h3
                    for next_sibling in h3_tag.next_siblings:
                        if next_sibling.name == "h3":
                            break
                        if next_sibling.name:
                            context_parts.append(str(next_sibling))

                    truncated_content = "\n".join(context_parts)
                    return (
                        "[...CONTENT TRUNCATED...]\n"
                        "The following is the most relevant section of the HTML "
                        "based on the rule's anchor ID.\n\n"
                        f"{truncated_content}"
                    )
        except Exception as e:
            logger.warning(
                f"[Adjudicator] Failed to extract context for anchor {anchor_id}: {e}"
            )

    # Fallback: first and last chunks
    half_window = CONTEXT_WINDOW_CHARS // 2
    return (
        f"{html_content[:half_window]}\n\n"
        "[...CONTENT TRUNCATED - MIDDLE SECTION OMITTED...]\n\n"
        f"{html_content[-half_window:]}"
    )


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
