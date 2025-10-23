"""Unit tests for ParserValidator class."""

import pytest


def test_parser_validator_initialization():
    """Test ParserValidator can be initialized."""
    from scripts.parser.validator import ParserValidator

    validator = ParserValidator()
    assert validator is not None


def test_validate_parsed_document_all_valid():
    """Test validation passes for valid parsed document."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )
    from scripts.parser.validator import ParserValidator

    doc = ParsedDocument(
        title="Test Doc",
        document_id="S1-F1-C1",
        metadata=Metadata(expense_type=["meals", "travel"]),
        sections=[
            Section(
                section_title="Rules",
                section_level=1,
                content=[
                    TextChunk(
                        type="paragraph",
                        text="Content",
                        citation_id="S1-F1-C1-p1.1",
                    )
                ],
            )
        ],
    )

    validator = ParserValidator()
    report = validator.validate_parsed_document(doc)

    assert report["valid"] is True
    assert report["errors"] == []
    assert report["warnings"] == []


def test_validate_parsed_document_invalid_citation():
    """Test validation detects invalid citation format."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )
    from scripts.parser.validator import ParserValidator

    doc = ParsedDocument(
        title="Test Doc",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Rules",
                section_level=1,
                content=[
                    TextChunk(
                        type="paragraph",
                        text="Content",
                        citation_id="invalid-citation",  # Invalid format
                    )
                ],
            )
        ],
    )

    validator = ParserValidator()
    report = validator.validate_parsed_document(doc)

    assert report["valid"] is False
    assert len(report["errors"]) == 1
    assert "citation" in report["errors"][0].lower()


def test_validate_parsed_document_invalid_expense_type():
    """Test validation detects invalid expense types."""
    from qe_tax_rag.parser.schema import Metadata, ParsedDocument
    from scripts.parser.validator import ParserValidator

    doc = ParsedDocument(
        title="Test Doc",
        document_id="S1-F1-C1",
        metadata=Metadata(expense_type=["meals", "invalid_type"]),
        sections=[],
    )

    validator = ParserValidator()
    report = validator.validate_parsed_document(doc)

    # Invalid types should be warnings, not errors
    assert len(report["warnings"]) >= 1
    assert any("invalid_type" in w for w in report["warnings"])


def test_validate_parsed_document_statistics():
    """Test validation report includes statistics."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )
    from scripts.parser.validator import ParserValidator

    doc = ParsedDocument(
        title="Test Doc",
        document_id="S1-F1-C1",
        metadata=Metadata(expense_type=["meals"]),
        sections=[
            Section(
                section_title="Section 1",
                section_level=1,
                content=[
                    TextChunk(type="paragraph", text="A", citation_id="S1-F1-C1-p1.1"),
                    TextChunk(type="paragraph", text="B", citation_id="S1-F1-C1-p1.2"),
                ],
            )
        ],
    )

    validator = ParserValidator()
    report = validator.validate_parsed_document(doc)

    assert "statistics" in report
    assert report["statistics"]["total_sections"] == 1
    assert report["statistics"]["total_content_items"] == 2


def test_validate_parsed_document_multiple_errors():
    """Test validation collects multiple errors."""
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )
    from scripts.parser.validator import ParserValidator

    doc = ParsedDocument(
        title="Test Doc",
        document_id="S1-F1-C1",
        metadata=Metadata(),
        sections=[
            Section(
                section_title="Rules",
                section_level=1,
                content=[
                    TextChunk(type="paragraph", text="A", citation_id="bad1"),
                    TextChunk(type="paragraph", text="B", citation_id="bad2"),
                ],
            )
        ],
    )

    validator = ParserValidator()
    report = validator.validate_parsed_document(doc)

    assert report["valid"] is False
    assert len(report["errors"]) >= 2  # Multiple citation errors
