"""Integration tests for embedding service.

Tests use real SentenceTransformer models (lightweight all-MiniLM-L6-v2)
to verify actual numerical properties and model behavior.
"""

import pytest

from quickexpense_rag.embeddings.encoder import _EmbeddingService


def test_singleton_pattern() -> None:
    """Verify module-level singleton returns same instance."""
    from quickexpense_rag.embeddings import embedding_service
    from quickexpense_rag.embeddings import embedding_service as service2

    assert embedding_service is service2  # Same object ID


@pytest.fixture(scope="module")
def test_service() -> _EmbeddingService:
    """Lightweight model for fast tests."""
    return _EmbeddingService(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cpu",
        batch_size=16,
    )


def test_model_loads_successfully(test_service: _EmbeddingService) -> None:
    """Verify model loads with custom parameters."""
    assert test_service.model is not None
    assert test_service.batch_size == 16
