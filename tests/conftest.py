"""Shared pytest fixtures for test suite."""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import numpy as np
import pytest


def normalize_yaml_for_golden_comparison(data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize YAML data for resilient golden file comparison.

    Removes volatile fields (timestamps, IDs) that change between runs
    but don't affect functional correctness. Makes golden file tests
    less brittle to non-breaking changes.

    Args:
        data: Loaded YAML data (typically RuleSet dict)

    Returns:
        Normalized copy with volatile fields removed

    """
    normalized = data.copy()
    # Remove timestamp - changes with every extraction but doesn't affect correctness
    normalized.pop("extraction_timestamp", None)
    return normalized


@pytest.fixture(scope="session")
def fixture_db_path() -> Path:
    """
    Return path to committed fixture database.

    The fixture database is a small, reproducible SQLite database with
    synthetic test data, tracked in git with LFS. It contains:
    - 12 test rows with diverse coverage
    - Deterministic embeddings (384-dim, seeded random)
    - Coverage across provinces, business types, expense types

    This fixture enables testing the runtime library without requiring
    the indexing pipeline or network access.

    Returns:
        Path to test_database.db

    """
    return Path(__file__).parent / "fixtures" / "test_database.db"


@pytest.fixture(scope="session")
def fixture_db(fixture_db_path: Path) -> Path:
    """
    Return path to committed fixture database (alias for fixture_db_path).

    This provides a shorter name for tests while maintaining backward
    compatibility with existing fixture_db_path fixture.

    Returns:
        Path to test_database.db

    """
    if not fixture_db_path.exists():
        pytest.fail(f"Fixture database not found: {fixture_db_path}")
    return fixture_db_path


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """
    Create temporary database path for mutation tests.

    Returns path to a non-existent database file in tmp_path.
    Tests should create/initialize this database as needed.
    Each test gets a fresh temporary directory (function scope).

    Use this for:
    - Tests that modify database state
    - Tests that need a clean database
    - Tests that create new databases

    Do NOT use this for read-only tests (use fixture_db instead).

    Returns:
        Path to temporary test.db (not created yet)

    """
    return tmp_path / "test.db"


@pytest.fixture(scope="session")
def mock_encoder() -> Mock:
    """
    Mock BGEEncoder for fast unit tests.

    Returns a mock encoder that produces zero embeddings with
    correct dimensions (384-dim for BGE-small-en-v1.5).

    Use this for tests that don't need real embeddings but need
    to verify embedding calls or mock embedding behavior.

    Configured methods:
    - embed_query(text) -> np.ndarray[384]
    - embed_documents(texts) -> np.ndarray[N, 384]

    Returns:
        Mock encoder with configured return values

    """
    encoder = Mock()
    encoder.embed_query.return_value = np.zeros(384)
    encoder.embed_documents.return_value = np.zeros((10, 384))
    return encoder


@pytest.fixture(scope="session")
def sample_chunks() -> list[dict]:
    """
    Load sample chunks from fixtures.

    Deferred: Only implement if parser tests require it.
    For now, return empty list.

    Returns:
        Empty list (to be implemented when needed)

    """
    return []


@pytest.fixture(scope="module")
def module_monkeypatch() -> pytest.MonkeyPatch:
    """
    Module-scoped monkeypatch fixture for settings tests.

    Allows setting environment variables once for an entire test module,
    useful for VCR tests that need API keys for client initialization.

    Returns:
        MonkeyPatch instance with module scope

    """
    mpatch = pytest.MonkeyPatch()
    yield mpatch
    mpatch.undo()


# ============================================================================
# Ticket 2 Fixtures: YAML → SQLite Conversion Testing
# ============================================================================


@pytest.fixture
def in_memory_db():
    """
    Fresh SQLite connection with full schema for each test.

    Creates an in-memory database with complete schema (rules, rules_fts,
    rules_vec, metadata, expense_types). Each test gets a clean database
    to ensure isolation.

    Use this for:
    - Testing DatabaseChunk insertion
    - Testing database constraints (UNIQUE, NOT NULL)
    - Integration tests for YAML → Database conversion

    Returns:
        sqlite3.Connection to in-memory database with initialized schema

    """
    import sqlite3

    from qe_tax_rag.data.schema import CREATE_TABLES_SQL, init_metadata

    conn = sqlite3.connect(":memory:")

    # Load sqlite-vec extension for vector search
    try:
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (AttributeError, ImportError):
        # Extension loading not supported or sqlite-vec not available
        pass

    # Create schema
    conn.executescript(CREATE_TABLES_SQL)
    init_metadata(conn, data_version="test-1.0", embedding_model="test-bge-small")

    yield conn
    conn.close()


@pytest.fixture
def source_files_mapping():
    """
    SourceFile mapping for test fixtures.

    Provides a dict mapping source file stems to SourceFile objects.
    Used by RuleSet.to_database_chunks() to look up source metadata.

    Mapping includes:
    - simple_rule: tests/fixtures/extraction/ca/simple_rule.html
    - complex_rule: tests/fixtures/extraction/ca/complex_rule.html
    - t4002-3: Real CRA document fixture

    Returns:
        dict[str, SourceFile]: Mapping of file stem to SourceFile

    """
    from qe_tax_rag.search.models import SourceFile

    return {
        "simple_rule": SourceFile(
            path="simple_rule.html",
            url="file://tests/fixtures/extraction/ca/simple_rule.html",
            hash="abc123simple",
        ),
        "complex_rule": SourceFile(
            path="complex_rule.html",
            url="file://tests/fixtures/extraction/ca/complex_rule.html",
            hash="abc123complex",
        ),
        "t4002-3": SourceFile(
            path="t4002-3.html",
            url="file://cra_documents/t4002-3.html",
            hash="abc123t4002",
        ),
    }


@pytest.fixture
def mock_embedding_service(monkeypatch):
    """
    Mock embedding service that returns constant 384-dim zero vectors.

    Patches _EmbeddingService.embed_documents() to return deterministic
    zero vectors instead of calling the real BGE model. This makes tests:
    - Fast (no model loading)
    - Deterministic (same output every time)
    - Isolated (no external dependencies)

    Use this for:
    - Unit tests for transformation logic
    - Integration tests that don't need real embeddings
    - Tests validating embedding dimensions

    The mock returns:
    - np.zeros(384, dtype=np.float32) for each input text
    - Correct shape: (len(texts), 384)

    Returns:
        None (patches via monkeypatch)

    """
    from qe_tax_rag.embeddings.encoder import _EmbeddingService

    def mock_embed_documents(self, texts):
        """Return zero vectors for all inputs."""
        return [np.zeros(384, dtype=np.float32) for _ in texts]

    monkeypatch.setattr(
        _EmbeddingService, "embed_documents", mock_embed_documents
    )


