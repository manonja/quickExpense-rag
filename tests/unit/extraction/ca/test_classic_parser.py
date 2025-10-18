"""Tests for classic HTML parser."""

from pathlib import Path

import pytest
from qe_tax_rag.extraction.ca.classic_parser import parse
from qe_tax_rag.extraction.ca.exceptions import ParserError
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
)


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


@pytest.mark.unit
def test_parse_complex_content_structure(fixture_html_path: Path) -> None:
    """Test parsing rule with multiple p tags and ol list."""
    rules = parse(str(fixture_html_path))

    # Line 9200 has multiple p tags + ol list
    rule = next((r for r in rules if r.rule_number == 9200), None)

    assert rule is not None, "Line 9200 should be extracted"
    assert rule.title == "Legal and accounting fees"
    assert ApplicabilityType.BUSINESS in rule.applies_to
    assert ApplicabilityType.FISHING in rule.applies_to

    # Verify content includes all paragraphs and list items
    assert "external professional advice" in rule.content.lower()
    assert "accounting fees" in rule.content.lower()
    assert "legal fees" in rule.content.lower()
    assert "not deduct fees for buying capital" in rule.content.lower()

    # Verify whitespace normalization (max 2 newlines)
    assert "\n\n\n" not in rule.content


@pytest.mark.unit
def test_skip_conceptual_h3_without_line_pattern(fixture_html_path: Path) -> None:
    """Test that h3 tags without 'Line XXXX –' are skipped."""
    rules = parse(str(fixture_html_path))

    # Should not find "Prepaid expenses"
    assert not any("prepaid" in r.title.lower() for r in rules)
    assert not any("prepaid" in r.content.lower() for r in rules)


@pytest.mark.unit
def test_skip_malformed_rule_and_log_warning(fixture_html_path: Path, caplog) -> None:  # type: ignore[no-untyped-def]
    """Test parser skips malformed rules and logs warning."""
    import logging

    caplog.set_level(logging.WARNING)

    rules = parse(str(fixture_html_path))

    # Line 9999 has no content - should be skipped
    assert not any(r.rule_number == 9999 for r in rules)

    # Should have logged warning
    assert any(
        "9999" in record.message and "no content" in record.message.lower()
        for record in caplog.records
    )


@pytest.mark.unit
def test_continue_after_malformed_rule(fixture_html_path: Path) -> None:
    """Test parser continues after encountering malformed rule."""
    rules = parse(str(fixture_html_path))

    # Line 8960 comes after malformed 9999 - should still be parsed
    rule = next((r for r in rules if r.rule_number == 8960), None)

    assert rule is not None, "Line 8960 should be extracted"
    assert rule.title == "Office expenses"
    assert "pens, pencils" in rule.content.lower()


@pytest.mark.unit
def test_raise_parser_error_on_invalid_file_path() -> None:
    """Test ParserError raised for non-existent file."""
    with pytest.raises(ParserError, match="not found"):
        parse("/nonexistent/path/to/file.html")


@pytest.mark.unit
def test_return_empty_list_for_files_without_line_patterns(tmp_path: Path) -> None:
    """Parser should return [] (not error) for HTML without 'Line XXXX –' patterns.

    Files like CCA chapters (t4002-6.html) contain valid content but no
    line-numbered expense rules. This is an expected edge case.
    """
    import logging

    # Create HTML file without "Line XXXX –" patterns (CCA chapter example)
    cca_html = tmp_path / "t4002-cca-chapter.html"
    cca_html.write_text(
        """
        <!DOCTYPE html>
        <html>
        <head><title>CCA Chapter</title></head>
        <body>
            <main>
                <h1>Chapter 4 – Capital Cost Allowance</h1>
                <h2>Basic information about CCA</h2>
                <h3><a id="ch4cd32321"></a>Basic information about CCA</h3>
                <p>Capital cost allowance (CCA) is the tax deduction...</p>
                <h3><a id="ch4IEI"></a>Immediate expensing incentive</h3>
                <p>Details about the incentive...</p>
            </main>
        </body>
        </html>
        """,
        encoding="utf-8",
    )

    # This should NOT raise ParserError
    result = parse(str(cca_html))

    # Assertions
    assert result == [], "Should return empty list for files without line patterns"
