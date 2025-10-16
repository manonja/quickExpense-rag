"""Integration tests for LLM parser against real CRA HTML files."""

from pathlib import Path

import pytest

from qe_tax_rag.extraction.ca.llm_parser import parse
from qe_tax_rag.extraction.ca.schema import ExpertSource

# Mark all tests as integration
pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not Path("cra_documents/cra_t4002e_rev24_dump").exists(),
    reason="CRA HTML dump not found",
)
def test_parse_real_html_file():
    """Test LLM parser against real CRA HTML file (requires API key)."""
    # Find first HTML file in dump
    html_dir = Path("cra_documents/cra_t4002e_rev24_dump")
    html_files = list(html_dir.glob("*.html"))

    if not html_files:
        pytest.skip("No HTML files found in dump directory")

    # Parse first file
    rules = parse(str(html_files[0]))

    # Basic assertions
    assert isinstance(rules, list)
    assert all(rule.expert_source == ExpertSource.LLM for rule in rules)

    # Log results for manual inspection
    print(f"\nParsed {len(rules)} rules from {html_files[0].name}")
    if rules:
        print(f"First rule: {rules[0].rule_number} - {rules[0].title}")
