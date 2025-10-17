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


# ============================================================================
# Test Data Structures
# ============================================================================


class TestDataStructures:
    """Tests for TriageResult and ManualReviewItem data structures."""

    def test_triage_result_structure(self) -> None:
        """TriageResult should be a NamedTuple with three fields."""
        from src.qe_tax_rag.extraction.ca.adjudicator import TriageResult

        # Create sample rules
        rule1 = ExtractedRule(
            rule_number=8523,
            title="Meals",
            content="Content",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section="Part 4",
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            anchor_id="tocch3ln8523",
            confidence_score=1.0,
        )

        rule2 = ExtractedRule(
            rule_number=8910,
            title="Vehicle",
            content="Content",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8910",
            chapter="Chapter 3",
            section="Part 4",
            source_file="t4002-5.html",
            expert_source=ExpertSource.LLM,
            anchor_id="tocch3ln8910",
            confidence_score=0.85,
        )

        # Create TriageResult
        result = TriageResult(
            perfect_matches=[rule1],
            conflicts=[(rule1, rule2)],
            orphans=[rule2],
        )

        # Verify structure
        assert len(result.perfect_matches) == 1
        assert len(result.conflicts) == 1
        assert len(result.orphans) == 1
        assert result.perfect_matches[0] == rule1
        assert result.conflicts[0] == (rule1, rule2)
        assert result.orphans[0] == rule2

    def test_manual_review_item_required_fields(self) -> None:
        """ManualReviewItem should require specific fields."""
        from src.qe_tax_rag.extraction.ca.adjudicator import ManualReviewItem

        item = ManualReviewItem(
            rule_number=8523,
            discrepancy_type="CONFLICT",
            failure_reason="API timeout",
            source_file="t4002-5.html",
            timestamp="2025-10-16T10:30:00Z",
        )

        assert item.rule_number == 8523
        assert item.discrepancy_type == "CONFLICT"
        assert item.failure_reason == "API timeout"
        assert item.source_file == "t4002-5.html"
        assert item.timestamp == "2025-10-16T10:30:00Z"

    def test_manual_review_item_for_conflict(self) -> None:
        """ManualReviewItem for conflict should include both versions."""
        from src.qe_tax_rag.extraction.ca.adjudicator import ManualReviewItem

        classic_version = {
            "rule_number": 8523,
            "title": "Meals",
            "content": "Classic content",
            "applies_to": ["business"],
        }

        llm_version = {
            "rule_number": 8523,
            "title": "Meals",
            "content": "LLM content",
            "applies_to": ["business", "fishing"],
        }

        item = ManualReviewItem(
            rule_number=8523,
            discrepancy_type="CONFLICT",
            failure_reason="LLM reported insufficient evidence",
            source_file="t4002-5.html",
            timestamp="2025-10-16T10:30:00Z",
            classic_version=classic_version,
            llm_version=llm_version,
        )

        assert item.classic_version == classic_version
        assert item.llm_version == llm_version
        assert item.orphan_version is None
        assert item.found_by is None

    def test_manual_review_item_for_orphan(self) -> None:
        """ManualReviewItem for orphan should include single version and found_by."""
        from src.qe_tax_rag.extraction.ca.adjudicator import ManualReviewItem

        orphan_version = {
            "rule_number": 9270,
            "title": "Professional fees",
            "content": "Orphan content",
            "applies_to": ["business"],
        }

        item = ManualReviewItem(
            rule_number=9270,
            discrepancy_type="ORPHAN",
            failure_reason="API call failed",
            source_file="t4002-4.html",
            timestamp="2025-10-16T10:30:05Z",
            orphan_version=orphan_version,
            found_by="llm",
        )

        assert item.orphan_version == orphan_version
        assert item.found_by == "llm"
        assert item.classic_version is None
        assert item.llm_version is None
