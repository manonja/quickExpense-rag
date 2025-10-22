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


@pytest.fixture
def mock_gemini_client(mocker):  # type: ignore[no-untyped-def]
    """
    Mock Gemini API client for deterministic LLM parser testing.

    Returns pre-defined ExtractedRule objects based on the input file,
    avoiding network calls and ensuring test reproducibility.

    Args:
        mocker: pytest-mock fixture for patching

    Returns:
        Mock object for llm_parse function

    """
    from qe_tax_rag.extraction.ca.schema import (
        ApplicabilityType,
        ExpertSource,
        ExtractedRule,
    )

    def mock_llm_parse(
        html_path: str,
        cache_dir: Path | None = None,  # noqa: ARG001
    ) -> list[ExtractedRule]:
        """Mock implementation of llm_parse()."""
        # Determine which fixture is being parsed
        path = Path(html_path)

        if "simple_rule" in path.name:
            # Return single rule for simple fixture
            return [
                ExtractedRule(
                    rule_number=8523,
                    title="Meals and entertainment",
                    content="The maximum amount you can claim for food, beverages and entertainment expenses is 50% of the lesser of the following amounts:\n\nthe amount incurred for these expenses\nan amount that is reasonable in the circumstances\n\nWhen you claim expenses on this line, you will have to calculate the allowable part you can claim for business use.",
                    applies_to=[ApplicabilityType.BUSINESS],
                    source_citation="Line 8523",
                    chapter="Chapter 3 – Business Expenses",
                    section="Part 1 – Meals and Entertainment",
                    source_file=path.name,
                    expert_source=ExpertSource.LLM,
                    anchor_id="tocch3ln8523",
                    confidence_score=0.95,
                ),
            ]

        if "complex_rule" in path.name:
            # Return multiple rules for complex fixture
            return [
                ExtractedRule(
                    rule_number=8523,
                    title="Meals and entertainment",
                    content="You can deduct 50% of the cost of food, beverages, or entertainment.",
                    applies_to=[ApplicabilityType.BUSINESS],
                    source_citation="Line 8523",
                    chapter="Chapter 3 – Business Expenses",
                    section=None,
                    source_file=path.name,
                    expert_source=ExpertSource.LLM,
                    anchor_id="tocch3ln8523",
                    confidence_score=0.95,
                ),
                ExtractedRule(
                    rule_number=9270,
                    title="Motor vehicle expenses",
                    content="You can deduct motor vehicle expenses including fuel and maintenance.",
                    applies_to=[ApplicabilityType.BUSINESS, ApplicabilityType.FARMING],
                    source_citation="Line 9270",
                    chapter="Chapter 3 – Business Expenses",
                    section=None,
                    source_file=path.name,
                    expert_source=ExpertSource.LLM,
                    anchor_id="tocch3ln9270",
                    confidence_score=0.92,
                ),
                ExtractedRule(
                    rule_number=8000,
                    title="Utilities",
                    content="Deduct electricity, heating, and water expenses for fishing operations.",
                    applies_to=[ApplicabilityType.FISHING],
                    source_citation="Line 8000",
                    chapter="Chapter 3 – Business Expenses",
                    section=None,
                    source_file=path.name,
                    expert_source=ExpertSource.LLM,
                    anchor_id="tocch3ln8000",
                    confidence_score=0.88,
                ),
            ]

        if "malformed" in path.name:
            # Return empty list for malformed HTML (simulates parsing failure)
            return []

        # Default: return empty list
        return []

    # Patch the llm_parse function
    return mocker.patch(
        "qe_tax_rag.extraction.ca.orchestrator.llm_parse",
        side_effect=mock_llm_parse,
    )
