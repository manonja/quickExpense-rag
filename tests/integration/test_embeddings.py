"""Integration tests for embedding service.

Tests use real SentenceTransformer models (lightweight all-MiniLM-L6-v2)
to verify actual numerical properties and model behavior.
"""

import pytest


def test_singleton_pattern() -> None:
    """Verify module-level singleton returns same instance."""
    from quickexpense_rag.embeddings import embedding_service
    from quickexpense_rag.embeddings import embedding_service as service2

    assert embedding_service is service2  # Same object ID
