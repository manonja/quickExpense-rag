"""Unit tests for HybridSearchEngine methods."""

from pathlib import Path

import pytest
from qe_tax_rag.embeddings.encoder import embedding_service
from qe_tax_rag.search.enums import BusinessType, Province
from qe_tax_rag.search.hybrid import HybridSearchEngine
from qe_tax_rag.search.models import ExpenseQuery


@pytest.fixture
def search_engine(fixture_db_path: Path) -> HybridSearchEngine:
    """Create HybridSearchEngine instance with fixture database."""
    return HybridSearchEngine(db_path=fixture_db_path, encoder=embedding_service)


class TestBuildFilterClauses:
    """Test _build_filter_clauses method for SQL query construction."""

    def test_build_filter_clauses_no_filters(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Empty query returns empty JOIN and WHERE clauses."""
        query = ExpenseQuery(query="test query")

        join_clause, where_clause, params = search_engine._build_filter_clauses(query)

        assert join_clause == ""
        assert where_clause == ""
        assert params == []

    def test_build_filter_clauses_province_only(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Province filter generates correct SQL."""
        query = ExpenseQuery(query="test query", province=Province.BC)

        join_clause, where_clause, params = search_engine._build_filter_clauses(query)

        assert join_clause == ""
        assert "province" in where_clause.lower()
        assert "?" in where_clause
        assert params == ["BC"]

    def test_build_filter_clauses_business_type_only(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Business type filter generates correct SQL."""
        query = ExpenseQuery(
            query="test query", business_type=BusinessType.SOLE_PROPRIETORSHIP
        )

        join_clause, where_clause, params = search_engine._build_filter_clauses(query)

        assert join_clause == ""
        assert "business_type" in where_clause.lower()
        assert "?" in where_clause
        assert params == ["sole_proprietorship"]

    def test_build_filter_clauses_both_simple_filters(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Province and business_type combined with AND."""
        query = ExpenseQuery(
            query="test query",
            province=Province.ON,
            business_type=BusinessType.CORPORATION,
        )

        join_clause, where_clause, params = search_engine._build_filter_clauses(query)

        assert join_clause == ""
        assert "province" in where_clause.lower()
        assert "business_type" in where_clause.lower()
        assert "AND" in where_clause.upper()
        assert params == ["ON", "corporation"]

    def test_build_filter_clauses_expense_types_single(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Single expense type generates JOIN and IN clause."""
        query = ExpenseQuery(query="test query", expense_types=["meals"])

        join_clause, where_clause, params = search_engine._build_filter_clauses(query)

        # Should include JOINs for many-to-many relationship
        assert "rule_expense_type_links" in join_clause.lower()
        assert "expense_types" in join_clause.lower()
        # Should use IN clause for expense types
        assert "et.name" in where_clause.lower()
        assert "IN" in where_clause.upper()
        assert params == ["meals"]

    def test_build_filter_clauses_expense_types_multiple(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Multiple expense types generate IN clause with multiple placeholders."""
        query = ExpenseQuery(query="test query", expense_types=["meals", "travel"])

        join_clause, where_clause, params = search_engine._build_filter_clauses(query)

        # Should include JOINs
        assert "rule_expense_type_links" in join_clause.lower()
        assert "expense_types" in join_clause.lower()
        # Should use IN clause with multiple values
        assert "et.name" in where_clause.lower()
        assert "IN" in where_clause.upper()
        # Count placeholders
        assert where_clause.count("?") == 2
        assert params == ["meals", "travel"]

    def test_build_filter_clauses_all_filters(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """All filters combined: province + business_type + expense_types."""
        query = ExpenseQuery(
            query="test query",
            province=Province.BC,
            business_type=BusinessType.SOLE_PROPRIETORSHIP,
            expense_types=["meals", "vehicle"],
        )

        join_clause, where_clause, params = search_engine._build_filter_clauses(query)

        # Should include JOINs for expense_types
        assert "rule_expense_type_links" in join_clause.lower()
        assert "expense_types" in join_clause.lower()
        # Should include all filters in WHERE clause
        assert "province" in where_clause.lower()
        assert "business_type" in where_clause.lower()
        assert "et.name" in where_clause.lower()
        # All conditions combined with AND
        assert where_clause.count("AND") >= 2
        # Parameters in correct order
        assert params == ["BC", "sole_proprietorship", "meals", "vehicle"]


class TestGetCandidateIds:
    """Test _get_candidate_ids method for filtering with deduplication."""

    @pytest.mark.integration
    def test_get_candidate_ids_no_filters(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """No filters returns all rule IDs from fixture database."""
        query = ExpenseQuery(query="test")

        candidate_ids = search_engine._get_candidate_ids(query)

        # Fixture DB has 12 rows
        assert len(candidate_ids) == 12
        # All IDs should be unique (DISTINCT works)
        assert len(candidate_ids) == len(set(candidate_ids))

    @pytest.mark.integration
    def test_get_candidate_ids_with_expense_types(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """expense_types filter returns only matching rules."""
        query = ExpenseQuery(query="test", expense_types=["meals"])

        candidate_ids = search_engine._get_candidate_ids(query)

        # Fixture DB has meals in: S1-F1-C1-p1, S1-F1-C1-p2, S1-F1-C3-p1, S2-F1-C1-p1, S2-F1-C1-p2
        assert len(candidate_ids) >= 3  # At least a few meals entries
        # All IDs should be unique
        assert len(candidate_ids) == len(set(candidate_ids))

    @pytest.mark.integration
    def test_get_candidate_ids_deduplication(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Rule with multiple types appears only once in candidates."""
        query = ExpenseQuery(query="test", expense_types=["travel", "meals"])

        candidate_ids = search_engine._get_candidate_ids(query)

        # S1-F1-C1-p2 has BOTH travel and meals
        # Should appear only once in results
        assert len(candidate_ids) == len(set(candidate_ids))

        # Count total rows matching either type in fixture DB
        # This tests deduplication: rule with both types counted once
        assert len(candidate_ids) > 0

    @pytest.mark.integration
    def test_get_candidate_ids_with_province_and_expense_types(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Combined filters: province AND expense_types."""
        query = ExpenseQuery(
            query="test", province=Province.BC, expense_types=["meals"]
        )

        candidate_ids = search_engine._get_candidate_ids(query)

        # BC + meals: S1-F1-C1-p1, S1-F1-C1-p2, S2-F1-C1-p1
        assert len(candidate_ids) >= 2
        assert len(candidate_ids) == len(set(candidate_ids))


class TestKeywordSearch:
    """Test _keyword_search method for FTS5 full-text search (Phase 3.1)."""

    @pytest.mark.integration
    def test_keyword_search_empty_candidates(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Empty candidate list returns empty results."""
        results = search_engine._keyword_search(
            query_text="test", candidate_ids=[], k=5
        )

        assert results == []

    @pytest.mark.integration
    def test_keyword_search_with_match(self, search_engine: HybridSearchEngine) -> None:
        """Query matching documents returns ranked results."""
        # Get all candidate IDs
        all_ids = search_engine._get_candidate_ids(ExpenseQuery(query="test"))

        # Search for "test" (appears in all fixture rows)
        results = search_engine._keyword_search(
            query_text="test", candidate_ids=all_ids, k=5
        )

        # Should return results with scores
        assert len(results) > 0
        # Each result is (id, score)
        for result in results:
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], int)  # ID
            assert isinstance(result[1], float)  # Score

    @pytest.mark.integration
    def test_keyword_search_exact_term(self, search_engine: HybridSearchEngine) -> None:
        """Exact term matching works correctly."""
        # Get all candidate IDs
        all_ids = search_engine._get_candidate_ids(ExpenseQuery(query="test"))

        # Search for "T2125" (only in S2-F1-C1-p1)
        results = search_engine._keyword_search(
            query_text="T2125", candidate_ids=all_ids, k=5
        )

        # Should return at least one result
        assert len(results) >= 1
        # Results should be sorted by rank (best first)
        if len(results) > 1:
            # FTS5 rank is negative (lower is better), so we negate for comparison
            scores = [score for _, score in results]
            # Scores should be in descending order (higher score = better match)
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.integration
    def test_keyword_search_no_match(self, search_engine: HybridSearchEngine) -> None:
        """No matching documents returns empty results."""
        # Get all candidate IDs
        all_ids = search_engine._get_candidate_ids(ExpenseQuery(query="test"))

        # Search for term that doesn't exist
        results = search_engine._keyword_search(
            query_text="xyznonexistent", candidate_ids=all_ids, k=5
        )

        assert results == []

    @pytest.mark.integration
    def test_keyword_search_respects_k(self, search_engine: HybridSearchEngine) -> None:
        """Keyword search returns at most k results."""
        # Get all candidate IDs
        all_ids = search_engine._get_candidate_ids(ExpenseQuery(query="test"))

        # Search with k=3
        results = search_engine._keyword_search(
            query_text="test", candidate_ids=all_ids, k=3
        )

        # Should return at most 3 results
        assert len(results) <= 3


class TestVectorSearch:
    """Test _vector_search method for semantic search (Phase 4.1)."""

    @pytest.mark.integration
    def test_vector_search_empty_candidates(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Empty candidate list returns empty results."""
        results = search_engine._vector_search(query_text="test", candidate_ids=[], k=5)

        assert results == []

    @pytest.mark.integration
    def test_vector_search_with_match(self, search_engine: HybridSearchEngine) -> None:
        """Query returns semantically similar documents."""
        # Get all candidate IDs
        all_ids = search_engine._get_candidate_ids(ExpenseQuery(query="test"))

        # Search for semantic similarity
        results = search_engine._vector_search(
            query_text="business expense", candidate_ids=all_ids, k=5
        )

        # Should return results with distances
        assert len(results) > 0
        # Each result is (id, distance)
        for result in results:
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], int)  # ID
            assert isinstance(result[1], float)  # Distance

    @pytest.mark.integration
    def test_vector_search_semantic_similarity(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Semantically similar queries find related documents."""
        # Get all candidate IDs
        all_ids = search_engine._get_candidate_ids(ExpenseQuery(query="test"))

        # Search for "meal" (should find "meals" documents)
        results = search_engine._vector_search(
            query_text="dining restaurant meal", candidate_ids=all_ids, k=5
        )

        # Should return results
        assert len(results) > 0

        # Distances should be sorted (closest first)
        distances = [distance for _, distance in results]
        assert distances == sorted(distances)

    @pytest.mark.integration
    def test_vector_search_respects_k(self, search_engine: HybridSearchEngine) -> None:
        """Vector search returns at most k results."""
        # Get all candidate IDs
        all_ids = search_engine._get_candidate_ids(ExpenseQuery(query="test"))

        # Search with k=3
        results = search_engine._vector_search(
            query_text="expense", candidate_ids=all_ids, k=3
        )

        # Should return at most 3 results
        assert len(results) <= 3
