"""
Hybrid search engine combining FTS5 keyword and vector semantic search.

Uses Reciprocal Rank Fusion (RRF) to merge rankings from both search methods.
"""

import sqlite3
from pathlib import Path

from quickexpense_rag.embeddings.encoder import _EmbeddingService
from quickexpense_rag.search.models import ExpenseQuery, SearchResult


class HybridSearchEngine:
    """
    Hybrid search combining FTS5 keyword and vector semantic search.

    This engine performs multi-stage retrieval:
    1. Filter candidates by metadata (province, business_type, expense_types)
    2. Run FTS5 keyword search on filtered candidates
    3. Run vector semantic search on filtered candidates
    4. Merge results using Reciprocal Rank Fusion (RRF)
    5. Hydrate final results from database
    """

    def __init__(self, db_path: Path, encoder: _EmbeddingService) -> None:
        """
        Initialize hybrid search engine.

        Args:
            db_path: Path to SQLite database with FTS5 and vector tables.
            encoder: BGE embedding service for query encoding.

        Raises:
            FileNotFoundError: If database file does not exist.

        """
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        self.db_path = db_path
        self.encoder = encoder

    def search(self, query: ExpenseQuery) -> list[SearchResult]:
        """
        Execute hybrid search with metadata filtering.

        Args:
            query: Structured search query with filters.

        Returns:
            List of search results ranked by RRF fusion score.

        """
        # Will be implemented in subsequent steps
        raise NotImplementedError("search() will be implemented in Phase 1.3")
