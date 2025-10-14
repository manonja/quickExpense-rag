"""Integration tests for HybridSearchEngine with fixture database."""

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


class TestBasicSearch:
    """Integration tests for basic search with metadata filtering (Phase 1.3)."""

    @pytest.mark.integration
    def test_search_with_province_filter(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search with province filter returns only matching rows."""
        query = ExpenseQuery(query="test", province=Province.BC)

        results = search_engine.search(query)

        # All results should be from BC
        for result in results:
            assert result.province == Province.BC

        # Fixture DB has BC test cases: TEST-BC-001, TEST-BC-002, TEST-KW-001, TEST-EDGE-002
        # Should return at least some results from BC
        assert len(results) > 0

    @pytest.mark.integration
    def test_search_with_business_type_filter(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search with business type filter returns only matching rows."""
        query = ExpenseQuery(
            query="test", business_type=BusinessType.SOLE_PROPRIETORSHIP
        )

        results = search_engine.search(query)

        # All results should be sole proprietorships
        for result in results:
            assert result.business_type == BusinessType.SOLE_PROPRIETORSHIP

        # Fixture DB has sole proprietorship test cases
        assert len(results) > 0

    @pytest.mark.integration
    def test_search_with_combined_filters(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search with province AND business_type filters."""
        query = ExpenseQuery(
            query="test",
            province=Province.ON,
            business_type=BusinessType.CORPORATION,
        )

        results = search_engine.search(query)

        # All results should match both filters
        for result in results:
            assert result.province == Province.ON
            assert result.business_type == BusinessType.CORPORATION

        # Fixture DB has TEST-ON-001 matching this combination
        assert len(results) > 0

    @pytest.mark.integration
    def test_search_no_filters_returns_all(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search with no filters returns results from entire database."""
        query = ExpenseQuery(query="test")

        results = search_engine.search(query)

        # Should return multiple results (fixture DB has 12 rows)
        assert len(results) > 0

    @pytest.mark.integration
    def test_search_respects_top_k(self, search_engine: HybridSearchEngine) -> None:
        """Search returns at most top_k results."""
        query = ExpenseQuery(query="test", top_k=3)

        results = search_engine.search(query)

        # Should return at most 3 results
        assert len(results) <= 3


class TestExpenseTypesFiltering:
    """Integration tests for expense_types filtering (Phase 2.3)."""

    @pytest.mark.integration
    def test_search_expense_types_or_logic(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """expense_types filter matches ANY of the specified types (OR logic)."""
        query = ExpenseQuery(query="test", expense_types=["meals", "vehicle"])

        results = search_engine.search(query)

        # Should return rules with EITHER meals OR vehicle
        assert len(results) > 0

        # Each result should have at least one matching expense type
        for result in results:
            matching_types = set(result.expense_types) & {"meals", "vehicle"}
            assert len(matching_types) > 0, (
                f"Result {result.citation_id} has expense_types {result.expense_types} "
                f"but should match meals or vehicle"
            )

    @pytest.mark.integration
    def test_search_expense_types_no_duplicates(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Rule with multiple matching types appears only once."""
        query = ExpenseQuery(query="test", expense_types=["travel", "meals"])

        results = search_engine.search(query)

        # S1-F1-C1-p2 has BOTH travel and meals
        # Should appear only once in results
        citation_ids = [r.citation_id for r in results]
        assert len(citation_ids) == len(set(citation_ids)), (
            f"Duplicate citation IDs found: {citation_ids}"
        )

    @pytest.mark.integration
    def test_search_expense_types_with_province(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """expense_types AND province filters combined."""
        query = ExpenseQuery(
            query="test", province=Province.BC, expense_types=["meals"]
        )

        results = search_engine.search(query)

        # All results should be from BC
        for result in results:
            assert result.province == Province.BC

        # All results should have meals
        for result in results:
            assert "meals" in result.expense_types

        # Fixture DB has BC+meals: S1-F1-C1-p1, S1-F1-C1-p2, S2-F1-C1-p1
        assert len(results) >= 2

    @pytest.mark.integration
    def test_search_expense_types_empty_result(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """No matches returns empty list."""
        # Query for expense type that doesn't exist in fixture DB
        query = ExpenseQuery(query="test", expense_types=["nonexistent_type"])

        results = search_engine.search(query)

        assert results == []
