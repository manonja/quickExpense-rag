"""Unit tests for optional field handling in ExtractedRule → DatabaseChunk.

Tests validate that transformation correctly handles optional fields
(section, anchor_id) when they are None, ensuring robustness against
real-world extraction variations.

Coverage:
- Rules with section=None
- Rules with anchor_id=None
- Both fields None simultaneously
- Multiple applicability types
- Edge cases (empty content handling)
"""

import pytest
from qe_tax_rag.data.models import DatabaseChunk
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
    RuleSet,
)
from qe_tax_rag.search.models import SourceFile


@pytest.fixture
def source_file_stub():
    """Minimal SourceFile for testing."""
    return SourceFile(
        path="test.html",
        url="file://test.html",
        hash="abc123",
    )


@pytest.fixture
def source_files_mapping_stub(source_file_stub):
    """Minimal source_files mapping for testing."""
    return {"test": source_file_stub}


# =============================================================================
# Optional Field Handling
# =============================================================================


def test_rule_with_section_none(source_files_mapping_stub):
    """Transform succeeds when section=None."""
    rule = ExtractedRule(
        rule_number=1234,
        title="Test Rule",
        content="Test content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 1234",
        chapter="Chapter 1",
        section=None,  # Optional field set to None
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id="test-anchor",
        confidence_score=1.0,
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files_mapping_stub)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.citation_id == "LINE-1234"
    # section_title may be None or chapter name - either is valid
    assert chunk.metadata.section_title is not None  # Should fall back to chapter


def test_rule_with_anchor_id_none(source_files_mapping_stub):
    """Transform succeeds when anchor_id=None."""
    rule = ExtractedRule(
        rule_number=5678,
        title="Rule Without Anchor",
        content="Content without anchor",
        applies_to=[ApplicabilityType.FARMING],
        source_citation="Line 5678",
        chapter="Chapter 2",
        section="Part 1",
        source_file="test.html",
        expert_source=ExpertSource.LLM,
        anchor_id=None,  # Optional field set to None
        confidence_score=0.85,
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files_mapping_stub)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.metadata.source_anchor is None


def test_rule_with_both_optional_fields_none(source_files_mapping_stub):
    """Transform succeeds when both section and anchor_id are None."""
    rule = ExtractedRule(
        rule_number=9999,
        title="Minimal Rule",
        content="Minimal content",
        applies_to=[ApplicabilityType.FISHING],
        source_citation="Line 9999",
        chapter="Chapter 3",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.ADJUDICATED,
        anchor_id=None,
        confidence_score=0.9,
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files_mapping_stub)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.citation_id == "LINE-9999"
    assert chunk.metadata.source_anchor is None


# =============================================================================
# Multiple Applicability Types
# =============================================================================


def test_rule_with_multiple_applicability_types(source_files_mapping_stub):
    """Rules with multiple applies_to values map to income_type list."""
    rule = ExtractedRule(
        rule_number=4567,
        title="Multi-Applicability Rule",
        content="Applies to multiple business types",
        applies_to=[
            ApplicabilityType.BUSINESS,
            ApplicabilityType.FARMING,
            ApplicabilityType.FISHING,
        ],
        source_citation="Line 4567",
        chapter="Chapter 1",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id="test-multi",
        confidence_score=1.0,
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files_mapping_stub)

    chunk = chunks[0]
    assert len(chunk.metadata.income_type) == 3
    assert set(chunk.metadata.income_type) == {"business", "farming", "fishing"}


def test_rule_with_single_applicability_type(source_files_mapping_stub):
    """Rules with single applies_to value produce single-item income_type list."""
    rule = ExtractedRule(
        rule_number=2345,
        title="Business-Only Rule",
        content="Only applies to business",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 2345",
        chapter="Chapter 1",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id="test-business",
        confidence_score=1.0,
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files_mapping_stub)

    chunk = chunks[0]
    assert len(chunk.metadata.income_type) == 1
    assert chunk.metadata.income_type == ["business"]


# =============================================================================
# Edge Cases
# =============================================================================


def test_empty_ruleset(source_files_mapping_stub):
    """Empty RuleSet produces empty chunks list."""
    ruleset = RuleSet(
        rules=[],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files_mapping_stub)

    assert len(chunks) == 0
    assert isinstance(chunks, list)


def test_rule_with_minimal_content(source_files_mapping_stub):
    """Transform handles rules with minimal content (single character)."""
    rule = ExtractedRule(
        rule_number=1111,
        title="T",  # Single-char title
        content="C",  # Single-char content
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 1111",
        chapter="Chapter 1",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id=None,
        confidence_score=1.0,
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files_mapping_stub)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.content == "T\n\nC"
    assert chunk.citation_id == "LINE-1111"


def test_rule_with_special_characters_in_content(source_files_mapping_stub):
    """Transform preserves special characters in title and content."""
    rule = ExtractedRule(
        rule_number=3333,
        title="Rule with $pecial Ch@racters & Symbols!",
        content="Content with <HTML> tags, [brackets], and \"quotes\"",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 3333",
        chapter="Chapter 1",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id=None,
        confidence_score=1.0,
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files_mapping_stub)

    chunk = chunks[0]
    assert "Rule with $pecial Ch@racters & Symbols!" in chunk.content
    assert "<HTML>" in chunk.content
    assert "[brackets]" in chunk.content
    assert '"quotes"' in chunk.content
