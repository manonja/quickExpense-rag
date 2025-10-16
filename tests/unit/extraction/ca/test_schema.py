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
        citation_id="S1-F2-C3-p4.5",
        rule_text="Business meals are 50% deductible.",
        expert_source=ExpertSource.CLASSIC,
        applicability=ApplicabilityType.BUSINESS,
        confidence_score=0.95,
        section="1",
        form="2",
        chapter="3",
        page="4.5",
    )

    assert rule.citation_id == "S1-F2-C3-p4.5"
    assert rule.rule_text == "Business meals are 50% deductible."
    assert rule.expert_source == ExpertSource.CLASSIC
    assert rule.applicability == ApplicabilityType.BUSINESS
    assert rule.confidence_score == 0.95
    assert rule.section == "1"
    assert rule.form == "2"
    assert rule.chapter == "3"
    assert rule.page == "4.5"


def test_extracted_rule_validates_required_fields() -> None:
    """Verify all required fields must be present."""
    with pytest.raises(ValidationError) as exc_info:
        ExtractedRule(
            citation_id="S1-F2-C3-p4.5",
            # Missing rule_text, expert_source, etc.
        )

    errors = exc_info.value.errors()
    assert len(errors) > 0
    missing_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
    assert "rule_text" in missing_fields


def test_extracted_rule_validates_confidence_score_range() -> None:
    """Verify confidence_score must be between 0.0 and 1.0."""
    # Test score too high
    with pytest.raises(ValidationError) as exc_info:
        ExtractedRule(
            citation_id="S1-F2-C3-p4.5",
            rule_text="Test rule",
            expert_source=ExpertSource.LLM,
            applicability=ApplicabilityType.BUSINESS,
            confidence_score=1.5,  # Invalid: > 1.0
            section="1",
            form="2",
            chapter="3",
            page="4.5",
        )

    assert any("less than or equal to 1" in str(e) for e in exc_info.value.errors())

    # Test score too low
    with pytest.raises(ValidationError) as exc_info:
        ExtractedRule(
            citation_id="S1-F2-C3-p4.5",
            rule_text="Test rule",
            expert_source=ExpertSource.LLM,
            applicability=ApplicabilityType.BUSINESS,
            confidence_score=-0.1,  # Invalid: < 0.0
            section="1",
            form="2",
            chapter="3",
            page="4.5",
        )

    assert any("greater than or equal to 0" in str(e) for e in exc_info.value.errors())


def test_extracted_rule_is_frozen() -> None:
    """Verify ExtractedRule instances are immutable."""
    rule = ExtractedRule(
        citation_id="S1-F2-C3-p4.5",
        rule_text="Test rule",
        expert_source=ExpertSource.ADJUDICATED,
        applicability=ApplicabilityType.FARMING,
        confidence_score=0.9,
        section="1",
        form="2",
        chapter="3",
        page="4.5",
    )

    with pytest.raises(ValidationError, match="frozen"):
        rule.rule_text = "Modified text"  # type: ignore[misc]


def test_extracted_rule_forbids_extra_fields() -> None:
    """Verify ExtractedRule rejects extra fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExtractedRule(
            citation_id="S1-F2-C3-p4.5",
            rule_text="Test rule",
            expert_source=ExpertSource.LLM,
            applicability=ApplicabilityType.FISHING,
            confidence_score=0.85,
            section="1",
            form="2",
            chapter="3",
            page="4.5",
            extra_field="not allowed",  # type: ignore[call-arg]
        )


def test_extracted_rule_json_serialization() -> None:
    """Verify ExtractedRule can be serialized to and from JSON."""
    original = ExtractedRule(
        citation_id="S1-F2-C3-p4.5",
        rule_text="Test rule for serialization",
        expert_source=ExpertSource.LLM,
        applicability=ApplicabilityType.BUSINESS,
        confidence_score=0.88,
        section="1",
        form="2",
        chapter="3",
        page="4.5",
    )

    # Serialize to JSON
    json_data = original.model_dump_json()
    assert isinstance(json_data, str)
    assert "Test rule for serialization" in json_data

    # Deserialize from JSON
    reconstructed = ExtractedRule.model_validate_json(json_data)
    assert reconstructed == original
    assert reconstructed.citation_id == "S1-F2-C3-p4.5"
    assert reconstructed.expert_source == ExpertSource.LLM


# RuleSet model tests


def test_ruleset_creates_with_rules_list() -> None:
    """Verify RuleSet can be created with list of rules and metadata."""
    rule1 = ExtractedRule(
        citation_id="S1-F2-C3-p4.5",
        rule_text="First rule",
        expert_source=ExpertSource.CLASSIC,
        applicability=ApplicabilityType.BUSINESS,
        confidence_score=0.95,
        section="1",
        form="2",
        chapter="3",
        page="4.5",
    )
    rule2 = ExtractedRule(
        citation_id="S2-F3-C4-p5.6",
        rule_text="Second rule",
        expert_source=ExpertSource.LLM,
        applicability=ApplicabilityType.FARMING,
        confidence_score=0.88,
        section="2",
        form="3",
        chapter="4",
        page="5.6",
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    ruleset = RuleSet(
        rules=[rule1, rule2],
        schema_version="1.0",
        extraction_timestamp=timestamp,
    )

    assert len(ruleset.rules) == 2
    assert ruleset.rules[0].citation_id == "S1-F2-C3-p4.5"
    assert ruleset.rules[1].citation_id == "S2-F3-C4-p5.6"
    assert ruleset.schema_version == "1.0"
    assert ruleset.extraction_timestamp == timestamp


def test_ruleset_requires_metadata() -> None:
    """Verify RuleSet requires schema_version and extraction_timestamp."""
    rule = ExtractedRule(
        citation_id="S1-F2-C3-p4.5",
        rule_text="Test rule",
        expert_source=ExpertSource.CLASSIC,
        applicability=ApplicabilityType.BUSINESS,
        confidence_score=0.95,
        section="1",
        form="2",
        chapter="3",
        page="4.5",
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
        citation_id="S1-F2-C3-p4.5",
        rule_text="Test rule",
        expert_source=ExpertSource.ADJUDICATED,
        applicability=ApplicabilityType.FISHING,
        confidence_score=0.92,
        section="1",
        form="2",
        chapter="3",
        page="4.5",
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
        citation_id="S1-F2-C3-p4.5",
        rule_text="Test rule",
        expert_source=ExpertSource.LLM,
        applicability=ApplicabilityType.BUSINESS,
        confidence_score=0.87,
        section="1",
        form="2",
        chapter="3",
        page="4.5",
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
        citation_id="S1-F2-C3-p4.5",
        rule_text="Test YAML serialization",
        expert_source=ExpertSource.ADJUDICATED,
        applicability=ApplicabilityType.BUSINESS,
        confidence_score=0.96,
        section="1",
        form="2",
        chapter="3",
        page="4.5",
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
    assert "S1-F2-C3-p4.5" in yaml_str

    # Deserialize from YAML
    yaml_data = yaml.safe_load(yaml_str)
    reconstructed = RuleSet.model_validate(yaml_data)

    assert len(reconstructed.rules) == 1
    assert reconstructed.rules[0].citation_id == "S1-F2-C3-p4.5"
    assert reconstructed.rules[0].rule_text == "Test YAML serialization"
    assert reconstructed.schema_version == "1.0"
    assert reconstructed.extraction_timestamp == timestamp
