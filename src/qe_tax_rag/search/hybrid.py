"""
Hybrid search engine combining FTS5 keyword and vector semantic search.

Uses Reciprocal Rank Fusion (RRF) to merge rankings from both search methods.
"""

import sqlite3
from pathlib import Path
from typing import Any

from qe_tax_rag.embeddings.encoder import _EmbeddingService
from qe_tax_rag.search.models import ExpenseQuery, SearchResult

# Type aliases for ranked search results
RankedResult = tuple[int, float]  # (rule_id, score/distance)
RankedResults = list[RankedResult]


def reciprocal_rank_fusion(
    fts_results: RankedResults,
    vec_results: RankedResults,
    k: int = 60,
) -> RankedResults:
    """
    Merge FTS5 and vector search results using Reciprocal Rank Fusion.

    RRF assigns each document a score based on its rank in each result list:
    score = sum(1 / (k + rank + 1)) for each list where document appears.

    Documents appearing in both lists get higher scores (sum of contributions).
    The constant k (default 60) controls the relative importance of rank positions.

    Args:
        fts_results: List of (rule_id, score) from FTS5 keyword search.
        vec_results: List of (rule_id, distance) from vector search.
        k: RRF constant controlling rank sensitivity (default: 60).

    Returns:
        List of (rule_id, combined_score) sorted by score descending (best first).
        Empty list if both inputs are empty.

    References:
        Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).
        Reciprocal rank fusion outperforms condorcet and individual rank
        learning methods. SIGIR 2009.

    """
    scores: dict[int, float] = {}

    # Add scores from FTS5 results
    for rank, (rule_id, _) in enumerate(fts_results):
        scores[rule_id] = scores.get(rule_id, 0.0) + 1 / (k + rank + 1)

    # Add scores from vector results
    for rank, (rule_id, _) in enumerate(vec_results):
        scores[rule_id] = scores.get(rule_id, 0.0) + 1 / (k + rank + 1)

    # Sort by combined score (descending)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridSearchEngine:
    """
    Hybrid search combining FTS5 keyword and vector semantic search.

    This engine performs multi-stage retrieval:
    1. Filter candidates by metadata (province, business_type, expense_types)
    2. Run FTS5 keyword search on filtered candidates
    3. Run vector semantic search on filtered candidates
    4. Merge results using Reciprocal Rank Fusion (RRF)
    5. Hydrate final results from database

    Security:
        All SQL queries use parameterized statements (? placeholders) to prevent
        SQL injection. User inputs are never concatenated into query strings.
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

    def _build_filter_clauses(self, query: ExpenseQuery) -> tuple[str, str, list[Any]]:
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
        sql = f"SELECT DISTINCT r.id FROM rules r {join_clause}"  # noqa: S608

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

    def _keyword_search(
        self, query_text: str, candidate_ids: list[int], k: int
    ) -> RankedResults:
        """
        Perform FTS5 keyword search on filtered candidates.

        Searches the rules_fts virtual table for exact and fuzzy matches.
        Uses SQLite FTS5 MATCH syntax with porter stemming.

        Args:
            query_text: Search query text for keyword matching.
            candidate_ids: List of rule IDs to search within (pre-filtered).
            k: Maximum number of results to return.

        Returns:
            List of (rule_id, score) tuples sorted by relevance (best first).
            Empty list if no matches or empty candidates.
            Note: FTS5 rank is negative (lower is better), we negate for consistency.

        """
        # Handle empty candidates
        if not candidate_ids:
            return []

        # Build SQL query for FTS5 search
        placeholders = ", ".join(["?"] * len(candidate_ids))
        sql = f"""
            SELECT rowid, -rank as score
            FROM rules_fts
            WHERE rowid IN ({placeholders})
              AND content MATCH ?
            ORDER BY rank
            LIMIT ?
        """  # noqa: S608

        # Execute query
        conn = sqlite3.connect(self.db_path)
        try:
            # Parameters: candidate_ids + query_text + k
            params = [*candidate_ids, query_text, k]
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            # Return list of (id, score) tuples
            return [(row[0], row[1]) for row in rows]
        finally:
            conn.close()

    def _vector_search(
        self, query_text: str, candidate_ids: list[int], k: int
    ) -> RankedResults:
        """
        Perform vector semantic search on filtered candidates.

        Embeds the query using BGE encoder and searches rules_vec table
        for semantically similar documents using cosine similarity.

        Args:
            query_text: Search query text to embed.
            candidate_ids: List of rule IDs to search within (pre-filtered).
            k: Maximum number of results to return.

        Returns:
            List of (rule_id, distance) tuples sorted by similarity (closest first).
            Empty list if no matches or empty candidates.
            Note: Lower distance = more similar (cosine distance).

        """
        # Handle empty candidates
        if not candidate_ids:
            return []

        # Embed query using BGE encoder
        query_vector = self.encoder.embed_query(query_text)

        # Convert to bytes for sqlite-vec
        query_vec_bytes = query_vector.tobytes()

        # Build SQL query for vector search
        # sqlite-vec uses vec_distance_cosine for cosine distance
        placeholders = ", ".join(["?"] * len(candidate_ids))
        sql = f"""
            SELECT
                rowid,
                distance
            FROM rules_vec
            WHERE rowid IN ({placeholders})
              AND embedding MATCH ?
            ORDER BY distance
            LIMIT ?
        """

        # Execute query
        conn = sqlite3.connect(self.db_path)
        try:
            # Load sqlite-vec extension
            # Some Python builds don't support enable_load_extension
            try:
                conn.enable_load_extension(True)
            except AttributeError:
                # Extension loading not supported in this build
                # sqlite-vec must be statically compiled or pre-loaded
                pass

            import sqlite_vec

            sqlite_vec.load(conn)

            # Disable extension loading if it was enabled
            try:
                conn.enable_load_extension(False)
            except AttributeError:
                pass

            # Parameters: candidate_ids + query_vec_bytes + k
            params = [*candidate_ids, query_vec_bytes, k]
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            # Return list of (id, distance) tuples
            return [(row[0], row[1]) for row in rows]
        finally:
            conn.close()

    def _hydrate_results(self, rule_ids: list[int]) -> list[SearchResult]:
        """
        Hydrate SearchResult objects from rule IDs.

        Fetches full rule data and aggregates expense_types using GROUP_CONCAT.
        Preserves the order of input rule_ids (important for ranked results).

        Args:
            rule_ids: List of rule IDs to hydrate (may be empty).

        Returns:
            List of SearchResult objects in the same order as rule_ids.
            Returns empty list if rule_ids is empty.

        """
        if not rule_ids:
            return []

        # Build SQL query with placeholders for rule IDs
        placeholders = ", ".join(["?"] * len(rule_ids))
        sql = f"""
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
            WHERE r.id IN ({placeholders})
            GROUP BY r.id
        """

        # Execute query
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(sql, rule_ids)
            rows = cursor.fetchall()

            # Create a mapping from ID to row for preserving order
            id_to_row = {row[0]: row for row in rows}

            # Hydrate results in the same order as rule_ids
            results: list[SearchResult] = []
            for rule_id in rule_ids:
                row = id_to_row.get(rule_id)
                if row is None:
                    continue  # Skip if rule was deleted

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

    def search(self, query: ExpenseQuery) -> list[SearchResult]:
        """
        Execute hybrid search with RRF fusion of FTS5 and vector results.

        Complete implementation: Combines keyword and semantic search using
        Reciprocal Rank Fusion (RRF) for optimal ranking.

        Search pipeline:
        1. Metadata filtering → candidate IDs
        2. FTS5 keyword search on candidates
        3. Vector semantic search on candidates
        4. RRF fusion of rankings
        5. Result hydration

        Args:
            query: Structured search query with filters.

        Returns:
            List of search results ranked by RRF combined score (limited to top_k).

        """
        from qe_tax_rag.settings import settings

        # Step 1: Get candidate IDs from metadata filtering
        candidate_ids = self._get_candidate_ids(query)

        # Step 2: Short-circuit if no candidates
        if not candidate_ids:
            return []

        # Step 3: Run FTS5 keyword search on candidates
        fts_results = self._keyword_search(
            query_text=query.query,
            candidate_ids=candidate_ids,
            k=query.top_k * 2,  # Get more candidates for RRF fusion
        )

        # Step 4: Run vector semantic search on candidates
        vec_results = self._vector_search(
            query_text=query.query,
            candidate_ids=candidate_ids,
            k=query.top_k * 2,  # Get more candidates for RRF fusion
        )

        # Step 5: Apply Reciprocal Rank Fusion to merge rankings
        fused_results = reciprocal_rank_fusion(
            fts_results=fts_results, vec_results=vec_results, k=settings.rrf_k
        )

        # Step 6: Take top_k fused results
        top_fused = fused_results[: query.top_k]

        # Step 7: Extract ranked IDs
        ranked_ids = [rule_id for rule_id, _ in top_fused]

        # Step 8: Hydrate results (preserving RRF ranking order)
        results = self._hydrate_results(ranked_ids)

        return results
