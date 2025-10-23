"""Property-based tests for ExtractedRule → DatabaseChunk transformation.

Uses Hypothesis to generate diverse RuleSet inputs and verify transformation
invariants hold across all valid inputs. Tests robustness beyond fixed examples.

Coverage:
- Citation ID format invariants (LINE-{number})
- Metadata preservation (never lost or corrupted)
- Content format invariants (title always prepended)
- Determinism (same input → same output)
- Count preservation (N rules → N chunks)

Strategy: tests/strategies.py provides extracted_rule_strategy() and
ruleset_strategy() that generate valid Pydantic models matching schema.
"""

from hypothesis import given
from qe_tax_rag.extraction.ca.schema import RuleSet
from qe_tax_rag.search.models import SourceFile
from tests.strategies import extracted_rule_strategy, ruleset_strategy


# =============================================================================
# Property-Based Invariants
# =============================================================================


@given(ruleset=ruleset_strategy(min_rules=1, max_rules=10))
def test_citation_id_format_invariant(ruleset: RuleSet):
    """Citation IDs always follow LINE-{number} format for all generated inputs."""
    # Create stub source files mapping
    source_files = {
        "test": SourceFile(path="test.html", url="file://test.html", hash="abc123")
    }

    # Override source_file in all rules to match stub mapping
    rules_with_stub_source = [
        rule.model_copy(update={"source_file": "test.html"}) for rule in ruleset.rules
    ]
    updated_ruleset = ruleset.model_copy(update={"rules": rules_with_stub_source})

    chunks = updated_ruleset.to_database_chunks(source_files)

    for chunk in chunks:
        # Citation ID must match LINE-{number} pattern
        assert chunk.citation_id.startswith("LINE-")
        rule_number = chunk.citation_id.split("-", 1)[1]
        assert rule_number.isdigit()


@given(ruleset=ruleset_strategy(min_rules=1, max_rules=10))
def test_citation_id_never_none_or_empty(ruleset: RuleSet):
    """Citation IDs are never None or empty string (database constraint)."""
    source_files = {
        "test": SourceFile(path="test.html", url="file://test.html", hash="abc123")
    }

    rules_with_stub_source = [
        rule.model_copy(update={"source_file": "test.html"}) for rule in ruleset.rules
    ]
    updated_ruleset = ruleset.model_copy(update={"rules": rules_with_stub_source})

    chunks = updated_ruleset.to_database_chunks(source_files)

    for chunk in chunks:
        assert chunk.citation_id is not None
        assert chunk.citation_id != ""
        assert isinstance(chunk.citation_id, str)


@given(ruleset=ruleset_strategy(min_rules=1, max_rules=10))
def test_metadata_preservation_invariant(ruleset: RuleSet):
    """Metadata fields never lost or corrupted during transformation."""
    source_files = {
        "test": SourceFile(path="test.html", url="file://test.html", hash="abc123")
    }

    rules_with_stub_source = [
        rule.model_copy(update={"source_file": "test.html"}) for rule in ruleset.rules
    ]
    updated_ruleset = ruleset.model_copy(update={"rules": rules_with_stub_source})

    chunks = updated_ruleset.to_database_chunks(source_files)

    for chunk, original_rule in zip(chunks, updated_ruleset.rules, strict=True):
        # Required metadata fields must be preserved
        assert chunk.metadata.extraction_source == original_rule.expert_source.value
        assert (
            chunk.metadata.extraction_confidence == original_rule.confidence_score
        )
        assert chunk.metadata.source_anchor == original_rule.anchor_id

        # income_type must match applies_to
        assert set(chunk.metadata.income_type) == {
            at.value for at in original_rule.applies_to
        }


@given(ruleset=ruleset_strategy(min_rules=1, max_rules=10))
def test_content_format_invariant(ruleset: RuleSet):
    """Content always includes title prepended with double newline separator."""
    source_files = {
        "test": SourceFile(path="test.html", url="file://test.html", hash="abc123")
    }

    rules_with_stub_source = [
        rule.model_copy(update={"source_file": "test.html"}) for rule in ruleset.rules
    ]
    updated_ruleset = ruleset.model_copy(update={"rules": rules_with_stub_source})

    chunks = updated_ruleset.to_database_chunks(source_files)

    for chunk, original_rule in zip(chunks, updated_ruleset.rules, strict=True):
        # Content must start with title
        assert chunk.content.startswith(original_rule.title)

        # Title and content must be separated by double newline
        expected_start = f"{original_rule.title}\n\n"
        assert chunk.content.startswith(expected_start)

        # Original content must be present
        assert original_rule.content in chunk.content


@given(ruleset=ruleset_strategy(min_rules=1, max_rules=10))
def test_count_preservation_invariant(ruleset: RuleSet):
    """Number of chunks equals number of rules (no loss or duplication)."""
    source_files = {
        "test": SourceFile(path="test.html", url="file://test.html", hash="abc123")
    }

    rules_with_stub_source = [
        rule.model_copy(update={"source_file": "test.html"}) for rule in ruleset.rules
    ]
    updated_ruleset = ruleset.model_copy(update={"rules": rules_with_stub_source})

    chunks = updated_ruleset.to_database_chunks(source_files)

    assert len(chunks) == len(updated_ruleset.rules)


@given(ruleset=ruleset_strategy(min_rules=1, max_rules=5))
def test_determinism_invariant(ruleset: RuleSet):
    """Transformation is deterministic: same input produces identical output."""
    source_files = {
        "test": SourceFile(path="test.html", url="file://test.html", hash="abc123")
    }

    rules_with_stub_source = [
        rule.model_copy(update={"source_file": "test.html"}) for rule in ruleset.rules
    ]
    updated_ruleset = ruleset.model_copy(update={"rules": rules_with_stub_source})

    # Transform twice
    chunks_1 = updated_ruleset.to_database_chunks(source_files)
    chunks_2 = updated_ruleset.to_database_chunks(source_files)

    # Results must be identical
    assert len(chunks_1) == len(chunks_2)

    for chunk1, chunk2 in zip(chunks_1, chunks_2, strict=True):
        assert chunk1.citation_id == chunk2.citation_id
        assert chunk1.content == chunk2.content
        assert chunk1.metadata == chunk2.metadata
        assert chunk1.source_url == chunk2.source_url
        assert chunk1.source_hash == chunk2.source_hash


@given(ruleset=ruleset_strategy(min_rules=1, max_rules=10))
def test_source_url_preserved(ruleset: RuleSet):
    """Source URL from SourceFile preserved in all chunks."""
    test_url = "https://example.com/test.html"
    source_files = {
        "test": SourceFile(path="test.html", url=test_url, hash="abc123")
    }

    rules_with_stub_source = [
        rule.model_copy(update={"source_file": "test.html"}) for rule in ruleset.rules
    ]
    updated_ruleset = ruleset.model_copy(update={"rules": rules_with_stub_source})

    chunks = updated_ruleset.to_database_chunks(source_files)

    for chunk in chunks:
        assert chunk.source_url == test_url


@given(ruleset=ruleset_strategy(min_rules=1, max_rules=10))
def test_source_hash_preserved(ruleset: RuleSet):
    """Source hash from SourceFile preserved in all chunks."""
    test_hash = "test_hash_abc123xyz"
    source_files = {
        "test": SourceFile(path="test.html", url="file://test.html", hash=test_hash)
    }

    rules_with_stub_source = [
        rule.model_copy(update={"source_file": "test.html"}) for rule in ruleset.rules
    ]
    updated_ruleset = ruleset.model_copy(update={"rules": rules_with_stub_source})

    chunks = updated_ruleset.to_database_chunks(source_files)

    for chunk in chunks:
        assert chunk.source_hash == test_hash


# =============================================================================
# Optional Field Invariants
# =============================================================================


@given(rule=extracted_rule_strategy())
def test_optional_fields_never_cause_failure(rule):
    """Transformation never fails regardless of optional field values."""
    source_files = {
        "test": SourceFile(path="test.html", url="file://test.html", hash="abc123")
    }

    # Override source_file to match stub mapping
    rule_with_stub_source = rule.model_copy(update={"source_file": "test.html"})

    ruleset = RuleSet(
        rules=[rule_with_stub_source],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )

    # Should never raise, even if section or anchor_id is None
    chunks = ruleset.to_database_chunks(source_files)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.citation_id is not None
    assert chunk.content is not None
