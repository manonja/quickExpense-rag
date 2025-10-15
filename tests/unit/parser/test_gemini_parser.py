"""Unit tests for GeminiParser class."""

from unittest.mock import MagicMock, patch

import pytest


def test_gemini_parser_initialization():
    """Test GeminiParser can be initialized."""
    from scripts.parser.gemini_parser import GeminiParser

    parser = GeminiParser(api_key="test-key")
    assert parser is not None
    assert parser.api_key == "test-key"
    assert parser.model == "gemini-2.0-flash-exp"


def test_gemini_parser_custom_model():
    """Test GeminiParser accepts custom model name."""
    from scripts.parser.gemini_parser import GeminiParser

    parser = GeminiParser(api_key="test-key", model="gemini-custom")
    assert parser.model == "gemini-custom"


def test_build_prompt_includes_role():
    """Test prompt includes expert role."""
    from scripts.parser.gemini_parser import GeminiParser

    parser = GeminiParser(api_key="test-key")
    prompt = parser._build_prompt("Sample text", "S1-F1-C1")

    assert "expert" in prompt.lower()
    assert "cra" in prompt.lower() or "canada revenue agency" in prompt.lower()


def test_build_prompt_includes_verbatim_instruction():
    """Test prompt emphasizes verbatim extraction."""
    from scripts.parser.gemini_parser import GeminiParser

    parser = GeminiParser(api_key="test-key")
    prompt = parser._build_prompt("Sample text", "S1-F1-C1")

    assert "verbatim" in prompt.lower()


def test_build_prompt_includes_expense_types_list():
    """Test prompt includes canonical expense types."""
    from scripts.parser.gemini_parser import GeminiParser

    parser = GeminiParser(api_key="test-key")
    prompt = parser._build_prompt("Sample text", "S1-F1-C1")

    # Should include some canonical expense types
    assert "meals" in prompt.lower()
    assert "travel" in prompt.lower()
    assert "vehicle" in prompt.lower()


def test_build_prompt_includes_document_id():
    """Test prompt includes the document ID."""
    from scripts.parser.gemini_parser import GeminiParser

    parser = GeminiParser(api_key="test-key")
    prompt = parser._build_prompt("Sample text", "S3-F2-C1")

    assert "S3-F2-C1" in prompt


def test_build_prompt_includes_source_text():
    """Test prompt includes the source text to parse."""
    from scripts.parser.gemini_parser import GeminiParser

    parser = GeminiParser(api_key="test-key")
    source_text = "This is a unique source text for testing."
    prompt = parser._build_prompt(source_text, "S1-F1-C1")

    assert source_text in prompt


def test_parse_document_with_mocked_api():
    """Test parse_document with mocked Gemini API response."""
    from scripts.parser.gemini_parser import GeminiParser

    # Mock response that looks like a valid ParsedDocument
    mock_response = MagicMock()
    mock_response.text = """{
        "title": "Test Document",
        "document_id": "S1-F1-C1",
        "metadata": {
            "province": ["BC"],
            "business_type": ["sole_proprietorship"],
            "expense_type": ["meals"]
        },
        "sections": [
            {
                "section_title": "Overview",
                "section_level": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "text": "Test content",
                        "citation_id": "S1-F1-C1-p1.1"
                    }
                ]
            }
        ]
    }"""

    parser = GeminiParser(api_key="test-key")

    with patch.object(parser, "_call_gemini_api", return_value=mock_response):
        result = parser.parse_document("Sample text", "S1-F1-C1")

        assert result.title == "Test Document"
        assert result.document_id == "S1-F1-C1"
        assert len(result.sections) == 1


def test_parse_document_extracts_token_usage():
    """Test parse_document extracts token usage from API response."""
    from scripts.parser.gemini_parser import GeminiParser

    mock_response = MagicMock()
    mock_response.text = """{
        "title": "Test",
        "metadata": {"province": [], "business_type": [], "expense_type": []},
        "sections": []
    }"""
    # Mock usage metadata
    mock_response.usage_metadata = MagicMock()
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50

    parser = GeminiParser(api_key="test-key")

    with patch.object(parser, "_call_gemini_api", return_value=mock_response):
        result = parser.parse_document("Sample text", "S1-F1-C1")

        # Should store token usage
        assert hasattr(parser, "last_token_usage")
        assert parser.last_token_usage["prompt_tokens"] == 100
        assert parser.last_token_usage["completion_tokens"] == 50


def test_parse_document_handles_api_error():
    """Test parse_document raises error on API failure."""
    from scripts.parser.gemini_parser import GeminiParser

    parser = GeminiParser(api_key="test-key")

    with patch.object(parser, "_call_gemini_api", side_effect=Exception("API Error")):
        with pytest.raises(Exception, match="API Error"):
            parser.parse_document("Sample text", "S1-F1-C1")
