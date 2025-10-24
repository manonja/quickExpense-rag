"""
Integration tests for P0-3 MVP Search Validation with Lineage Verification.

Tests validate that HybridSearchEngine:
1. Answers real user queries successfully
2. Provides complete lineage traceability for all results

Success threshold: 7/10 queries must return relevant results with valid lineage.

Database: output/PRE-144/mvp_rules.db (63 chunks, 100% lineage coverage)
"""

import logging
from pathlib import Path

import pytest
import yaml
from qe_tax_rag.embeddings.encoder import embedding_service
from qe_tax_rag.search.hybrid import HybridSearchEngine
from qe_tax_rag.search.models import ExpenseQuery, SearchResult

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def mvp_db_path(request) -> Path:
    """
    Database path for MVP search validation.

    Defaults to PRE-144 database. Override with:
    pytest tests/integration/test_mvp_search.py --db-path /path/to/db

    Returns:
        Path to database for testing

    """
    # Get from command line or use default
    db_path_str = request.config.getoption("--db-path", default=None)
    if db_path_str:
        return Path(db_path_str)

    # Default: PRE-144 validated database
    default_path = Path("output/PRE-144/mvp_rules.db")
    if not default_path.exists():
        pytest.skip(f"PRE-144 database not found: {default_path}")

    return default_path


@pytest.fixture(scope="module")
def search_engine(mvp_db_path: Path) -> HybridSearchEngine:
    """Initialize search engine with MVP database."""
    return HybridSearchEngine(db_path=mvp_db_path, encoder=embedding_service)


@pytest.fixture(scope="module")
def mvp_queries() -> list[dict]:
    """Load MVP query fixture."""
    fixture_path = Path("tests/fixtures/mvp_queries.yml")
    with open(fixture_path) as f:
        data = yaml.safe_load(f)
    return data["queries"]


class TestMVPSearchValidation:
    """Integration tests for P0-3 MVP search validation."""

    def _validate_query_results(
        self, query_spec: dict, results: list[SearchResult]
    ) -> tuple[bool, str]:
        """
        Validate search results meet requirements.

        Args:
            query_spec: Query specification from mvp_queries.yml
            results: Search results from HybridSearchEngine

        Returns:
            Tuple of (is_valid, message)

        """
        # Check 1: Minimum result count
        expected_min = query_spec["expected_min_results"]
        if len(results) < expected_min:
            return False, f"Expected >= {expected_min}, got {len(results)}"

        # For queries with expected_min_results=0, pass if no results
        if expected_min == 0:
            return True, "PASS (edge case, no results expected)"

        # Check 2: All results have lineage
        for result in results:
            if result.lineage is None:
                return False, f"Missing lineage: {result.citation_id}"

            # Check lineage_chain format
            if not result.lineage.lineage_chain:
                return False, f"Empty lineage_chain: {result.citation_id}"

            if " | " not in result.lineage.lineage_chain:
                return (
                    False,
                    f"Invalid lineage_chain format: {result.lineage.lineage_chain}",
                )

            # Check source_document present
            if not result.lineage.source_document:
                return False, f"Missing source_document: {result.citation_id}"

        return True, f"PASS ({len(results)} results with valid lineage)"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_mvp_queries_pass_rate(
        self, search_engine: HybridSearchEngine, mvp_queries: list[dict]
    ) -> None:
        """
        Validate 7/10 queries return relevant results with lineage.

        This is the main validation test for PRE-145. It executes all
        10 queries from mvp_queries.yml and verifies:
        - Result count meets minimum expectations
        - All results have lineage metadata
        - Lineage format is valid
        - Source document is present

        Success threshold: 7/10 queries pass

        """
        results_by_query: dict[str, dict] = {}
        passed = 0
        failed = 0

        for query_spec in mvp_queries:
            query = ExpenseQuery(query=query_spec["query"], top_k=5)
            results = search_engine.search(query)

            # Validate results
            is_valid, message = self._validate_query_results(query_spec, results)

            results_by_query[query_spec["query"]] = {
                "passed": is_valid,
                "message": message,
                "result_count": len(results),
                "results": results,
            }

            if is_valid:
                passed += 1
            else:
                failed += 1

        # Calculate pass rate
        total = len(mvp_queries)
        pass_rate = passed / total if total > 0 else 0

        # Log detailed results
        logger.info(
            "MVP Search Validation: %d/%d passed (%0.1f%%)",
            passed,
            total,
            pass_rate * 100,
        )
        for query, result in results_by_query.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            logger.info("  %s: %s - %s", status, query, result["message"])

        # Assert 7/10 threshold
        assert passed >= 7, (
            f"MVP search validation failed: {passed}/{total} passed "
            f"(threshold: 7/10). Failed queries: "
            f"{[q for q, r in results_by_query.items() if not r['passed']]}"
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_lineage_traceability(self, search_engine: HybridSearchEngine) -> None:
        """
        Verify lineage can trace results back to source.

        Tests that lineage metadata is complete and follows expected format:
        - source_document: HTML filename (e.g., "t4002-5.html")
        - expert_source: "classic" or "adjudicated"
        - extraction_timestamp: ISO 8601 UTC timestamp
        - pipeline_stages: Non-empty list
        - lineage_chain: Format "source | stage[timestamp]"

        """
        query = ExpenseQuery(query="meal expenses", top_k=3)
        results = search_engine.search(query)

        assert len(results) > 0, "No results for meal expenses"

        # For each result, verify lineage chain is complete
        for result in results:
            assert result.lineage is not None, f"Missing lineage: {result.citation_id}"
            assert result.lineage.source_document, (
                f"Missing source_document: {result.citation_id}"
            )
            assert result.lineage.expert_source in ["classic", "adjudicated"], (
                f"Invalid expert_source: {result.lineage.expert_source}"
            )
            assert result.lineage.extraction_timestamp, (
                f"Missing extraction_timestamp: {result.citation_id}"
            )
            assert len(result.lineage.pipeline_stages) > 0, (
                f"Empty pipeline_stages: {result.citation_id}"
            )

            # Verify lineage_chain format: "source | stage[timestamp]"
            chain_parts = result.lineage.lineage_chain.split(" | ")
            assert len(chain_parts) >= 2, (
                f"Invalid lineage_chain format: {result.lineage.lineage_chain}"
            )
            assert result.lineage.source_document in chain_parts[0], (
                f"source_document not in lineage_chain: {result.lineage.lineage_chain}"
            )

    @pytest.mark.integration
    def test_search_with_lineage_display(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """
        Test that lineage is available for display in results.

        Verifies lineage fields are suitable for user-facing display:
        - lineage_chain contains parser stage name
        - All lineage fields are non-empty

        """
        query = ExpenseQuery(query="LINE-8523", top_k=1)
        results = search_engine.search(query)

        assert len(results) == 1, "Expected exactly 1 result for LINE-8523"
        result = results[0]

        # Verify lineage is suitable for user display
        assert result.lineage is not None, "Missing lineage"
        assert result.lineage.lineage_chain, "Empty lineage_chain"
        assert (
            "classic_parser" in result.lineage.lineage_chain
            or "adjudicator" in result.lineage.lineage_chain
        ), f"lineage_chain missing parser stage: {result.lineage.lineage_chain}"
