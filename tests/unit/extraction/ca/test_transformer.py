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

import pytest
