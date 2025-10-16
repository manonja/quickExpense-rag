"""
Canadian tax document extraction pipeline.

This package provides HTML-to-YAML extraction for CRA tax documents using
a Mixture-of-Experts approach with grounded adjudication.

Modules:
    schemas: Pydantic models for extraction data structures
    settings: Configuration management with pydantic-settings
    exceptions: Custom exception hierarchy
    classic_parser: Rule-based HTML parser (BeautifulSoup)
    llm_parser: LLM-based semantic parser (Gemini)
"""

__all__ = [
    "classic_parser",
    "llm_parser",
    "schemas",
    "settings",
    "exceptions",
]
