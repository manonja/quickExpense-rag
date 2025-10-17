"""Unit tests for parser Pydantic schema models."""

import pytest
from pydantic import ValidationError


def test_metadata_model_valid():
    """Test Metadata model accepts valid data."""
    from scripts.parser.schema import Metadata

    metadata = Metadata(
        province=["BC", "ON"],
        business_type=["sole_proprietorship"],
        expense_type=["meals", "travel"],
    )

    assert metadata.province == ["BC", "ON"]
    assert metadata.business_type == ["sole_proprietorship"]
    assert metadata.expense_type == ["meals", "travel"]


def test_metadata_model_defaults_to_empty_lists():
    """Test Metadata fields default to empty lists."""
    from scripts.parser.schema import Metadata

    metadata = Metadata()

    assert metadata.province == []
    assert metadata.business_type == []
    assert metadata.expense_type == []


def test_metadata_model_immutable():
    """Test Metadata model is immutable (frozen)."""
    from scripts.parser.schema import Metadata

    metadata = Metadata(province=["BC"])

    with pytest.raises((ValidationError, AttributeError)):
        metadata.province = ["ON"]


def test_text_chunk_model_with_citation():
    """Test TextChunk model with citation."""
    from scripts.parser.schema import TextChunk

    chunk = TextChunk(
        type="paragraph",
        text="A taxpayer's capital cost of depreciable property...",
        citation_id="S3-F2-C1-p1.25",
    )

    assert chunk.type == "paragraph"
    assert "capital cost" in chunk.text
    assert chunk.citation_id == "S3-F2-C1-p1.25"


def test_text_chunk_model_without_citation():
    """Test TextChunk model without citation (optional)."""
    from scripts.parser.schema import TextChunk

    chunk = TextChunk(type="footnote", text="See section 5 for details.")

    assert chunk.type == "footnote"
    assert chunk.citation_id is None


def test_text_chunk_type_literal_enforcement():
    """Test TextChunk type field only accepts 'paragraph' or 'footnote'."""
    from scripts.parser.schema import TextChunk

    # Valid types
    TextChunk(type="paragraph", text="Test")
    TextChunk(type="footnote", text="Test")

    # Invalid type should fail
    with pytest.raises(ValidationError):
        TextChunk(type="heading", text="Test")


def test_list_item_model_simple():
    """Test ListItem model without sub-items."""
    from scripts.parser.schema import ListItem

    item = ListItem(
        type="list_item",
        text="Meal expenses are 50% deductible",
        citation_id="S3-F2-C1-p2.1",
    )

    assert item.type == "list_item"
    assert item.text == "Meal expenses are 50% deductible"
    assert item.sub_items == []


def test_list_item_model_with_sub_items():
    """Test ListItem model with nested sub-items."""
    from scripts.parser.schema import ListItem

    sub_item = ListItem(type="list_item", text="Sub-item detail")
    parent_item = ListItem(type="list_item", text="Parent item", sub_items=[sub_item])

    assert len(parent_item.sub_items) == 1
    assert parent_item.sub_items[0].text == "Sub-item detail"


def test_list_chunk_model():
    """Test ListChunk model containing list items."""
    from scripts.parser.schema import ListChunk, ListItem

    items = [
        ListItem(type="list_item", text="Item 1"),
        ListItem(type="list_item", text="Item 2"),
    ]
    list_chunk = ListChunk(type="list", items=items)

    assert list_chunk.type == "list"
    assert len(list_chunk.items) == 2


def test_table_chunk_model():
    """Test TableChunk model with tabular data."""
    from scripts.parser.schema import TableChunk

    table = TableChunk(
        type="table",
        data=[
            ["Province", "Rate"],
            ["BC", "5%"],
            ["ON", "13%"],
        ],
        citation_id="S1-F1-C1-p3.5",
    )

    assert table.type == "table"
    assert len(table.data) == 3
    assert table.data[0] == ["Province", "Rate"]


def test_section_model():
    """Test Section model with nested content."""
    from scripts.parser.schema import Section, TextChunk

    content = [
        TextChunk(type="paragraph", text="Introduction text"),
        TextChunk(type="paragraph", text="More details"),
    ]
    section = Section(
        section_title="Deductible Expenses", section_level=2, content=content
    )

    assert section.section_title == "Deductible Expenses"
    assert section.section_level == 2
    assert len(section.content) == 2


def test_parsed_document_model():
    """Test ParsedDocument root model with complete structure."""
    from scripts.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )

    metadata = Metadata(
        province=["BC"], business_type=["sole_proprietorship"], expense_type=["meals"]
    )
    sections = [
        Section(
            section_title="Overview",
            section_level=1,
            content=[TextChunk(type="paragraph", text="Overview text")],
        )
    ]

    doc = ParsedDocument(
        title="CRA Expense Rules",
        document_id="S3-F2-C1",
        metadata=metadata,
        sections=sections,
    )

    assert doc.title == "CRA Expense Rules"
    assert doc.document_id == "S3-F2-C1"
    assert len(doc.sections) == 1
    assert doc.metadata.province == ["BC"]


def test_parsed_document_optional_document_id():
    """Test ParsedDocument allows optional document_id."""
    from scripts.parser.schema import Metadata, ParsedDocument

    doc = ParsedDocument(title="Test Doc", metadata=Metadata(), sections=[])

    assert doc.document_id is None


# --- NEW TESTS FOR TICKET T1.2 ---


def test_metadata_without_income_type() -> None:
    """Metadata should work without income_type (backward compat)."""
    from scripts.parser.schema import Metadata

    metadata = Metadata(
        province=["BC"],
        business_type=["sole_proprietorship"],
        expense_type=["meals"],
    )
    assert metadata.income_type == []  # Default empty list


def test_metadata_with_income_type() -> None:
    """Metadata should accept income_type field."""
    from scripts.parser.schema import Metadata

    metadata = Metadata(
        province=["BC"],
        business_type=["sole_proprietorship"],
        expense_type=["meals"],
        income_type=["business", "fishing"],  # NEW
    )
    assert metadata.income_type == ["business", "fishing"]


def test_text_chunk_without_extraction_metadata() -> None:
    """TextChunk should work without extraction metadata (backward compat)."""
    from scripts.parser.schema import TextChunk

    chunk = TextChunk(
        type="paragraph", text="Test content", citation_id="S3-F2-C1-p1"
    )
    assert chunk.extraction_source is None
    assert chunk.extraction_confidence is None
    assert chunk.source_anchor is None


def test_text_chunk_with_extraction_metadata() -> None:
    """TextChunk should accept extraction metadata."""
    from scripts.parser.schema import TextChunk

    chunk = TextChunk(
        type="paragraph",
        text="Test content",
        citation_id="LINE-8523",
        extraction_source="adjudicated",
        extraction_confidence=0.95,
        source_anchor="tocch3ln8523",
    )
    assert chunk.extraction_source == "adjudicated"
    assert chunk.extraction_confidence == 0.95
    assert chunk.source_anchor == "tocch3ln8523"
