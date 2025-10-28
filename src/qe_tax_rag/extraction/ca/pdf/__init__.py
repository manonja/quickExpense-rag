"""PDF extraction module for Canadian tax documents.

This module provides functionality to extract structured content from PDF files
using a lightweight two-pass approach:

1. Structure Discovery: Detect semantic sections using font metadata
2. Content Extraction: Extract and structure content per section using LLM

The extracted content is compatible with the existing YAML → DatabaseChunk pipeline.
"""

from qe_tax_rag.extraction.ca.pdf.structure_detector import (
    SemanticSection,
    discover_sections,
)

__all__ = [
    "SemanticSection",
    "discover_sections",
]
