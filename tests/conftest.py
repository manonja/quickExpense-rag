"""Shared pytest fixtures for test suite."""

from pathlib import Path

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
