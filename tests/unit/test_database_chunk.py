"""
Unit tests for ExtractedRule → DatabaseChunk transformation.

Tests validate that RuleSet.to_database_chunks() correctly transforms
YAML-deserialized ExtractedRule objects into DatabaseChunk objects with
proper metadata preservation, citation ID format, and content formatting.

Coverage:
- AC1: YAML deserialization produces valid RuleSet
- AC2: DatabaseChunk transformation preserves citation ID format
- AC4: Metadata fields correctly mapped
- AC7: Content field includes title

Uses real YAML fixtures from tests/fixtures/conversion/ (generated from
actual extraction pipeline after Phase 0 architectural fixes).
"""

from pathlib import Path

import pytest
import yaml
from qe_tax_rag.data.models import DatabaseChunk
from qe_tax_rag.extraction.ca.schema import RuleSet


@pytest.fixture
def simple_rule_yaml():
    """Load simple_rule.yml fixture (1 rule)."""
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "conversion" / "simple_rule.yml"
    )
    with open(fixture_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def complex_rule_yaml():
    """Load complex_rule.yml fixture (3 rules)."""
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "conversion" / "complex_rule.yml"
    )
    with open(fixture_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def simple_ruleset(simple_rule_yaml):
    """RuleSet deserialized from simple_rule.yml."""
    return RuleSet.model_validate(simple_rule_yaml)


@pytest.fixture
def complex_ruleset(complex_rule_yaml):
    """RuleSet deserialized from complex_rule.yml."""
    return RuleSet.model_validate(complex_rule_yaml)


# =============================================================================
# AC1: YAML Deserialization
# =============================================================================


def test_yaml_deserializes_to_valid_ruleset(simple_rule_yaml, complex_rule_yaml):
    """
    YAML fixtures deserialize into valid RuleSet objects.

    Validates Pydantic parsing of real YAML output from extraction
    pipeline. Ensures all required fields present and types correct.
    """
    # Simple rule (1 rule)
    simple_rs = RuleSet.model_validate(simple_rule_yaml)
    assert simple_rs.schema_version == "1.0"
    assert len(simple_rs.rules) == 1
    assert simple_rs.rules[0].rule_number == 8523
    assert simple_rs.rules[0].title == "Meals and entertainment"

    # Complex rules (3 rules)
    complex_rs = RuleSet.model_validate(complex_rule_yaml)
    assert complex_rs.schema_version == "1.0"
    assert len(complex_rs.rules) == 3
    assert complex_rs.rules[0].rule_number == 8000
    assert complex_rs.rules[1].rule_number == 8523
    assert complex_rs.rules[2].rule_number == 9270


# =============================================================================
# AC2: Citation ID Format
# =============================================================================


def test_citation_id_format_simple_rule(simple_ruleset, source_files_mapping):
    """DatabaseChunk uses correct LINE-{number} citation format."""
    chunks = simple_ruleset.to_database_chunks(source_files_mapping)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.citation_id == "LINE-8523"


def test_citation_id_format_complex_rules(complex_ruleset, source_files_mapping):
    """Multiple rules generate distinct LINE-{number} citation IDs."""
    chunks = complex_ruleset.to_database_chunks(source_files_mapping)

    assert len(chunks) == 3
    citation_ids = {chunk.citation_id for chunk in chunks}
    assert citation_ids == {"LINE-8000", "LINE-8523", "LINE-9270"}


def test_citation_id_never_none(simple_ruleset, source_files_mapping):
    """
    Citation ID is never None (database constraint enforcement).

    CRITICAL: Missing citation_id violates database UNIQUE NOT NULL
    constraint. Transformation MUST raise ValueError, never produce None.
    """
    chunks = simple_ruleset.to_database_chunks(source_files_mapping)

    for chunk in chunks:
        assert chunk.citation_id is not None
        assert chunk.citation_id != ""
        assert isinstance(chunk.citation_id, str)


# =============================================================================
# AC4: Metadata Preservation
# =============================================================================


def test_metadata_expert_source_mapped(simple_ruleset, source_files_mapping):
    """expert_source from YAML maps to extraction_source in metadata."""
    chunks = simple_ruleset.to_database_chunks(source_files_mapping)

    chunk = chunks[0]
    assert chunk.metadata.extraction_source == "adjudicated"


def test_metadata_confidence_score_mapped(simple_ruleset, source_files_mapping):
    """confidence_score from YAML maps to extraction_confidence in metadata."""
    chunks = simple_ruleset.to_database_chunks(source_files_mapping)

    chunk = chunks[0]
    assert chunk.metadata.extraction_confidence == 0.95


def test_metadata_anchor_id_mapped(simple_ruleset, source_files_mapping):
    """anchor_id from YAML maps to source_anchor in metadata."""
    chunks = simple_ruleset.to_database_chunks(source_files_mapping)

    chunk = chunks[0]
    assert chunk.metadata.source_anchor == "tocch3ln8523"


def test_metadata_all_fields_present(complex_ruleset, source_files_mapping):
    """All metadata fields populated for every DatabaseChunk."""
    chunks = complex_ruleset.to_database_chunks(source_files_mapping)

    for chunk in chunks:
        # Required fields (never None)
        assert chunk.metadata.extraction_source is not None
        assert chunk.metadata.extraction_confidence is not None

        # Optional fields (may be None but must exist)
        assert hasattr(chunk.metadata, "source_anchor")
        assert hasattr(chunk.metadata, "section_title")
        assert hasattr(chunk.metadata, "document_id")


# =============================================================================
# AC7: Content Formatting (Title Inclusion)
# =============================================================================


def test_content_includes_title(simple_ruleset, source_files_mapping):
    """
    Content field includes rule title for RAG quality.

    After Phase 0 architectural fix, DatabaseChunk.content should be
    formatted as: "{title}\n\n{content}" for optimal retrieval.
    """
    chunks = simple_ruleset.to_database_chunks(source_files_mapping)

    chunk = chunks[0]
    assert chunk.content.startswith("Meals and entertainment\n\n")
    assert "50% of the lesser" in chunk.content


def test_content_format_preserves_original_content(
    complex_ruleset, source_files_mapping
):
    """Original rule content preserved after title prepending."""
    chunks = complex_ruleset.to_database_chunks(source_files_mapping)

    # Find the "Motor vehicle expenses" rule (LINE-9270)
    motor_vehicle_chunk = next(
        chunk for chunk in chunks if chunk.citation_id == "LINE-9270"
    )

    # Title should be prepended
    assert motor_vehicle_chunk.content.startswith("Motor vehicle expenses\n\n")
    # Original content should follow
    assert "fuel and maintenance" in motor_vehicle_chunk.content


def test_content_multiline_handling(simple_ruleset, source_files_mapping):
    """Multiline content correctly formatted with title prepending."""
    chunks = simple_ruleset.to_database_chunks(source_files_mapping)

    chunk = chunks[0]
    lines = chunk.content.split("\n")

    # First line: title
    assert lines[0] == "Meals and entertainment"
    # Second line: blank (separator)
    assert lines[1] == ""
    # Remaining lines: original content
    assert len(lines) > 2


# =============================================================================
# Integration: Full Transformation Pipeline
# =============================================================================


def test_transformation_preserves_all_rules(complex_ruleset, source_files_mapping):
    """All rules from RuleSet transform to DatabaseChunks (no loss)."""
    chunks = complex_ruleset.to_database_chunks(source_files_mapping)

    assert len(chunks) == len(complex_ruleset.rules)

    # Verify all rule numbers present
    rule_numbers = {chunk.citation_id.split("-")[1] for chunk in chunks}
    expected_rule_numbers = {"8000", "8523", "9270"}
    assert rule_numbers == expected_rule_numbers


def test_transformation_deterministic(simple_ruleset, source_files_mapping):
    """Transformation produces identical output for same input (deterministic)."""
    chunks_1 = simple_ruleset.to_database_chunks(source_files_mapping)
    chunks_2 = simple_ruleset.to_database_chunks(source_files_mapping)

    assert len(chunks_1) == len(chunks_2)
    assert chunks_1[0].citation_id == chunks_2[0].citation_id
    assert chunks_1[0].content == chunks_2[0].content
    assert chunks_1[0].metadata == chunks_2[0].metadata
