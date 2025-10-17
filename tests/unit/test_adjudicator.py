"""Unit tests for the adjudicator module."""

import pytest
from src.qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
)


# ============================================================================
# Test Normalization
# ============================================================================


class TestNormalization:
    """Tests for _normalize_rule_for_comparison helper function."""

    def test_normalize_rule_strips_whitespace_from_title(self) -> None:
        """Normalization should strip leading/trailing whitespace from title."""
        from src.qe_tax_rag.extraction.ca.adjudicator import (
            _normalize_rule_for_comparison,
        )

        rule = ExtractedRule(
            rule_number=8523,
            title="  Meals and entertainment  ",
            content="You can deduct the cost of meals.",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section="Part 4",
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            anchor_id="tocch3ln8523",
            confidence_score=1.0,
        )

        normalized = _normalize_rule_for_comparison(rule)

        assert normalized["title"] == "Meals and entertainment"
        assert normalized["title"] == rule.title.strip()

    def test_normalize_rule_collapses_whitespace_in_content(self) -> None:
        """Normalization should collapse consecutive whitespace to single space."""
        from src.qe_tax_rag.extraction.ca.adjudicator import (
            _normalize_rule_for_comparison,
        )

        rule = ExtractedRule(
            rule_number=8523,
            title="Meals",
            content="You can deduct\n\n  the cost  of\t\tmeals.",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section="Part 4",
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            anchor_id="tocch3ln8523",
            confidence_score=1.0,
        )

        normalized = _normalize_rule_for_comparison(rule)

        assert normalized["content"] == "You can deduct the cost of meals."
        # Verify no consecutive spaces
        assert "  " not in normalized["content"]
        assert "\n" not in normalized["content"]
        assert "\t" not in normalized["content"]

    def test_normalize_rule_sorts_applies_to_list(self) -> None:
        """Normalization should sort applies_to list alphabetically."""
        from src.qe_tax_rag.extraction.ca.adjudicator import (
            _normalize_rule_for_comparison,
        )

        rule = ExtractedRule(
            rule_number=8523,
            title="Meals",
            content="Content here",
            applies_to=[
                ApplicabilityType.FISHING,
                ApplicabilityType.BUSINESS,
                ApplicabilityType.FARMING,
            ],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section="Part 4",
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            anchor_id="tocch3ln8523",
            confidence_score=1.0,
        )

        normalized = _normalize_rule_for_comparison(rule)

        # Should be sorted: business, farming, fishing
        assert normalized["applies_to"] == ["business", "farming", "fishing"]

    def test_normalize_rule_handles_empty_applies_to(self) -> None:
        """Normalization should handle empty applies_to list."""
        from src.qe_tax_rag.extraction.ca.adjudicator import (
            _normalize_rule_for_comparison,
        )

        rule = ExtractedRule(
            rule_number=8523,
            title="Meals",
            content="Content here",
            applies_to=[],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section="Part 4",
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            anchor_id="tocch3ln8523",
            confidence_score=1.0,
        )

        normalized = _normalize_rule_for_comparison(rule)

        assert normalized["applies_to"] == []
