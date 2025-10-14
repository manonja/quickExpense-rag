"""
Hybrid search engine combining FTS5 keyword and vector semantic search.

Uses Reciprocal Rank Fusion (RRF) to merge rankings from both search methods.
"""

import sqlite3
from pathlib import Path
from typing import Any

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

    def _build_filter_clauses(
        self, query: ExpenseQuery
    ) -> tuple[str, str, list[Any]]:
        """
        Build SQL JOIN and WHERE clauses for metadata filtering.

        Handles province, business_type, and expense_types filters.
        expense_types uses many-to-many JOINs (OR logic: matches ANY type).

        Args:
            query: Search query with optional metadata filters.

        Returns:
            Tuple of (join_clause, where_clause, params):
            - join_clause: SQL JOIN statements (for expense_types)
            - where_clause: SQL WHERE conditions (may be empty)
            - params: List of parameter values for SQL placeholders

        """
        where_conditions: list[str] = []
        params: list[Any] = []
        join_clause = ""

        # Province filter
        if query.province is not None:
            where_conditions.append("r.province = ?")
            params.append(query.province.value)

        # Business type filter
        if query.business_type is not None:
            where_conditions.append("r.business_type = ?")
            params.append(query.business_type.value)

        # Expense types filter (many-to-many with OR logic)
        if query.expense_types:
            # Add JOINs to access expense_types table
            join_clause = """
                JOIN rule_expense_type_links retl ON r.id = retl.rule_id
                JOIN expense_types et ON retl.expense_type_id = et.id
            """

            # Generate IN clause with placeholders
            placeholders = ", ".join(["?"] * len(query.expense_types))
            where_conditions.append(f"et.name IN ({placeholders})")
            params.extend(query.expense_types)

        # Combine conditions with AND
        where_clause = " AND ".join(where_conditions) if where_conditions else ""

        return join_clause, where_clause, params

    def _get_candidate_ids(self, query: ExpenseQuery) -> list[int]:
        """
        Get candidate rule IDs matching metadata filters with deduplication.

        Uses DISTINCT to ensure rules with multiple matching expense types
        appear only once in the results (deduplication).

        Args:
            query: Search query with optional metadata filters.

        Returns:
            List of unique rule IDs matching the filters.
            Empty list if no matches found.

        """
        # Build filter clauses
        join_clause, where_clause, params = self._build_filter_clauses(query)

        # Build SQL query with DISTINCT for deduplication
        sql = f"SELECT DISTINCT r.id FROM rules r {join_clause}"

        # Add WHERE clause if filters exist
        if where_clause:
            sql += f" WHERE {where_clause}"

        # Execute query
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def search(self, query: ExpenseQuery) -> list[SearchResult]:
        """
        Execute hybrid search with metadata filtering.

        Phase 1.3 implementation: Basic search with metadata filtering only.
        FTS5, vector search, and RRF fusion will be added in later phases.

        Args:
            query: Structured search query with filters.

        Returns:
            List of search results (limited to top_k).
            Note: Results are not yet ranked by relevance (Phase 1.3 limitation).

        """
        # Build filter clauses
        join_clause, where_clause, params = self._build_filter_clauses(query)

        # Build SQL query
        sql = """
            SELECT
                r.id,
                r.content,
                r.citation_id,
                r.source_url,
                r.province,
                r.business_type,
                r.retrieved_at,
                GROUP_CONCAT(et.name) as expense_type_names
            FROM rules r
            LEFT JOIN rule_expense_type_links retl ON r.id = retl.rule_id
            LEFT JOIN expense_types et ON retl.expense_type_id = et.id
        """

        # Add WHERE clause if filters exist
        if where_clause:
            sql += f" WHERE {where_clause}"

        # Group by rule ID to aggregate expense types
        sql += " GROUP BY r.id"

        # Limit results to top_k
        sql += f" LIMIT {query.top_k}"

        # Execute query
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            # Hydrate SearchResult objects
            results: list[SearchResult] = []
            for row in rows:
                # Parse expense types (comma-separated string → list)
                expense_types_str = row[7]  # GROUP_CONCAT result
                expense_types = (
                    expense_types_str.split(",") if expense_types_str else []
                )

                result = SearchResult(
                    content=row[1],
                    citation_id=row[2],
                    source_url=row[3],
                    score=1.0,  # Placeholder score (will be replaced by RRF in Phase 5)
                    province=row[4],
                    business_type=row[5],
                    expense_types=expense_types,
                    retrieved_at=row[6],
                )
                results.append(result)

            return results
        finally:
            conn.close()
