"""Unit tests for HybridSearchEngine methods."""

from pathlib import Path

import pytest

from quickexpense_rag.embeddings.encoder import embedding_service
from quickexpense_rag.search.enums import BusinessType, Province
from quickexpense_rag.search.hybrid import HybridSearchEngine
from quickexpense_rag.search.models import ExpenseQuery


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
