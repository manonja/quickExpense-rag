"""Tests for classic HTML parser."""

import pytest
from pathlib import Path

from qe_tax_rag.extraction.ca.classic_parser import parse
from qe_tax_rag.extraction.ca.schema import ExtractedRule, ExpertSource, ApplicabilityType
from qe_tax_rag.extraction.ca.exceptions import ParserError


@pytest.fixture
def fixture_html_path() -> Path:
    """Path to test HTML fixture."""
    return (
        Path(__file__).parent.parent.parent.parent
        / "fixtures/extraction/ca/classic_parser_test.html"
    )


@pytest.mark.unit
def test_parse_standard_line_item(fixture_html_path: Path) -> None:
    """Test parsing standard line with single icon and simple content."""
    rules = parse(str(fixture_html_path))

    # Find Line 8523 (Meals and entertainment)
    rule = next((r for r in rules if r.rule_number == 8523), None)

    assert rule is not None, "Line 8523 should be extracted"
    assert rule.title == "Meals and entertainment"
    assert "deduct 50%" in rule.content.lower() or "50%" in rule.content
    assert rule.applies_to == [ApplicabilityType.BUSINESS]
    assert rule.expert_source == ExpertSource.CLASSIC
    assert rule.source_citation == "Line 8523"
    assert rule.confidence_score == 1.0
    assert rule.chapter == "Chapter 3 – Business Expenses"
    assert rule.section == "Part 1 – Income/Loss and Net Income"
    assert rule.source_file == "classic_parser_test.html"
    assert rule.anchor_id == "tocch3ln8523"
