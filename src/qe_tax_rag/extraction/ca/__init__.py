"""
Canadian tax document extraction pipeline.

This package provides HTML-to-YAML extraction for CRA tax documents using
a Mixture-of-Experts approach with grounded adjudication.

Modules:
    schema: Pydantic models for extraction data structures
    settings: Configuration management with pydantic-settings
    exceptions: Custom exception hierarchy
    classic_parser: Rule-based HTML parser (BeautifulSoup)
    llm_parser: LLM-based semantic parser (Gemini)
    adjudicator: Grounded LLM adjudication with self-correction
"""

from src.qe_tax_rag.extraction.ca.adjudicator import adjudicate

__all__ = [
    "adjudicate",
    "classic_parser",
    "exceptions",
    "llm_parser",
    "schema",
    "settings",
]
