"""Tests for extraction pipeline data schema."""

import pytest
from pydantic import ValidationError

from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
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
