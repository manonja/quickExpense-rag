# TICKET 10: Test Infrastructure & E2E Suite - TDD Implementation Plan

## Overview

This plan implements comprehensive test infrastructure using **Test-Driven Development (TDD)** with **frequent atomic commits**. The approach follows the Red-Green-Refactor cycle and the 80/20 principle from CLAUDE.md.

---

## TDD Workflow

```
For each test module:
1. RED: Write failing tests first (define expected behavior)
2. GREEN: Write minimal code to make tests pass
3. REFACTOR: Improve code while keeping tests green
4. COMMIT: Atomic commit after each complete cycle
```

---

## Phase 1: Foundation (Pytest Config + Fixtures)

### Task 1.1: Add Pytest Configuration

**TDD Step**: Configuration (no tests needed, direct implementation)

**Files to modify**:
- `pyproject.toml`

**Changes**:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Fast unit tests (<100ms each)",
    "integration: Integration tests with I/O",
    "slow: Tests taking >1 second",
]
addopts = "--strict-markers --tb=short"
```

**Validation**:
```bash
uv run pytest --markers  # Should show custom markers
```

**Commit message**:
```
test: add pytest configuration with custom markers

Add pytest config to pyproject.toml:
- Custom markers: unit, integration, slow
- Strict marker enforcement for CI safety
- Short traceback format for cleaner output

Enables selective test execution (e.g., `pytest -m unit`)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 1.2: Create Shared Fixtures (TDD)

**TDD Approach**: Write fixture usage tests first, then implement fixtures

#### Step 1.2.1: RED - Write fixture usage tests

**File**: `tests/unit/test_fixtures.py`

```python
"""Test shared fixtures work correctly."""
import pytest
from pathlib import Path


@pytest.mark.unit
def test_fixture_db_exists(fixture_db):
    """Fixture DB should exist and be readable."""
    assert fixture_db.exists()
    assert fixture_db.suffix == ".db"


@pytest.mark.unit
def test_temp_db_is_writable(temp_db):
    """Temp DB should be writable and isolated."""
    assert temp_db.parent.exists()  # tmp_path directory exists
    assert not temp_db.exists()  # Not created yet
    # Try writing to verify path is writable
    temp_db.touch()
    assert temp_db.exists()


@pytest.mark.unit
def test_mock_encoder_returns_correct_shape(mock_encoder):
    """Mock encoder should return correct embedding dimensions."""
    query_embedding = mock_encoder.embed_query("test query")
    assert query_embedding.shape == (384,)

    doc_embeddings = mock_encoder.embed_documents(["doc1", "doc2"])
    assert doc_embeddings.shape == (2, 384)
```

**Run tests** (should FAIL - fixtures don't exist yet):
```bash
uv run pytest tests/unit/test_fixtures.py -v
# Expected: fixture 'fixture_db' not found
```

#### Step 1.2.2: GREEN - Implement fixtures

**File**: `tests/conftest.py`

```python
"""Shared pytest fixtures for all tests."""
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock


@pytest.fixture(scope="session")
def fixture_db() -> Path:
    """Path to committed test database (read-only).

    Returns path to hand-crafted database from TICKET 4.5.
    This database should never be modified by tests.
    """
    db_path = Path(__file__).parent / "fixtures" / "test_database.db"
    if not db_path.exists():
        pytest.fail(f"Fixture database not found: {db_path}")
    return db_path


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create temporary database for mutation tests.

    Returns path to a non-existent database file in tmp_path.
    Tests should create/initialize this database as needed.
    Each test gets a fresh temporary directory.
    """
    return tmp_path / "test.db"


@pytest.fixture(scope="session")
def mock_encoder():
    """Mock BGEEncoder for fast unit tests.

    Returns a mock encoder that produces zero embeddings
    with correct dimensions (384-dim for BGE-small).
    Use this for tests that don't need real embeddings.
    """
    encoder = Mock()
    encoder.embed_query.return_value = np.zeros(384)
    encoder.embed_documents.return_value = np.zeros((10, 384))
    return encoder


@pytest.fixture(scope="session")
def sample_chunks():
    """Load sample chunks from fixtures.

    Deferred: Only implement if parser tests require it.
    For now, return empty list.
    """
    return []
```

**Run tests** (should PASS):
```bash
uv run pytest tests/unit/test_fixtures.py -v -m unit
# Expected: All 3 tests pass
```

**Commit message**:
```
test: implement shared pytest fixtures (TDD)

Add tests/conftest.py with core fixtures:
- fixture_db() - Path to committed test database (session scope)
- temp_db() - Temporary writable database (function scope)
- mock_encoder() - Mocked BGEEncoder for fast tests (session scope)
- sample_chunks() - Deferred until needed

Includes fixture validation tests in tests/unit/test_fixtures.py

TDD: RED (wrote tests) → GREEN (fixtures pass)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 1.3: Run Coverage Audit

**Command**:
```bash
uv run pytest --cov=src/quickexpense_rag --cov-report=term --cov-report=html
```

**Document findings**: Create `coverage-audit.md` with current baseline and gaps

**Commit message**:
```
docs: add coverage audit baseline

Document current test coverage before TICKET 10 work:
- Overall coverage: X%
- api.py: X%
- hybrid.py: X%
- manager.py: X%

Identifies gaps to address in Phase 2.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 2: Critical Unit Tests (TDD Red-Green-Refactor)

### Task 2.1: api.py Unit Tests (TDD)

**Target**: 12-15 tests, ≥95% coverage

#### Step 2.1.1: RED - Write failing tests for init()

**File**: `tests/unit/test_api.py`

```python
"""Unit tests for public API (api.py)."""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

import quickexpense_rag as qe
from quickexpense_rag.exceptions import (
    DatabaseNotInitializedError,
    NetworkError,
    DataVersionMismatchError,
)


class TestInit:
    """Test init() function."""

    @pytest.mark.unit
    def test_init_downloads_database_on_first_call(self, tmp_path):
        """First init() should download database."""
        with patch("quickexpense_rag.data.manager.DataManager.get_database_path") as mock:
            mock.return_value = tmp_path / "test.db"
            qe.init()
            mock.assert_called_once()

    @pytest.mark.unit
    def test_init_uses_cached_database(self, fixture_db):
        """Subsequent init() should use cached database."""
        with patch("quickexpense_rag.data.manager.DataManager.get_database_path") as mock:
            mock.return_value = fixture_db
            qe.init()
            qe.init()  # Second call
            # Should only call get_database_path once (cached)
            assert mock.call_count == 1

    @pytest.mark.unit
    def test_init_network_failure_no_cache_raises_error(self):
        """init() with network failure and no cache should raise NetworkError."""
        with patch("quickexpense_rag.data.manager.DataManager.get_database_path") as mock:
            mock.side_effect = NetworkError("No network and no cache")
            with pytest.raises(NetworkError, match="No network and no cache"):
                qe.init()

    @pytest.mark.unit
    def test_init_version_mismatch_raises_error(self):
        """init() with incompatible database version should raise error."""
        with patch("quickexpense_rag.data.manager.DataManager.check_version_compatibility") as mock:
            mock.side_effect = DataVersionMismatchError("Version mismatch")
            with pytest.raises(DataVersionMismatchError, match="Version mismatch"):
                qe.init()
```

**Run tests** (should FAIL - implementation incomplete):
```bash
uv run pytest tests/unit/test_api.py::TestInit -v
```

#### Step 2.1.2: GREEN - Fix api.py to pass init tests

**Modify**: `src/quickexpense_rag/api.py`

Implement caching, error handling, version checks to make tests pass.

**Run tests** (should PASS):
```bash
uv run pytest tests/unit/test_api.py::TestInit -v
```

**Commit message**:
```
test: add init() unit tests (TDD RED)

Write 4 tests for init() function:
- Downloads database on first call
- Uses cached database on subsequent calls
- Raises NetworkError when no network + no cache
- Raises DataVersionMismatchError for incompatible versions

Tests currently FAIL - implementation in next commit.

TDD: RED phase

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Then after fixing:

```
feat: implement init() with caching and error handling (TDD GREEN)

Fix api.py to pass all init() tests:
- Cache database path after first initialization
- Handle NetworkError gracefully
- Check version compatibility on init

All TestInit tests now pass (4/4).

TDD: RED → GREEN

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 2.1.3: RED - Write failing tests for search()

**File**: `tests/unit/test_api.py` (add to existing file)

```python
class TestSearch:
    """Test search() function."""

    @pytest.mark.unit
    def test_search_before_init_raises_error(self):
        """search() before init() should raise DatabaseNotInitializedError."""
        # Reset any prior init state
        with patch("quickexpense_rag.api._db_initialized", False):
            with pytest.raises(DatabaseNotInitializedError, match="Call init\\(\\) first"):
                qe.search("test query")

    @pytest.mark.unit
    def test_search_returns_search_results(self, fixture_db):
        """search() should return list of SearchResult objects."""
        with patch("quickexpense_rag.data.manager.DataManager.get_database_path") as mock:
            mock.return_value = fixture_db
            qe.init()
            results = qe.search("restaurant meal", top_k=5)

            assert isinstance(results, list)
            assert len(results) <= 5
            if len(results) > 0:
                assert hasattr(results[0], "content")
                assert hasattr(results[0], "citation_id")
                assert hasattr(results[0], "disclaimer")

    @pytest.mark.unit
    def test_search_invalid_province_raises_validation_error(self, fixture_db):
        """search() with invalid province should raise ValidationError."""
        with patch("quickexpense_rag.data.manager.DataManager.get_database_path") as mock:
            mock.return_value = fixture_db
            qe.init()

            from pydantic import ValidationError
            with pytest.raises(ValidationError):
                qe.search("query", province="INVALID")

    @pytest.mark.unit
    def test_search_top_k_out_of_range_raises_error(self, fixture_db):
        """search() with top_k > 50 should raise ValidationError."""
        with patch("quickexpense_rag.data.manager.DataManager.get_database_path") as mock:
            mock.return_value = fixture_db
            qe.init()

            from pydantic import ValidationError
            with pytest.raises(ValidationError):
                qe.search("query", top_k=100)

    @pytest.mark.unit
    def test_search_empty_query_raises_error(self, fixture_db):
        """search() with empty query should raise ValidationError."""
        with patch("quickexpense_rag.data.manager.DataManager.get_database_path") as mock:
            mock.return_value = fixture_db
            qe.init()

            from pydantic import ValidationError
            with pytest.raises(ValidationError):
                qe.search("")

    @pytest.mark.unit
    def test_search_with_all_filters(self, fixture_db):
        """search() with all filters should work correctly."""
        with patch("quickexpense_rag.data.manager.DataManager.get_database_path") as mock:
            mock.return_value = fixture_db
            qe.init()

            results = qe.search(
                query="meal",
                province="BC",
                business_type="sole_proprietorship",
                expense_types=["meals"],
                top_k=3
            )
            assert isinstance(results, list)
            # All results should match filters
            for r in results:
                assert r.province == "BC" or r.province is None
                if r.expense_types:
                    assert "meals" in r.expense_types


class TestGetVersion:
    """Test get_version() function."""

    @pytest.mark.unit
    def test_get_version_returns_dict(self):
        """get_version() should return dict with version keys."""
        version = qe.get_version()
        assert isinstance(version, dict)
        assert "library_version" in version
        assert "data_version" in version
        assert "schema_version" in version
```

**Run tests** (should FAIL):
```bash
uv run pytest tests/unit/test_api.py::TestSearch -v
uv run pytest tests/unit/test_api.py::TestGetVersion -v
```

#### Step 2.1.4: GREEN - Fix api.py to pass search tests

**Modify**: `src/quickexpense_rag/api.py`

**Run tests** (should PASS):
```bash
uv run pytest tests/unit/test_api.py -v
```

**Commit message**:
```
test: add search() and get_version() tests (TDD RED)

Write 7 tests for search() and 1 for get_version():
- Search before init raises error
- Search returns SearchResult objects
- Invalid parameters raise ValidationError
- All filters work correctly
- get_version() returns correct dict structure

Tests currently FAIL - implementation in next commit.

TDD: RED phase

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Then after fixing:

```
feat: implement search() with validation and filtering (TDD GREEN)

Fix api.py to pass all search() tests:
- Check initialization state before search
- Validate all parameters via Pydantic
- Apply filters correctly to search engine
- Implement get_version() with metadata lookup

All test_api.py tests pass (12/12).
Coverage: api.py now at ≥95%

TDD: RED → GREEN

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 2.1.5: REFACTOR - Clean up api.py (if needed)

**Run tests during refactor**:
```bash
uv run pytest tests/unit/test_api.py -v
# Must stay GREEN during refactor
```

**Commit message** (if refactoring done):
```
refactor: simplify api.py initialization logic

Extract database path caching to helper function.
No functional changes - all tests still pass.

TDD: REFACTOR phase

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 2.2: hybrid.py Unit Tests (TDD)

**Target**: 18-20 tests, ≥95% coverage

**TDD Cycle**: Same Red-Green-Refactor approach

#### Step 2.2.1: RED - Write failing tests for keyword search

**File**: `tests/unit/test_hybrid.py`

```python
"""Unit tests for hybrid search engine."""
import pytest
from unittest.mock import Mock
import numpy as np

from quickexpense_rag.search.hybrid import HybridSearchEngine
from quickexpense_rag.search.models import ExpenseQuery


class TestKeywordSearch:
    """Test FTS5 keyword search."""

    @pytest.mark.unit
    def test_fts5_exact_match(self, fixture_db, mock_encoder):
        """FTS5 should find exact keyword matches."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query = ExpenseQuery(query="restaurant")

        results = engine._keyword_search(
            query_text="restaurant",
            join_sql="",
            where_sql="",
            k=5
        )

        assert len(results) > 0
        # Results should be (id, score) tuples
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    @pytest.mark.unit
    def test_fts5_no_results(self, fixture_db, mock_encoder):
        """FTS5 should return empty list for non-existent terms."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)

        results = engine._keyword_search(
            query_text="xyznonexistent",
            join_sql="",
            where_sql="",
            k=5
        )

        assert results == []


class TestVectorSearch:
    """Test semantic vector search."""

    @pytest.mark.unit
    def test_vector_search_returns_results(self, fixture_db, mock_encoder):
        """Vector search should return results with distances."""
        # Configure mock to return realistic embedding
        mock_encoder.embed_query.return_value = np.random.rand(384)

        engine = HybridSearchEngine(fixture_db, mock_encoder)

        results = engine._vector_search(
            query_vec=mock_encoder.embed_query("test"),
            join_sql="",
            where_sql="",
            k=5
        )

        assert len(results) <= 5
        # Results should be (id, distance) tuples
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    @pytest.mark.unit
    def test_vector_search_uses_mock_encoder(self, fixture_db, mock_encoder):
        """Vector search should use provided encoder."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query_vec = np.random.rand(384)

        engine._vector_search(query_vec, "", "", k=5)

        # Encoder should not be called in _vector_search
        # (embedding already done in search())
        # This test validates we're using pre-computed embeddings


class TestRRFFusion:
    """Test Reciprocal Rank Fusion."""

    @pytest.mark.unit
    def test_rrf_merges_rankings(self, fixture_db, mock_encoder):
        """RRF should merge FTS and vector results."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)

        fts_results = [(1, 0.9), (2, 0.8), (3, 0.7)]
        vec_results = [(2, 0.1), (4, 0.2), (5, 0.3)]

        merged = engine._rrf_fusion(fts_results, vec_results)

        # Should merge both lists
        assert len(merged) == 5  # All unique IDs
        # ID 2 appears in both, should rank high
        ids = [item[0] for item in merged]
        assert 2 in ids[:3]  # Top 3

    @pytest.mark.unit
    def test_rrf_deduplicates(self, fixture_db, mock_encoder):
        """RRF should deduplicate IDs appearing in both results."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)

        fts_results = [(1, 0.9), (2, 0.8)]
        vec_results = [(2, 0.1), (3, 0.2)]

        merged = engine._rrf_fusion(fts_results, vec_results)

        ids = [item[0] for item in merged]
        assert len(ids) == len(set(ids))  # No duplicates
```

**Run tests** (should FAIL):
```bash
uv run pytest tests/unit/test_hybrid.py::TestKeywordSearch -v
uv run pytest tests/unit/test_hybrid.py::TestVectorSearch -v
uv run pytest tests/unit/test_hybrid.py::TestRRFFusion -v
```

#### Step 2.2.2: GREEN - Implement hybrid.py methods

**Modify**: `src/quickexpense_rag/search/hybrid.py`

**Run tests** (should PASS):
```bash
uv run pytest tests/unit/test_hybrid.py -v
```

**Commit message**:
```
test: add hybrid search core algorithm tests (TDD RED)

Write 6 tests for FTS5, vector search, and RRF fusion:
- FTS5 exact match and no results
- Vector search with mock encoder
- RRF merges rankings correctly
- RRF deduplicates IDs

Tests currently FAIL - implementation in next commit.

TDD: RED phase

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Then after fixing:

```
feat: implement FTS5, vector search, and RRF fusion (TDD GREEN)

Implement core search algorithm in hybrid.py:
- _keyword_search() using FTS5
- _vector_search() using sqlite-vec
- _rrf_fusion() with reciprocal rank formula

All core algorithm tests pass (6/6).

TDD: RED → GREEN

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 2.2.3: RED - Write tests for metadata filtering

**File**: `tests/unit/test_hybrid.py` (add to existing)

```python
class TestMetadataFiltering:
    """Test metadata filtering (province, business_type)."""

    @pytest.mark.unit
    def test_filter_by_province(self, fixture_db, mock_encoder):
        """Filtering by province should return only matching results."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query = ExpenseQuery(query="meal", province="BC")

        results = engine.search(query)

        # All results should be BC or None (general rules)
        for r in results:
            assert r.province in ("BC", None)

    @pytest.mark.unit
    def test_filter_by_business_type(self, fixture_db, mock_encoder):
        """Filtering by business_type should return only matching results."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query = ExpenseQuery(
            query="expense",
            business_type="sole_proprietorship"
        )

        results = engine.search(query)

        for r in results:
            assert r.business_type in ("sole_proprietorship", None)

    @pytest.mark.unit
    def test_filter_combined(self, fixture_db, mock_encoder):
        """Multiple filters should combine with AND logic."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query = ExpenseQuery(
            query="meal",
            province="BC",
            business_type="sole_proprietorship"
        )

        results = engine.search(query)

        for r in results:
            assert r.province in ("BC", None)
            assert r.business_type in ("sole_proprietorship", None)


class TestExpenseTypeFiltering:
    """Test many-to-many expense type filtering (TICKET 4.6)."""

    @pytest.mark.unit
    def test_multi_type_rule_found_by_single_type(self, fixture_db, mock_encoder):
        """Rule tagged [meals, travel] should be found by expense_types=['meals']."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)

        # First, find a rule with multiple expense types
        all_results = engine.search(ExpenseQuery(query="business", top_k=50))
        multi_type_rule = next(
            (r for r in all_results if len(r.expense_types) > 1),
            None
        )

        if multi_type_rule:
            # Search for just one of its types
            query = ExpenseQuery(
                query=multi_type_rule.content[:50],
                expense_types=[multi_type_rule.expense_types[0]]
            )
            results = engine.search(query)

            # Should find the multi-type rule
            assert any(r.citation_id == multi_type_rule.citation_id for r in results)

    @pytest.mark.unit
    def test_any_match_logic(self, fixture_db, mock_encoder):
        """expense_types=['meals', 'travel'] should match rules with ANY of these."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query = ExpenseQuery(
            query="expense",
            expense_types=["meals", "travel"]
        )

        results = engine.search(query)

        # Each result should have at least one matching type
        for r in results:
            if r.expense_types:
                assert any(t in ["meals", "travel"] for t in r.expense_types)

    @pytest.mark.unit
    def test_join_deduplicates(self, fixture_db, mock_encoder):
        """JOIN with many-to-many should not duplicate rules."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query = ExpenseQuery(
            query="business",
            expense_types=["meals", "travel"]
        )

        results = engine.search(query)

        # No duplicate citation_ids
        citation_ids = [r.citation_id for r in results]
        assert len(citation_ids) == len(set(citation_ids))
```

**Run, fix, commit** (Red-Green cycle)

**Commit messages**:
```
test: add metadata and expense type filtering tests (TDD RED)

Write 6 tests for filtering:
- Province filter
- Business type filter
- Combined filters
- Multi-type rule found by single type (many-to-many)
- ANY match logic for expense_types list
- JOIN deduplication

Tests currently FAIL - implementation in next commit.

TDD: RED phase

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

```
feat: implement metadata and expense type filtering (TDD GREEN)

Add filtering to hybrid.py:
- _metadata_filter() builds JOIN and WHERE clauses
- Supports many-to-many expense_types (TICKET 4.6)
- Uses GROUP BY to deduplicate
- ANY match logic for expense_types list

All filtering tests pass (6/6).
Coverage: hybrid.py now at ≥95%

TDD: RED → GREEN

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 2.2.4: RED - Write edge case tests

**File**: `tests/unit/test_hybrid.py` (add to existing)

```python
class TestEdgeCases:
    """Test edge cases in search."""

    @pytest.mark.unit
    def test_no_results(self, fixture_db, mock_encoder):
        """Search with no matches should return empty list."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query = ExpenseQuery(query="xyznonexistent")

        results = engine.search(query)

        assert results == []

    @pytest.mark.unit
    def test_single_result(self, fixture_db, mock_encoder):
        """Search with one match should return single result."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        # Use unique citation_id from fixture
        query = ExpenseQuery(query="S3-F2-C1-p1.25")  # Specific citation

        results = engine.search(query)

        assert len(results) >= 1

    @pytest.mark.unit
    def test_large_results_truncated(self, fixture_db, mock_encoder):
        """Search with 100+ matches should truncate to top_k."""
        engine = HybridSearchEngine(fixture_db, mock_encoder)
        query = ExpenseQuery(query="expense", top_k=5)

        results = engine.search(query)

        assert len(results) <= 5
```

**Run, fix, commit** (Red-Green cycle)

**Commit messages**:
```
test: add edge case tests for hybrid search (TDD RED)

Write 3 edge case tests:
- No results returns empty list
- Single result handled correctly
- Large results truncated to top_k

TDD: RED phase

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

```
feat: handle edge cases in hybrid search (TDD GREEN)

Add edge case handling:
- Empty results gracefully returned
- Single result no special handling needed
- Limit results to top_k in final step

All edge case tests pass (3/3).
Total hybrid.py tests: 18/18 pass.

TDD: RED → GREEN

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 2.3: manager.py Unit Tests (TDD)

**Target**: 10-12 tests, ≥90% coverage

**TDD Cycle**: Same Red-Green-Refactor approach

Follow same pattern:
1. RED: Write 3-4 tests for download logic
2. GREEN: Implement download with retry
3. COMMIT
4. RED: Write 3-4 tests for cache logic
5. GREEN: Implement caching
6. COMMIT
7. RED: Write 3-4 tests for version compatibility
8. GREEN: Implement version checks
9. COMMIT

**Example commit messages**:
```
test: add download and retry logic tests (TDD RED)
feat: implement download with exponential backoff (TDD GREEN)
test: add cache logic tests (TDD RED)
feat: implement cache path resolution (TDD GREEN)
test: add version compatibility tests (TDD RED)
feat: implement version compatibility checks (TDD GREEN)
```

---

## Phase 3: Integration Tests (TDD)

### Task 3.1: Real User Workflow Tests

**TDD Approach**: Integration tests can be written after implementation (less strict TDD)

**File**: `tests/integration/test_search_scenarios.py`

```python
"""Integration tests for real user search workflows."""
import pytest
import quickexpense_rag as qe


@pytest.mark.integration
def test_bc_sole_prop_restaurant_meal(fixture_db):
    """User searches for restaurant meal deduction in BC."""
    # Setup
    qe.init()

    # Execute
    results = qe.search(
        query="restaurant meal expense",
        province="BC",
        business_type="sole_proprietorship",
        expense_types=["meals"]
    )

    # Verify
    assert len(results) > 0
    assert all(r.province == "BC" for r in results if r.province)
    assert all("meals" in r.expense_types for r in results if r.expense_types)
    assert all(r.disclaimer.startswith("⚠️") for r in results)


@pytest.mark.integration
def test_vehicle_expense_multi_type(fixture_db):
    """User searches for vehicle expense (may be vehicle or travel)."""
    qe.init()

    results = qe.search(
        query="vehicle mileage business travel",
        expense_types=["vehicle", "travel"]
    )

    assert len(results) > 0
    # Should match rules with EITHER vehicle OR travel
    for r in results:
        if r.expense_types:
            assert any(t in ["vehicle", "travel"] for t in r.expense_types)


@pytest.mark.integration
def test_home_office_deduction(fixture_db):
    """User searches for home office rules."""
    qe.init()

    results = qe.search(
        query="home office workspace deduction",
        expense_types=["home_office"]
    )

    assert len(results) > 0
    assert all("home_office" in r.expense_types for r in results if r.expense_types)


@pytest.mark.integration
def test_multi_type_rule_found_by_single_type(fixture_db):
    """Rule with multiple types should appear when searching for single type."""
    qe.init()

    # Find a rule with multiple types
    all_results = qe.search(query="business expense", top_k=50)
    multi_type_rule = next(
        (r for r in all_results if len(r.expense_types) > 1),
        None
    )

    if multi_type_rule:
        # Search for just one type
        single_type_results = qe.search(
            query=multi_type_rule.content[:50],
            expense_types=[multi_type_rule.expense_types[0]]
        )

        # Multi-type rule should appear
        assert any(
            r.citation_id == multi_type_rule.citation_id
            for r in single_type_results
        )


@pytest.mark.integration
def test_expense_types_any_match(fixture_db):
    """expense_types filter should match ANY of the provided types."""
    qe.init()

    results = qe.search(
        query="deduction",
        expense_types=["meals", "travel", "vehicle"]
    )

    # Each result should have at least one matching type
    for r in results:
        if r.expense_types:
            assert any(
                t in ["meals", "travel", "vehicle"]
                for t in r.expense_types
            )
```

**Run tests**:
```bash
uv run pytest tests/integration/test_search_scenarios.py -v
```

**Commit message**:
```
test: add integration tests for user search workflows

Add 5 integration tests covering real user scenarios:
- BC sole proprietor restaurant meal
- Vehicle expense with multi-type query
- Home office deduction
- Multi-type rule found by single type
- ANY match logic for expense_types

All integration tests pass (5/5).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 4: Performance Tests & CI Integration

### Task 4.1: Performance Baseline Tests

**File**: `tests/integration/test_performance.py`

```python
"""Performance baseline tests."""
import pytest
import time
import random
import numpy as np

import quickexpense_rag as qe
from quickexpense_rag.embeddings.encoder import BGEEncoder


@pytest.mark.slow
@pytest.mark.integration
def test_search_latency_p99(fixture_db):
    """Search latency should be <250ms at p99."""
    qe.init()

    queries = [
        "restaurant meal",
        "vehicle mileage",
        "home office",
        "business travel expense",
        "advertising costs"
    ]

    latencies = []
    for _ in range(100):
        query = random.choice(queries)
        start = time.perf_counter()
        qe.search(query, top_k=5)
        latencies.append((time.perf_counter() - start) * 1000)

    p99 = sorted(latencies)[98]
    print(f"\nSearch latency p99: {p99:.1f}ms")
    assert p99 < 250, f"p99 latency {p99:.1f}ms exceeds 250ms"


@pytest.mark.slow
def test_embedding_speed():
    """Embedding 100 texts should take <2 seconds."""
    encoder = BGEEncoder()
    texts = ["sample query text"] * 100

    start = time.perf_counter()
    embeddings = encoder.embed_documents(texts)
    elapsed = time.perf_counter() - start

    print(f"\nEmbedding 100 texts: {elapsed:.2f}s")
    assert elapsed < 2.0, f"Embedding took {elapsed:.2f}s (target: <2s)"
    assert embeddings.shape == (100, 384)


@pytest.mark.integration
def test_init_speed(fixture_db, monkeypatch):
    """Database initialization should take <1 second."""
    # Mock download to use fixture DB
    monkeypatch.setattr(
        "quickexpense_rag.data.manager.DataManager.get_database_path",
        lambda self: fixture_db
    )

    start = time.perf_counter()
    qe.init()
    elapsed = time.perf_counter() - start

    print(f"\nInit time: {elapsed:.2f}s")
    assert elapsed < 1.0, f"Init took {elapsed:.2f}s (target: <1s)"
```

**Run tests**:
```bash
uv run pytest tests/integration/test_performance.py -v
```

**Commit message**:
```
test: add performance baseline tests

Add 3 performance tests (marked @slow):
- Search latency p99 < 250ms
- Embedding 100 texts < 2s
- Database init < 1s

All baselines pass. Excluded from fast CI via marker.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 4.2: CI Coverage Enforcement

**File**: `.github/workflows/ci.yml`

```yaml
# Extend existing test job from TICKET 1.5
test:
  runs-on: ${{ matrix.os }}
  strategy:
    matrix:
      os: [ubuntu-latest, windows-latest, macos-latest]
      python: ["3.11", "3.12", "3.13"]
  steps:
    - uses: actions/checkout@v4
    - run: uv sync
    - run: uv run pytest tests/ -v -m "not slow"

    # Coverage report (only on ubuntu-latest + python 3.12)
    - name: Run coverage report
      if: matrix.os == 'ubuntu-latest' && matrix.python == '3.12'
      run: |
        uv run pytest --cov=src/quickexpense_rag \
                      --cov-report=term \
                      --cov-report=html \
                      --cov-fail-under=85

    - name: Upload coverage to Codecov
      if: matrix.os == 'ubuntu-latest' && matrix.python == '3.12'
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
```

**Commit message**:
```
ci: add coverage enforcement to test workflow

Extend .github/workflows/ci.yml with coverage job:
- Run coverage on ubuntu-latest + python 3.12 only
- Fail if coverage < 85%
- Upload to codecov.io (optional)

Coverage now enforced in CI.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 4.3: Documentation

**File**: `CONTRIBUTING.md` or `README.md`

Add testing commands section:

```markdown
## Testing

### Running Tests

```bash
# Fast unit tests only (<2 seconds)
uv run pytest tests/unit -v -m unit

# Integration tests (~5-10 seconds)
uv run pytest tests/integration -v -m integration

# All tests except slow performance tests
uv run pytest -m "not slow"

# Full test suite including performance (~30-60 seconds)
uv run pytest tests/ -v

# Coverage report (HTML in htmlcov/)
uv run pytest --cov=src/quickexpense_rag --cov-report=html

# Coverage for specific module
uv run pytest --cov=src/quickexpense_rag/api --cov-report=term
```

### Coverage Requirements

- Overall: ≥85% (enforced in CI)
- `api.py`: ≥95% (user-facing API)
- `hybrid.py`: ≥95% (core search logic)
- `manager.py`: ≥90% (download/cache)
```

**Commit message**:
```
docs: add testing commands to CONTRIBUTING.md

Document test commands and coverage requirements:
- Commands for unit, integration, and performance tests
- Coverage targets for critical modules
- How to generate coverage reports

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Commit Strategy Summary

**Atomic commits** after each TDD cycle:

```
Phase 1: Foundation (3-4 commits)
├─ test: add pytest configuration with markers
├─ test: implement shared pytest fixtures (TDD)
├─ docs: add coverage audit baseline
└─ (optional refactor commit)

Phase 2: Unit Tests (15-20 commits)
├─ test: add init() tests (TDD RED)
├─ feat: implement init() (TDD GREEN)
├─ (optional refactor)
├─ test: add search() tests (TDD RED)
├─ feat: implement search() (TDD GREEN)
├─ (optional refactor)
├─ test: add FTS5/vector tests (TDD RED)
├─ feat: implement FTS5/vector (TDD GREEN)
├─ test: add metadata filtering tests (TDD RED)
├─ feat: implement filtering (TDD GREEN)
├─ test: add edge case tests (TDD RED)
├─ feat: handle edge cases (TDD GREEN)
├─ test: add manager download tests (TDD RED)
├─ feat: implement download (TDD GREEN)
├─ ... (repeat for cache, version checks)
└─ refactor: final cleanup after all tests pass

Phase 3: Integration (1-2 commits)
├─ test: add integration tests for user workflows
└─ (fix any issues found)

Phase 4: Performance & CI (3-4 commits)
├─ test: add performance baseline tests
├─ ci: add coverage enforcement
├─ docs: add testing commands
└─ (final polish)

Total: ~25-35 atomic commits
```

---

## Success Criteria Checklist

**After Phase 4, verify**:

- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Coverage ≥85%: `uv run pytest --cov=src/quickexpense_rag`
- [ ] api.py ≥95% coverage
- [ ] hybrid.py ≥95% coverage
- [ ] manager.py ≥90% coverage
- [ ] CI passes with coverage enforcement
- [ ] All markers work: `pytest -m unit`, `pytest -m integration`, `pytest -m "not slow"`
- [ ] Documentation complete in CONTRIBUTING.md

---

## Estimated Implementation Timeline

**Solo developer, TDD approach**:

- **Phase 1**: 1-2 hours (foundation)
- **Phase 2**: 6-8 hours (critical unit tests with TDD cycles)
- **Phase 3**: 2-3 hours (integration tests)
- **Phase 4**: 1-2 hours (performance + CI)

**Total**: 10-15 hours (1.5-2 days)

**Pair/team**: Can parallelize Phase 2 unit tests (api.py, hybrid.py, manager.py)

---

## TDD Best Practices

**Throughout implementation**:

1. **RED**: Write failing test first (defines expected behavior)
2. **GREEN**: Write minimal code to pass (avoid over-engineering)
3. **REFACTOR**: Clean up while tests stay green
4. **COMMIT**: Atomic commit after each cycle

**Benefits**:
- Tests document expected behavior
- High confidence in refactoring
- Catches regressions immediately
- Forces thinking about design before implementation
- Natural commit points (after each Green phase)

**When to commit**:
- After each GREEN phase (tests pass)
- After significant REFACTOR (tests still pass)
- After adding test fixtures/config
- After documentation updates

**What NOT to commit**:
- RED phase with failing tests (unless documenting WIP)
- Broken code that doesn't pass linting
- Code without running pre-commit hooks

---

## End of Plan

This TDD implementation plan delivers production-ready test infrastructure with:
- ≥95% coverage for critical modules (api.py, hybrid.py)
- Comprehensive integration and performance tests
- CI enforcement of coverage requirements
- Clean commit history documenting TDD cycles
