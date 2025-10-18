"""Test orchestrator circuit breaker pattern for catastrophic API failures.

When the LLM parser fails consistently across multiple files (indicating sustained
API quota exhaustion), the orchestrator should halt processing (circuit breaker)
instead of wasting time processing all remaining files.

This prevents:
- Wasting ~10+ seconds retrying doomed API calls for each file
- Generating misleading "0 rules extracted" output
- Unclear error messages (final error looks like validation, not quota)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from qe_tax_rag.extraction.ca.exceptions import ParserError
from qe_tax_rag.extraction.ca.orchestrator import run_extraction


@pytest.fixture
def temp_html_files(tmp_path):
    """Create 5 minimal HTML files for circuit breaker testing."""
    html_dir = tmp_path / "html"
    html_dir.mkdir()

    for i in range(1, 6):
        html_file = html_dir / f"test_{i}.html"
        html_file.write_text(
            f"""
            <html>
                <main>
                    <h1>Chapter {i}</h1>
                    <h3><a id="ln8523">Line 8523 – Test Rule {i}</a></h3>
                    <p>Test content for file {i}</p>
                </main>
            </html>
            """,
            encoding="utf-8"
        )

    return html_dir


class TestOrchestratorCircuitBreaker:
    """Test circuit breaker pattern under sustained API failures."""

    @patch("qe_tax_rag.extraction.ca.orchestrator.llm_parse")
    @patch("qe_tax_rag.extraction.ca.orchestrator.classic_parse")
    def test_circuit_breaker_halts_after_3_consecutive_failures(
        self, mock_classic, mock_llm, temp_html_files, tmp_path
    ):
        """Circuit breaker should halt processing after 3 consecutive LLM parser failures.

        Expected behavior (NEW):
        - LLM parser fails on file 1 → continue (could be transient)
        - LLM parser fails on file 2 → continue (still could be transient)
        - LLM parser fails on file 3 → HALT (circuit breaker opens)
        - Files 4 and 5 are NOT processed
        - Clear error message: "Circuit breaker opened after 3 consecutive failures"

        Current behavior (BUG):
        - All 5 files are processed despite quota exhaustion
        - Wastes ~10s per file retrying doomed API calls
        - Final output: 0 rules extracted (misleading)
        """
        # Setup: Classic parser always succeeds
        mock_classic.return_value = []

        # LLM parser always fails (simulating sustained quota exhaustion)
        mock_llm.side_effect = ParserError("API call failed permanently after 4 attempts")

        output_yaml = tmp_path / "output.yml"
        manual_review_yaml = tmp_path / "manual_review.yml"

        # Act
        result = run_extraction(
            input_path=temp_html_files,
            output_yaml=output_yaml,
            manual_review_yaml=manual_review_yaml,
            dry_run=False,
        )

        # Assert - Circuit breaker should have opened
        assert mock_llm.call_count == 3, "Should stop after 3 failures (circuit breaker)"
        assert mock_classic.call_count == 3, "Should stop classic parser too"

        # Only 3 files should be marked as failed (not 5)
        assert len(result["failed_files"]) == 3

        # Note: processed_files = total_files - failed_files
        # With circuit breaker: 5 total - 3 failed = 2 "processed" (actually skipped)
        # This is semantically confusing but acceptable for now
        assert result["total_files"] == 5
        assert result["processed_files"] == 2  # 2 files were never attempted (skipped)
        assert result["total_rules"] == 0  # No rules extracted

    @patch("qe_tax_rag.extraction.ca.orchestrator.llm_parse")
    @patch("qe_tax_rag.extraction.ca.orchestrator.classic_parse")
    def test_circuit_breaker_resets_on_success(
        self, mock_classic, mock_llm, temp_html_files, tmp_path
    ):
        """Circuit breaker should reset failure counter when a file succeeds.

        This ensures transient failures (1-2 retries) don't trigger circuit breaker.
        Only sustained failures (3 consecutive) should halt processing.
        """
        from qe_tax_rag.extraction.ca.schema import ExtractedRule, ExpertSource

        # Setup
        mock_classic.return_value = []

        # LLM fails, fails, succeeds, fails, fails → should NOT halt
        # (failure counter resets after success)
        mock_llm.side_effect = [
            ParserError("Failure 1"),
            ParserError("Failure 2"),
            [ExtractedRule(  # Success on file 3
                rule_number=8523,
                title="Test",
                content="Test content",
                applies_to=[],
                source_citation="Line 8523",
                chapter="Chapter 1",
                section=None,
                source_file="test_3.html",
                expert_source=ExpertSource.LLM,
                anchor_id=None,
                confidence_score=0.8,
            )],
            ParserError("Failure 4"),
            ParserError("Failure 5"),
        ]

        output_yaml = tmp_path / "output.yml"
        manual_review_yaml = tmp_path / "manual_review.yml"

        # Act
        result = run_extraction(
            input_path=temp_html_files,
            output_yaml=output_yaml,
            manual_review_yaml=manual_review_yaml,
            dry_run=False,
        )

        # Assert - All 5 files should be processed (success reset counter)
        assert mock_llm.call_count == 5, "Should process all files (counter reset after success)"
        assert len(result["failed_files"]) == 4  # 4 failures, 1 success
        assert result["processed_files"] == 1  # 1 file succeeded

    @patch("qe_tax_rag.extraction.ca.orchestrator.llm_parse")
    @patch("qe_tax_rag.extraction.ca.orchestrator.classic_parse")
    def test_non_parser_errors_do_not_increment_circuit_breaker(
        self, mock_classic, mock_llm, temp_html_files, tmp_path
    ):
        """Circuit breaker should only count LLM parser failures, not other errors.

        File read errors, adjudication failures, etc. should not contribute to
        the circuit breaker counter (they're not API quota issues).
        """
        from qe_tax_rag.extraction.ca.schema import ExtractedRule, ExpertSource

        # Setup
        mock_classic.side_effect = [
            [],  # File 1: success
            OSError("File read error"),  # File 2: non-parser error
            [],  # File 3: success
            [],  # File 4: success
            [],  # File 5: success
        ]

        mock_llm.return_value = []

        output_yaml = tmp_path / "output.yml"
        manual_review_yaml = tmp_path / "manual_review.yml"

        # Act
        result = run_extraction(
            input_path=temp_html_files,
            output_yaml=output_yaml,
            manual_review_yaml=manual_review_yaml,
            dry_run=False,
        )

        # Assert - All 5 files should be attempted (non-parser errors ignored)
        assert mock_classic.call_count == 5, "Should process all files (non-parser error)"
        assert mock_llm.call_count == 4  # Only called for non-failing classic runs
        assert len(result["failed_files"]) == 1  # Only the OSError file
        assert result["processed_files"] == 4

    @patch("qe_tax_rag.extraction.ca.orchestrator.llm_parse")
    @patch("qe_tax_rag.extraction.ca.orchestrator.classic_parse")
    def test_circuit_breaker_threshold_configurable(
        self, mock_classic, mock_llm, temp_html_files, tmp_path
    ):
        """Circuit breaker threshold should be configurable (default=3).

        This test documents the circuit breaker threshold value.
        If we want to make it configurable later, update this test.
        """
        # Setup
        mock_classic.return_value = []
        mock_llm.side_effect = ParserError("Quota exhausted")

        output_yaml = tmp_path / "output.yml"
        manual_review_yaml = tmp_path / "manual_review.yml"

        # Act
        result = run_extraction(
            input_path=temp_html_files,
            output_yaml=output_yaml,
            manual_review_yaml=manual_review_yaml,
            dry_run=False,
        )

        # Assert - Threshold is hardcoded to 3
        assert mock_llm.call_count == 3, "Circuit breaker threshold is 3 (hardcoded)"

        # If we add a configuration parameter later, update this test:
        # result = run_extraction(..., circuit_breaker_threshold=5)
        # assert mock_llm.call_count == 5
