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


def test_embed_documents_returns_correct_shape(test_service: _EmbeddingService) -> None:
    """Verify document embedding returns correct shape."""
    import numpy as np

    texts = ["hello world", "foo bar", "test"]
    embeddings = test_service.embed_documents(texts)
    assert embeddings.shape == (3, 384)
    assert embeddings.dtype == np.float32


def test_embed_documents_empty_input_raises_error(
    test_service: _EmbeddingService,
) -> None:
    """Verify empty input raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        test_service.embed_documents([])


def test_embeddings_are_normalized(test_service: _EmbeddingService) -> None:
    """Verify embeddings are L2 normalized."""
    import numpy as np

    texts = ["test sentence"]
    embeddings = test_service.embed_documents(texts)
    norm = np.linalg.norm(embeddings[0])
    np.testing.assert_allclose(norm, 1.0, atol=1e-6)
