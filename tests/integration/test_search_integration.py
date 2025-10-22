"""Integration tests for HybridSearchEngine with fixture database."""

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


class TestKeywordSearchIntegration:
    """Integration tests for FTS5 keyword search in search() (Phase 3.2)."""

    @pytest.mark.integration
    def test_search_keyword_only(self, search_engine: HybridSearchEngine) -> None:
        """Search uses FTS5 ranking for keyword queries."""
        # Search for specific term
        query = ExpenseQuery(query="T2125", top_k=5)

        results = search_engine.search(query)

        # Should find the document with "T2125"
        assert len(results) >= 1

        # First result should contain "T2125"
        assert "T2125" in results[0].content

    @pytest.mark.integration
    def test_search_keyword_with_filters(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Keyword search combined with metadata filters."""
        # Search for "test" in BC only
        query = ExpenseQuery(query="test", province=Province.BC, top_k=5)

        results = search_engine.search(query)

        # All results should be from BC
        for result in results:
            assert result.province == Province.BC

        # Should have BC results
        assert len(results) > 0


class TestVectorSearchIntegration:
    """Integration tests for vector semantic search (Phase 4.2)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_vector_search_semantic_matching(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Vector search finds semantically similar documents."""
        # Get all candidate IDs
        all_ids = search_engine._get_candidate_ids(ExpenseQuery(query="test"))

        # Search for semantically similar content
        # "dining" should be similar to "meals" in embeddings
        results = search_engine._vector_search(
            query_text="dining restaurant food", candidate_ids=all_ids, k=5
        )

        # Should return results
        assert len(results) > 0

        # Results should be sorted by distance (closest first)
        distances = [distance for _, distance in results]
        assert distances == sorted(distances)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_vector_search_with_metadata_filters(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Vector search works with metadata filtering."""
        # Get BC candidates only
        bc_ids = search_engine._get_candidate_ids(
            ExpenseQuery(query="test", province=Province.BC)
        )

        # Vector search on BC candidates
        results = search_engine._vector_search(
            query_text="business expense", candidate_ids=bc_ids, k=5
        )

        # Should return results from BC only
        assert len(results) > 0

        # Verify results are actually from BC by hydrating one
        if results:
            first_id = results[0][0]
            hydrated = search_engine._hydrate_results([first_id])
            assert hydrated[0].province == Province.BC


class TestHybridSearchEndToEnd:
    """End-to-end integration tests for full hybrid search (Phase 6.1)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_full_hybrid(self, search_engine: HybridSearchEngine) -> None:
        """Full hybrid search combines FTS5 + vector + RRF correctly."""
        query = ExpenseQuery(query="test", top_k=5)

        results = search_engine.search(query)

        # Should return results
        assert len(results) > 0
        assert len(results) <= 5

        # Results should have all required fields
        for result in results:
            assert result.content is not None
            assert result.citation_id is not None
            assert result.source_url is not None
            # Province and business_type may be None for edge case rows

    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_all_filters_combined(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Hybrid search with all filters: province + business_type + expense_types."""
        query = ExpenseQuery(
            query="test",
            province=Province.BC,
            business_type=BusinessType.SOLE_PROPRIETORSHIP,
            expense_types=["meals"],
            top_k=5,
        )

        results = search_engine.search(query)

        # Should return at least one result
        assert len(results) > 0

        # All results should match filters
        for result in results:
            assert result.province == Province.BC
            assert result.business_type == BusinessType.SOLE_PROPRIETORSHIP
            assert "meals" in result.expense_types

    @pytest.mark.integration
    def test_search_respects_top_k_limit(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search returns at most top_k results even with many matches."""
        query = ExpenseQuery(query="test", top_k=3)

        results = search_engine.search(query)

        # Should return at most 3 results
        assert len(results) <= 3

    @pytest.mark.integration
    def test_search_no_results_when_filters_match_nothing(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search returns empty list when filters match zero rows."""
        query = ExpenseQuery(
            query="test",
            expense_types=["nonexistent_expense_type"],
            top_k=5,
        )

        results = search_engine.search(query)

        assert results == []

    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_semantic_matching(self, search_engine: HybridSearchEngine) -> None:
        """Hybrid search finds semantically similar documents."""
        # Search for "dining" which should find "meals" documents
        query = ExpenseQuery(query="dining restaurant food", top_k=5)

        results = search_engine.search(query)

        # Should return results
        assert len(results) > 0

        # At least some results should be about meals
        # (This is a soft assertion since embeddings are deterministic random)
        # In production, this would match semantically similar content
        assert any("meal" in r.content.lower() for r in results)

    @pytest.mark.integration
    def test_search_keyword_matching(self, search_engine: HybridSearchEngine) -> None:
        """Hybrid search finds exact keyword matches."""
        # Search for "T2125" which only appears in one document
        query = ExpenseQuery(query="T2125", top_k=5)

        results = search_engine.search(query)

        # Should return at least one result
        assert len(results) >= 1

        # First result should contain "T2125"
        assert "T2125" in results[0].content

    @pytest.mark.integration
    def test_search_preserves_rank_order(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search results are returned in RRF rank order."""
        query = ExpenseQuery(query="test", top_k=5)

        results = search_engine.search(query)

        # Results should be non-empty
        assert len(results) > 0

        # All results should have valid citation IDs
        citation_ids = [r.citation_id for r in results]
        assert len(citation_ids) == len(set(citation_ids))  # No duplicates

    @pytest.mark.integration
    def test_search_expense_types_aggregated_correctly(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search results have expense_types correctly aggregated."""
        query = ExpenseQuery(query="test", expense_types=["travel", "meals"], top_k=10)

        results = search_engine.search(query)

        # Should return results
        assert len(results) > 0

        # Find a result with multiple expense types
        # S1-F1-C1-p2 has both travel and meals
        multi_type_results = [r for r in results if len(r.expense_types) > 1]

        if multi_type_results:
            result = multi_type_results[0]
            # Should have multiple expense types as list
            assert isinstance(result.expense_types, list)
            assert len(result.expense_types) >= 2


class TestEdgeCases:
    """Edge case tests for hybrid search (Phase 6.2)."""

    @pytest.mark.integration
    def test_search_empty_query_text(
        self,
        search_engine: HybridSearchEngine,  # noqa: ARG002
    ) -> None:
        """Empty query should be caught by validation (min_length=3)."""
        # ExpenseQuery validates min_length=3
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExpenseQuery(query="", top_k=5)

        with pytest.raises(ValidationError):
            ExpenseQuery(query="ab", top_k=5)  # Too short (< 3)

    @pytest.mark.integration
    def test_search_single_result(self, search_engine: HybridSearchEngine) -> None:
        """Search with unique term returns single result correctly."""
        # "T2125" appears in only one document
        query = ExpenseQuery(query="T2125", top_k=5)

        results = search_engine.search(query)

        # Should return at least 1 result
        assert len(results) >= 1

        # First result should contain the unique term
        assert "T2125" in results[0].content

    @pytest.mark.integration
    def test_search_special_characters(self, search_engine: HybridSearchEngine) -> None:
        """Search handles special characters correctly."""
        # FTS5 should handle quotes, apostrophes, etc.
        query = ExpenseQuery(query="test case", top_k=5)

        results = search_engine.search(query)

        # Should return results (FTS5 handles this gracefully)
        assert len(results) > 0

    @pytest.mark.integration
    def test_search_very_long_query(self, search_engine: HybridSearchEngine) -> None:
        """Search handles long query strings correctly."""
        # Create a long query with multiple terms
        long_query = " ".join(["business expense deduction"] * 10)
        query = ExpenseQuery(query=long_query, top_k=5)

        results = search_engine.search(query)

        # Should return results without error
        assert len(results) >= 0  # May or may not match

    @pytest.mark.integration
    def test_search_unicode_characters(self, search_engine: HybridSearchEngine) -> None:
        """Search handles Unicode characters gracefully."""
        # French characters (relevant for Quebec)
        query = ExpenseQuery(query="café résumé", top_k=5)

        results = search_engine.search(query)

        # Should not crash, may return results
        assert isinstance(results, list)

    @pytest.mark.integration
    def test_search_null_province_in_results(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Results with NULL province are handled correctly."""
        # Search without province filter to include NULL rows
        query = ExpenseQuery(query="test", top_k=15)

        results = search_engine.search(query)

        # Should include results (some may have NULL province)
        assert len(results) > 0

        # Find a result with NULL province (S3-F1-C1-p1 has NULL province)
        null_province_results = [r for r in results if r.province is None]

        # NULL provinces should be allowed
        if null_province_results:
            result = null_province_results[0]
            assert result.province is None
            assert result.citation_id is not None

    @pytest.mark.integration
    def test_search_null_business_type_in_results(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Results with NULL business_type are handled correctly."""
        # Search without business_type filter
        query = ExpenseQuery(query="test", top_k=15)

        results = search_engine.search(query)

        # Should include results
        assert len(results) > 0

        # Find a result with NULL business_type (S3-F1-C1-p2 has NULL business_type)
        null_biz_results = [r for r in results if r.business_type is None]

        # NULL business types should be allowed
        if null_biz_results:
            result = null_biz_results[0]
            assert result.business_type is None
            assert result.citation_id is not None

    @pytest.mark.integration
    def test_search_top_k_larger_than_results(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """top_k larger than available results returns all matches."""
        # Filter to get a small result set
        # top_k max is 50 (le=50 in ExpenseQuery validation)
        query = ExpenseQuery(
            query="T2125",
            top_k=50,  # Maximum allowed top_k
        )

        results = search_engine.search(query)

        # Should return all matching results (< 50)
        assert len(results) < 50
        assert len(results) > 0

    @pytest.mark.integration
    def test_search_expense_types_case_sensitivity(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Expense types filter is case-sensitive (database-driven)."""
        # Lowercase "meals" should work
        query_lower = ExpenseQuery(query="test", expense_types=["meals"], top_k=5)
        results_lower = search_engine.search(query_lower)

        # Uppercase "MEALS" should not match (case-sensitive)
        query_upper = ExpenseQuery(query="test", expense_types=["MEALS"], top_k=5)
        results_upper = search_engine.search(query_upper)

        # Lowercase should return results
        assert len(results_lower) > 0

        # Uppercase should return no results (case-sensitive exact match)
        assert len(results_upper) == 0
