"""Unit tests for ParsedDocument.to_flat_chunks() flattening logic."""

import pytest


def test_flatten_single_section_simple():
    """Test flattening a single section with simple text chunks."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )

    doc = ParsedDocument(
        title="Test Document",
        document_id="S1-F1-C1",
        metadata=Metadata(province=["BC"], expense_type=["meals"]),
        sections=[
            Section(
                section_title="Overview",
                section_level=1,
                content=[
                    TextChunk(
                        type="paragraph",
                        text="First paragraph",
                        citation_id="S1-F1-C1-p1.1",
                    ),
                    TextChunk(
                        type="paragraph",
                        text="Second paragraph",
                        citation_id="S1-F1-C1-p1.2",
                    ),
                ],
            )
        ],
    )

    chunks = doc.to_flat_chunks()

    assert len(chunks) == 2
    assert chunks[0]["content"] == "First paragraph"
    assert chunks[0]["citation_id"] == "S1-F1-C1-p1.1"
    assert chunks[1]["content"] == "Second paragraph"
    assert chunks[1]["citation_id"] == "S1-F1-C1-p1.2"


def test_flatten_preserves_section_context():
    """Test that section title is preserved in chunk metadata."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )

    doc = ParsedDocument(
        title="Test Document",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Deductible Expenses",
                section_level=1,
                content=[
                    TextChunk(
                        type="paragraph",
                        text="Meal expenses",
                        citation_id="S1-F1-C1-p1.1",
                    )
                ],
            )
        ],
    )

    chunks = doc.to_flat_chunks()

    assert chunks[0]["metadata"]["section_title"] == "Deductible Expenses"
    assert chunks[0]["metadata"]["document_id"] == "S1-F1-C1"


def test_flatten_preserves_document_metadata():
    """Test that document-level metadata is copied to each chunk."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )

    doc = ParsedDocument(
        title="Test Document",
        document_id="S3-F2-C1",
        metadata=Metadata(
            province=["BC", "ON"],
            business_type=["sole_proprietorship"],
            expense_type=["vehicle", "travel"],
        ),
        sections=[
            Section(
                section_title="Rules",
                section_level=1,
                content=[
                    TextChunk(
                        type="paragraph", text="Rule text", citation_id="S3-F2-C1-p1.1"
                    )
                ],
            )
        ],
    )

    chunks = doc.to_flat_chunks()

    assert chunks[0]["metadata"]["province"] == ["BC", "ON"]
    assert chunks[0]["metadata"]["business_type"] == ["sole_proprietorship"]
    assert chunks[0]["metadata"]["expense_type"] == ["vehicle", "travel"]


def test_flatten_handles_list_chunks():
    """Test flattening ListChunk to individual list items."""
    from qe_tax_rag.parser.schema import (
        ListChunk,
        ListItem,
        Metadata,
        ParsedDocument,
        Section,
    )

    doc = ParsedDocument(
        title="Test Document",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Expense Types",
                section_level=1,
                content=[
                    ListChunk(
                        type="list",
                        items=[
                            ListItem(
                                type="list_item",
                                text="Meal expenses",
                                citation_id="S1-F1-C1-p2.1",
                            ),
                            ListItem(
                                type="list_item",
                                text="Travel expenses",
                                citation_id="S1-F1-C1-p2.2",
                            ),
                        ],
                    )
                ],
            )
        ],
    )

    chunks = doc.to_flat_chunks()

    assert len(chunks) == 2
    assert chunks[0]["content"] == "Meal expenses"
    assert chunks[0]["citation_id"] == "S1-F1-C1-p2.1"
    assert chunks[1]["content"] == "Travel expenses"
    assert chunks[1]["citation_id"] == "S1-F1-C1-p2.2"


def test_flatten_handles_nested_list_items():
    """Test flattening nested list items (sub-items)."""
    from qe_tax_rag.parser.schema import (
        ListChunk,
        ListItem,
        Metadata,
        ParsedDocument,
        Section,
    )

    doc = ParsedDocument(
        title="Test Document",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Rules",
                section_level=1,
                content=[
                    ListChunk(
                        type="list",
                        items=[
                            ListItem(
                                type="list_item",
                                text="Parent item",
                                citation_id="S1-F1-C1-p3.1",
                                sub_items=[
                                    ListItem(
                                        type="list_item",
                                        text="Sub-item A",
                                        citation_id="S1-F1-C1-p3.1.1",
                                    ),
                                    ListItem(
                                        type="list_item",
                                        text="Sub-item B",
                                        citation_id="S1-F1-C1-p3.1.2",
                                    ),
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    )

    chunks = doc.to_flat_chunks()

    # Should flatten to 3 chunks: parent + 2 sub-items
    assert len(chunks) == 3
    assert chunks[0]["content"] == "Parent item"
    assert chunks[1]["content"] == "Sub-item A"
    assert chunks[2]["content"] == "Sub-item B"


def test_flatten_handles_table_chunks():
    """Test flattening TableChunk to a single chunk with table data."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TableChunk,
    )

    doc = ParsedDocument(
        title="Test Document",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Rates",
                section_level=1,
                content=[
                    TableChunk(
                        type="table",
                        data=[["Province", "Rate"], ["BC", "5%"], ["ON", "13%"]],
                        citation_id="S1-F1-C1-p4.1",
                    )
                ],
            )
        ],
    )

    chunks = doc.to_flat_chunks()

    assert len(chunks) == 1
    # Table should be converted to text representation
    assert "Province" in chunks[0]["content"]
    assert "BC" in chunks[0]["content"]
    assert chunks[0]["citation_id"] == "S1-F1-C1-p4.1"


def test_flatten_multiple_sections():
    """Test flattening multiple sections preserves all content."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )

    doc = ParsedDocument(
        title="Test Document",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Section 1",
                section_level=1,
                content=[
                    TextChunk(
                        type="paragraph", text="Content 1", citation_id="S1-F1-C1-p1.1"
                    )
                ],
            ),
            Section(
                section_title="Section 2",
                section_level=1,
                content=[
                    TextChunk(
                        type="paragraph", text="Content 2", citation_id="S1-F1-C1-p2.1"
                    )
                ],
            ),
        ],
    )

    chunks = doc.to_flat_chunks()

    assert len(chunks) == 2
    assert chunks[0]["metadata"]["section_title"] == "Section 1"
    assert chunks[1]["metadata"]["section_title"] == "Section 2"


def test_flatten_empty_document():
    """Test flattening document with no sections."""
    from qe_tax_rag.parser.schema import Metadata, ParsedDocument

    doc = ParsedDocument(
        title="Empty Doc", document_id="S1-F1-C1", metadata=Metadata(), sections=[]
    )

    chunks = doc.to_flat_chunks()

    assert chunks == []


def test_flatten_chunk_without_citation():
    """Test flattening chunks without citation_id (footnotes, etc.)."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )

    doc = ParsedDocument(
        title="Test Document",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Rules",
                section_level=1,
                content=[
                    TextChunk(
                        type="footnote", text="See section 5 for details."
                    )  # No citation_id
                ],
            )
        ],
    )

    chunks = doc.to_flat_chunks()

    assert len(chunks) == 1
    assert chunks[0]["citation_id"] is None
    assert chunks[0]["content"] == "See section 5 for details."


def test_flat_chunks_include_source_url():
    """Test that flattened chunks include source_url field."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )

    # Source URL will be injected during parsing, but we simulate it here
    doc = ParsedDocument(
        title="Test Document",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Rules",
                section_level=1,
                content=[
                    TextChunk(
                        type="paragraph", text="Content", citation_id="S1-F1-C1-p1.1"
                    )
                ],
            )
        ],
    )

    chunks = doc.to_flat_chunks(source_url="https://canada.ca/en/revenue-agency/...")

    assert chunks[0]["source_url"] == "https://canada.ca/en/revenue-agency/..."
