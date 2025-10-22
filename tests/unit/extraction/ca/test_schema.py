"""Unit tests for extraction pipeline schema models."""

from pathlib import Path

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
def sample_rule() -> ExtractedRule:
    """Minimal valid rule for testing."""
    return ExtractedRule(
        rule_number=8523,
        title="Business Meal Expenses",
        content="You can deduct 50% of meal and entertainment expenses.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        section="Meals and entertainment",
        source_file="t4002-24e.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )


@pytest.fixture
def source_files() -> dict[str, SourceFile]:
    """Mock source file mapping."""
    return {
        "t4002-24e": SourceFile(
            path="t4002-24e.html",
            url="https://www.canada.ca/t4002-24e.html",
            hash="abc123def456",
        )
    }


@pytest.mark.unit
def test_ruleset_to_database_chunks_basic(
    sample_rule: ExtractedRule,
    source_files: dict[str, SourceFile],
) -> None:
    """Test basic conversion from RuleSet to DatabaseChunk."""
    ruleset = RuleSet(
        rules=[sample_rule],
        schema_version="1.0",
        extraction_timestamp="2024-12-15T10:30:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files=source_files)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, DatabaseChunk)
    assert chunk.content == "You can deduct 50% of meal and entertainment expenses."
    assert chunk.citation_id == "LINE-8523"
    assert chunk.source_url == "https://www.canada.ca/t4002-24e.html"
    assert chunk.source_hash == "abc123def456"
    # Expense type inference: "meal" keyword triggers "meals" expense type
    assert "meals" in chunk.expense_types


@pytest.mark.unit
def test_ruleset_to_database_chunks_preserves_metadata(
    sample_rule: ExtractedRule,
    source_files: dict[str, SourceFile],
) -> None:
    """Test that extraction metadata is preserved in chunks."""
    ruleset = RuleSet(
        rules=[sample_rule],
        schema_version="1.0",
        extraction_timestamp="2024-12-15T10:30:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files=source_files)

    chunk = chunks[0]
    assert chunk.metadata.extraction_source == "classic"
    assert chunk.metadata.extraction_confidence == 1.0
    # section_title is mapped from rule.chapter (not rule.section)
    assert chunk.metadata.section_title == "Chapter 3"


@pytest.mark.unit
def test_ruleset_to_database_chunks_raises_on_missing_source(
    sample_rule: ExtractedRule,
) -> None:
    """Test that missing source file raises clear error."""
    ruleset = RuleSet(
        rules=[sample_rule],
        schema_version="1.0",
        extraction_timestamp="2024-12-15T10:30:00Z",
    )

    with pytest.raises(ValueError, match="No SourceFile found"):
        ruleset.to_database_chunks(source_files={})


@pytest.mark.unit
def test_ruleset_to_database_chunks_expense_classification(
    source_files: dict[str, SourceFile],
) -> None:
    """Test expense type classification from content."""
    rules = [
        ExtractedRule(
            rule_number=101,
            title="Vehicle",
            content="Deduct vehicle expenses including fuel and maintenance.",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 101",
            chapter="Chapter 1",
            section=None,
            source_file="t4002-24e.html",
            expert_source=ExpertSource.LLM,
            confidence_score=0.95,
        ),
        ExtractedRule(
            rule_number=102,
            title="Office",
            content="Home office expenses are deductible.",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 102",
            chapter="Chapter 1",
            section=None,
            source_file="t4002-24e.html",
            expert_source=ExpertSource.ADJUDICATED,
            confidence_score=0.98,
        ),
    ]
    ruleset = RuleSet(
        rules=rules,
        schema_version="1.0",
        extraction_timestamp="2024-12-15T10:30:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files=source_files)

    assert "vehicle" in chunks[0].expense_types
    assert "maintenance" in chunks[0].expense_types
    assert "home_office" in chunks[1].expense_types


@pytest.mark.unit
def test_ruleset_to_database_chunks_multiple_rules(
    source_files: dict[str, SourceFile],
) -> None:
    """Test conversion with multiple rules."""
    rules = [
        ExtractedRule(
            rule_number=101,
            title="Rule 1",
            content="Content 1",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 101",
            chapter="Chapter 1",
            section="Section A",
            source_file="t4002-24e.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
        ExtractedRule(
            rule_number=102,
            title="Rule 2",
            content="Content 2",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 102",
            chapter="Chapter 1",
            section="Section B",
            source_file="t4002-24e.html",
            expert_source=ExpertSource.LLM,
            confidence_score=0.9,
        ),
        ExtractedRule(
            rule_number=103,
            title="Rule 3",
            content="Content 3",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 103",
            chapter="Chapter 2",
            section=None,
            source_file="t4002-24e.html",
            expert_source=ExpertSource.ADJUDICATED,
            confidence_score=0.95,
        ),
    ]
    ruleset = RuleSet(
        rules=rules,
        schema_version="1.0",
        extraction_timestamp="2024-12-15T10:30:00Z",
    )

    chunks = ruleset.to_database_chunks(source_files=source_files)

    assert len(chunks) == 3
    assert all(isinstance(chunk, DatabaseChunk) for chunk in chunks)
    assert chunks[0].citation_id == "LINE-101"
    assert chunks[1].citation_id == "LINE-102"
    assert chunks[2].citation_id == "LINE-103"
    # section_title is mapped from chapter, not section
    assert chunks[0].metadata.section_title == "Chapter 1"
    assert chunks[1].metadata.section_title == "Chapter 1"
    assert chunks[2].metadata.section_title == "Chapter 2"
