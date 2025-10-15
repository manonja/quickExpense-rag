"""Shared pytest fixtures for test suite."""

from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest


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
