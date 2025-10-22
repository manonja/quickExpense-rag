# Critical Issues Implementation Plan

**Branch**: feat/test-strategy-html-to-yaml
**Created**: 2025-10-21
**Scope**: Address critical test coverage gaps and high-priority code duplication identified in PR #38 code review

## Context

This plan addresses critical issues found during code review of the data model normalization work documented in `DATA_MODEL_NORMALIZATION_PLAN.md`. While the implementation is complete (transformer elimination, DatabaseChunk unification, YAML loading), the **test coverage is missing** for the new code paths.

## Commit Strategy

**Commit after EACH completed subtask** - Do not batch multiple subtasks into one commit. Each commit should:
- Pass all pre-commit hooks (ruff, ruff-format, mypy, pyright)
- Include clear commit message following conventional commits format
- Reference the subtask number (e.g., "test: add YAML format auto-detection tests (Subtask 1.1)")

## PHASE 1: CRITICAL - Add YAML Loading Tests (BLOCKER)

**Scope Reference**: These tests validate the implementation completed in DATA_MODEL_NORMALIZATION_PLAN.md:
- Task 3: RuleSet.to_database_chunks() (IMPLEMENTED, UNTESTED)
- Task 4: IndexBuilder YAML support (IMPLEMENTED, UNTESTED)
- Task 5: DatabaseChunk unified model (IMPLEMENTED, PARTIALLY TESTED)

### Subtask 1.1: Test YAML File Format Auto-Detection

**File**: `tests/unit/test_builder.py`
**Location**: Add to existing TestIndexBuilder class (~line 50)

**Test Cases**:
```python
@pytest.mark.unit
def test_build_from_file_detects_yaml_format(self, tmp_path: Path) -> None:
    """Test that .yml/.yaml files are detected and routed to YAML loader."""
    yaml_file = tmp_path / "rules.yml"
    yaml_file.write_text("rules: []")

    builder = IndexBuilder(output_db=tmp_path / "test.db")
    # Should NOT raise "Unknown file format" error
    # Should call _load_from_yaml() internally

@pytest.mark.unit
def test_build_from_file_detects_jsonl_format(self, tmp_path: Path) -> None:
    """Test that .jsonl files are detected and routed to JSONL loader."""
    jsonl_file = tmp_path / "chunks.jsonl"
    jsonl_file.write_text('{"content": "test"}\n')

    builder = IndexBuilder(output_db=tmp_path / "test.db")
    # Should call _load_from_jsonl() internally

@pytest.mark.unit
def test_build_from_file_raises_on_unknown_format(self, tmp_path: Path) -> None:
    """Test that unsupported file formats raise clear error."""
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("invalid")

    builder = IndexBuilder(output_db=tmp_path / "test.db")
    with pytest.raises(ValueError, match="Unknown file format"):
        builder.build_from_file(input_path=txt_file)
```

**Acceptance Criteria**:
- [x] 3 new tests added to test_builder.py
- [x] Tests verify format detection logic in build_from_file()
- [x] All tests pass
- [x] Commit: "test: add YAML format auto-detection tests (Subtask 1.1)"

---

### Subtask 1.2: Test RuleSet.to_database_chunks() Conversion

**File**: `tests/unit/extraction/ca/test_schema.py` (NEW FILE)
**Rationale**: Separation of concerns - extraction schema tests separate from builder tests

**Test Cases**:
```python
"""Unit tests for extraction pipeline schema models."""

import pytest
from pathlib import Path
from src.qe_tax_rag.extraction.ca.schema import (
    RuleSet,
    ExtractedRule,
    ApplicabilityType,
    ExpertSource,
)
from src.qe_tax_rag.search.models import SourceFile
from src.qe_tax_rag.data.models import DatabaseChunk


@pytest.fixture
def sample_rule() -> ExtractedRule:
    """Minimal valid rule for testing."""
    return ExtractedRule(
        rule_number=8523,
        title="Test Rule",
        content="You can deduct business meals.",
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
    ruleset = RuleSet(rules=[sample_rule])

    chunks = ruleset.to_database_chunks(source_files=source_files)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, DatabaseChunk)
    assert chunk.content == "You can deduct business meals."
    assert chunk.citation_id == "LINE-8523"
    assert chunk.source_url == "https://www.canada.ca/t4002-24e.html"
    assert chunk.source_hash == "abc123def456"
    assert "meals" in chunk.expense_types  # Inferred by classifier


@pytest.mark.unit
def test_ruleset_to_database_chunks_preserves_metadata(
    sample_rule: ExtractedRule,
    source_files: dict[str, SourceFile],
) -> None:
    """Test that extraction metadata is preserved in chunks."""
    ruleset = RuleSet(rules=[sample_rule])

    chunks = ruleset.to_database_chunks(source_files=source_files)

    chunk = chunks[0]
    assert chunk.metadata.extraction_source == "classic"
    assert chunk.metadata.extraction_confidence == 1.0
    assert chunk.metadata.section_title == "Meals and entertainment"


@pytest.mark.unit
def test_ruleset_to_database_chunks_raises_on_missing_source(
    sample_rule: ExtractedRule,
) -> None:
    """Test that missing source file raises clear error."""
    ruleset = RuleSet(rules=[sample_rule])

    with pytest.raises(ValueError, match="No source file found"):
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
    ruleset = RuleSet(rules=rules)

    chunks = ruleset.to_database_chunks(source_files=source_files)

    assert "vehicle" in chunks[0].expense_types
    assert "maintenance" in chunks[0].expense_types
    assert "home_office" in chunks[1].expense_types
```

**Acceptance Criteria**:
- [x] New test file created: tests/unit/extraction/ca/test_schema.py
- [x] 5 test cases covering conversion, metadata preservation, error handling, expense classification
- [x] All tests pass
- [x] Commit: "test: add RuleSet.to_database_chunks() conversion tests (Subtask 1.2)"

---

### Subtask 1.3: Test IndexBuilder._load_from_yaml() Method

**File**: `tests/unit/test_builder.py`
**Location**: Add to TestIndexBuilder class

**Test Cases**:
```python
@pytest.mark.unit
def test_load_from_yaml_valid_file(self, tmp_path: Path) -> None:
    """Test loading valid YAML file with RuleSet structure."""
    yaml_content = """
rules:
  - rule_number: 8523
    title: "Test Rule"
    content: "Test content"
    applies_to: [business]
    source_citation: "Line 8523"
    chapter: "Chapter 3"
    section: null
    source_file: "t4002-24e.html"
    expert_source: classic
    anchor_id: null
    confidence_score: 1.0
"""
    yaml_file = tmp_path / "rules.yml"
    yaml_file.write_text(yaml_content)

    builder = IndexBuilder(output_db=tmp_path / "test.db")
    chunks = builder._load_from_yaml(yaml_file)

    assert len(chunks) > 0
    assert all(isinstance(chunk, DatabaseChunk) for chunk in chunks)
    assert chunks[0].citation_id == "LINE-8523"


@pytest.mark.unit
def test_load_from_yaml_empty_rules(self, tmp_path: Path) -> None:
    """Test loading YAML with empty rules list."""
    yaml_file = tmp_path / "empty.yml"
    yaml_file.write_text("rules: []")

    builder = IndexBuilder(output_db=tmp_path / "test.db")
    chunks = builder._load_from_yaml(yaml_file)

    assert chunks == []


@pytest.mark.unit
def test_load_from_yaml_invalid_schema(self, tmp_path: Path) -> None:
    """Test that invalid YAML schema raises validation error."""
    yaml_file = tmp_path / "invalid.yml"
    yaml_file.write_text("invalid: yaml")

    builder = IndexBuilder(output_db=tmp_path / "test.db")
    with pytest.raises(Exception):  # ValidationError or KeyError
        builder._load_from_yaml(yaml_file)
```

**Acceptance Criteria**:
- [x] 3 new tests added to test_builder.py
- [x] Tests cover valid YAML, empty rules, invalid schema
- [x] All tests pass
- [x] Commit: "test: add IndexBuilder._load_from_yaml() tests (Subtask 1.3)"

---

### Subtask 1.4: Integration Test - YAML to Database

**File**: `tests/unit/test_builder.py`
**Location**: Add new test class TestBuildFromFileYAML

**Test Cases**:
```python
@pytest.mark.unit
class TestBuildFromFileYAML:
    """Integration tests for YAML → SQLite database path."""

    def test_yaml_to_database_end_to_end(self, tmp_path: Path) -> None:
        """Test complete pipeline: YAML file → SQLite database with indices."""
        yaml_content = """
rules:
  - rule_number: 8523
    title: "Business Meals"
    content: "You can deduct 50% of business meal expenses."
    applies_to: [business]
    source_citation: "Line 8523"
    chapter: "Chapter 3"
    section: "Meals and entertainment"
    source_file: "t4002-24e.html"
    expert_source: classic
    anchor_id: null
    confidence_score: 1.0
  - rule_number: 9281
    title: "Vehicle Expenses"
    content: "Deduct vehicle expenses including fuel and insurance."
    applies_to: [business]
    source_citation: "Line 9281"
    chapter: "Chapter 4"
    section: "Vehicle expenses"
    source_file: "t4002-24e.html"
    expert_source: llm
    anchor_id: "vehicle-expenses"
    confidence_score: 0.95
"""
        yaml_file = tmp_path / "rules.yml"
        yaml_file.write_text(yaml_content)

        db_path = tmp_path / "test.db"
        builder = IndexBuilder(output_db=db_path)
        builder.build_from_file(
            input_path=yaml_file,
            source_files={
                "t4002-24e": SourceFile(
                    path="t4002-24e.html",
                    url="https://www.canada.ca/t4002-24e.html",
                    hash="abc123",
                )
            },
        )

        # Verify database was created
        assert db_path.exists()

        # Verify tables exist
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check rules table
        cursor.execute("SELECT COUNT(*) FROM rules")
        assert cursor.fetchone()[0] == 2

        # Check FTS5 table
        cursor.execute("SELECT COUNT(*) FROM rules_fts")
        assert cursor.fetchone()[0] == 2

        # Check vector table
        cursor.execute("SELECT COUNT(*) FROM rules_vec")
        assert cursor.fetchone()[0] == 2

        # Verify citation_id format
        cursor.execute("SELECT citation_id FROM rules ORDER BY citation_id")
        citations = [row[0] for row in cursor.fetchall()]
        assert citations == ["LINE-8523", "LINE-9281"]

        conn.close()


    def test_yaml_preserves_extraction_metadata(self, tmp_path: Path) -> None:
        """Test that extraction metadata survives YAML → database conversion."""
        yaml_content = """
rules:
  - rule_number: 8523
    title: "Test"
    content: "Test content"
    applies_to: [business]
    source_citation: "Line 8523"
    chapter: "Chapter 3"
    section: "Test section"
    source_file: "t4002-24e.html"
    expert_source: adjudicated
    anchor_id: "test-anchor"
    confidence_score: 0.88
"""
        yaml_file = tmp_path / "rules.yml"
        yaml_file.write_text(yaml_content)

        db_path = tmp_path / "test.db"
        builder = IndexBuilder(output_db=db_path)
        builder.build_from_file(
            input_path=yaml_file,
            source_files={
                "t4002-24e": SourceFile(
                    path="t4002-24e.html",
                    url="https://www.canada.ca/t4002.html",
                    hash="xyz789",
                )
            },
        )

        # Query metadata from database
        import sqlite3
        import json
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM rules WHERE citation_id = 'LINE-8523'")
        metadata_json = cursor.fetchone()[0]
        metadata = json.loads(metadata_json)

        assert metadata["extraction_source"] == "adjudicated"
        assert metadata["extraction_confidence"] == 0.88
        assert metadata["source_anchor"] == "test-anchor"
        assert metadata["section_title"] == "Test section"

        conn.close()
```

**Acceptance Criteria**:
- [x] New test class TestBuildFromFileYAML added
- [x] 2 integration tests covering end-to-end YAML → database + metadata preservation
- [x] Tests verify table creation, row counts, citation_id format, metadata fields
- [x] All tests pass
- [x] Commit: "test: add YAML to database integration tests (Subtask 1.4)"

---

### Subtask 1.5: Update Existing Tests to Use DatabaseChunk

**File**: `tests/unit/test_builder.py`
**Location**: Lines ~932-1176 (existing tests)

**Changes Needed**:
```python
# OLD (line 932)
def test_build_from_jsonl_creates_database(self, tmp_path: Path) -> None:
    ...
    # Tests expect dict[str, object] chunks
    chunks = [{"content": "test", "citation_id": "S1-F1-C1-p1"}]

# NEW
def test_build_from_file_jsonl_creates_database(self, tmp_path: Path) -> None:
    ...
    # Tests should use DatabaseChunk objects
    from src.qe_tax_rag.data.models import DatabaseChunk
    chunks = [DatabaseChunk(
        content="test",
        citation_id="S1-F1-C1-p1",
        source_url="https://example.com",
        source_hash="abc123",
        province=[],
        business_type=[],
        expense_types=[],
    )]
```

**Test Cases to Update**:
1. `test_build_from_jsonl_creates_database` → `test_build_from_file_jsonl_creates_database`
2. `test_build_from_jsonl_populates_tables` → `test_build_from_file_jsonl_populates_tables`
3. Any other tests using old method name or dict-based chunks

**Acceptance Criteria**:
- [x] All references to `build_from_jsonl()` in tests updated to `build_from_file()`
- [x] All tests using `dict[str, object]` updated to use `DatabaseChunk` objects
- [x] Test names updated to reflect new API
- [x] All tests pass
- [x] Commit: "test: update existing builder tests to use DatabaseChunk (Subtask 1.5)"

---

## PHASE 2: HIGH - Refactor CLI Code Duplication

**Scope**: Eliminate ~200 LOC duplication in scripts/cli.py (lines 508-647)

### Subtask 2.1: Extract _run_preprocess_logic() Helper

**File**: `scripts/cli.py`
**Location**: Add new helper function before pipeline() command (~line 400)

**Implementation**:
```python
def _run_preprocess_logic(
    input_dir: Path,
    console: Console,
) -> Path:
    """
    Run preprocessing logic (HTML → YAML extraction).

    Extracted from pipeline command to eliminate duplication.

    Returns:
        Path to generated rules.yml file
    """
    # Extract duplicate logic from lines 528-580
    # Return path to generated YAML file
    pass
```

**Acceptance Criteria**:
- [x] New helper function added with clear docstring
- [x] Function signature matches usage in both preprocess and pipeline commands
- [x] No logic changes - pure extraction
- [x] All CLI commands still pass manual smoke tests
- [x] Commit: "refactor: extract _run_preprocess_logic() helper (Subtask 2.1)"

---

### Subtask 2.2: Extract _run_build_logic() Helper

**File**: `scripts/cli.py`
**Location**: Add new helper function after _run_preprocess_logic()

**Implementation**:
```python
def _run_build_logic(
    input_file: Path,
    output_db: Path,
    console: Console,
) -> None:
    """
    Run database build logic (YAML/JSONL → SQLite).

    Extracted from pipeline command to eliminate duplication.
    """
    # Extract duplicate logic from lines 590-647
    pass
```

**Acceptance Criteria**:
- [x] New helper function added with clear docstring
- [x] Function signature matches usage in both build and pipeline commands
- [x] No logic changes - pure extraction
- [x] All CLI commands still pass manual smoke tests
- [x] Commit: "refactor: extract _run_build_logic() helper (Subtask 2.2)"

---

### Subtask 2.3: Update Pipeline Command to Use Helpers

**File**: `scripts/cli.py`
**Location**: Lines 508-647 (pipeline command)

**Changes**:
```python
# BEFORE (lines 528-647 - ~120 LOC)
@app.command()
def pipeline(...):
    # Duplicate preprocessing logic
    console.print("[cyan]Stage 1/3: Extraction...[/cyan]")
    # ... 50+ lines duplicated from preprocess command ...

    # Duplicate build logic
    console.print("[cyan]Stage 2/3: Database Build...[/cyan]")
    # ... 50+ lines duplicated from build command ...

# AFTER (lines 528-560 - ~30 LOC)
@app.command()
def pipeline(...):
    # Stage 1: Extraction
    console.print("[cyan]Stage 1/3: Extraction...[/cyan]")
    rules_yaml = _run_preprocess_logic(input_dir=input_dir, console=console)

    # Stage 2: Build
    console.print("[cyan]Stage 2/3: Database Build...[/cyan]")
    _run_build_logic(input_file=rules_yaml, output_db=output_db, console=console)

    # Stage 3: Validation (unchanged)
    console.print("[cyan]Stage 3/3: Validation...[/cyan]")
    # ... validation logic ...
```

**Acceptance Criteria**:
- [x] Pipeline command refactored to use helper functions
- [x] Net LOC reduction: ~90 lines removed
- [x] Behavior unchanged - output matches previous implementation
- [x] Manual smoke test: `uv run python scripts/cli.py pipeline-extraction` succeeds
- [x] Commit: "refactor: use helpers in pipeline command to eliminate duplication (Subtask 2.3)"

---

## PHASE 3: OPTIONAL - Polish & Safety Improvements

**Note**: These are low-priority improvements. Only implement if time permits after PHASE 1 and PHASE 2.

### Subtask 3.1: Use zip(..., strict=True)

**File**: `src/qe_tax_rag/data/builder.py`
**Location**: Line 389

**Change**:
```python
# Before
for chunk_data, embedding in zip(chunks, embeddings):

# After
for chunk_data, embedding in zip(chunks, embeddings, strict=True):
```

**Acceptance Criteria**:
- [x] Change applied at line 389
- [x] Tests still pass
- [x] Commit: "fix: add strict=True to zip() for safety (Subtask 3.1)"

---

### Subtask 3.2: Make data_version Configurable

**File**: `src/qe_tax_rag/data/builder.py`
**Location**: Lines 115-120 (hardcoded "2024.12")

**Change**: Add `data_version` parameter to build_from_file() method

**Acceptance Criteria**:
- [x] Parameter added with default value "2024.12"
- [x] Tests updated to use parameter
- [x] Commit: "feat: make data_version configurable in IndexBuilder (Subtask 3.2)"

---

## Testing Strategy

After each subtask:
1. Run unit tests: `uv run pytest tests/unit -v -m unit`
2. Verify pre-commit hooks pass: `uv run pre-commit run --all-files`
3. For integration changes (Subtask 1.4), run integration tests: `uv run pytest tests/integration -v -m integration`

Before marking PR as ready for review:
1. Run full test suite: `uv run pytest tests/ -v`
2. Manual smoke test: `uv run python scripts/cli.py pipeline-extraction --help`
3. Verify coverage: `uv run pytest tests/ --cov=src/qe_tax_rag --cov-report=html`

## Success Criteria

**PHASE 1 (CRITICAL)** - PR cannot merge without this:
- [x] All 15+ new tests pass
- [x] YAML loading path has >90% code coverage
- [x] RuleSet.to_database_chunks() has >95% code coverage
- [x] No test failures in CI/CD

**PHASE 2 (HIGH)** - Improves maintainability:
- [x] CLI code duplication reduced by ~90 LOC
- [x] Helper functions have clear, single responsibilities
- [x] Pipeline command logic is <50 LOC

**PHASE 3 (OPTIONAL)** - Nice to have:
- [x] Safety improvements applied
- [x] No regressions introduced

## References

- **Original Implementation Plan**: `DATA_MODEL_NORMALIZATION_PLAN.md`
- **Code Review Findings**: PR #38 description
- **Schema Documentation**: `src/qe_tax_rag/extraction/ca/schema.py` (RuleSet model)
- **Builder Documentation**: `src/qe_tax_rag/data/builder.py` (IndexBuilder class)
- **Existing Tests**: `tests/unit/test_builder.py` (lines 1-1176)
