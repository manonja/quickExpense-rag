"""
Unit tests for YAMLTransformer (TICKET T2.1: Core Transformer Module).

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
# PYTEST FIXTURES: Test data for transformer tests
# ============================================================================


@pytest.fixture
def sample_rules_multiple_files() -> list[ExtractedRule]:
    """Create rules from multiple source files."""
    return [
        ExtractedRule(
            rule_number=8523,
            title="Meals",
            content="...",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section=None,
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
        ExtractedRule(
            rule_number=9200,
            title="Travel",
            content="...",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 9200",
            chapter="Chapter 3",
            section=None,
            source_file="t4002-6.html",  # Different file
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
    ]


@pytest.fixture
def sample_rule_with_section() -> ExtractedRule:
    """Create a rule with section information."""
    return ExtractedRule(
        rule_number=8523,
        title="Meal expenses",
        content="You can deduct 50% of meals and entertainment expenses.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 1",
        section="General Rules",
        source_file="t4002-5.html",
        expert_source=ExpertSource.ADJUDICATED,
        confidence_score=0.95,
    )


@pytest.fixture
def sample_rule_without_section() -> ExtractedRule:
    """Create a rule without section (only chapter)."""
    return ExtractedRule(
        rule_number=9200,
        title="Vehicle expenses",
        content="You can deduct motor vehicle expenses for business use.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 9200",
        chapter="Chapter 2",
        section=None,
        source_file="t4002-5.html",
        expert_source=ExpertSource.LLM,
        confidence_score=0.88,
    )


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


# ============================================================================
# TESTS: Group By Source File
# ============================================================================


def test_group_by_source_file(sample_rules_multiple_files: list[ExtractedRule]) -> None:
    """Rules should be grouped by source_file."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    transformer = YAMLTransformer()
    grouped = transformer._group_by_source_file(sample_rules_multiple_files)

    # Should have 2 groups
    assert len(grouped) == 2
    assert "t4002-5.html" in grouped
    assert "t4002-6.html" in grouped

    # Each group should have 1 rule
    assert len(grouped["t4002-5.html"]) == 1
    assert len(grouped["t4002-6.html"]) == 1

    # Verify correct rules in each group
    assert grouped["t4002-5.html"][0].rule_number == 8523
    assert grouped["t4002-6.html"][0].rule_number == 9200


def test_group_by_source_file_empty() -> None:
    """Empty rules list should return empty dict."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    transformer = YAMLTransformer()
    grouped = transformer._group_by_source_file([])

    assert grouped == {}


# ============================================================================
# TESTS: Rule to TextChunk Conversion
# ============================================================================


def test_rule_to_text_chunk_with_section(
    sample_rule_with_section: ExtractedRule,
) -> None:
    """Convert ExtractedRule to TextChunk with all metadata."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    transformer = YAMLTransformer()
    chunk = transformer._rule_to_text_chunk(sample_rule_with_section)

    # Verify basic structure
    assert chunk.type == "paragraph"
    assert chunk.text == "You can deduct 50% of meals and entertainment expenses."

    # Verify citation ID format: LINE-{rule_number}
    assert chunk.citation_id == "LINE-8523"

    # Verify extraction metadata
    assert chunk.extraction_source == "adjudicated"
    assert chunk.extraction_confidence == 0.95

    # Verify source anchor format: {chapter}{section}ln{rule_number} (normalized)
    # "Chapter 1" → "ch1", "General Rules" → "generalrules", line → "ln8523"
    assert chunk.source_anchor == "ch1generalrulesln8523"


def test_rule_to_text_chunk_without_section(
    sample_rule_without_section: ExtractedRule,
) -> None:
    """Convert rule without section (only chapter)."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    transformer = YAMLTransformer()
    chunk = transformer._rule_to_text_chunk(sample_rule_without_section)

    # Verify basic structure
    assert chunk.type == "paragraph"
    assert chunk.text == "You can deduct motor vehicle expenses for business use."

    # Verify citation ID
    assert chunk.citation_id == "LINE-9200"

    # Verify extraction metadata
    assert chunk.extraction_source == "llm"
    assert chunk.extraction_confidence == 0.88

    # Verify source anchor without section: {chapter}ln{rule_number}
    # "Chapter 2" → "ch2", no section, line → "ln9200"
    assert chunk.source_anchor == "ch2ln9200"


def test_rule_to_text_chunk_expert_source_mapping() -> None:
    """Verify expert_source enum values map to extraction_source strings."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    transformer = YAMLTransformer()

    # Test CLASSIC → "classic"
    rule_classic = ExtractedRule(
        rule_number=1000,
        title="Test",
        content="Content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 1000",
        chapter="Chapter 1",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )
    chunk = transformer._rule_to_text_chunk(rule_classic)
    assert chunk.extraction_source == "classic"

    # Test LLM → "llm"
    rule_llm = ExtractedRule(
        rule_number=2000,
        title="Test",
        content="Content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 2000",
        chapter="Chapter 1",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.LLM,
        confidence_score=0.8,
    )
    chunk = transformer._rule_to_text_chunk(rule_llm)
    assert chunk.extraction_source == "llm"

    # Test ADJUDICATED → "adjudicated"
    rule_adj = ExtractedRule(
        rule_number=3000,
        title="Test",
        content="Content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 3000",
        chapter="Chapter 1",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.ADJUDICATED,
        confidence_score=0.95,
    )
    chunk = transformer._rule_to_text_chunk(rule_adj)
    assert chunk.extraction_source == "adjudicated"


def test_rule_to_text_chunk_preserves_confidence_score() -> None:
    """Confidence scores should be preserved exactly (no rounding)."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    transformer = YAMLTransformer()

    # Test various confidence scores
    test_scores = [0.0, 0.5, 0.88, 0.95, 1.0, 0.123456]

    for score in test_scores:
        rule = ExtractedRule(
            rule_number=1000,
            title="Test",
            content="Content",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 1000",
            chapter="Chapter 1",
            section=None,
            source_file="test.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=score,
        )
        chunk = transformer._rule_to_text_chunk(rule)
        assert chunk.extraction_confidence == score


# ============================================================================
# TESTS: Expense Type Classifier
# ============================================================================


def test_expense_type_inference_meals() -> None:
    """Meals keywords should infer meals type."""
    from qe_tax_rag.extraction.ca.transformer import ExpenseTypeClassifier

    rule = ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="You can deduct 50% of restaurant and dining expenses...",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        section=None,
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    classifier = ExpenseTypeClassifier()
    types = classifier.infer_expense_types(rule)

    assert "meals" in types


def test_expense_type_inference_vehicle() -> None:
    """Vehicle keywords should infer vehicle type."""
    from qe_tax_rag.extraction.ca.transformer import ExpenseTypeClassifier

    rule = ExtractedRule(
        rule_number=9200,
        title="Motor vehicle expenses",
        content="Deductible car expenses include fuel, mileage, maintenance...",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 9200",
        chapter="Chapter 3",
        section=None,
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    classifier = ExpenseTypeClassifier()
    types = classifier.infer_expense_types(rule)

    assert "vehicle" in types


def test_expense_type_inference_multiple() -> None:
    """Rule can match multiple expense types."""
    from qe_tax_rag.extraction.ca.transformer import ExpenseTypeClassifier

    rule = ExtractedRule(
        rule_number=9999,
        title="Travel and accommodation",
        content="Hotel, airfare, and restaurant meals during business trips...",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 9999",
        chapter="Chapter 3",
        section=None,
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    classifier = ExpenseTypeClassifier()
    types = classifier.infer_expense_types(rule)

    # Should match both travel and meals
    assert "travel" in types
    assert "meals" in types


def test_expense_type_inference_fallback() -> None:
    """No matches should return 'general'."""
    from qe_tax_rag.extraction.ca.transformer import ExpenseTypeClassifier

    rule = ExtractedRule(
        rule_number=9999,
        title="Miscellaneous",
        content="Other deductible expenses...",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 9999",
        chapter="Chapter 3",
        section=None,
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    classifier = ExpenseTypeClassifier()
    types = classifier.infer_expense_types(rule)

    assert types == ["general"]


def test_expense_type_case_insensitive() -> None:
    """Matching should be case-insensitive."""
    from qe_tax_rag.extraction.ca.transformer import ExpenseTypeClassifier

    rule = ExtractedRule(
        rule_number=9999,
        title="MEALS AND ENTERTAINMENT",
        content="RESTAURANT expenses...",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 9999",
        chapter="Chapter 3",
        section=None,
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    classifier = ExpenseTypeClassifier()
    types = classifier.infer_expense_types(rule)

    assert "meals" in types


def test_expense_type_inference_avoids_partial_word_match() -> None:
    """Substring matches should be avoided; only whole words should match."""
    from qe_tax_rag.extraction.ca.transformer import ExpenseTypeClassifier

    # "different" contains "rent", but should not match "home_office"
    rule = ExtractedRule(
        rule_number=9998,
        title="A different kind of rule",
        content="This rule is about something completely different.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 9998",
        chapter="Chapter 3",
        section=None,
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    classifier = ExpenseTypeClassifier()
    types = classifier.infer_expense_types(rule)

    # It should fall back to "general" and not match "home_office"
    assert types == ["general"]
    assert "home_office" not in types


# ============================================================================
# TESTS: Metadata Aggregation
# ============================================================================


def test_aggregate_metadata() -> None:
    """Metadata should aggregate from all rules in document."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    rules = [
        ExtractedRule(
            rule_number=8523,
            title="Meals",
            content="restaurant dining",
            applies_to=[ApplicabilityType.BUSINESS, ApplicabilityType.FISHING],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section=None,
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
        ExtractedRule(
            rule_number=9200,
            title="Vehicle",
            content="car mileage fuel",
            applies_to=[ApplicabilityType.FARMING],
            source_citation="Line 9200",
            chapter="Chapter 3",
            section=None,
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
    ]

    transformer = YAMLTransformer()
    metadata = transformer._aggregate_metadata(rules)

    # income_type from applies_to
    assert set(metadata.income_type) == {"business", "fishing", "farming"}

    # expense_type from inference
    assert "meals" in metadata.expense_type
    assert "vehicle" in metadata.expense_type

    # Federal rules have no province/business_type
    assert metadata.province == []
    assert metadata.business_type == []


# ============================================================================
# TESTS: Build Sections
# ============================================================================


def test_build_sections_single_chapter() -> None:
    """Rules should be organized into sections by chapter."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    rules = [
        ExtractedRule(
            rule_number=8523,
            title="Rule 1",
            content="Content 1",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 3 - Expenses",
            section="Part 4",
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
        ExtractedRule(
            rule_number=9200,
            title="Rule 2",
            content="Content 2",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 9200",
            chapter="Chapter 3 - Expenses",  # Same chapter
            section="Part 5",  # Different section
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
    ]

    transformer = YAMLTransformer()
    sections = transformer._build_sections(rules)

    # Should have 1 section (flattened by chapter)
    assert len(sections) == 1
    assert sections[0].section_title == "Chapter 3 - Expenses"
    assert sections[0].section_level == 1

    # Should have 2 chunks (one per rule)
    assert len(sections[0].content) == 2


def test_build_sections_multiple_chapters() -> None:
    """Multiple chapters should create multiple sections."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    rules = [
        ExtractedRule(
            rule_number=8523,
            title="Rule 1",
            content="Content 1",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section=None,
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
        ExtractedRule(
            rule_number=9200,
            title="Rule 2",
            content="Content 2",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 9200",
            chapter="Chapter 4",  # Different chapter
            section=None,
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
    ]

    transformer = YAMLTransformer()
    sections = transformer._build_sections(rules)

    # Should have 2 sections
    assert len(sections) == 2
    chapter_titles = {s.section_title for s in sections}
    assert chapter_titles == {"Chapter 3", "Chapter 4"}


# ============================================================================
# TESTS: Document Transformation
# ============================================================================


def test_transform_rules_to_document() -> None:
    """Rules should transform to complete ParsedDocument."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    rules = [
        ExtractedRule(
            rule_number=8523,
            title="Meals",
            content="restaurant expenses",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 3",
            section=None,
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            confidence_score=1.0,
        ),
    ]

    transformer = YAMLTransformer()
    doc = transformer._transform_rules_to_document("t4002-5.html", rules)

    # Check document structure
    assert doc.document_id == "t4002-5"
    assert "T4002" in doc.title.upper()
    assert "5" in doc.title

    # Check sections
    assert len(doc.sections) == 1
    assert doc.sections[0].section_title == "Chapter 3"

    # Check content
    assert len(doc.sections[0].content) == 1

    # Check metadata
    assert "business" in doc.metadata.income_type
    assert "meals" in doc.metadata.expense_type


def test_transform_rules_to_document_title_generation() -> None:
    """Document title should be generated from source file."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    transformer = YAMLTransformer()

    # Test various source file formats
    doc1 = transformer._transform_rules_to_document("t4002-5.html", [])
    assert doc1.document_id == "t4002-5"
    assert doc1.title == "CRA T4002 - PART 5"

    doc2 = transformer._transform_rules_to_document("t4002-10.html", [])
    assert doc2.document_id == "t4002-10"
    assert doc2.title == "CRA T4002 - PART 10"


# ============================================================================
# TESTS: YAML Loading
# ============================================================================


def test_load_yaml(tmp_path) -> None:
    """Should load and parse YAML file to RuleSet."""
    from pathlib import Path

    import yaml
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    # Create test YAML file
    yaml_content = {
        "schema_version": "1.0",
        "extraction_timestamp": "2025-01-01T00:00:00Z",
        "rules": [
            {
                "rule_number": 8523,
                "title": "Meals",
                "content": "Test content",
                "applies_to": ["business"],
                "source_citation": "Line 8523",
                "chapter": "Chapter 3",
                "section": None,
                "source_file": "t4002-5.html",
                "expert_source": "classic",
                "confidence_score": 1.0,
            }
        ],
    }

    yaml_path = tmp_path / "test_rules.yml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f)

    # Load YAML
    transformer = YAMLTransformer()
    rule_set = transformer._load_yaml(yaml_path)

    assert rule_set.schema_version == "1.0"
    assert len(rule_set.rules) == 1
    assert rule_set.rules[0].rule_number == 8523


# ============================================================================
# TESTS: JSONL Writing
# ============================================================================


def test_write_jsonl(tmp_path) -> None:
    """Should write ParsedDocuments to JSONL file."""
    from pathlib import Path

    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    # Create test documents
    documents = [
        ParsedDocument(
            title="Test Doc 1",
            document_id="test-1",
            metadata=Metadata(),
            sections=[],
        ),
        ParsedDocument(
            title="Test Doc 2",
            document_id="test-2",
            metadata=Metadata(),
            sections=[],
        ),
    ]

    jsonl_path = tmp_path / "output" / "test.jsonl"

    # Write JSONL
    transformer = YAMLTransformer()
    transformer._write_jsonl(documents, jsonl_path)

    # Verify file exists
    assert jsonl_path.exists()

    # Verify content
    with open(jsonl_path) as f:
        lines = f.readlines()
        assert len(lines) == 2

        # Verify each line is valid JSON
        doc1 = json.loads(lines[0])
        assert doc1["document_id"] == "test-1"

        doc2 = json.loads(lines[1])
        assert doc2["document_id"] == "test-2"


# ============================================================================
# TESTS: Input Validation
# ============================================================================


def test_validate_yaml_input_duplicate_rule_numbers() -> None:
    """Should raise error on duplicate rule_numbers."""
    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        YAMLTransformer,
    )

    rule_set = RuleSet(
        schema_version="1.0",
        extraction_timestamp="2025-01-01T00:00:00Z",
        rules=[
            ExtractedRule(
                rule_number=8523,  # Duplicate
                title="Rule 1",
                content="...",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="Chapter 3",
                section=None,
                source_file="t4002-5.html",
                expert_source=ExpertSource.CLASSIC,
                confidence_score=1.0,
            ),
            ExtractedRule(
                rule_number=8523,  # Duplicate
                title="Rule 2",
                content="...",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="Chapter 3",
                section=None,
                source_file="t4002-5.html",
                expert_source=ExpertSource.CLASSIC,
                confidence_score=1.0,
            ),
        ],
    )

    transformer = YAMLTransformer()

    with pytest.raises(CriticalTransformationError, match="Duplicate rule_numbers"):
        transformer._validate_yaml_input(rule_set)


def test_validate_yaml_input_missing_source_file() -> None:
    """Should raise error on missing source_file."""
    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        YAMLTransformer,
    )

    rule_set = RuleSet(
        schema_version="1.0",
        extraction_timestamp="2025-01-01T00:00:00Z",
        rules=[
            ExtractedRule(
                rule_number=8523,
                title="Rule 1",
                content="...",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="Chapter 3",
                section=None,
                source_file="",  # Empty source_file
                expert_source=ExpertSource.CLASSIC,
                confidence_score=1.0,
            ),
        ],
    )

    transformer = YAMLTransformer()

    with pytest.raises(
        CriticalTransformationError, match="missing required field 'source_file'"
    ):
        transformer._validate_yaml_input(rule_set)


def test_validate_yaml_input_missing_chapter() -> None:
    """Should raise error on missing chapter."""
    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        YAMLTransformer,
    )

    rule_set = RuleSet(
        schema_version="1.0",
        extraction_timestamp="2025-01-01T00:00:00Z",
        rules=[
            ExtractedRule(
                rule_number=8523,
                title="Rule 1",
                content="...",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="",  # Empty chapter
                section=None,
                source_file="t4002-5.html",
                expert_source=ExpertSource.CLASSIC,
                confidence_score=1.0,
            ),
        ],
    )

    transformer = YAMLTransformer()

    with pytest.raises(
        CriticalTransformationError, match="missing required field 'chapter'"
    ):
        transformer._validate_yaml_input(rule_set)


def test_validate_yaml_input_valid() -> None:
    """Should pass validation for valid RuleSet."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    rule_set = RuleSet(
        schema_version="1.0",
        extraction_timestamp="2025-01-01T00:00:00Z",
        rules=[
            ExtractedRule(
                rule_number=8523,
                title="Rule 1",
                content="...",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="Chapter 3",
                section=None,
                source_file="t4002-5.html",
                expert_source=ExpertSource.CLASSIC,
                confidence_score=1.0,
            ),
        ],
    )

    transformer = YAMLTransformer()
    # Should not raise
    transformer._validate_yaml_input(rule_set)


def test_validate_yaml_input_unsupported_schema_version() -> None:
    """Should raise error on unsupported schema version."""
    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        YAMLTransformer,
    )

    rule_set = RuleSet(
        schema_version="2.0",  # Unsupported version
        extraction_timestamp="2025-01-01T00:00:00Z",
        rules=[
            ExtractedRule(
                rule_number=8523,
                title="Rule 1",
                content="...",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="Chapter 3",
                section=None,
                source_file="t4002-5.html",
                expert_source=ExpertSource.CLASSIC,
                confidence_score=1.0,
            ),
        ],
    )

    transformer = YAMLTransformer()

    with pytest.raises(
        CriticalTransformationError, match="Unsupported schema version"
    ):
        transformer._validate_yaml_input(rule_set)


def test_validate_yaml_input_supported_schema_version() -> None:
    """Should accept schema version 1.0."""
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    rule_set = RuleSet(
        schema_version="1.0",  # Supported version
        extraction_timestamp="2025-01-01T00:00:00Z",
        rules=[
            ExtractedRule(
                rule_number=8523,
                title="Rule 1",
                content="...",
                applies_to=[ApplicabilityType.BUSINESS],
                source_citation="Line 8523",
                chapter="Chapter 3",
                section=None,
                source_file="t4002-5.html",
                expert_source=ExpertSource.CLASSIC,
                confidence_score=1.0,
            ),
        ],
    )

    transformer = YAMLTransformer()
    # Should not raise
    transformer._validate_yaml_input(rule_set)


# ============================================================================
# TESTS: Output Validation
# ============================================================================


def test_validate_jsonl_output_valid(tmp_path) -> None:
    """Should pass validation for valid JSONL."""
    from pathlib import Path

    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    # Create valid JSONL file
    jsonl_path = tmp_path / "valid.jsonl"
    doc = ParsedDocument(
        title="Test",
        document_id="test-1",
        metadata=Metadata(),
        sections=[],
    )
    with open(jsonl_path, "w") as f:
        f.write(doc.model_dump_json() + "\n")

    # Should not raise
    transformer = YAMLTransformer()
    transformer._validate_jsonl_output(jsonl_path)


def test_validate_jsonl_output_invalid_json(tmp_path) -> None:
    """Should raise error for invalid JSON."""
    from pathlib import Path

    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        YAMLTransformer,
    )

    # Create invalid JSONL file
    jsonl_path = tmp_path / "invalid.jsonl"
    jsonl_path.write_text('{"invalid": "json"\n')  # Missing closing brace

    transformer = YAMLTransformer()

    with pytest.raises(CriticalTransformationError, match="Invalid JSONL"):
        transformer._validate_jsonl_output(jsonl_path)


def test_validate_jsonl_output_invalid_schema(tmp_path) -> None:
    """Should raise error for invalid schema."""
    from pathlib import Path

    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        YAMLTransformer,
    )

    # Create JSONL with invalid schema
    jsonl_path = tmp_path / "invalid_schema.jsonl"
    jsonl_path.write_text('{"wrong": "schema"}\n')

    transformer = YAMLTransformer()

    with pytest.raises(CriticalTransformationError, match="Invalid JSONL"):
        transformer._validate_jsonl_output(jsonl_path)


# ============================================================================
# TESTS: End-to-End Transformation
# ============================================================================


def test_transform_yaml_to_jsonl_end_to_end(tmp_path) -> None:
    """Full transformation pipeline should work end-to-end."""
    from pathlib import Path

    import yaml
    from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

    # Create test YAML
    yaml_content = {
        "schema_version": "1.0",
        "extraction_timestamp": "2025-01-01T00:00:00Z",
        "rules": [
            {
                "rule_number": 8523,
                "title": "Meals and entertainment",
                "content": "You can deduct 50% of restaurant expenses...",
                "applies_to": ["business", "fishing"],
                "source_citation": "Line 8523",
                "chapter": "Chapter 3 – Expenses",
                "section": "Part 4",
                "source_file": "t4002-5.html",
                "expert_source": "adjudicated",
                "anchor_id": "tocch3ln8523",
                "confidence_score": 0.95,
            },
            {
                "rule_number": 9200,
                "title": "Motor vehicle",
                "content": "Car mileage fuel...",
                "applies_to": ["business"],
                "source_citation": "Line 9200",
                "chapter": "Chapter 3 – Expenses",
                "section": "Part 5",
                "source_file": "t4002-5.html",
                "expert_source": "classic",
                "confidence_score": 1.0,
            },
        ],
    }

    yaml_path = tmp_path / "rules.yml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f)

    jsonl_path = tmp_path / "chunks.jsonl"

    # Run transformation
    transformer = YAMLTransformer()
    report = transformer.transform_yaml_to_jsonl(
        yaml_path=yaml_path,
        jsonl_path=jsonl_path,
        continue_on_error=True,
    )

    # Verify report
    assert report.total_rules == 2
    assert report.successful == 2
    assert report.skipped == 0
    assert len(report.errors) == 0

    # Verify JSONL output
    assert jsonl_path.exists()
    with open(jsonl_path) as f:
        lines = f.readlines()
        assert len(lines) == 1  # One document (grouped by source_file)

        doc_data = json.loads(lines[0])
        assert doc_data["document_id"] == "t4002-5"
        assert set(doc_data["metadata"]["income_type"]) == {"business", "fishing"}
        assert "meals" in doc_data["metadata"]["expense_type"]
        assert "vehicle" in doc_data["metadata"]["expense_type"]

        # Verify citations
        chunks = doc_data["sections"][0]["content"]
        citations = [c["citation_id"] for c in chunks]
        assert "LINE-8523" in citations
        assert "LINE-9200" in citations


def test_transform_yaml_to_jsonl_with_errors(tmp_path) -> None:
    """Should handle errors gracefully with continue_on_error."""
    from pathlib import Path

    import yaml
    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        YAMLTransformer,
    )

    # Create YAML with duplicate rule_numbers
    yaml_content = {
        "schema_version": "1.0",
        "extraction_timestamp": "2025-01-01T00:00:00Z",
        "rules": [
            {
                "rule_number": 8523,  # Duplicate
                "title": "Rule 1",
                "content": "...",
                "applies_to": ["business"],
                "source_citation": "Line 8523",
                "chapter": "Chapter 3",
                "section": None,
                "source_file": "t4002-5.html",
                "expert_source": "classic",
                "confidence_score": 1.0,
            },
            {
                "rule_number": 8523,  # Duplicate
                "title": "Rule 2",
                "content": "...",
                "applies_to": ["business"],
                "source_citation": "Line 8523",
                "chapter": "Chapter 3",
                "section": None,
                "source_file": "t4002-5.html",
                "expert_source": "classic",
                "confidence_score": 1.0,
            },
        ],
    }

    yaml_path = tmp_path / "bad_rules.yml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f)

    jsonl_path = tmp_path / "chunks.jsonl"

    # Should raise CriticalTransformationError (duplicate rule_numbers)
    transformer = YAMLTransformer()
    with pytest.raises(CriticalTransformationError, match="Duplicate"):
        transformer.transform_yaml_to_jsonl(
            yaml_path=yaml_path,
            jsonl_path=jsonl_path,
            continue_on_error=True,
        )
