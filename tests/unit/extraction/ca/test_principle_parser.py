"""
Unit tests for principle_parser.py (Phase 2).

Tests extraction of rule references (PRINCIPLE content type).
"""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from qe_tax_rag.extraction.ca.models import ContentType
from qe_tax_rag.extraction.ca.principle_parser import (
    extract_line_references,
    is_rule_definition,
)


@pytest.mark.unit
def test_extract_line_references_single():
    """Test extracting single line reference from text."""
    text = "Enter on line 9925 the total business part of the cost."

    references = extract_line_references(text)

    assert references == ["LINE-9925"]


@pytest.mark.unit
def test_extract_line_references_multiple():
    """Test extracting multiple line references from text."""
    text = "Complete line 9600 if you have farming income. Also see line 9270 for expenses."

    references = extract_line_references(text)

    # Should be sorted and deduplicated
    assert references == ["LINE-9270", "LINE-9600"]


@pytest.mark.unit
def test_extract_line_references_case_insensitive():
    """Test that pattern matching is case-insensitive."""
    text = "See Line 8523, line 9600, and LINE 9270 for details."

    references = extract_line_references(text)

    assert references == ["LINE-8523", "LINE-9270", "LINE-9600"]


@pytest.mark.unit
def test_extract_line_references_deduplication():
    """Test that duplicate references are deduplicated."""
    text = "Enter line 9925 for equipment. Also see line 9925 for buildings."

    references = extract_line_references(text)

    # Should only appear once
    assert references == ["LINE-9925"]


@pytest.mark.unit
def test_extract_line_references_no_matches():
    """Test that empty list is returned when no line references found."""
    text = "This paragraph doesn't mention any line numbers at all."

    references = extract_line_references(text)

    assert references == []


@pytest.mark.unit
def test_extract_line_references_boundary():
    """Test that pattern only matches 4-digit line numbers."""
    # Should NOT match 3-digit or 5-digit numbers
    text = "Line 123 is too short. Line 12345 is too long. Line 9600 is just right."

    references = extract_line_references(text)

    # Only 4-digit number should match
    assert references == ["LINE-9600"]


@pytest.mark.unit
def test_is_rule_definition_with_anchor():
    """Test that tags with anchor IDs are recognized as rule definitions."""
    html = """
    <h3>
        <a id="tocch2ln9600"></a>
        Line 9600 – Other income
    </h3>
    """
    soup = BeautifulSoup(html, "lxml")
    h3_tag = soup.find("h3")

    assert is_rule_definition(h3_tag) is True


@pytest.mark.unit
def test_is_rule_definition_with_suffix():
    """Test that anchor IDs with suffixes are recognized as rule definitions."""
    html = """
    <h3>
        <a id="tocch2ln8299fshng"></a>
        Line 8299 – Fishing gear
    </h3>
    """
    soup = BeautifulSoup(html, "lxml")
    h3_tag = soup.find("h3")

    assert is_rule_definition(h3_tag) is True


@pytest.mark.unit
def test_is_rule_definition_without_anchor():
    """Test that tags without anchor IDs are NOT rule definitions."""
    html = """
    <p>
        Enter on <span class="nowrap">line 9925</span> the total.
    </p>
    """
    soup = BeautifulSoup(html, "lxml")
    p_tag = soup.find("p")

    assert is_rule_definition(p_tag) is False


@pytest.mark.unit
def test_is_rule_definition_wrong_pattern():
    """Test that anchors not matching pattern are NOT rule definitions."""
    html = """
    <h3>
        <a id="some-other-anchor"></a>
        Some heading
    </h3>
    """
    soup = BeautifulSoup(html, "lxml")
    h3_tag = soup.find("h3")

    assert is_rule_definition(h3_tag) is False


@pytest.mark.unit
def test_parse_extracts_principles_from_fixture(tmp_path: Path):
    """
    Test principle extraction from a simple HTML fixture.

    Acceptance Criterion 2.2.2: Non-empty extraction
    Acceptance Criterion 2.2.3: Correct content typing
    """
    from qe_tax_rag.extraction.ca.principle_parser import parse

    # Create minimal HTML fixture with principles
    html_content = """
    <html>
    <body>
        <p>Enter on line 9925 the total business part of the cost of the equipment.</p>
        <p>Enter on line 9927 the total business part of the cost of the buildings.</p>
        <li>line 9600 for farming income</li>
        <li>line 9270 for fishing expenses</li>
        <p>This paragraph has no line references.</p>
    </body>
    </html>
    """

    # Write to temp file
    html_file = tmp_path / "test.html"
    html_file.write_text(html_content)

    # Extract principles
    principles = parse(str(html_file))

    # AC 2.2.2: Non-empty extraction
    assert len(principles) > 0, "Should extract at least one principle"

    # AC 2.2.3: Correct content typing
    for principle in principles:
        assert principle.content_type == ContentType.PRINCIPLE

    # Verify expected count (4 tags with line references)
    assert len(principles) == 4


@pytest.mark.unit
def test_parse_reference_integrity(tmp_path: Path):
    """
    Test reference-text integrity for principles.

    Acceptance Criterion 2.2.4: For known principle containing "line 9925",
    the extracted object must contain accurate text and references list.
    """
    from qe_tax_rag.extraction.ca.principle_parser import parse

    html_content = """
    <html>
    <body>
        <p>Enter on line 9925 the total business part of the cost of the equipment.</p>
    </body>
    </html>
    """

    html_file = tmp_path / "test.html"
    html_file.write_text(html_content)

    principles = parse(str(html_file))

    # Should extract exactly one principle
    assert len(principles) == 1

    principle = principles[0]

    # AC 2.2.4: Text integrity
    assert "line 9925" in principle.text.lower()
    assert "equipment" in principle.text.lower()

    # AC 2.2.4: References list integrity
    assert "LINE-9925" in principle.references


@pytest.mark.unit
def test_parse_excludes_rule_definitions(tmp_path: Path):
    """
    Test that parser excludes content where is_rule_definition() returns True.

    Acceptance Criterion 2.2.5: Parser must NOT extract rule definitions
    as principles, even if they contain line references.
    """
    from qe_tax_rag.extraction.ca.principle_parser import parse

    # HTML with both rule definition and principle reference
    html_content = """
    <html>
    <body>
        <!-- This is a RULE definition (has anchor ID) -->
        <h3>
            <a id="tocch2ln9600"></a>
            Line 9600 – Other income
        </h3>
        <p>This is the content of the rule definition.</p>

        <!-- This is a PRINCIPLE (reference to line 9600) -->
        <p>Complete line 9600 if you have other farming income.</p>
    </body>
    </html>
    """

    html_file = tmp_path / "test.html"
    html_file.write_text(html_content)

    principles = parse(str(html_file))

    # Should only extract the <p> tag, not the <h3> rule definition
    assert len(principles) == 1

    # Verify it's the principle, not the definition
    principle = principles[0]
    assert "Complete line 9600" in principle.text
    assert "Other income" not in principle.text

    # Verify content type
    assert principle.content_type == ContentType.PRINCIPLE


@pytest.mark.unit
def test_parse_citation_id_format(tmp_path: Path):
    """Test that citation_id follows expected format: {source_file}-PRINCIPLE-{seq}."""
    from qe_tax_rag.extraction.ca.principle_parser import parse

    html_content = """
    <html>
    <body>
        <p>Enter on line 9925 the total.</p>
        <p>Enter on line 9927 the buildings.</p>
    </body>
    </html>
    """

    html_file = tmp_path / "t4002-6.html"
    html_file.write_text(html_content)

    principles = parse(str(html_file))

    # Should have two principles
    assert len(principles) == 2

    # Verify citation_id format
    assert principles[0].citation_id == "t4002-6-PRINCIPLE-1"
    assert principles[1].citation_id == "t4002-6-PRINCIPLE-2"


@pytest.mark.unit
def test_parse_empty_when_no_references(tmp_path: Path):
    """Test that parser returns empty list when no line references found."""
    from qe_tax_rag.extraction.ca.principle_parser import parse

    html_content = """
    <html>
    <body>
        <p>This paragraph has no line references.</p>
        <p>Neither does this one.</p>
    </body>
    </html>
    """

    html_file = tmp_path / "test.html"
    html_file.write_text(html_content)

    principles = parse(str(html_file))

    # Should return empty list (no principles)
    assert principles == []
