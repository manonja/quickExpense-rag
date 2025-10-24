"""
Test adjudicator graceful degradation with API quota exhaustion fallback.

When Gemini API calls fail during adjudication (429 quota errors, timeouts, etc.),
the adjudicator should fall back to using classic parser results instead of
creating ManualReviewItems. This ensures the pipeline continues extracting rules
even under API failures.
"""

from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import ResourceExhausted
from qe_tax_rag.extraction.ca.adjudicator import adjudicate
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
)


@pytest.fixture
def sample_html_content():
    """Minimal HTML fixture for adjudication tests."""
    return """
    <html>
        <main>
            <h1>Chapter 3 – Expenses</h1>
            <h2>Part 4 – Net income</h2>
            <h3><a id="tocch3ln8523">Line 8523 – Meals</a>
                <img alt="business icon">
            </h3>
            <p>You can deduct 50% of meal costs.</p>
        </main>
    </html>
    """


@pytest.fixture
def classic_rule():
    """Classic parser result - deterministic and trustworthy."""
    return ExtractedRule(
        rule_number=8523,
        title="Meals",
        content="You can deduct 50% of meal costs.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523 – Meals",
        chapter="Chapter 3 – Expenses",
        section="Part 4 – Net income",
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id="tocch3ln8523",
        confidence_score=0.9,
    )


@pytest.fixture
def llm_rule():
    """LLM parser result - slightly different from classic (conflict scenario)."""
    return ExtractedRule(
        rule_number=8523,
        title="Meals and Entertainment",  # Different title
        content="You can deduct 50% of meal costs.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523 – Meals",
        chapter="Chapter 3 – Expenses",
        section="Part 4 – Net income",
        source_file="t4002-5.html",
        expert_source=ExpertSource.LLM,
        anchor_id="tocch3ln8523",
        confidence_score=0.8,
    )


class TestAdjudicatorFallback:
    """Test adjudicator fallback behavior under API failures."""

    @patch("google.generativeai.GenerativeModel")
    def test_conflict_falls_back_to_classic_on_quota_error(
        self, mock_genai, classic_rule, llm_rule, sample_html_content
    ):
        """
        When adjudication API fails with 429, use classic parser result instead of ManualReviewItem.

        Expected behavior (NEW):
        - Detect ResourceExhausted error
        - Fall back to classic_rule (deterministic source of truth)
        - Return ExtractedRule with expert_source=CLASSIC
        - NO ManualReviewItem created

        Current behavior (BUG):
        - Catches all exceptions
        - Creates ManualReviewItem
        - Final output has 0 rules
        """
        mock_model = mock_genai.return_value
        mock_model.generate_content.side_effect = ResourceExhausted(
            "429 quota exceeded"
        )

        # Act
        resolved_rules, manual_items, stats = adjudicate(
            classic_rules=[classic_rule],
            llm_rules=[llm_rule],
            source_html_content=sample_html_content,
            source_file="t4002-5.html",
        )

        # Assert - Should fall back to classic, not manual review
        assert (
            len(resolved_rules) == 1
        ), "Should have 1 resolved rule (classic fallback)"
        assert (
            len(manual_items) == 0
        ), "Should NOT create manual review item on quota error"

        # Verify the returned rule is the classic one
        assert resolved_rules[0].rule_number == 8523
        assert resolved_rules[0].title == "Meals"  # Classic version
        assert resolved_rules[0].expert_source == ExpertSource.CLASSIC

        # Stats should reflect fallback
        assert stats["perfect_matches"] == 0
        assert stats["auto_corrected"] == 1  # Fallback counted as auto-correction
        assert stats["manual_review"] == 0

    @patch("google.generativeai.GenerativeModel")
    def test_orphan_falls_back_to_classic_on_timeout(
        self, mock_genai, classic_rule, sample_html_content
    ):
        """
        When adjudication times out on orphan, use the orphan rule if it's from classic parser.

        Expected behavior (NEW):
        - Detect timeout error
        - If orphan is from classic parser → trust it (fallback)
        - If orphan is from LLM parser → create ManualReviewItem (can't trust LLM without validation)
        - Return ExtractedRule with expert_source=CLASSIC for classic orphans

        Current behavior (BUG):
        - Creates ManualReviewItem for all orphans on error
        - Loses classic parser's deterministic result
        """
        import socket

        mock_model = mock_genai.return_value
        mock_model.generate_content.side_effect = socket.timeout("Timeout after 30s")

        # Act - Only classic parser found this rule (orphan from classic)
        resolved_rules, manual_items, stats = adjudicate(
            classic_rules=[classic_rule],
            llm_rules=[],  # LLM didn't find it
            source_html_content=sample_html_content,
            source_file="t4002-5.html",
        )

        # Assert - Should trust classic orphan on timeout
        assert len(resolved_rules) == 1, "Should trust classic orphan on timeout"
        assert (
            len(manual_items) == 0
        ), "Should NOT create manual review for classic orphan"

        assert resolved_rules[0].rule_number == 8523
        assert resolved_rules[0].expert_source == ExpertSource.CLASSIC

        assert stats["manual_review"] == 0

    @patch("google.generativeai.GenerativeModel")
    def test_llm_orphan_creates_manual_review_on_api_failure(
        self, mock_genai, llm_rule, sample_html_content
    ):
        """
        LLM orphans still require manual review on API failure (can't trust without validation).

        This is the correct behavior - we can't blindly trust LLM parser results
        without adjudication. Only classic parser is deterministic enough to trust
        during API failures.
        """
        mock_model = mock_genai.return_value
        mock_model.generate_content.side_effect = ResourceExhausted(
            "429 quota exceeded"
        )

        # Act - Only LLM found this rule (orphan from LLM)
        resolved_rules, manual_items, stats = adjudicate(
            classic_rules=[],  # Classic didn't find it
            llm_rules=[llm_rule],
            source_html_content=sample_html_content,
            source_file="t4002-5.html",
        )

        # Assert - LLM orphan should go to manual review (can't trust)
        assert (
            len(resolved_rules) == 0
        ), "Should NOT auto-accept LLM orphan on API failure"
        assert len(manual_items) == 1, "Should create manual review for LLM orphan"

        assert manual_items[0].rule_number == 8523
        assert manual_items[0].discrepancy_type == "ORPHAN"
        assert manual_items[0].found_by == "llm"

        assert stats["manual_review"] == 1

    @patch("google.generativeai.GenerativeModel")
    def test_multiple_conflicts_all_fall_back_to_classic(
        self, mock_genai, sample_html_content
    ):
        """
        When API quota is exhausted, all conflicts should fall back to classic parser.

        This ensures the pipeline continues producing rules even when all
        adjudication calls fail (e.g., sustained quota exhaustion).
        """
        mock_model = mock_genai.return_value
        mock_model.generate_content.side_effect = ResourceExhausted(
            "429 quota exceeded"
        )

        # Create 3 conflicting rules
        classic_rules = [
            ExtractedRule(
                rule_number=8523,
                title="Meals",
                content="Content A",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="Chapter 3",
                section=None,
                source_file="test.html",
                expert_source=ExpertSource.CLASSIC,
                anchor_id=None,
                confidence_score=0.9,
            ),
            ExtractedRule(
                rule_number=8590,
                title="Travel",
                content="Content B",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8590",
                chapter="Chapter 3",
                section=None,
                source_file="test.html",
                expert_source=ExpertSource.CLASSIC,
                anchor_id=None,
                confidence_score=0.9,
            ),
            ExtractedRule(
                rule_number=9281,
                title="Vehicle",
                content="Content C",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 9281",
                chapter="Chapter 3",
                section=None,
                source_file="test.html",
                expert_source=ExpertSource.CLASSIC,
                anchor_id=None,
                confidence_score=0.9,
            ),
        ]

        llm_rules = [
            ExtractedRule(
                rule_number=8523,
                title="Meals and Entertainment",  # Different
                content="Content A",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="Chapter 3",
                section=None,
                source_file="test.html",
                expert_source=ExpertSource.LLM,
                anchor_id=None,
                confidence_score=0.8,
            ),
            ExtractedRule(
                rule_number=8590,
                title="Travel Expenses",  # Different
                content="Content B",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8590",
                chapter="Chapter 3",
                section=None,
                source_file="test.html",
                expert_source=ExpertSource.LLM,
                anchor_id=None,
                confidence_score=0.8,
            ),
            ExtractedRule(
                rule_number=9281,
                title="Motor Vehicle",  # Different
                content="Content C",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 9281",
                chapter="Chapter 3",
                section=None,
                source_file="test.html",
                expert_source=ExpertSource.LLM,
                anchor_id=None,
                confidence_score=0.8,
            ),
        ]

        # Act
        resolved_rules, manual_items, stats = adjudicate(
            classic_rules=classic_rules,
            llm_rules=llm_rules,
            source_html_content=sample_html_content,
            source_file="test.html",
        )

        # Assert - All conflicts should resolve to classic versions
        assert (
            len(resolved_rules) == 3
        ), "Should have 3 resolved rules (all classic fallbacks)"
        assert len(manual_items) == 0, "Should have NO manual review items"

        # Verify all are classic versions
        titles = [r.title for r in resolved_rules]
        assert "Meals" in titles  # Not "Meals and Entertainment"
        assert "Travel" in titles  # Not "Travel Expenses"
        assert "Vehicle" in titles  # Not "Motor Vehicle"

        assert all(r.expert_source == ExpertSource.CLASSIC for r in resolved_rules)

        assert stats["auto_corrected"] == 3
        assert stats["manual_review"] == 0
