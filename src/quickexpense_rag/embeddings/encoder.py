"""BGE embedding service with module-level singleton pattern.

This module provides a lightweight wrapper around SentenceTransformer
for embedding documents and queries using BGE models.
"""


class _EmbeddingService:
    """Internal embedding service implementation.

    Not intended for direct instantiation. Use the module-level
    `embedding_service` singleton instead.
    """

    pass


# Module-level singleton with production defaults
embedding_service = _EmbeddingService()
