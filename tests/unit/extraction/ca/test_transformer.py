"""Unit tests for YAMLTransformer (TICKET T2.1: Core Transformer Module).

Test-Driven Development approach following RED→GREEN→REFACTOR cycle:
1. Write failing test (RED)
2. Implement minimal code to pass (GREEN)
3. Refactor and commit

This module tests the transformation from ExtractedRule YAML to ParsedDocument JSONL.

Architecture:
    Input:  YAML files with ExtractedRule schema (from adjudicator)
    Output: JSONL files with ParsedDocument schema (for database builder)

Test Coverage:
    - Exception hierarchy (CriticalTransformationError, SkippableTransformationError)
    - Rule grouping by section_title
    - Individual rule transformation to TextChunk
    - Expense type classification (keyword-based)
    - Metadata aggregation (province, business_type, expense_type)
    - Section building from grouped rules
    - Document transformation (ExtractedRule → ParsedDocument)
    - YAML loading and parsing
    - JSONL writing and validation
    - Input validation (schema compliance)
    - Output validation (citation format, metadata)
    - Edge cases (empty files, malformed data, missing fields)
"""

import json

import pytest
from pydantic import ValidationError

from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
    RuleSet,
)
from qe_tax_rag.parser.schema import Metadata, ParsedDocument, Section, TextChunk


# ============================================================================
# FIXTURES: Sample YAML input data (ExtractedRule schema)
# ============================================================================

SAMPLE_EXTRACTED_RULES_YAML = """
rules:
  - line_number: 8523
    section_title: "Chapter 1 - General Rules"
    title: "Meal expenses"
    content: "You can deduct 50% of meals and entertainment expenses."
    applies_to:
      - business
    expert_source: adjudicated
    confidence_score: 0.95

  - line_number: 8524
    section_title: "Chapter 1 - General Rules"
    title: "Long-haul truck drivers"
    content: "Long-haul truck drivers may deduct 80% of meal expenses."
    applies_to:
      - business
    expert_source: adjudicated
    confidence_score: 0.92

  - line_number: 9200
    section_title: "Chapter 2 - Vehicle Expenses"
    title: "Motor vehicle expenses"
    content: "You can deduct motor vehicle expenses if you use your vehicle for business purposes."
    applies_to:
      - business
      - farming
    expert_source: llm
    confidence_score: 0.88

metadata:
  document_id: t4002-1
  source_url: https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4002.html
  extraction_date: "2024-12-15T10:30:00Z"
"""

# Expected JSONL output (ParsedDocument schema) - line by line
SAMPLE_PARSED_DOCUMENT_LINE1 = {
    "title": "t4002-1 - Tax Rules",
    "document_id": "t4002-1",
    "metadata": {
        "province": [],
        "business_type": [],
        "expense_type": ["meals"],
        "income_type": ["business"],
    },
    "sections": [
        {
            "section_title": "Chapter 1 - General Rules",
            "section_level": 1,
            "content": [
                {
                    "type": "paragraph",
                    "text": "You can deduct 50% of meals and entertainment expenses.",
                    "citation_id": "LINE-8523",
                    "extraction_source": "adjudicated",
                    "extraction_confidence": 0.95,
                    "source_anchor": "tocch1ln8523",
                },
                {
                    "type": "paragraph",
                    "text": "Long-haul truck drivers may deduct 80% of meal expenses.",
                    "citation_id": "LINE-8524",
                    "extraction_source": "adjudicated",
                    "extraction_confidence": 0.92,
                    "source_anchor": "tocch1ln8524",
                },
            ],
        },
        {
            "section_title": "Chapter 2 - Vehicle Expenses",
            "section_level": 1,
            "content": [
                {
                    "type": "paragraph",
                    "text": "You can deduct motor vehicle expenses if you use your vehicle for business purposes.",
                    "citation_id": "LINE-9200",
                    "extraction_source": "llm",
                    "extraction_confidence": 0.88,
                    "source_anchor": "tocch2ln9200",
                }
            ],
        },
    ],
}


# ============================================================================
# TESTS: Exception Hierarchy
# ============================================================================


def test_critical_transformation_error_inherits_from_exception():
    """CriticalTransformationError should inherit from Exception."""
    from qe_tax_rag.extraction.ca.transformer import CriticalTransformationError

    assert issubclass(CriticalTransformationError, Exception)


def test_skippable_transformation_error_inherits_from_exception():
    """SkippableTransformationError should inherit from Exception."""
    from qe_tax_rag.extraction.ca.transformer import SkippableTransformationError

    assert issubclass(SkippableTransformationError, Exception)


def test_transformation_errors_can_be_raised_with_message():
    """Both error types should accept and preserve error messages."""
    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        SkippableTransformationError,
    )

    critical_msg = "Critical: Invalid schema"
    skippable_msg = "Warning: Missing optional field"

    with pytest.raises(CriticalTransformationError) as exc_info:
        raise CriticalTransformationError(critical_msg)
    assert critical_msg in str(exc_info.value)

    with pytest.raises(SkippableTransformationError) as exc_info:
        raise SkippableTransformationError(skippable_msg)
    assert skippable_msg in str(exc_info.value)
