"""Performance tests for hybrid search engine (Phase 6.3)."""

import time
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


class TestSearchPerformance:
    """Performance validation tests for hybrid search (Phase 6.3)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_performance_benchmark(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Search performance benchmark: 100 searches should complete in reasonable time."""
        # Define a variety of queries to benchmark
        queries = [
            ExpenseQuery(query="test expense", top_k=5),
            ExpenseQuery(query="business deduction", top_k=5),
            ExpenseQuery(query="T2125 form", top_k=5),
            ExpenseQuery(query="vehicle expense", province=Province.BC, top_k=5),
            ExpenseQuery(
                query="meals travel",
                business_type=BusinessType.SOLE_PROPRIETORSHIP,
                top_k=5,
            ),
            ExpenseQuery(
                query="home office",
                province=Province.ON,
                expense_types=["home_office"],
                top_k=5,
            ),
            ExpenseQuery(query="restaurant dining", expense_types=["meals"], top_k=10),
            ExpenseQuery(query="expense claim", top_k=3),
        ]

        # Run 100 searches (reusing queries to simulate realistic usage)
        num_iterations = 100
        start_time = time.perf_counter()

        for i in range(num_iterations):
            query = queries[i % len(queries)]
            results = search_engine.search(query)
            # Ensure results are valid
            assert isinstance(results, list)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time = total_time / num_iterations

        # Print performance metrics
        print(f"\n--- Performance Benchmark ---")
        print(f"Total searches: {num_iterations}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time per search: {avg_time * 1000:.2f}ms")
        print(f"Searches per second: {num_iterations / total_time:.2f}")

        # Performance assertion: average search should be < 250ms
        # This is a reasonable target for hybrid search with a small fixture DB
        assert (
            avg_time < 0.25
        ), f"Average search time {avg_time * 1000:.2f}ms exceeds 250ms target"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_search_latency_p99(self, search_engine: HybridSearchEngine) -> None:
        """Verify p99 latency is acceptable."""
        # Run 50 searches and measure p99 latency
        queries = [
            ExpenseQuery(query="test expense", top_k=5),
            ExpenseQuery(query="business deduction", province=Province.BC, top_k=5),
            ExpenseQuery(
                query="meals travel",
                expense_types=["meals", "travel"],
                top_k=10,
            ),
        ]

        latencies: list[float] = []

        for i in range(50):
            query = queries[i % len(queries)]
            start_time = time.perf_counter()
            results = search_engine.search(query)
            end_time = time.perf_counter()

            latency = end_time - start_time
            latencies.append(latency)
            assert isinstance(results, list)

        # Calculate p99 latency
        latencies_sorted = sorted(latencies)
        p99_index = int(len(latencies_sorted) * 0.99)
        p99_latency = latencies_sorted[p99_index]

        print(f"\n--- Latency Distribution ---")
        print(f"Min: {min(latencies) * 1000:.2f}ms")
        print(f"Median: {latencies_sorted[len(latencies_sorted) // 2] * 1000:.2f}ms")
        print(f"p99: {p99_latency * 1000:.2f}ms")
        print(f"Max: {max(latencies) * 1000:.2f}ms")

        # p99 should be < 300ms for small fixture DB
        assert (
            p99_latency < 0.3
        ), f"p99 latency {p99_latency * 1000:.2f}ms exceeds 300ms target"

    @pytest.mark.integration
    def test_search_with_filters_performance(
        self, search_engine: HybridSearchEngine
    ) -> None:
        """Filtered searches should be fast (benefit from early filtering)."""
        # Filtered search should be fast because candidate set is small
        query = ExpenseQuery(
            query="test",
            province=Province.BC,
            business_type=BusinessType.SOLE_PROPRIETORSHIP,
            expense_types=["meals"],
            top_k=5,
        )

        start_time = time.perf_counter()
        results = search_engine.search(query)
        end_time = time.perf_counter()

        search_time = end_time - start_time

        print(f"\n--- Filtered Search Performance ---")
        print(f"Search time: {search_time * 1000:.2f}ms")
        print(f"Results returned: {len(results)}")

        # Filtered search should be very fast (< 100ms)
        assert (
            search_time < 0.1
        ), f"Filtered search time {search_time * 1000:.2f}ms exceeds 100ms target"
