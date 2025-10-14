"""Unit tests for Reciprocal Rank Fusion algorithm."""

import pytest

from quickexpense_rag.search.hybrid import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    """Test reciprocal_rank_fusion function (Phase 5.1)."""

    def test_rrf_both_empty(self) -> None:
        """Both empty lists return empty result."""
        result = reciprocal_rank_fusion(fts_results=[], vec_results=[], k=60)

        assert result == []

    def test_rrf_one_empty(self) -> None:
        """One empty list uses the non-empty list."""
        fts_results = [(1, 0.5), (2, 0.3)]
        vec_results: list[tuple[int, float]] = []

        result = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=60)

        # Should return IDs from FTS results, sorted by RRF score
        result_ids = [id_ for id_, _ in result]
        assert result_ids == [1, 2]

    def test_rrf_no_overlap(self) -> None:
        """Disjoint result sets are merged."""
        fts_results = [(1, 0.5), (2, 0.3)]
        vec_results = [(3, 0.2), (4, 0.1)]

        result = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=60)

        # Should return all IDs
        result_ids = [id_ for id_, _ in result]
        assert set(result_ids) == {1, 2, 3, 4}
        # Should be 4 results total
        assert len(result) == 4

    def test_rrf_with_overlap(self) -> None:
        """Item in both lists gets higher combined score."""
        # ID 1 appears in both lists
        fts_results = [(1, 0.5), (2, 0.3)]
        vec_results = [(1, 0.2), (3, 0.1)]

        result = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=60)

        # ID 1 should be ranked first (appears in both)
        result_ids = [id_ for id_, _ in result]
        assert result_ids[0] == 1

    def test_rrf_scoring_formula(self) -> None:
        """Verify RRF scoring formula: score = 1/(k + rank + 1)."""
        # Single item in each list
        fts_results = [(1, 0.5)]  # rank 0 in FTS
        vec_results = [(2, 0.2)]  # rank 0 in vector

        k = 60
        result = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=k)

        # ID 1: score from FTS only = 1/(60 + 0 + 1) = 1/61
        # ID 2: score from vector only = 1/(60 + 0 + 1) = 1/61
        expected_score = 1 / (k + 0 + 1)

        for id_, score in result:
            assert abs(score - expected_score) < 1e-6

    def test_rrf_combined_scoring(self) -> None:
        """Item in both lists gets sum of individual scores."""
        fts_results = [(1, 0.5)]  # ID 1 at rank 0
        vec_results = [(1, 0.2)]  # ID 1 at rank 0

        k = 60
        result = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=k)

        # ID 1: score = 1/(60+0+1) + 1/(60+0+1) = 2/61
        expected_score = 2 / (k + 0 + 1)

        assert len(result) == 1
        assert result[0][0] == 1
        assert abs(result[0][1] - expected_score) < 1e-6

    def test_rrf_rank_matters(self) -> None:
        """Higher rank (later position) gets lower score contribution."""
        fts_results = [(1, 0.9), (2, 0.5)]  # ID 1 at rank 0, ID 2 at rank 1
        vec_results: list[tuple[int, float]] = []

        k = 60
        result = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=k)

        # ID 1: score = 1/(60+0+1) = 1/61 ≈ 0.0164
        # ID 2: score = 1/(60+1+1) = 1/62 ≈ 0.0161
        score_1 = result[0][1]
        score_2 = result[1][1]

        assert score_1 > score_2  # Earlier rank gets higher score

    def test_rrf_sorted_by_score_descending(self) -> None:
        """Results are sorted by combined score (highest first)."""
        fts_results = [(1, 0.5), (2, 0.3), (3, 0.1)]
        vec_results = [(3, 0.8), (2, 0.4), (4, 0.2)]

        result = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=60)

        # Scores should be in descending order
        scores = [score for _, score in result]
        assert scores == sorted(scores, reverse=True)

    def test_rrf_custom_k_value(self) -> None:
        """Custom k value affects scoring."""
        fts_results = [(1, 0.5)]
        vec_results: list[tuple[int, float]] = []

        # k=10 should give higher score than k=60
        result_k10 = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=10)
        result_k60 = reciprocal_rank_fusion(fts_results=fts_results, vec_results=vec_results, k=60)

        score_k10 = result_k10[0][1]
        score_k60 = result_k60[0][1]

        assert score_k10 > score_k60  # Lower k gives higher scores
