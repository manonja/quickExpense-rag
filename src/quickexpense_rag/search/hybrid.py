"""
Hybrid search engine combining FTS5 keyword and vector semantic search.

Uses Reciprocal Rank Fusion (RRF) to merge rankings from both search methods.
"""

from pathlib import Path

from quickexpense_rag.search.models import ExpenseQuery, SearchResult


class HybridSearchEngine:
    """
    Hybrid search combining FTS5 keyword and vector semantic search.

    Will be implemented in TICKET 7.
    """

    def __init__(self, db_path: Path) -> None:
        """
        Initialize hybrid search engine.

        Args:
            db_path: Path to SQLite database with FTS5 and vector tables.

        """
        self.db_path = db_path
        raise NotImplementedError("HybridSearchEngine will be implemented in TICKET 7")

    def search(self, query: ExpenseQuery) -> list[SearchResult]:
        """
        Execute hybrid search with metadata filtering.

        Args:
            query: Structured search query with filters.

        Returns:
            List of search results ranked by RRF fusion score.

        """
        raise NotImplementedError("search() will be implemented in TICKET 7")
