"""Unit tests for LLM parser with mocked Gemini API."""

from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions as google_exceptions
from qe_tax_rag.extraction.ca.exceptions import ParserError
from qe_tax_rag.extraction.ca.llm_parser import parse
from qe_tax_rag.extraction.ca.schema import ExpertSource


@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_parses_valid_llm_response(mock_genai, tmp_path):
    """Test LLM parser extracts valid JSON response."""
    # Arrange: Create minimal HTML fixture
    html_file = tmp_path / "test.html"
    html_file.write_text("""
    <html>
        <main>
            <h1>Chapter 3 – Expenses</h1>
            <h2>Part 4 – Net income</h2>
            <h3><a id="tocch3ln8523">Line 8523 – Meals</a>
                <img alt="business icon">
            </h3>
            <p>Some content about meals.</p>
        </main>
    </html>
    """)

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.text = """
    {
        "rules": [
            {
                "rule_number": 8523,
                "title": "Meals",
                "content": "Some content about meals.",
                "applies_to": ["business"],
                "source_citation": "Line 8523 – Meals",
                "chapter": "Chapter 3 – Expenses",
                "section": "Part 4 – Net income",
                "anchor_id": "tocch3ln8523"
            }
        ]
    }
    """
    mock_model = mock_genai.return_value
    mock_model.generate_content.return_value = mock_response

    # Act
    rules = parse(str(html_file))

    # Assert
    assert len(rules) == 1
    assert rules[0].rule_number == 8523
    assert rules[0].title == "Meals"
    assert rules[0].expert_source == ExpertSource.LLM
    assert rules[0].content == "Some content about meals."


@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
@patch("qe_tax_rag.extraction.ca.llm_parser.time.sleep")  # Mock sleep
def test_retries_on_rate_limit_then_succeeds(mock_sleep, mock_genai, tmp_path):
    """Test parser retries on 429 and succeeds on 2nd attempt."""
    # Arrange
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_response = MagicMock()
    mock_response.text = '{"rules": []}'

    mock_model = mock_genai.return_value
    # Fail on first call, succeed on second
    mock_model.generate_content.side_effect = [
        google_exceptions.ResourceExhausted("Rate limited"),
        mock_response,
    ]

    # Act
    rules = parse(str(html_file))

    # Assert
    assert mock_model.generate_content.call_count == 2
    assert mock_sleep.call_count == 1
    assert rules == []


@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
@patch("qe_tax_rag.extraction.ca.llm_parser.time.sleep")
def test_raises_error_after_max_retries(mock_sleep, mock_genai, tmp_path):
    """Test parser raises ParserError after 4 total failed attempts."""
    # Arrange
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_model = mock_genai.return_value
    mock_model.generate_content.side_effect = google_exceptions.ResourceExhausted(
        "Rate limited"
    )

    # Act & Assert
    with pytest.raises(ParserError, match="API call failed permanently"):
        parse(str(html_file))

    # The code is configured for 4 total attempts (1 initial + 3 retries)
    assert mock_model.generate_content.call_count == 4
    assert mock_sleep.call_count == 3  # Sleeps after attempts 1, 2, and 3


@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_extracts_multiple_applies_to_values(mock_genai, tmp_path):
    """Test parser handles multiple icons (business + fishing)."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_response = MagicMock()
    mock_response.text = """
    {
        "rules": [{
            "rule_number": 9999,
            "title": "Test",
            "content": "Test content",
            "applies_to": ["business", "fishing"],
            "source_citation": "Line 9999 – Test",
            "chapter": "Chapter 1",
            "section": null,
            "anchor_id": null
        }]
    }
    """
    mock_genai.return_value.generate_content.return_value = mock_response

    rules = parse(str(html_file))

    assert len(rules) == 1
    assert len(rules[0].applies_to) == 2
    assert "business" in [str(t) for t in rules[0].applies_to]
    assert "fishing" in [str(t) for t in rules[0].applies_to]


@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_handles_empty_applies_to_list(mock_genai, tmp_path):
    """Test parser handles rules with no icons."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_response = MagicMock()
    mock_response.text = """
    {
        "rules": [{
            "rule_number": 9999,
            "title": "Test",
            "content": "Test content",
            "applies_to": [],
            "source_citation": "Line 9999 – Test",
            "chapter": "Chapter 1",
            "section": null,
            "anchor_id": null
        }]
    }
    """
    mock_genai.return_value.generate_content.return_value = mock_response

    rules = parse(str(html_file))

    assert len(rules) == 1
    assert rules[0].applies_to == []


@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_returns_empty_list_for_malformed_json(mock_genai, tmp_path, caplog):
    """
    Parser should return [] (not crash) when Gemini returns malformed JSON.

    Large HTML files can sometimes cause Gemini to return truncated/malformed
    JSON responses. The parser should log a warning and return [], allowing
    the adjudicator to use Classic Parser results as fallback.
    """
    import logging

    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_response = MagicMock()
    # Simulate truncated JSON (like the real error from t4002-5.html)
    mock_response.text = '{"rules": [{"rule_number": 8523, "title": "Meals", "content": "Unterminated string...'
    mock_genai.return_value.generate_content.return_value = mock_response

    # This should NOT raise ParserError
    with caplog.at_level(logging.WARNING):
        result = parse(str(html_file))

    # Assertions
    assert result == [], "Should return empty list for malformed JSON"
    assert (
        "malformed" in caplog.text.lower() or "failed to parse" in caplog.text.lower()
    )
    assert (
        "fallback" in caplog.text.lower()
    ), "Should mention fallback to Classic Parser"


def test_raises_parser_error_on_invalid_file_path():
    """Test parser raises error on non-existent file."""
    with pytest.raises(ParserError, match="HTML file not found"):
        parse("/nonexistent/path.html")


@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_logs_warning_for_large_content(mock_genai, tmp_path, caplog):
    """Test parser logs warning for content exceeding token limit."""
    import logging

    html_file = tmp_path / "test.html"
    # Create large HTML content
    large_content = "<html><main>" + ("x" * 800_000) + "</main></html>"
    html_file.write_text(large_content)

    mock_response = MagicMock()
    mock_response.text = '{"rules": []}'

    mock_model = mock_genai.return_value
    mock_count_result = MagicMock()
    mock_count_result.total_tokens = 1_100_000
    mock_model.count_tokens.return_value = mock_count_result
    mock_model.generate_content.return_value = mock_response

    with caplog.at_level(logging.WARNING):
        parse(str(html_file))

    assert "exceeds token limit" in caplog.text
    assert mock_model.count_tokens.called
