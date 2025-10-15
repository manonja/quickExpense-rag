"""
BGE embedding service with module-level singleton pattern.

This module provides a lightweight wrapper around SentenceTransformer
for embedding documents and queries using BGE models.
"""

import logging

import numpy as np
import numpy.typing as npt
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class _EmbeddingService:
    """
    Internal embedding service implementation.

    Not intended for direct instantiation. Use the module-level
    `embedding_service` singleton instead.
    """

    QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        device: str = "cpu",
        batch_size: int = 32,
    ) -> None:
        """
        Initialize the embedding service.

        Args:
            model_name: HuggingFace model identifier for sentence-transformers
            device: Device to run model on ('cpu', 'cuda', 'cuda:0', etc.)
            batch_size: Batch size for encoding operations

        Raises:
            ModelLoadingError: If model fails to load

        """
        # Device validation with CUDA fallback
        if device.startswith("cuda") and not torch.cuda.is_available():
            logger.warning(
                "CUDA device '%s' not available. Falling back to 'cpu'.", device
            )
            device = "cpu"

        self.device = device
        self.batch_size = batch_size
        self.model_name = model_name

        try:
            self.model: SentenceTransformer = SentenceTransformer(
                model_name, device=device
            )
        except Exception as e:
            from quickexpense_rag.exceptions import ModelLoadingError

            raise ModelLoadingError(f"Failed to load model '{model_name}': {e}") from e

    def embed_documents(self, texts: list[str]) -> npt.NDArray[np.float32]:
        """
        Embed documents for indexing.

        Args:
            texts: List of text strings to embed

        Returns:
            Numpy array of shape (n_texts, 384) with L2-normalized embeddings

        Raises:
            ValueError: If texts is empty

        """
        if not texts:
            raise ValueError("texts cannot be empty")

        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)

    def embed_query(self, query: str) -> npt.NDArray[np.float32]:
        """
        Embed query with instruction prefix for retrieval.

        Args:
            query: Query string to embed

        Returns:
            Numpy array of shape (384,) with L2-normalized embedding

        Raises:
            ValueError: If query is empty or whitespace-only

        """
        if not query.strip():
            raise ValueError("query cannot be empty")

        embedding: npt.NDArray[np.float32] = self.model.encode(
            self.QUERY_INSTRUCTION + query,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embedding.astype(np.float32)


# Module-level singleton with production defaults
embedding_service = _EmbeddingService()
