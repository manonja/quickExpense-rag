"""Unit tests for the adjudicator module."""

import pytest
from src.qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_rule_classic() -> ExtractedRule:
    """Sample rule from classic parser."""
    return ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="You can deduct the cost of meals and entertainment.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3 – Expenses",
        section="Part 4 – Net income (loss) before adjustments",
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id="tocch3ln8523",
        confidence_score=1.0,
    )


@pytest.fixture
def sample_rule_llm_identical() -> ExtractedRule:
    """Sample rule from LLM parser identical to classic."""
    return ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="You can deduct the cost of meals and entertainment.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3 – Expenses",
        section="Part 4 – Net income (loss) before adjustments",
        source_file="t4002-5.html",
        expert_source=ExpertSource.LLM,
        anchor_id="tocch3ln8523",
        confidence_score=0.85,
    )


@pytest.fixture
def sample_rule_llm_diff_title() -> ExtractedRule:
    """Sample rule from LLM with different title."""
    return ExtractedRule(
        rule_number=8523,
        title="Meals & entertainment",  # Different
        content="You can deduct the cost of meals and entertainment.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3 – Expenses",
        section="Part 4",
        source_file="t4002-5.html",
        expert_source=ExpertSource.LLM,
        anchor_id="tocch3ln8523",
        confidence_score=0.85,
    )


@pytest.fixture
def sample_rule_llm_diff_applies_to() -> ExtractedRule:
    """Sample rule from LLM with different applies_to."""
    return ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="You can deduct the cost of meals and entertainment.",
        applies_to=[ApplicabilityType.BUSINESS, ApplicabilityType.FISHING],  # Different
        source_citation="Line 8523",
        chapter="Chapter 3 – Expenses",
        section="Part 4",
        source_file="t4002-5.html",
        expert_source=ExpertSource.LLM,
        anchor_id="tocch3ln8523",
        confidence_score=0.85,
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


# ============================================================================
# Test Triage
# ============================================================================


class TestTriage:
    """Tests for _triage_rules function."""

    def test_triage_perfect_match_identical_rules(
        self,
        sample_rule_classic: ExtractedRule,
        sample_rule_llm_identical: ExtractedRule,
    ) -> None:
        """Perfect match when normalized rules are identical."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        result = _triage_rules([sample_rule_classic], [sample_rule_llm_identical])

        assert len(result.perfect_matches) == 1
        assert len(result.conflicts) == 0
        assert len(result.orphans) == 0
        # Should prefer classic parser version
        assert result.perfect_matches[0].expert_source == ExpertSource.CLASSIC

    def test_triage_perfect_match_prefers_classic_parser(
        self,
        sample_rule_classic: ExtractedRule,
        sample_rule_llm_identical: ExtractedRule,
    ) -> None:
        """On perfect match, should use classic parser version (deterministic)."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        result = _triage_rules([sample_rule_classic], [sample_rule_llm_identical])

        perfect_match = result.perfect_matches[0]
        assert perfect_match.expert_source == ExpertSource.CLASSIC
        assert perfect_match.confidence_score == 1.0  # Classic parser confidence

    def test_triage_conflict_when_title_differs(
        self,
        sample_rule_classic: ExtractedRule,
        sample_rule_llm_diff_title: ExtractedRule,
    ) -> None:
        """Conflict when title differs between parsers."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        result = _triage_rules([sample_rule_classic], [sample_rule_llm_diff_title])

        assert len(result.perfect_matches) == 0
        assert len(result.conflicts) == 1
        assert len(result.orphans) == 0

        classic_rule, llm_rule = result.conflicts[0]
        assert classic_rule.expert_source == ExpertSource.CLASSIC
        assert llm_rule.expert_source == ExpertSource.LLM
        assert classic_rule.title != llm_rule.title

    def test_triage_conflict_when_applies_to_differs(
        self,
        sample_rule_classic: ExtractedRule,
        sample_rule_llm_diff_applies_to: ExtractedRule,
    ) -> None:
        """Conflict when applies_to list differs between parsers."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        result = _triage_rules([sample_rule_classic], [sample_rule_llm_diff_applies_to])

        assert len(result.perfect_matches) == 0
        assert len(result.conflicts) == 1
        assert len(result.orphans) == 0

        classic_rule, llm_rule = result.conflicts[0]
        assert len(classic_rule.applies_to) == 1
        assert len(llm_rule.applies_to) == 2

    def test_triage_orphan_classic_only(
        self, sample_rule_classic: ExtractedRule
    ) -> None:
        """Orphan when only classic parser found the rule."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        result = _triage_rules([sample_rule_classic], [])

        assert len(result.perfect_matches) == 0
        assert len(result.conflicts) == 0
        assert len(result.orphans) == 1
        assert result.orphans[0].expert_source == ExpertSource.CLASSIC

    def test_triage_orphan_llm_only(
        self, sample_rule_llm_identical: ExtractedRule
    ) -> None:
        """Orphan when only LLM parser found the rule."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        result = _triage_rules([], [sample_rule_llm_identical])

        assert len(result.perfect_matches) == 0
        assert len(result.conflicts) == 0
        assert len(result.orphans) == 1
        assert result.orphans[0].expert_source == ExpertSource.LLM

    def test_triage_multiple_orphans_from_both_parsers(
        self, sample_rule_classic: ExtractedRule
    ) -> None:
        """Multiple orphans from different parsers."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        classic_orphan = sample_rule_classic

        llm_orphan = ExtractedRule(
            rule_number=9270,
            title="Professional fees",
            content="You can deduct professional fees.",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 9270",
            chapter="Chapter 3",
            section="Part 4",
            source_file="t4002-5.html",
            expert_source=ExpertSource.LLM,
            anchor_id="tocch3ln9270",
            confidence_score=0.85,
        )

        result = _triage_rules([classic_orphan], [llm_orphan])

        assert len(result.perfect_matches) == 0
        assert len(result.conflicts) == 0
        assert len(result.orphans) == 2

        # Should have one from each parser
        expert_sources = {orphan.expert_source for orphan in result.orphans}
        assert expert_sources == {ExpertSource.CLASSIC, ExpertSource.LLM}

    def test_triage_empty_input_lists(self) -> None:
        """Triage with empty input lists should return empty results."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        result = _triage_rules([], [])

        assert len(result.perfect_matches) == 0
        assert len(result.conflicts) == 0
        assert len(result.orphans) == 0

    def test_triage_logs_summary_correctly(
        self,
        sample_rule_classic: ExtractedRule,
        sample_rule_llm_identical: ExtractedRule,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Triage should log summary of categorization results."""
        import logging

        from src.qe_tax_rag.extraction.ca.adjudicator import _triage_rules

        caplog.set_level(logging.INFO)

        _triage_rules([sample_rule_classic], [sample_rule_llm_identical])

        # Check for triage log messages
        assert any("Triage complete" in record.message for record in caplog.records)
        assert any("1 perfect matches" in record.message for record in caplog.records)


# ============================================================================
# Test HTML Truncation
# ============================================================================


class TestHTMLTruncation:
    """Tests for _truncate_html_for_prompt function."""

    def test_truncate_html_no_truncation_for_small_content(self) -> None:
        """Small HTML content should not be truncated."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _truncate_html_for_prompt

        small_html = (
            "<html><body><h3>Line 8523 – Meals</h3><p>Content here</p></body></html>"
        )

        result = _truncate_html_for_prompt(small_html, anchor_id="tocch3ln8523")

        # Should return full content unchanged
        assert result == small_html

    def test_truncate_html_with_anchor_id_extracts_context(self) -> None:
        """Large HTML with anchor_id should extract contextual window."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _truncate_html_for_prompt

        # Create large HTML content (over 300K chars)
        # Need to ensure it's actually over 300K
        filler = "x" * 10000  # 10K chars per filler
        large_html = (
            "<html><body>"
            + f"<p>{filler}</p>" * 20  # 200K chars of filler
            + "<h2>Part 4 – Net income</h2>"
            + "<p>Section intro</p>"
            + '<h3 id="tocch3ln8523"><a id="tocch3ln8523"></a>Line 8523 – Meals</h3>'
            + "<p>You can deduct meals.</p>"
            + "<ul><li>Item 1</li></ul>"
            + "<h3>Line 8910 – Vehicle</h3>"
            + f"<p>{filler}</p>" * 20  # Another 200K chars
            + "</body></html>"
        )

        result = _truncate_html_for_prompt(large_html, anchor_id="tocch3ln8523")

        # Should include truncation notice OR extracted only relevant section (not full HTML)
        is_truncated = (
            "[...CONTENT TRUNCATED...]" in result
            or len(result) < len(large_html) * 0.5  # Less than half original size
        )
        assert is_truncated, "HTML should be truncated"
        # Should include the target h3
        assert "Line 8523 – Meals" in result
        # Should NOT include all the filler (context extraction should work)
        # Count how many 'x' chars are in result vs original
        x_count_in_result = result.count("x")
        x_count_in_original = large_html.count("x")
        assert x_count_in_result < x_count_in_original * 0.5, (
            "Should have removed most filler"
        )

    def test_truncate_html_without_anchor_id_takes_first_and_last(self) -> None:
        """Large HTML without anchor_id should take first and last chunks."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _truncate_html_for_prompt

        # Create large HTML content
        large_html = (
            "<html><body><h1>Start content</h1>"
            + "<p>Filler</p>" * 100000
            + "<h1>End content</h1></body></html>"
        )

        result = _truncate_html_for_prompt(large_html, anchor_id=None)

        # Should include truncation notice
        assert "[...CONTENT TRUNCATED" in result or "TRUNCATED" in result
        # Should have start and end
        assert "Start content" in result
        assert "End content" in result

    def test_truncate_html_handles_missing_anchor_id(self) -> None:
        """Large HTML with anchor_id that doesn't exist should fall back."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _truncate_html_for_prompt

        large_html = (
            "<html><body><h1>Start</h1>"
            + "<p>Filler</p>" * 100000
            + "<h1>End</h1></body></html>"
        )

        result = _truncate_html_for_prompt(large_html, anchor_id="nonexistent_anchor")

        # Should fall back to first/last chunks
        assert "TRUNCATED" in result
        assert "Start" in result
        assert "End" in result

    def test_truncate_html_includes_truncation_warning(self) -> None:
        """Truncated HTML should include warning message."""
        from src.qe_tax_rag.extraction.ca.adjudicator import _truncate_html_for_prompt

        large_html = "<p>Content</p>" * 200000

        result = _truncate_html_for_prompt(large_html, anchor_id=None)

        # Should have clear truncation warning
        assert "TRUNCATED" in result.upper()
