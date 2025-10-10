"""BGE embedding service with module-level singleton pattern.

This module provides a lightweight wrapper around SentenceTransformer
for embedding documents and queries using BGE models.
"""

import logging
from typing import Any

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class _EmbeddingService:
    """Internal embedding service implementation.

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
        """Initialize the embedding service.

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
                f"CUDA device '{device}' not available. Falling back to 'cpu'."
            )
            device = "cpu"

        self.device = device
        self.batch_size = batch_size

        try:
            self.model: SentenceTransformer = SentenceTransformer(
                model_name, device=device
            )
        except Exception as e:
            from quickexpense_rag.exceptions import ModelLoadingError

            raise ModelLoadingError(
                f"Failed to load model '{model_name}': {e}"
            ) from e


# Module-level singleton with production defaults
embedding_service = _EmbeddingService()
