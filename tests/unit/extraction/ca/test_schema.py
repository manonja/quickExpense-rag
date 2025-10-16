"""Tests for extraction pipeline data schema."""

from datetime import datetime, timezone

import pytest
import yaml
from pydantic import ValidationError
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
    RuleSet,
)


def test_expert_source_enum_values() -> None:
    """Verify ExpertSource enum has expected values."""
    assert ExpertSource.CLASSIC.value == "classic"
    assert ExpertSource.LLM.value == "llm"
    assert ExpertSource.ADJUDICATED.value == "adjudicated"


def test_applicability_type_enum_values() -> None:
    """Verify ApplicabilityType enum has expected values."""
    assert ApplicabilityType.BUSINESS.value == "business"
    assert ApplicabilityType.FARMING.value == "farming"
    assert ApplicabilityType.FISHING.value == "fishing"


def test_enums_are_string_enums() -> None:
    """Verify enums inherit from str for JSON serialization."""
    assert isinstance(ExpertSource.CLASSIC, str)
    assert isinstance(ExpertSource.LLM, str)
    assert isinstance(ApplicabilityType.BUSINESS, str)

    # Verify string comparison works
    assert ExpertSource.CLASSIC == "classic"
    assert ApplicabilityType.FARMING == "farming"


# ExtractedRule model tests


def test_extracted_rule_creates_with_valid_data() -> None:
    """Verify ExtractedRule can be created with all required fields."""
    rule = ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="Business meals are 50% deductible.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3 – Expenses",
        section="Part 1 – Income/Loss",
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id="tocch3ln8523",
        confidence_score=0.95,
    )

    assert rule.rule_number == 8523
    assert rule.title == "Meals and entertainment"
    assert rule.content == "Business meals are 50% deductible."
    assert rule.applies_to == [ApplicabilityType.BUSINESS]
    assert rule.source_citation == "Line 8523"
    assert rule.chapter == "Chapter 3 – Expenses"
    assert rule.section == "Part 1 – Income/Loss"
    assert rule.source_file == "t4002-5.html"
    assert rule.expert_source == ExpertSource.CLASSIC
    assert rule.anchor_id == "tocch3ln8523"
    assert rule.confidence_score == 0.95


def test_extracted_rule_validates_required_fields() -> None:
    """Verify all required fields must be present."""
    with pytest.raises(ValidationError) as exc_info:
        ExtractedRule(
            rule_number=8523,
            title="Test Rule",
            # Missing content, applies_to, etc.
        )

    errors = exc_info.value.errors()
    assert len(errors) > 0
    missing_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
    assert "content" in missing_fields


def test_extracted_rule_optional_fields_default_to_none() -> None:
    """Verify optional fields (section, anchor_id) default to None."""
    rule = ExtractedRule(
        rule_number=9999,
        title="Test Rule",
        content="Test content without section or anchor.",
        applies_to=[ApplicabilityType.FARMING],
        source_citation="Line 9999",
        chapter="Chapter 1",
        # section and anchor_id omitted
        source_file="test.html",
        expert_source=ExpertSource.LLM,
        confidence_score=0.88,
    )

    assert rule.section is None
    assert rule.anchor_id is None


def test_extracted_rule_applies_to_multiple_types() -> None:
    """Verify applies_to can contain multiple ApplicabilityType values."""
    rule = ExtractedRule(
        rule_number=9270,
        title="Motor vehicle expenses",
        content="Deduct vehicle costs for business and farming.",
        applies_to=[ApplicabilityType.BUSINESS, ApplicabilityType.FARMING],
        source_citation="Line 9270",
        chapter="Chapter 3",
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    assert len(rule.applies_to) == 2
    assert ApplicabilityType.BUSINESS in rule.applies_to
    assert ApplicabilityType.FARMING in rule.applies_to


def test_extracted_rule_applies_to_can_be_empty() -> None:
    """Verify applies_to can be an empty list when no icons present."""
    rule = ExtractedRule(
        rule_number=8810,
        title="Salaries and wages",
        content="Deduct gross salaries.",
        applies_to=[],  # No icons in source HTML
        source_citation="Line 8810",
        chapter="Chapter 3",
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    assert rule.applies_to == []


def test_extracted_rule_validates_confidence_score_range() -> None:
    """Verify confidence_score must be between 0.0 and 1.0."""
    # Test score too high
    with pytest.raises(ValidationError) as exc_info:
        ExtractedRule(
            rule_number=8523,
            title="Test",
            content="Test content",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 1",
            source_file="test.html",
            expert_source=ExpertSource.LLM,
            confidence_score=1.5,  # Invalid: > 1.0
        )

    assert any("less than or equal to 1" in str(e) for e in exc_info.value.errors())

    # Test score too low
    with pytest.raises(ValidationError) as exc_info:
        ExtractedRule(
            rule_number=8523,
            title="Test",
            content="Test content",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 1",
            source_file="test.html",
            expert_source=ExpertSource.LLM,
            confidence_score=-0.1,  # Invalid: < 0.0
        )

    assert any("greater than or equal to 0" in str(e) for e in exc_info.value.errors())


def test_extracted_rule_is_frozen() -> None:
    """Verify ExtractedRule instances are immutable."""
    rule = ExtractedRule(
        rule_number=8523,
        title="Test Rule",
        content="Test content",
        applies_to=[ApplicabilityType.FARMING],
        source_citation="Line 8523",
        chapter="Chapter 1",
        source_file="test.html",
        expert_source=ExpertSource.ADJUDICATED,
        confidence_score=0.9,
    )

    with pytest.raises(ValidationError, match="frozen"):
        rule.content = "Modified text"  # type: ignore[misc]


def test_extracted_rule_forbids_extra_fields() -> None:
    """Verify ExtractedRule rejects extra fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExtractedRule(
            rule_number=8523,
            title="Test",
            content="Test content",
            applies_to=[ApplicabilityType.FISHING],
            source_citation="Line 8523",
            chapter="Chapter 1",
            source_file="test.html",
            expert_source=ExpertSource.LLM,
            confidence_score=0.85,
            extra_field="not allowed",  # type: ignore[call-arg]
        )


def test_extracted_rule_json_serialization() -> None:
    """Verify ExtractedRule can be serialized to and from JSON."""
    original = ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="Test rule for serialization",
        applies_to=[ApplicabilityType.BUSINESS, ApplicabilityType.FISHING],
        source_citation="Line 8523",
        chapter="Chapter 3",
        section="Part 1",
        source_file="t4002-5.html",
        expert_source=ExpertSource.LLM,
        anchor_id="tocch3ln8523",
        confidence_score=0.88,
    )

    # Serialize to JSON
    json_data = original.model_dump_json()
    assert isinstance(json_data, str)
    assert "Test rule for serialization" in json_data
    assert "8523" in json_data

    # Deserialize from JSON
    reconstructed = ExtractedRule.model_validate_json(json_data)
    assert reconstructed == original
    assert reconstructed.rule_number == 8523
    assert reconstructed.expert_source == ExpertSource.LLM
    assert len(reconstructed.applies_to) == 2


# RuleSet model tests


def test_ruleset_creates_with_rules_list() -> None:
    """Verify RuleSet can be created with list of rules and metadata."""
    rule1 = ExtractedRule(
        rule_number=8523,
        title="First rule",
        content="Content for first rule",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=0.95,
    )
    rule2 = ExtractedRule(
        rule_number=9270,
        title="Second rule",
        content="Content for second rule",
        applies_to=[ApplicabilityType.FARMING],
        source_citation="Line 9270",
        chapter="Chapter 3",
        source_file="t4002-5.html",
        expert_source=ExpertSource.LLM,
        confidence_score=0.88,
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    ruleset = RuleSet(
        rules=[rule1, rule2],
        schema_version="1.0",
        extraction_timestamp=timestamp,
    )

    assert len(ruleset.rules) == 2
    assert ruleset.rules[0].rule_number == 8523
    assert ruleset.rules[1].rule_number == 9270
    assert ruleset.schema_version == "1.0"
    assert ruleset.extraction_timestamp == timestamp


def test_ruleset_requires_metadata() -> None:
    """Verify RuleSet requires schema_version and extraction_timestamp."""
    rule = ExtractedRule(
        rule_number=8523,
        title="Test Rule",
        content="Test content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 1",
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=0.95,
    )

    # Missing schema_version and extraction_timestamp
    with pytest.raises(ValidationError) as exc_info:
        RuleSet(rules=[rule])  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    missing_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
    assert "schema_version" in missing_fields
    assert "extraction_timestamp" in missing_fields


def test_ruleset_is_frozen() -> None:
    """Verify RuleSet instances are immutable."""
    rule = ExtractedRule(
        rule_number=8523,
        title="Test Rule",
        content="Test content",
        applies_to=[ApplicabilityType.FISHING],
        source_citation="Line 8523",
        chapter="Chapter 1",
        source_file="test.html",
        expert_source=ExpertSource.ADJUDICATED,
        confidence_score=0.92,
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    ruleset = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp=timestamp,
    )

    with pytest.raises(ValidationError, match="frozen"):
        ruleset.schema_version = "2.0"  # type: ignore[misc]


def test_ruleset_forbids_extra_fields() -> None:
    """Verify RuleSet rejects extra fields."""
    rule = ExtractedRule(
        rule_number=8523,
        title="Test Rule",
        content="Test content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 1",
        source_file="test.html",
        expert_source=ExpertSource.LLM,
        confidence_score=0.87,
    )

    timestamp = datetime.now(timezone.utc).isoformat()

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RuleSet(
            rules=[rule],
            schema_version="1.0",
            extraction_timestamp=timestamp,
            extra_field="not allowed",  # type: ignore[call-arg]
        )


def test_ruleset_yaml_serialization() -> None:
    """Verify RuleSet can be serialized to and from YAML."""
    rule = ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="Test YAML serialization",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        section="Part 1",
        source_file="t4002-5.html",
        expert_source=ExpertSource.ADJUDICATED,
        anchor_id="tocch3ln8523",
        confidence_score=0.96,
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    original = RuleSet(
        rules=[rule],
        schema_version="1.0",
        extraction_timestamp=timestamp,
    )

    # Serialize to YAML (use mode='json' to convert enums to strings)
    yaml_str = yaml.dump(
        original.model_dump(mode="json"),
        default_flow_style=False,
        allow_unicode=True,
    )
    assert isinstance(yaml_str, str)
    assert "Test YAML serialization" in yaml_str
    assert "8523" in yaml_str
    assert "Line 8523" in yaml_str

    # Deserialize from YAML
    yaml_data = yaml.safe_load(yaml_str)
    reconstructed = RuleSet.model_validate(yaml_data)

    assert len(reconstructed.rules) == 1
    assert reconstructed.rules[0].rule_number == 8523
    assert reconstructed.rules[0].title == "Meals and entertainment"
    assert reconstructed.rules[0].content == "Test YAML serialization"
    assert reconstructed.schema_version == "1.0"
    assert reconstructed.extraction_timestamp == timestamp
