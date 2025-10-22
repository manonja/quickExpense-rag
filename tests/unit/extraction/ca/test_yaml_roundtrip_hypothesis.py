"""Property-based tests for YAML serialization roundtrips using Hypothesis.

These tests ensure that RuleSet objects can be serialized to YAML and
deserialized back without data loss, validating the intermediate format
used in the extraction pipeline.
"""

import yaml
import pytest
from hypothesis import given
from qe_tax_rag.extraction.ca.schema import RuleSet, ExtractedRule
from tests.strategies import ruleset_strategy, extracted_rule_strategy


@pytest.mark.unit
@given(ruleset_strategy())
def test_yaml_roundtrip_preserves_ruleset(ruleset: RuleSet) -> None:
    """Property: RuleSet → YAML → RuleSet is an identity function.

    Serialization to YAML and back should preserve all data exactly,
    including nested structures, enums, and optional fields.

    Args:
        ruleset: Generated RuleSet instance
    """
    # Serialize to YAML
    yaml_data = ruleset.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False)

    # Deserialize back to RuleSet
    deserialized_data = yaml.safe_load(yaml_str)
    deserialized_ruleset = RuleSet.model_validate(deserialized_data)

    # Postcondition: original and deserialized are equal
    assert deserialized_ruleset == ruleset
    assert deserialized_ruleset.schema_version == ruleset.schema_version
    assert len(deserialized_ruleset.rules) == len(ruleset.rules)


@pytest.mark.unit
@given(extracted_rule_strategy())
def test_yaml_roundtrip_preserves_extracted_rule(rule: ExtractedRule) -> None:
    """Property: ExtractedRule → YAML → ExtractedRule is an identity function.

    Individual rules should survive YAML serialization/deserialization.

    Args:
        rule: Generated ExtractedRule instance
    """
    # Serialize to YAML
    yaml_data = rule.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True)

    # Deserialize back to ExtractedRule
    deserialized_data = yaml.safe_load(yaml_str)
    deserialized_rule = ExtractedRule.model_validate(deserialized_data)

    # Postcondition: original and deserialized are equal
    assert deserialized_rule == rule
    assert deserialized_rule.rule_number == rule.rule_number
    assert deserialized_rule.title == rule.title
    assert deserialized_rule.content == rule.content


@pytest.mark.unit
@given(ruleset_strategy())
def test_pydantic_validation_survives_yaml(ruleset: RuleSet) -> None:
    """Property: Pydantic validation constraints are enforced after YAML roundtrip.

    All Pydantic model constraints (frozen=True, extra='forbid') should
    remain enforced after deserialization from YAML.

    Args:
        ruleset: Generated RuleSet instance
    """
    # Serialize and deserialize
    yaml_data = ruleset.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True)
    deserialized_data = yaml.safe_load(yaml_str)
    deserialized_ruleset = RuleSet.model_validate(deserialized_data)

    # Postcondition: Pydantic constraints still enforced
    # Model is frozen - attribute assignment should fail
    with pytest.raises(Exception):  # ValidationError or AttributeError
        deserialized_ruleset.schema_version = "2.0"  # type: ignore[misc]

    # Model forbids extra fields
    invalid_data = deserialized_data.copy()
    invalid_data["extra_field"] = "invalid"

    with pytest.raises(Exception):  # ValidationError
        RuleSet.model_validate(invalid_data)


@pytest.mark.unit
@given(extracted_rule_strategy())
def test_yaml_preserves_optional_fields(rule: ExtractedRule) -> None:
    """Property: Optional fields (section, anchor_id) are preserved correctly.

    YAML should correctly serialize None values and distinguish between
    missing fields and None values.

    Args:
        rule: Generated ExtractedRule instance
    """
    # Serialize to YAML
    yaml_data = rule.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True)

    # Deserialize
    deserialized_data = yaml.safe_load(yaml_str)
    deserialized_rule = ExtractedRule.model_validate(deserialized_data)

    # Postcondition: Optional fields match
    assert deserialized_rule.section == rule.section
    assert deserialized_rule.anchor_id == rule.anchor_id


@pytest.mark.unit
@given(ruleset_strategy())
def test_yaml_preserves_list_fields(ruleset: RuleSet) -> None:
    """Property: List fields (rules, applies_to) are preserved correctly.

    Lists should maintain order, length, and element values after YAML
    serialization.

    Args:
        ruleset: Generated RuleSet instance
    """
    # Serialize and deserialize
    yaml_data = ruleset.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True)
    deserialized_data = yaml.safe_load(yaml_str)
    deserialized_ruleset = RuleSet.model_validate(deserialized_data)

    # Postcondition: List lengths match
    assert len(deserialized_ruleset.rules) == len(ruleset.rules)

    # Postcondition: Each rule's applies_to list is preserved
    for original_rule, deserialized_rule in zip(ruleset.rules, deserialized_ruleset.rules):
        assert deserialized_rule.applies_to == original_rule.applies_to
        assert len(deserialized_rule.applies_to) == len(original_rule.applies_to)


@pytest.mark.unit
@given(extracted_rule_strategy())
def test_yaml_preserves_enum_fields(rule: ExtractedRule) -> None:
    """Property: Enum fields (ApplicabilityType, ExpertSource) serialize correctly.

    Enums should be represented as strings in YAML and deserialize back
    to the correct enum values.

    Args:
        rule: Generated ExtractedRule instance
    """
    # Serialize to YAML
    yaml_data = rule.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True)

    # Check YAML representation (should be strings)
    assert "applies_to:" in yaml_str
    assert "expert_source:" in yaml_str

    # Deserialize and validate
    deserialized_data = yaml.safe_load(yaml_str)
    deserialized_rule = ExtractedRule.model_validate(deserialized_data)

    # Postcondition: Enum values match
    assert deserialized_rule.expert_source == rule.expert_source
    assert deserialized_rule.applies_to == rule.applies_to


@pytest.mark.unit
@given(ruleset_strategy())
def test_yaml_preserves_float_precision(ruleset: RuleSet) -> None:
    """Property: Float fields (confidence_score) maintain precision.

    Confidence scores should serialize with sufficient precision and
    deserialize to the same value (within floating-point tolerance).

    Args:
        ruleset: Generated RuleSet instance
    """
    # Serialize and deserialize
    yaml_data = ruleset.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True)
    deserialized_data = yaml.safe_load(yaml_str)
    deserialized_ruleset = RuleSet.model_validate(deserialized_data)

    # Postcondition: Confidence scores are preserved
    for original_rule, deserialized_rule in zip(ruleset.rules, deserialized_ruleset.rules):
        # Use approximate equality for floats
        assert abs(deserialized_rule.confidence_score - original_rule.confidence_score) < 1e-6


@pytest.mark.unit
@given(ruleset_strategy())
def test_yaml_output_is_valid_utf8(ruleset: RuleSet) -> None:
    """Property: YAML output is valid UTF-8 text.

    All generated YAML should be valid UTF-8 and contain no encoding errors.

    Args:
        ruleset: Generated RuleSet instance
    """
    # Serialize to YAML
    yaml_data = ruleset.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True)

    # Postcondition: YAML is valid UTF-8
    assert isinstance(yaml_str, str)

    # Should be encodable to UTF-8 bytes and back
    yaml_bytes = yaml_str.encode("utf-8")
    decoded = yaml_bytes.decode("utf-8")
    assert decoded == yaml_str
