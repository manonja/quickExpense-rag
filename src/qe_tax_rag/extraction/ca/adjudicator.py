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

from qe_tax_rag.extraction.ca.exceptions import AdjudicationError
from qe_tax_rag.extraction.ca.schema import ExpertSource, ExtractedRule
from qe_tax_rag.extraction.ca.settings import settings

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
                h3_tag = (
                    target_tag
                    if target_tag.name == "h3"
                    else target_tag.find_parent("h3")
                )
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


ADJUDICATION_PROMPT_TEMPLATE = """You are an expert adjudicator for a Canadian tax law data extraction pipeline. Two parsers (classic rule-based and LLM semantic) have extracted expense rules from CRA HTML documents, and you must resolve discrepancies.

You will be given:
1. The full HTML content from the source document
2. Details about the discrepancy (conflict or orphan)

Your task is to determine the CORRECT extraction by examining the source HTML evidence.

CRITICAL REQUIREMENTS:
- Base your decision ONLY on evidence from the provided HTML
- Provide an exact quote (citation) from the HTML that supports your decision
- Explain your reasoning step-by-step
- If you cannot find sufficient evidence, say so explicitly

--- DISCREPANCY DETAILS ---
Discrepancy Type: {discrepancy_type}
Rule Number: {rule_number}
Source File: {source_file}
Anchor ID: {anchor_id}

{discrepancy_details}

--- FULL HTML SOURCE ---
{html_content}

Respond ONLY with a single JSON object (no markdown, no explanatory text):

{{
  "analysis": "<Brief 1-2 sentence explanation of what discrepancy you found>",
  "reasoning": "<Step-by-step explanation of how you analyzed the HTML to resolve it>",
  "citation": "<Exact quote from the HTML that justifies your decision>",
  "corrected_rule": {{
    "rule_number": <integer>,
    "title": "<string>",
    "content": "<string>",
    "applies_to": [<list of strings: 'business', 'farming', or 'fishing'>],
    "source_citation": "<string>",
    "chapter": "<string>",
    "section": "<string or null>",
    "source_file": "<string>",
    "anchor_id": "<string or null>"
  }}
}}

If you cannot resolve the discrepancy with confidence, set "analysis" to start with "INSUFFICIENT_EVIDENCE:" and explain why.
"""


def _build_adjudication_prompt(
    discrepancy_type: str,
    rule_number: int,
    source_file: str,
    anchor_id: str | None,
    html_content: str,
    classic_rule: ExtractedRule | None = None,
    llm_rule: ExtractedRule | None = None,
) -> str:
    """
    Build a grounded adjudication prompt with structured details.

    Creates a comprehensive prompt for the LLM adjudicator that includes:
    - Structured metadata about the discrepancy
    - Side-by-side comparison (for conflicts) or single rule (for orphans)
    - Full HTML source for evidence-based resolution

    Args:
        discrepancy_type: "CONFLICT" or "ORPHAN"
        rule_number: The rule number being adjudicated
        source_file: Source HTML filename
        anchor_id: Optional anchor ID for HTML navigation
        html_content: Full or truncated HTML content
        classic_rule: Rule from classic parser (for conflicts or classic orphans)
        llm_rule: Rule from LLM parser (for conflicts or LLM orphans)

    Returns:
        Formatted prompt string ready for LLM

    Example:
        >>> prompt = _build_adjudication_prompt(
        ...     "CONFLICT",
        ...     8523,
        ...     "t4002-5.html",
        ...     "tocch3ln8523",
        ...     html_content,
        ...     classic_rule,
        ...     llm_rule,
        ... )
        >>> "CONFLICT" in prompt
        True

    """
    import yaml

    if discrepancy_type == "CONFLICT" and classic_rule and llm_rule:
        classic_yaml = yaml.dump(
            classic_rule.model_dump(exclude={"expert_source", "confidence_score"})
        )
        llm_yaml = yaml.dump(
            llm_rule.model_dump(exclude={"expert_source", "confidence_score"})
        )

        discrepancy_details = f"""A conflict was found for this rule. Here are the two versions.

[CLASSIC PARSER VERSION]
{classic_yaml}

[LLM PARSER VERSION]
{llm_yaml}"""
    else:  # ORPHAN
        orphan_rule = classic_rule or llm_rule
        if not orphan_rule:
            raise ValueError(
                "Either classic_rule or llm_rule must be provided for ORPHAN"
            )
        found_by = "classic" if classic_rule else "llm"
        orphan_yaml = yaml.dump(
            orphan_rule.model_dump(exclude={"expert_source", "confidence_score"})
        )

        discrepancy_details = f"""This rule was found only by the {found_by} parser. Please verify if it is a valid rule based on the HTML source.

[ORPHAN RULE DATA]
{orphan_yaml}"""

    return ADJUDICATION_PROMPT_TEMPLATE.format(
        discrepancy_type=discrepancy_type,
        rule_number=rule_number,
        source_file=source_file,
        anchor_id=anchor_id or "N/A",
        discrepancy_details=discrepancy_details,
        html_content=html_content,
    )


def _adjudicate_item_with_llm(
    discrepancy_type: str,
    rule_number: int,
    source_file: str,
    html_content: str,
    classic_rule: ExtractedRule | None = None,
    llm_rule: ExtractedRule | None = None,
) -> ExtractedRule | ManualReviewItem:
    """
    Adjudicate a single conflict or orphan using Gemini Pro.

    Makes a synchronous API call to the LLM adjudicator with full HTML context
    and structured prompt. Handles all error scenarios gracefully by returning
    ManualReviewItem for failed adjudications.

    Args:
        discrepancy_type: "CONFLICT" or "ORPHAN"
        rule_number: Rule number being adjudicated
        source_file: Source HTML filename
        html_content: Full or truncated HTML content
        classic_rule: Rule from classic parser (if applicable)
        llm_rule: Rule from LLM parser (if applicable)

    Returns:
        ExtractedRule with expert_source=ADJUDICATED on success,
        ManualReviewItem on any failure

    Example:
        >>> result = _adjudicate_item_with_llm(
        ...     "CONFLICT", 8523, "t4002-5.html", html, classic, llm
        ... )
        >>> isinstance(result, (ExtractedRule, ManualReviewItem))
        True

    """
    import json
    from datetime import datetime, timezone

    import google.generativeai as genai
    from pydantic import ValidationError

    # Get anchor_id from whichever rule we have
    anchor_id = (
        (classic_rule or llm_rule).anchor_id if (classic_rule or llm_rule) else None
    )

    try:
        # Truncate HTML if needed
        truncated_html = _truncate_html_for_prompt(html_content, anchor_id)

        # Build prompt
        prompt = _build_adjudication_prompt(
            discrepancy_type=discrepancy_type,
            rule_number=rule_number,
            source_file=source_file,
            anchor_id=anchor_id,
            html_content=truncated_html,
            classic_rule=classic_rule,
            llm_rule=llm_rule,
        )

        # Call Gemini API
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.adjudicator_model_name)

        # 30-second timeout
        response = model.generate_content(prompt, request_options={"timeout": 30})

        # Parse JSON
        data = json.loads(response.text)

        # Check for insufficient evidence
        if data.get("analysis", "").startswith("INSUFFICIENT_EVIDENCE:"):
            raise AdjudicationError(
                f"LLM reported insufficient evidence: {data['analysis']}"
            )

        # Validate and create ExtractedRule
        corrected_rule_data = data["corrected_rule"]
        corrected_rule_data["expert_source"] = ExpertSource.ADJUDICATED
        corrected_rule_data["confidence_score"] = 0.95

        corrected_rule = ExtractedRule.model_validate(corrected_rule_data)

        # Log success
        logger.info(
            f"[Adjudicator] Adjudicated rule {rule_number}: {data['analysis']}",
            extra={
                "reasoning": data.get("reasoning"),
                "citation": data.get("citation"),
                "rule_number": rule_number,
            },
        )

        return corrected_rule

    except Exception as e:
        # Determine specific failure reason
        failure_reason = _determine_failure_reason(e, locals())

        logger.error(
            f"[Adjudicator] Failed to adjudicate rule {rule_number}: {failure_reason}",
            exc_info=True,
        )

        # Create ManualReviewItem
        manual_item = ManualReviewItem(
            rule_number=rule_number,
            discrepancy_type=discrepancy_type,
            failure_reason=failure_reason,
            source_file=source_file,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if discrepancy_type == "CONFLICT" and classic_rule and llm_rule:
            manual_item.classic_version = classic_rule.model_dump(
                exclude={"expert_source", "confidence_score", "anchor_id"}
            )
            manual_item.llm_version = llm_rule.model_dump(
                exclude={"expert_source", "confidence_score", "anchor_id"}
            )
        else:
            orphan_rule = classic_rule or llm_rule
            if orphan_rule:
                manual_item.orphan_version = orphan_rule.model_dump(
                    exclude={"expert_source", "confidence_score", "anchor_id"}
                )
                manual_item.found_by = "classic" if classic_rule else "llm"

        return manual_item


def _determine_failure_reason(
    exception: Exception, local_vars: dict[str, object]
) -> str:
    """Determine specific failure reason from exception type."""
    import json

    if "TimeoutError" in str(type(exception)):
        return "API timeout after 30s"
    elif isinstance(exception, json.JSONDecodeError):
        response_text = local_vars.get("response")
        if response_text and hasattr(response_text, "text"):
            logger.error(f"[Adjudicator] Raw LLM response: {response_text.text[:500]}")
        return f"Failed to parse LLM JSON response: {exception!s}"
    elif "ValidationError" in str(type(exception)):
        return f"LLM response failed schema validation: {exception!s}"
    elif isinstance(exception, AdjudicationError):
        return str(exception)
    else:
        return f"Unexpected error: {type(exception).__name__}: {exception!s}"


def adjudicate(
    classic_rules: list[ExtractedRule],
    llm_rules: list[ExtractedRule],
    source_html_content: str,
    source_file: str,
) -> tuple[list[ExtractedRule], list[ManualReviewItem], dict[str, int]]:
    """
    Merge, adjudicate, and self-correct rules from classic and LLM parsers.

    Uses a Mixture-of-Experts approach with grounded LLM adjudication:
    1. Triage rules into perfect matches, conflicts, and orphans
    2. Trust classic parser for perfect matches (deterministic source of truth)
    3. Use Gemini Pro to resolve conflicts/orphans with full HTML context
    4. Return clean list of rules plus manual review items for failed adjudications

    Args:
        classic_rules: Rules extracted by classic HTML parser
        llm_rules: Rules extracted by LLM-based parser
        source_html_content: Full HTML content for grounding
        source_file: Source filename for audit trail

    Returns:
        Tuple of:
        - Resolved rules (sorted by rule_number)
        - Manual review items (failed adjudications)
        - Statistics dict with counts

    Raises:
        AdjudicationError: Only for catastrophic failures (not individual items)

    Example:
        >>> resolved, manual, stats = adjudicate(
        ...     classic_rules, llm_rules, html_content, "t4002-5.html"
        ... )
        >>> stats["perfect_matches"] + stats["auto_corrected"] + stats["manual_review"]
        len(resolved) + len(manual)

    """
    logger.info("[Adjudicator] Starting adjudication process...")

    # Step 1: Triage
    triage_result = _triage_rules(classic_rules, llm_rules)

    # Step 2: Start with perfect matches
    final_rules: list[ExtractedRule] = list(triage_result.perfect_matches)
    manual_review_items: list[ManualReviewItem] = []

    stats = {
        "perfect_matches": len(triage_result.perfect_matches),
        "auto_corrected": 0,
        "manual_review": 0,
    }

    # Step 3: Adjudicate conflicts
    logger.info(
        f"[Adjudicator] Adjudicating {len(triage_result.conflicts)} conflicts..."
    )
    for classic_rule, llm_rule in triage_result.conflicts:
        result = _adjudicate_item_with_llm(
            discrepancy_type="CONFLICT",
            rule_number=classic_rule.rule_number,
            source_file=source_file,
            html_content=source_html_content,
            classic_rule=classic_rule,
            llm_rule=llm_rule,
        )

        if isinstance(result, ExtractedRule):
            final_rules.append(result)
            stats["auto_corrected"] += 1
        else:
            manual_review_items.append(result)
            stats["manual_review"] += 1
            logger.warning(
                f"[Adjudicator] Added rule {result.rule_number} to manual review: "
                f"{result.failure_reason}"
            )

    # Step 4: Adjudicate orphans
    logger.info(f"[Adjudicator] Adjudicating {len(triage_result.orphans)} orphans...")
    for orphan_rule in triage_result.orphans:
        # Determine which parser found it
        is_classic = orphan_rule.expert_source == ExpertSource.CLASSIC

        result = _adjudicate_item_with_llm(
            discrepancy_type="ORPHAN",
            rule_number=orphan_rule.rule_number,
            source_file=source_file,
            html_content=source_html_content,
            classic_rule=orphan_rule if is_classic else None,
            llm_rule=orphan_rule if not is_classic else None,
        )

        if isinstance(result, ExtractedRule):
            final_rules.append(result)
            stats["auto_corrected"] += 1
        else:
            manual_review_items.append(result)
            stats["manual_review"] += 1
            logger.warning(
                f"[Adjudicator] Added rule {result.rule_number} to manual review: "
                f"{result.failure_reason}"
            )

    # Step 5: Sort and log final summary
    final_rules_sorted = sorted(final_rules, key=lambda r: r.rule_number)

    total_rules = len(final_rules_sorted)
    manual_count = len(manual_review_items)

    logger.info(
        f"[Adjudicator] Adjudication complete: {total_rules} rules in output, "
        f"{manual_count} sent for manual review"
    )

    return final_rules_sorted, manual_review_items, stats


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
