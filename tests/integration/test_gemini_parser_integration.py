"""Integration test for GeminiParser with real API (requires GEMINI_API_KEY)."""

import os

import pytest

# Skip this test if no API key is available
pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY environment variable not set",
)


@pytest.mark.slow
@pytest.mark.integration
def test_parse_real_cra_document():
    """
    Integration test: Parse a real (small) CRA document with Gemini API.

    This test requires a valid GEMINI_API_KEY environment variable.
    It validates the entire parsing pipeline end-to-end.
    """
    from scripts.parser.gemini_parser import GeminiParser
    from scripts.parser.validator import ParserValidator

    # Sample CRA text (abbreviated for cost efficiency)
    sample_text = """
Business Expenses - Meals and Entertainment

When you travel for business purposes, you can deduct meal and beverage expenses.
However, the amount you can deduct is limited to 50% of the lesser of the following amounts:

- The amount you actually paid
- An amount that is reasonable in the circumstances

Citation: S3-F2-C1-p1.25

For self-employed individuals operating a sole proprietorship in British Columbia,
the same 50% limitation applies to meal expenses incurred while traveling.

This rule applies to meals consumed during:
- Business travel
- Client entertainment
- Professional development conferences

Note: Alcohol is subject to the same 50% limitation.
"""

    api_key = os.getenv("GEMINI_API_KEY")
    assert api_key, "GEMINI_API_KEY must be set for integration tests"

    # Initialize parser
    parser = GeminiParser(api_key=api_key, model="gemini-2.0-flash-exp", temperature=0.0)

    # Parse the document
    parsed_doc = parser.parse_document(sample_text, "S3-F2-C1.txt")

    # Validate basic structure
    assert parsed_doc.title is not None
    assert parsed_doc.document_id == "S3-F2-C1"
    assert len(parsed_doc.sections) > 0

    # Validate at least one section has content
    assert len(parsed_doc.sections[0].content) > 0

    # Validate token usage was tracked
    assert hasattr(parser, "last_token_usage")
    assert parser.last_token_usage["prompt_tokens"] > 0
    assert parser.last_token_usage["completion_tokens"] > 0

    # Validate parsed content with ParserValidator
    validator = ParserValidator()
    report = validator.validate_parsed_document(parsed_doc)

    # Print report for debugging
    print("\n=== Validation Report ===")
    print(f"Valid: {report['valid']}")
    print(f"Errors: {report['errors']}")
    print(f"Warnings: {report['warnings']}")
    print(f"Statistics: {report['statistics']}")
    print(f"Token Usage: {parser.last_token_usage}")

    # Should have minimal errors (might have some warnings about expense types)
    assert len(report["errors"]) <= 2, f"Too many validation errors: {report['errors']}"

    # Test flattening
    chunks = parsed_doc.to_flat_chunks(source_url="https://canada.ca/test")

    assert len(chunks) > 0
    assert all("content" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)

    # Print cost estimate (approximate)
    total_tokens = parser.last_token_usage["total_tokens"]
    # Gemini Flash pricing: ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens
    estimated_cost = (
        parser.last_token_usage["prompt_tokens"] / 1_000_000 * 0.075
        + parser.last_token_usage["completion_tokens"] / 1_000_000 * 0.30
    )
    print(f"\nEstimated cost for this test: ${estimated_cost:.6f}")

    # Assert reasonable cost (should be < $0.01 for this small sample)
    assert estimated_cost < 0.01, f"Cost too high: ${estimated_cost}"


if __name__ == "__main__":
    # Allow running integration test directly
    test_parse_real_cra_document()
