"""Test LLM parser retry logic with quota exhaustion scenarios."""

import time
from unittest.mock import Mock, patch

import pytest
from google.api_core.exceptions import ResourceExhausted

from qe_tax_rag.extraction.ca.exceptions import ParserError
from qe_tax_rag.extraction.ca.llm_parser import parse


class TestLLMParserRetryLogic:
    """Test retry behavior under API quota exhaustion."""

    @patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
    def test_retry_uses_exponential_backoff_with_jitter(self, mock_model_class, tmp_path):
        """Verify retry delays increase exponentially with jitter."""
        # Create minimal HTML file
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><body><main>Test content</main></body></html>",
            encoding="utf-8"
        )

        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Simulate quota exhaustion on first 2 attempts, success on 3rd
        mock_model.generate_content.side_effect = [
            ResourceExhausted("429 quota exceeded"),
            ResourceExhausted("429 quota exceeded"),
            Mock(text='{"rules": []}'),
        ]
        mock_model.count_tokens.return_value = Mock(total_tokens=1000)

        start_time = time.time()

        with patch("qe_tax_rag.extraction.ca.llm_parser.settings") as mock_settings:
            mock_settings.gemini_api_key = "test_key"
            mock_settings.llm_model_name = "gemini-1.5-flash"

            # Should succeed on 3rd attempt after delays
            result = parse(str(html_file))

        elapsed = time.time() - start_time

        # Expected delays: ~1s (attempt 0) + ~5s (attempt 1) + jitter ≈ 6-8s
        # Current implementation: 1s + 2s = 3s (will fail this test)
        assert elapsed >= 6, f"Retry too fast: {elapsed}s (expected ≥6s with new backoff)"
        assert elapsed <= 8, f"Retry too slow: {elapsed}s (expected ≤8s)"

        # Should have made 3 attempts total
        assert mock_model.generate_content.call_count == 3

    @patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
    def test_retry_fails_after_max_attempts(self, mock_model_class, tmp_path):
        """Verify parser raises ParserError after exhausting retries."""
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><body><main>Test content</main></body></html>",
            encoding="utf-8"
        )

        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Simulate persistent quota exhaustion
        mock_model.generate_content.side_effect = ResourceExhausted("429 quota exceeded")
        mock_model.count_tokens.return_value = Mock(total_tokens=1000)

        with patch("qe_tax_rag.extraction.ca.llm_parser.settings") as mock_settings:
            mock_settings.gemini_api_key = "test_key"
            mock_settings.llm_model_name = "gemini-1.5-flash"

            with pytest.raises(ParserError, match="API call failed permanently"):
                parse(str(html_file))

        # Should have tried 4 times (initial + 3 retries with new config)
        # Current implementation: 3 attempts (will fail this assertion)
        assert mock_model.generate_content.call_count == 4

    @patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
    @patch("qe_tax_rag.extraction.ca.llm_parser.random.uniform")
    def test_retry_adds_jitter_to_prevent_thundering_herd(
        self, mock_random, mock_model_class, tmp_path
    ):
        """Verify jitter is added to retry delays."""
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><body><main>Test content</main></body></html>",
            encoding="utf-8"
        )

        mock_random.return_value = 0.5  # Fixed jitter for testing
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        mock_model.generate_content.side_effect = [
            ResourceExhausted("429 quota exceeded"),
            Mock(text='{"rules": []}'),
        ]
        mock_model.count_tokens.return_value = Mock(total_tokens=1000)

        with patch("qe_tax_rag.extraction.ca.llm_parser.settings") as mock_settings:
            mock_settings.gemini_api_key = "test_key"
            mock_settings.llm_model_name = "gemini-1.5-flash"

            parse(str(html_file))

        # Jitter function should have been called for the retry
        # Current implementation: no jitter (will fail this assertion)
        assert mock_random.call_count >= 1, "Jitter should be applied to retry delays"
