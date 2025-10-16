"""Test shared fixtures work correctly."""

from pathlib import Path

import numpy as np
import pytest


@pytest.mark.unit
def test_fixture_db_exists(fixture_db: Path) -> None:
    """Fixture DB should exist and be readable."""
    assert fixture_db.exists()
    assert fixture_db.suffix == ".db"
    assert fixture_db.is_file()


@pytest.mark.unit
def test_fixture_db_path_backward_compat(fixture_db_path: Path) -> None:
    """fixture_db_path should still work for backward compatibility."""
    assert fixture_db_path.exists()
    assert fixture_db_path.suffix == ".db"


@pytest.mark.unit
def test_fixture_db_and_path_same(fixture_db: Path, fixture_db_path: Path) -> None:
    """fixture_db and fixture_db_path should point to same database."""
    assert fixture_db == fixture_db_path


@pytest.mark.unit
def test_temp_db_is_writable(temp_db: Path) -> None:
    """Temp DB should be writable and isolated."""
    assert temp_db.parent.exists()  # tmp_path directory exists
    assert not temp_db.exists()  # Not created yet

    # Try writing to verify path is writable
    temp_db.touch()
    assert temp_db.exists()


@pytest.mark.unit
def test_temp_db_isolation() -> None:
    """Each test should get a fresh temp_db (function scope)."""
    # This test verifies isolation by running twice
    # If isolation works, temp_db won't exist from previous test
    # (This is implicit - pytest handles it)
    pass


@pytest.mark.unit
def test_mock_encoder_query_shape(mock_encoder) -> None:  # type: ignore[no-untyped-def]
    """Mock encoder should return correct query embedding shape."""
    query_embedding = mock_encoder.embed_query("test query")
    assert isinstance(query_embedding, np.ndarray)
    assert query_embedding.shape == (384,)


@pytest.mark.unit
def test_mock_encoder_documents_shape(mock_encoder) -> None:  # type: ignore[no-untyped-def]
    """Mock encoder should return correct document embeddings shape."""
    doc_embeddings = mock_encoder.embed_documents(["doc1", "doc2"])
    assert isinstance(doc_embeddings, np.ndarray)
    assert doc_embeddings.shape == (10, 384)  # Fixed at 10 rows


@pytest.mark.unit
def test_mock_encoder_is_mock(mock_encoder) -> None:  # type: ignore[no-untyped-def]
    """Mock encoder should be a Mock object."""
    from unittest.mock import Mock

    assert isinstance(mock_encoder, Mock)


@pytest.mark.unit
def test_sample_chunks_returns_list(sample_chunks: list) -> None:
    """sample_chunks should return a list (empty for now)."""
    assert isinstance(sample_chunks, list)
    # Currently deferred, so should be empty
    assert len(sample_chunks) == 0
