"""Unit tests for LLM parser with mocked Gemini API."""

from unittest.mock import MagicMock, patch

import pytest

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
