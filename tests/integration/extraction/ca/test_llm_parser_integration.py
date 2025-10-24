"""Integration tests for LLM parser using VCR for API response recording."""

from pathlib import Path

import pytest
import vcr
from qe_tax_rag.extraction.ca.llm_parser import parse
from qe_tax_rag.extraction.ca.schema import ExpertSource

# Mark all tests as integration
pytestmark = pytest.mark.integration

# Configure VCR for Gemini API
my_vcr = vcr.VCR(
    cassette_library_dir="tests/fixtures/vcr_cassettes",
    record_mode="once",  # Record on first run, replay on subsequent runs
    match_on=["method", "scheme", "host", "port", "path", "query"],
    filter_headers=["authorization", "x-goog-api-key"],  # Remove API key from cassettes
)


@my_vcr.use_cassette("llm_parser_real_html.yaml")
@pytest.mark.skipif(
    not Path("cra_documents/cra_t4002e_rev24_dump").exists(),
    reason="CRA HTML dump not found",
)
def test_parse_real_html_file():
    """
    Test LLM parser against real CRA HTML (uses VCR for API response replay).

    First run: Makes real Gemini API call and records response to cassette.
    Subsequent runs: Replays response from cassette (no API call, instant).
    """
    # Find first HTML file in dump
    html_dir = Path("cra_documents/cra_t4002e_rev24_dump")
    html_files = list(html_dir.glob("*.html"))

    if not html_files:
        pytest.skip("No HTML files found in dump directory")

    # Parse first file (VCR intercepts HTTP calls)
    rules = parse(str(html_files[0]))

    # Basic assertions
    assert isinstance(rules, list)
    assert all(rule.expert_source == ExpertSource.LLM for rule in rules)

    # Log results for manual inspection
    print(f"\nParsed {len(rules)} rules from {html_files[0].name}")
    if rules:
        print(f"First rule: {rules[0].rule_number} - {rules[0].title}")
