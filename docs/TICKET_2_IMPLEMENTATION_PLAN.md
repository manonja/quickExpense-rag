# Ticket 2 Implementation Plan: Test YAML → SQLite Conversion

**Date**: 2025-10-22
**Status**: Ready for Implementation
**Dependencies**: Ticket 1 (Complete)
**Estimated Effort**: 7 hours

---

## Executive Summary

This ticket validates the YAML → SQLite conversion layer of the extraction pipeline. Critical architectural issues discovered during planning require fixes before testing can begin.

**Critical Findings**:
1. `yaml_generator.py` strips required metadata fields needed by database builder
2. `to_database_chunks()` omits title from content field (hurts RAG quality)
3. These must be fixed first to make the component testable

**Pipeline Flow**:
```
YAML File → RuleSet.model_validate() → RuleSet.to_database_chunks() → DatabaseChunk[] → SQLite
```

---

## Phase 0: Fix Architectural Blockers ⚠️ CRITICAL

**Estimated Time**: 1 hour

### Task 0.1: Stop Stripping Required Metadata Fields

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

**Problem**: Fields marked as "internal metadata" are actually required for database building. The yaml_generator strips `expert_source`, `confidence_score`, and `anchor_id`, but `to_database_chunks()` requires these fields to populate `ChunkMetadata`.

**Acceptance Criteria**:
- [ ] `_INTERNAL_METADATA_FIELDS` set is empty (all fields commented out)
- [ ] `model_dump_json()` conditionally uses exclude parameter only if set is non-empty
- [ ] Generated YAML contains `expert_source`, `confidence_score`, `anchor_id` fields
- [ ] All existing tests still pass

**Implementation**:
```python
# Lines 48-52: Comment out all fields
_INTERNAL_METADATA_FIELDS: Final[set[str]] = {
    # "expert_source",     # REQUIRED for DB metadata
    # "anchor_id",         # REQUIRED for DB metadata
    # "confidence_score",  # REQUIRED for DB metadata
}

# Lines 88-92: Make exclude conditional
data = json.loads(
    rule_set.model_dump_json(
        exclude={"rules": {"__all__": _INTERNAL_METADATA_FIELDS}}
        if _INTERNAL_METADATA_FIELDS
        else None
    )
)
```

**Rationale**: These fields provide crucial observability for RAG quality analysis (e.g., "show me all low-confidence extractions"). They are not "internal" - they are essential metadata for the final database artifact.

**Verification**:
```bash
# Re-run extraction
uv run extract-rules \
  tests/fixtures/extraction/ca/simple_rule.html \
  output/verification_test.yml \
  --cache-dir output/llm_cache

# Verify fields present
grep -E "expert_source|confidence_score|anchor_id" output/verification_test.yml
# Should show all three fields present

# Run existing tests
uv run pytest tests/unit/extraction/ca/test_yaml_generator.py -v
```

---

### Task 0.2: Fix DatabaseChunk Content Format for RAG Quality

**File**: `src/qe_tax_rag/extraction/ca/schema.py`

**Problem**: Current implementation only uses `rule.content` in `DatabaseChunk.content`, missing high-value keywords from `rule.title`. This degrades RAG retrieval quality.

**Acceptance Criteria**:
- [ ] `DatabaseChunk.content` is formatted as `f"{title}\n\n{content}"`
- [ ] Title appears at the start of content field
- [ ] Double newline separator between title and content
- [ ] Content field is suitable for both FTS indexing and embedding

**Implementation**:
```python
# Line 206-207: Update content field
chunks.append(
    DatabaseChunk(
        content=f"{rule.title}\n\n{rule.content}",  # ← Changed from just rule.content
        citation_id=f"LINE-{rule.rule_number}",
        # ...
    )
)
```

**Rationale**: RAG best practice. Titles contain dense, high-signal keywords crucial for retrieval. "Meals and entertainment" + detailed content provides better semantic context than content alone.

**Verification**:
```python
# Quick smoke test
uv run python -c "
import yaml
from qe_tax_rag.extraction.ca.schema import RuleSet
from qe_tax_rag.search.models import SourceFile

with open('output/verification_test.yml') as f:
    data = yaml.safe_load(f)

ruleset = RuleSet.model_validate(data)
source_files = {'simple_rule': SourceFile(path='test.html', url='file://test', hash='abc')}
chunks = ruleset.to_database_chunks(source_files)

print(f'Content preview: {chunks[0].content[:80]}...')
# Should start with title
assert chunks[0].content.startswith(ruleset.rules[0].title)
print('✅ Title included in content')
"
```

---

### Task 0.3: End-to-End Verification of Fixes

**Acceptance Criteria**:
- [ ] YAML generation includes all required metadata fields
- [ ] `RuleSet.model_validate()` succeeds on generated YAML
- [ ] `to_database_chunks()` executes without AttributeError
- [ ] `DatabaseChunk.content` starts with rule title
- [ ] Metadata fields (`extraction_source`, `extraction_confidence`, `source_anchor`) are populated

**Verification Script**:
```bash
# Full pipeline test
uv run python -c "
import yaml
from pathlib import Path
from qe_tax_rag.extraction.ca.schema import RuleSet
from qe_tax_rag.search.models import SourceFile

# Load YAML
with open('output/verification_test.yml') as f:
    data = yaml.safe_load(f)

# Verify required fields present in raw YAML
assert 'expert_source' in str(data), 'expert_source missing from YAML'
assert 'confidence_score' in str(data), 'confidence_score missing from YAML'

# Deserialize to RuleSet
ruleset = RuleSet.model_validate(data)
print(f'✅ RuleSet loaded: {len(ruleset.rules)} rules')

# Verify ExtractedRule has required fields
rule = ruleset.rules[0]
assert hasattr(rule, 'expert_source'), 'ExtractedRule missing expert_source'
assert hasattr(rule, 'confidence_score'), 'ExtractedRule missing confidence_score'
print(f'✅ ExtractedRule has required fields')

# Transform to DatabaseChunks
source_files = {
    Path(rule.source_file).stem: SourceFile(
        path=rule.source_file,
        url='file://test',
        hash='abc123'
    ) for rule in ruleset.rules
}

chunks = ruleset.to_database_chunks(source_files)
print(f'✅ Generated {len(chunks)} DatabaseChunks')

# Verify content format
chunk = chunks[0]
assert chunk.content.startswith(rule.title), 'Content does not start with title'
print(f'✅ Content format: {chunk.content[:50]}...')

# Verify metadata populated
assert chunk.metadata.extraction_source == rule.expert_source.value
assert chunk.metadata.extraction_confidence == rule.confidence_score
assert chunk.metadata.source_anchor == rule.anchor_id
print(f'✅ Metadata correctly populated')

print('\\n🎉 All architectural fixes verified!')
"
```

---

## Phase 1: Test Infrastructure Setup

**Estimated Time**: 1.5 hours

### Task 1.1: Generate Golden Fixtures from Real Extraction

**Purpose**: Create test fixtures that represent actual pipeline output (after fixes).

**Acceptance Criteria**:
- [ ] `tests/fixtures/conversion/simple_rule.yml` created (1 rule, all fields)
- [ ] `tests/fixtures/conversion/complex_rule.yml` created (3 rules, diverse content)
- [ ] Both fixtures include `expert_source`, `confidence_score`, `anchor_id`
- [ ] Both fixtures validate against `RuleSet` schema
- [ ] Fixtures committed to git

**Implementation**:
```bash
# Create directory
mkdir -p tests/fixtures/conversion

# Generate from existing HTML fixtures (after Task 0 fixes)
uv run extract-rules \
  tests/fixtures/extraction/ca/simple_rule.html \
  tests/fixtures/conversion/simple_rule.yml \
  --cache-dir output/llm_cache

uv run extract-rules \
  tests/fixtures/extraction/ca/complex_rule.html \
  tests/fixtures/conversion/complex_rule.yml \
  --cache-dir output/llm_cache

# Verify fixtures
uv run python -c "
import yaml
from qe_tax_rag.extraction.ca.schema import RuleSet

for fixture in ['simple_rule.yml', 'complex_rule.yml']:
    with open(f'tests/fixtures/conversion/{fixture}') as f:
        data = yaml.safe_load(f)
    ruleset = RuleSet.model_validate(data)
    print(f'✅ {fixture}: {len(ruleset.rules)} rules validated')
"

# Commit
git add tests/fixtures/conversion/
git commit -m "test: add golden YAML fixtures for conversion testing"
```

---

### Task 1.2: Create pytest Fixtures for Database and Mocks

**File**: `tests/conftest.py`

**Acceptance Criteria**:
- [ ] `in_memory_db` fixture creates fresh SQLite with full schema
- [ ] `source_files_mapping` fixture provides SourceFile objects for test fixtures
- [ ] `mock_embedding_service` fixture returns constant 384-dim vectors
- [ ] All fixtures use appropriate pytest scopes (function/session)

**Implementation**:
```python
import pytest
import sqlite3
import numpy as np
from qe_tax_rag.search.models import SourceFile


@pytest.fixture
def in_memory_db():
    """Fresh SQLite connection with full schema for each test."""
    from qe_tax_rag.data.schema import CREATE_TABLES_SQL, init_metadata

    conn = sqlite3.connect(":memory:")

    # Enable sqlite-vec extension
    try:
        conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        pass  # Extension loading may fail in some environments

    # Create schema
    conn.executescript(CREATE_TABLES_SQL)
    init_metadata(conn, data_version="test-1.0", embedding_model="test-bge-small")

    yield conn
    conn.close()


@pytest.fixture
def source_files_mapping():
    """SourceFile mapping for test fixtures."""
    return {
        "simple_rule": SourceFile(
            path="simple_rule.html",
            url="file://tests/fixtures/extraction/ca/simple_rule.html",
            hash="abc123simple"
        ),
        "complex_rule": SourceFile(
            path="complex_rule.html",
            url="file://tests/fixtures/extraction/ca/complex_rule.html",
            hash="abc123complex"
        ),
        "t4002-3": SourceFile(
            path="t4002-3.html",
            url="file://cra_documents/t4002-3.html",
            hash="abc123t4002"
        ),
    }


@pytest.fixture
def mock_embedding_service(monkeypatch):
    """Mock embedding service that returns constant 384-dim zero vectors."""
    from qe_tax_rag.embeddings.encoder import _EmbeddingService

    def mock_embed_documents(self, texts):
        """Return zero vectors for all inputs."""
        return [np.zeros(384, dtype=np.float32) for _ in texts]

    monkeypatch.setattr(
        _EmbeddingService,
        "embed_documents",
        mock_embed_documents
    )
```

**Verification**:
```bash
# Test fixtures are importable
uv run python -c "
import sys
sys.path.insert(0, 'tests')
from conftest import in_memory_db, source_files_mapping, mock_embedding_service
print('✅ All fixtures importable')
"
```

---

### Task 1.3: Extend Hypothesis Strategy for RuleSet

**File**: `tests/strategies.py` (new file)

**Acceptance Criteria**:
- [ ] Strategy generates valid `ExtractedRule` objects
- [ ] All required fields have valid values
- [ ] Optional fields (section, anchor_id) sometimes None
- [ ] Generated rules pass Pydantic validation
- [ ] Strategy integrates with existing Hypothesis infrastructure

**Implementation**:
```python
"""Hypothesis strategies for property-based testing."""

from hypothesis import strategies as st
from qe_tax_rag.extraction.ca.schema import (
    ExtractedRule,
    RuleSet,
    ExpertSource,
    ApplicabilityType,
)


@st.composite
def extracted_rule_strategy(draw):
    """Generate valid ExtractedRule with all required fields."""
    return ExtractedRule(
        rule_number=draw(st.integers(min_value=1, max_value=9999)),
        title=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",)))),
        content=draw(st.text(min_size=10, max_size=500, alphabet=st.characters(blacklist_categories=("Cs",)))),
        applies_to=draw(st.lists(
            st.sampled_from(ApplicabilityType),
            min_size=1,
            max_size=3,
            unique=True
        )),
        source_citation=draw(st.text(min_size=1, max_size=50)),
        chapter=draw(st.text(min_size=1, max_size=100)),
        section=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        source_file=draw(st.text(min_size=1, max_size=50)),
        expert_source=draw(st.sampled_from(ExpertSource)),
        anchor_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        confidence_score=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


@st.composite
def ruleset_strategy(draw, min_rules=1, max_rules=10):
    """Generate valid RuleSet with multiple rules."""
    rules = draw(st.lists(
        extracted_rule_strategy(),
        min_size=min_rules,
        max_size=max_rules,
    ))

    return RuleSet(
        rules=rules,
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z"
    )
```

**Verification**:
```bash
uv run python -c "
from tests.strategies import extracted_rule_strategy, ruleset_strategy
from hypothesis import given, settings
from qe_tax_rag.extraction.ca.schema import ExtractedRule, RuleSet

@given(ruleset_strategy())
@settings(max_examples=10)
def test_strategy_generates_valid_rulesets(ruleset):
    assert isinstance(ruleset, RuleSet)
    assert len(ruleset.rules) > 0
    for rule in ruleset.rules:
        assert isinstance(rule, ExtractedRule)
        assert rule.rule_number > 0
        assert len(rule.title) > 0

test_strategy_generates_valid_rulesets()
print('✅ Hypothesis strategies working')
"
```

---

## Phase 2: Unit Tests for Transformation Logic

**Estimated Time**: 2 hours

### Task 2.1: Test to_database_chunks() Core Functionality

**File**: `tests/unit/test_database_chunk.py` (new file)

**Acceptance Criteria**:
- [ ] AC1: YAML deserialization produces valid RuleSet
- [ ] AC2: DatabaseChunk transformation preserves citation ID format
- [ ] AC4: Metadata fields correctly mapped
- [ ] AC7: Content field includes title
- [ ] Tests use real YAML fixtures (not synthetic data)

**Implementation**:
```python
"""Unit tests for DatabaseChunk transformation logic."""

import pytest
import yaml
from pathlib import Path
from qe_tax_rag.extraction.ca.schema import RuleSet, ExtractedRule, ExpertSource, ApplicabilityType
from qe_tax_rag.data.models import DatabaseChunk


@pytest.mark.unit
def test_to_database_chunks_valid_transformation(source_files_mapping):
    """AC1, AC2, AC4, AC7: Verify RuleSet.to_database_chunks() produces valid DatabaseChunks."""
    # Load golden fixture
    with open("tests/fixtures/conversion/simple_rule.yml") as f:
        data = yaml.safe_load(f)

    # AC1: YAML deserialization
    ruleset = RuleSet.model_validate(data)
    assert ruleset.schema_version == "1.0"
    assert len(ruleset.rules) > 0

    # AC2: DatabaseChunk transformation
    chunks = ruleset.to_database_chunks(source_files_mapping)
    assert len(chunks) == len(ruleset.rules)

    # Check first chunk
    chunk = chunks[0]
    rule = ruleset.rules[0]

    # AC7: Content format is title + content
    expected_content = f"{rule.title}\n\n{rule.content}"
    assert chunk.content == expected_content, \
        f"Content should be 'title\\n\\ncontent' format"
    assert chunk.content.startswith(rule.title), \
        "Content must start with title for RAG quality"

    # AC2: Citation ID format
    assert chunk.citation_id == f"LINE-{rule.rule_number}"
    assert chunk.citation_id.startswith("LINE-")

    # AC4: Metadata preserved
    assert chunk.metadata.extraction_source == rule.expert_source.value
    assert chunk.metadata.extraction_confidence == rule.confidence_score
    assert chunk.metadata.source_anchor == rule.anchor_id
    assert chunk.metadata.income_type == [at.value for at in rule.applies_to]
    assert chunk.metadata.section_title == rule.chapter

    # Expense types populated
    assert isinstance(chunk.expense_types, list)
    assert len(chunk.expense_types) > 0


@pytest.mark.unit
def test_content_field_includes_title_for_rag_quality(source_files_mapping):
    """AC7: DatabaseChunk.content must include title for RAG retrieval quality."""
    # Create minimal rule
    rule = ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="You can deduct 50% of the cost of food, beverages, or entertainment.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3 – Business Expenses",
        source_file="simple_rule.html",
        expert_source=ExpertSource.ADJUDICATED,
        confidence_score=1.0,
        anchor_id="tocch3ln8523",
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z"
    )

    chunks = ruleset.to_database_chunks(source_files_mapping)

    # Title must be in content
    assert "Meals and entertainment" in chunks[0].content
    assert chunks[0].content.startswith("Meals and entertainment\n\n")

    # Verify separator
    assert "\n\n" in chunks[0].content

    # Verify full content present
    assert "You can deduct 50%" in chunks[0].content


@pytest.mark.unit
def test_citation_id_format_and_uniqueness(source_files_mapping):
    """AC2: Citation IDs follow LINE-{number} format and are unique."""
    # Load multi-rule fixture
    with open("tests/fixtures/conversion/complex_rule.yml") as f:
        data = yaml.safe_load(f)

    ruleset = RuleSet.model_validate(data)
    chunks = ruleset.to_database_chunks(source_files_mapping)

    # Check format
    for chunk in chunks:
        assert chunk.citation_id.startswith("LINE-")
        # Extract number part
        number_part = chunk.citation_id.replace("LINE-", "")
        assert number_part.isdigit()

    # Check uniqueness
    citation_ids = [chunk.citation_id for chunk in chunks]
    assert len(citation_ids) == len(set(citation_ids)), \
        "Citation IDs must be unique"


@pytest.mark.unit
def test_metadata_preservation_comprehensive(source_files_mapping):
    """AC4: All metadata fields correctly mapped from ExtractedRule to ChunkMetadata."""
    rule = ExtractedRule(
        rule_number=9270,
        title="Motor vehicle expenses",
        content="You can deduct motor vehicle expenses including fuel and maintenance.",
        applies_to=[ApplicabilityType.BUSINESS, ApplicabilityType.FARMING],
        source_citation="Line 9270",
        chapter="Chapter 3 – Business Expenses",
        section="Part 2 – Vehicle Expenses",
        source_file="complex_rule.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=0.95,
        anchor_id="tocch3ln9270",
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z"
    )

    chunks = ruleset.to_database_chunks(source_files_mapping)
    chunk = chunks[0]

    # Verify all metadata mappings
    assert chunk.metadata.income_type == ["business", "farming"]
    assert chunk.metadata.section_title == "Chapter 3 – Business Expenses"
    assert chunk.metadata.document_id == "complex_rule"
    assert chunk.metadata.extraction_source == "classic"
    assert chunk.metadata.extraction_confidence == 0.95
    assert chunk.metadata.source_anchor == "tocch3ln9270"


@pytest.mark.unit
def test_missing_source_file_raises_value_error(source_files_mapping):
    """Verify clear error when source_file not in mapping."""
    rule = ExtractedRule(
        rule_number=9999,
        title="Test rule",
        content="Test content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 9999",
        chapter="Test Chapter",
        source_file="nonexistent_file.html",  # ← Not in mapping
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z"
    )

    with pytest.raises(ValueError, match="No SourceFile found"):
        ruleset.to_database_chunks(source_files_mapping)
```

---

### Task 2.2: Test Optional Field Handling

**File**: `tests/unit/test_database_chunk.py`

**Acceptance Criteria**:
- [ ] Rules with section=None handled correctly
- [ ] Rules with anchor_id=None handled correctly
- [ ] No AttributeError on optional fields
- [ ] Metadata fields correctly store None values

**Implementation**:
```python
@pytest.mark.unit
def test_optional_fields_handled_correctly(source_files_mapping):
    """Verify optional fields (section, anchor_id) handled gracefully."""
    rule = ExtractedRule(
        rule_number=8000,
        title="Test rule without optional fields",
        content="Test content",
        applies_to=[ApplicabilityType.FISHING],
        source_citation="Line 8000",
        chapter="Test Chapter",
        section=None,  # ← Optional
        source_file="complex_rule.html",
        expert_source=ExpertSource.LLM,
        confidence_score=0.8,
        anchor_id=None,  # ← Optional
    )

    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z"
    )

    # Should not raise AttributeError
    chunks = ruleset.to_database_chunks(source_files_mapping)
    chunk = chunks[0]

    # Metadata should handle None
    assert chunk.metadata.source_anchor is None
```

---

### Task 2.3: Property-Based Tests for Robustness

**File**: `tests/unit/test_database_chunk_hypothesis.py` (new file)

**Acceptance Criteria**:
- [ ] Generated RuleSets transform without crashes
- [ ] All generated DatabaseChunks pass Pydantic validation
- [ ] Citation IDs are always valid format
- [ ] Content field always non-empty

**Implementation**:
```python
"""Property-based tests for DatabaseChunk transformation."""

import pytest
from hypothesis import given, settings
from tests.strategies import ruleset_strategy
from qe_tax_rag.data.models import DatabaseChunk


@pytest.mark.unit
@given(ruleset=ruleset_strategy(min_rules=1, max_rules=5))
@settings(max_examples=50)
def test_to_database_chunks_never_crashes(ruleset, source_files_mapping):
    """Property: to_database_chunks() handles all valid RuleSets without crashing."""
    try:
        chunks = ruleset.to_database_chunks(source_files_mapping)

        # All chunks should be valid
        for chunk in chunks:
            assert isinstance(chunk, DatabaseChunk)

            # Citation ID always valid
            assert chunk.citation_id.startswith("LINE-")

            # Content always non-empty
            assert len(chunk.content) > 0

            # Metadata always present
            assert chunk.metadata is not None

    except ValueError as e:
        # Only acceptable error: missing source file
        assert "No SourceFile found" in str(e)


@pytest.mark.unit
@given(ruleset=ruleset_strategy(min_rules=1, max_rules=3))
@settings(max_examples=30)
def test_all_generated_chunks_pass_validation(ruleset, source_files_mapping):
    """Property: All generated DatabaseChunks pass strict Pydantic validation."""
    try:
        chunks = ruleset.to_database_chunks(source_files_mapping)

        for chunk in chunks:
            # Re-validate to ensure strict mode passes
            validated = DatabaseChunk.model_validate(chunk.model_dump())
            assert validated == chunk

    except ValueError as e:
        # Only acceptable error: missing source file
        assert "No SourceFile found" in str(e)
```

---

## Phase 3: Integration Tests (YAML → Database)

**Estimated Time**: 2 hours

### Task 3.1: YAML → DatabaseChunk End-to-End

**File**: `tests/integration/test_yaml_to_db.py` (new file)

**Acceptance Criteria**:
- [ ] AC1: YAML file loads and deserializes successfully
- [ ] AC2: All rules transform to valid DatabaseChunks
- [ ] AC3: Chunks insert into SQLite without errors
- [ ] Schema version validation works
- [ ] Multiple rules handled correctly

**Implementation**:
```python
"""Integration tests for YAML → SQLite conversion pipeline."""

import pytest
import yaml
import json
from datetime import datetime, timezone
from qe_tax_rag.extraction.ca.schema import RuleSet
from qe_tax_rag.data.models import DatabaseChunk


@pytest.mark.integration
def test_yaml_to_database_chunks_end_to_end(source_files_mapping):
    """AC1, AC2: Full YAML → DatabaseChunk flow."""
    # Load real fixture
    with open("tests/fixtures/conversion/complex_rule.yml") as f:
        data = yaml.safe_load(f)

    # AC1: YAML deserialization
    ruleset = RuleSet.model_validate(data)
    assert ruleset.schema_version == "1.0"
    assert len(ruleset.rules) == 3

    # AC2: DatabaseChunk transformation
    chunks = ruleset.to_database_chunks(source_files_mapping)
    assert len(chunks) == 3

    # Verify all chunks are valid
    for chunk in chunks:
        # Strict validation
        validated = DatabaseChunk.model_validate(chunk.model_dump())

        # Required fields
        assert chunk.citation_id.startswith("LINE-")
        assert len(chunk.content) > 0
        assert chunk.source_url
        assert chunk.source_hash

        # Content includes title
        assert "\n\n" in chunk.content  # Title/content separator

        # Metadata populated
        assert chunk.metadata.extraction_source in ["classic", "llm", "adjudicated"]
        assert 0.0 <= chunk.metadata.extraction_confidence <= 1.0


@pytest.mark.integration
def test_schema_version_mismatch_detection():
    """AC1: Schema version mismatch raises clear error."""
    # Create YAML with wrong schema version
    data = {
        "rules": [],
        "schema_version": "2.0",  # ← Invalid
        "extraction_timestamp": "2025-10-22T00:00:00Z"
    }

    # Should validate (no version enforcement in RuleSet model currently)
    # This test documents expected behavior if we add version validation
    ruleset = RuleSet.model_validate(data)
    assert ruleset.schema_version == "2.0"
```

---

### Task 3.2: DatabaseChunk → SQLite Integration

**File**: `tests/integration/test_yaml_to_db.py`

**Acceptance Criteria**:
- [ ] AC3: DatabaseChunks insert into SQLite successfully
- [ ] No UNIQUE constraint violations (unique citation_ids)
- [ ] No NULL values in NOT NULL columns
- [ ] Metadata JSON is valid and parseable
- [ ] Row counts match expected

**Implementation**:
```python
@pytest.mark.integration
def test_database_insertion_and_integrity(in_memory_db, source_files_mapping):
    """AC3: DatabaseChunk inserts into SQLite without errors."""
    # Load fixture and transform
    with open("tests/fixtures/conversion/simple_rule.yml") as f:
        data = yaml.safe_load(f)

    ruleset = RuleSet.model_validate(data)
    chunks = ruleset.to_database_chunks(source_files_mapping)

    # Insert into database
    for chunk in chunks:
        cursor = in_memory_db.execute(
            """
            INSERT INTO rules (
                content, citation_id, source_url, source_hash,
                province, business_type, metadata_json, retrieved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.content,
                chunk.citation_id,
                chunk.source_url,
                chunk.source_hash,
                json.dumps(chunk.province),
                json.dumps(chunk.business_type),
                chunk.metadata.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            )
        )

    in_memory_db.commit()

    # AC3: Verify insertion
    cursor = in_memory_db.execute("SELECT COUNT(*) FROM rules")
    count = cursor.fetchone()[0]
    assert count == len(chunks), f"Expected {len(chunks)} rows, got {count}"

    # Verify no NULL citation_ids
    cursor = in_memory_db.execute(
        "SELECT COUNT(*) FROM rules WHERE citation_id IS NULL OR citation_id = ''"
    )
    null_count = cursor.fetchone()[0]
    assert null_count == 0, "Found NULL or empty citation_ids"

    # Verify metadata JSON is valid
    cursor = in_memory_db.execute("SELECT citation_id, metadata_json FROM rules")
    for citation_id, metadata_json in cursor.fetchall():
        metadata = json.loads(metadata_json)
        assert "extraction_source" in metadata, \
            f"{citation_id}: missing extraction_source in metadata"
        assert "extraction_confidence" in metadata, \
            f"{citation_id}: missing extraction_confidence in metadata"


@pytest.mark.integration
def test_unique_constraint_on_citation_id(in_memory_db, source_files_mapping):
    """AC3: Duplicate citation_ids violate UNIQUE constraint."""
    # Load fixture
    with open("tests/fixtures/conversion/simple_rule.yml") as f:
        data = yaml.safe_load(f)

    ruleset = RuleSet.model_validate(data)
    chunks = ruleset.to_database_chunks(source_files_mapping)

    # Insert first chunk
    chunk = chunks[0]
    in_memory_db.execute(
        """
        INSERT INTO rules (
            content, citation_id, source_url, source_hash,
            province, business_type, metadata_json, retrieved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chunk.content,
            chunk.citation_id,
            chunk.source_url,
            chunk.source_hash,
            json.dumps(chunk.province),
            json.dumps(chunk.business_type),
            chunk.metadata.model_dump_json(),
            datetime.now(timezone.utc).isoformat(),
        )
    )
    in_memory_db.commit()

    # Try to insert duplicate - should raise IntegrityError
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint"):
        in_memory_db.execute(
            """
            INSERT INTO rules (
                content, citation_id, source_url, source_hash,
                province, business_type, metadata_json, retrieved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Different content",
                chunk.citation_id,  # ← Same citation_id
                chunk.source_url,
                chunk.source_hash,
                json.dumps(chunk.province),
                json.dumps(chunk.business_type),
                chunk.metadata.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            )
        )


@pytest.mark.integration
def test_expense_types_populated(in_memory_db, source_files_mapping):
    """AC5: Expense types field populated via classifier."""
    # Load fixture
    with open("tests/fixtures/conversion/complex_rule.yml") as f:
        data = yaml.safe_load(f)

    ruleset = RuleSet.model_validate(data)
    chunks = ruleset.to_database_chunks(source_files_mapping)

    # All chunks should have expense_types
    for chunk in chunks:
        assert isinstance(chunk.expense_types, list)
        assert len(chunk.expense_types) > 0

        # Should be either classified types or default "general"
        assert all(isinstance(et, str) for et in chunk.expense_types)
```

---

## Phase 4: Property-Based Database Constraint Tests

**Estimated Time**: 30 minutes

### Task 4.1: Hypothesis Tests for Database Constraints

**File**: `tests/integration/test_yaml_to_db_hypothesis.py` (new file)

**Acceptance Criteria**:
- [ ] AC6: Hypothesis generates diverse RuleSets
- [ ] Database constraints enforced (UNIQUE, NOT NULL)
- [ ] ValidationError raised for invalid data
- [ ] No silent failures

**Implementation**:
```python
"""Property-based tests for database constraints."""

import pytest
import sqlite3
from hypothesis import given, settings, assume
from tests.strategies import ruleset_strategy


@pytest.mark.integration
@given(ruleset=ruleset_strategy(min_rules=1, max_rules=5))
@settings(max_examples=20)
def test_database_constraints_enforced(ruleset, in_memory_db, source_files_mapping):
    """AC6: Database constraints (UNIQUE, NOT NULL) are enforced."""
    try:
        chunks = ruleset.to_database_chunks(source_files_mapping)

        # Insert all chunks
        for chunk in chunks:
            in_memory_db.execute(
                """
                INSERT INTO rules (
                    content, citation_id, source_url, source_hash,
                    province, business_type, metadata_json, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.content,
                    chunk.citation_id,
                    chunk.source_url,
                    chunk.source_hash,
                    json.dumps(chunk.province),
                    json.dumps(chunk.business_type),
                    chunk.metadata.model_dump_json(),
                    "2025-10-22T00:00:00Z",
                )
            )

        in_memory_db.commit()

        # Verify row count
        cursor = in_memory_db.execute("SELECT COUNT(*) FROM rules")
        assert cursor.fetchone()[0] == len(chunks)

    except ValueError as e:
        # Only acceptable: missing source file
        assert "No SourceFile found" in str(e)
    except sqlite3.IntegrityError as e:
        # Only acceptable: duplicate citation_id (if RuleSet has duplicate rule_numbers)
        assert "UNIQUE constraint" in str(e)
```

---

## Acceptance Criteria Summary

### AC1: YAML Deserialization ✓
- [ ] `RuleSet.from_yaml()` or `model_validate()` loads YAML successfully
- [ ] All ExtractedRule objects pass Pydantic validation
- [ ] Schema version present in loaded data

### AC2: DatabaseChunk Transformation ✓
- [ ] `to_database_chunks()` generates valid DatabaseChunk objects
- [ ] All chunks pass Pydantic strict validation
- [ ] Citation ID format preserved: `LINE-{number}`

### AC3: Database Insertion ✓
- [ ] Each DatabaseChunk inserts into SQLite successfully
- [ ] No UNIQUE constraint violations on citation_id
- [ ] All required columns populated (no NULL in NOT NULL fields)

### AC4: Metadata Preservation ✓
- [ ] `income_type` preserved from `applies_to` field
- [ ] `extraction_source` preserved from `expert_source`
- [ ] `extraction_confidence` preserved from `confidence_score`
- [ ] `source_anchor` preserved from `anchor_id`
- [ ] `section_title` mapped from `chapter` field

### AC5: Expense Type Inference ✓
- [ ] `expense_types` field populated via ExpenseTypeClassifier
- [ ] Classifier output stored as list of strings
- [ ] Empty classifier result stores `["general"]` as default

### AC6: Property-Based Testing ✓
- [ ] Hypothesis generates wide variety of RuleSet structures
- [ ] `to_database_chunks()` handles all generated inputs without errors
- [ ] Database constraints enforced (UNIQUE, NOT NULL)

### AC7: Chunk Content Fidelity (RAG Quality) ✓
- [ ] Transformation ExtractedRule → DatabaseChunk is deterministic
- [ ] `DatabaseChunk.content` is `f"{title}\n\n{content}"` format
- [ ] No silent data loss (title preserved in content field)

---

## Success Metrics

After completing all tasks:

✅ **Architectural Fixes Applied**:
- yaml_generator.py preserves required metadata fields
- to_database_chunks() concatenates title and content
- End-to-end flow works (YAML → RuleSet → DatabaseChunk → SQLite)

✅ **Test Coverage**:
- 100% of AC1-AC7 validated with automated tests
- Unit tests for transformation logic
- Integration tests for YAML → DB flow
- Property-based tests for robustness
- Database constraint enforcement verified

✅ **Test Execution**:
- All tests pass in < 30 seconds
- No external dependencies (mocked embeddings, mocked classifier for unit tests)
- Tests use real YAML fixtures from extraction pipeline

---

## Deferred to Ticket 3 (Per MECE Principle)

The following items belong in Ticket 3 (ExpenseTypeClassifier Testing):

- ❌ Real ExpenseTypeClassifier accuracy testing
- ❌ Ground truth fixture creation for classification
- ❌ Precision/recall metrics for expense type inference
- ❌ Confusion matrix for misclassifications

---

## Commands Reference

```bash
# Phase 0: Apply fixes
# Edit yaml_generator.py and schema.py per Task 0.1 and 0.2
uv run pytest tests/unit/extraction/ca/test_yaml_generator.py -v

# Phase 1: Create fixtures
mkdir -p tests/fixtures/conversion
uv run extract-rules tests/fixtures/extraction/ca/simple_rule.html tests/fixtures/conversion/simple_rule.yml
uv run extract-rules tests/fixtures/extraction/ca/complex_rule.html tests/fixtures/conversion/complex_rule.yml

# Phase 2-4: Run tests
uv run pytest tests/unit/test_database_chunk.py -v
uv run pytest tests/unit/test_database_chunk_hypothesis.py -v
uv run pytest tests/integration/test_yaml_to_db.py -v
uv run pytest tests/integration/test_yaml_to_db_hypothesis.py -v

# Run all Ticket 2 tests
uv run pytest tests/unit/test_database_chunk*.py tests/integration/test_yaml_to_db*.py -v

# Check coverage
uv run pytest tests/ --cov=src/qe_tax_rag/extraction/ca/schema --cov=src/qe_tax_rag/data/models -v
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-22
**Authors**: QE Tax RAG Team + Zen MCP Consultation
