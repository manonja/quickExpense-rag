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


@pytest.mark.unit
def test_extract_multiple_icons(fixture_html_path: Path) -> None:
    """Test extraction of multiple icons (business + farming)."""
    rules = parse(str(fixture_html_path))

    # Line 9270 has both business and farm icons
    rule = next((r for r in rules if r.rule_number == 9270), None)

    assert rule is not None, "Line 9270 should be extracted"
    assert rule.title == "Motor vehicle expenses"
    assert ApplicabilityType.BUSINESS in rule.applies_to
    assert ApplicabilityType.FARMING in rule.applies_to
    assert len(rule.applies_to) == 2


@pytest.mark.unit
def test_no_icons_empty_applies_to(fixture_html_path: Path) -> None:
    """Test rules without icons have empty applies_to list."""
    rules = parse(str(fixture_html_path))

    # Line 8810 has no icons
    rule = next((r for r in rules if r.rule_number == 8810), None)

    assert rule is not None, "Line 8810 should be extracted"
    assert rule.title == "Salaries and wages"
    assert rule.applies_to == []


@pytest.mark.unit
def test_fishing_icon_extraction(fixture_html_path: Path) -> None:
    """Test fishing icon extracted correctly."""
    rules = parse(str(fixture_html_path))

    # Line 8000 has fish icon
    rule = next((r for r in rules if r.rule_number == 8000), None)

    assert rule is not None, "Line 8000 should be extracted"
    assert rule.title == "Utilities"
    assert rule.applies_to == [ApplicabilityType.FISHING]
