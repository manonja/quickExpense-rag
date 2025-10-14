"""
Integration tests for embedding service.

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


def test_embed_query_returns_correct_shape(test_service: _EmbeddingService) -> None:
    """Verify query embedding returns correct shape."""
    import numpy as np

    query = "search query"
    embedding = test_service.embed_query(query)
    assert embedding.shape == (384,)  # 1D array for single query
    assert embedding.dtype == np.float32


def test_embed_query_empty_raises_error(test_service: _EmbeddingService) -> None:
    """Verify empty query raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        test_service.embed_query("")


def test_embed_query_whitespace_raises_error(test_service: _EmbeddingService) -> None:
    """Verify whitespace-only query raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        test_service.embed_query("   ")


def test_query_embedding_differs_from_document(test_service: _EmbeddingService) -> None:
    """Query prefix should change the embedding."""
    import numpy as np

    text = "restaurant expense"

    # Embed as document
    doc_emb = test_service.embed_documents([text])[0]

    # Embed as query (with instruction prefix)
    query_emb = test_service.embed_query(text)

    # Should be different due to prefix
    similarity = np.dot(doc_emb, query_emb)
    assert similarity < 1.0  # Not identical
    assert similarity > 0.6  # But still similar (relaxed threshold)


def test_batch_encoding_matches_sequential(test_service: _EmbeddingService) -> None:
    """
    Verify batch processing gives same results as sequential.

    This test is critical for ensuring consistency: users should get
    identical embeddings whether they process texts one-by-one or in batches.
    SentenceTransformer guarantees this behavior, but we validate it explicitly.
    """
    import numpy as np

    texts = ["text one", "text two", "text three"]

    # Batch encoding
    batch_emb = test_service.embed_documents(texts)

    # Sequential encoding
    sequential_emb = np.vstack(
        [test_service.embed_documents([t]) for t in texts]
    )

    # Should be numerically identical (within float tolerance)
    np.testing.assert_allclose(batch_emb, sequential_emb, atol=1e-5)


def test_similar_texts_have_high_similarity(test_service: _EmbeddingService) -> None:
    """
    Verify semantically similar texts have high cosine similarity.

    This test validates that the embedding model actually works correctly
    by checking that semantically related words produce similar embeddings
    while unrelated words produce dissimilar embeddings.
    """
    import numpy as np

    text1 = "cat"
    text2 = "kitten"
    text3 = "airplane"

    emb1 = test_service.embed_documents([text1])[0]
    emb2 = test_service.embed_documents([text2])[0]
    emb3 = test_service.embed_documents([text3])[0]

    # Cat and kitten should be similar
    similarity_similar = np.dot(emb1, emb2)
    assert similarity_similar > 0.5

    # Cat and airplane should be dissimilar
    similarity_dissimilar = np.dot(emb1, emb3)
    assert similarity_dissimilar < similarity_similar


def test_cuda_fallback_when_unavailable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Verify graceful fallback to CPU when CUDA unavailable.

    Tests that requesting CUDA on a CPU-only system:
    1. Logs a warning about the fallback
    2. Successfully falls back to CPU device
    3. Still produces valid embeddings

    This test will be skipped on systems where CUDA is available.
    """
    import torch

    if torch.cuda.is_available():
        pytest.skip("CUDA is available, cannot test fallback behavior")

    # Request CUDA on CPU-only system
    service = _EmbeddingService(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cuda",
    )

    # Should log warning about fallback
    assert "Falling back to 'cpu'" in caplog.text

    # Should still work with CPU
    emb = service.embed_documents(["test"])
    assert emb.shape == (1, 384)
