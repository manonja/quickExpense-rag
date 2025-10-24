"""
Property-based tests for YAML serialization roundtrips using Hypothesis.

These tests ensure that RuleSet objects can be serialized to YAML and
deserialized back without data loss, validating the intermediate format
used in the extraction pipeline.
"""

import pytest
import yaml
from hypothesis import given
from qe_tax_rag.extraction.ca.schema import ExtractedRule, RuleSet

from tests.strategies import extracted_rule_strategy, ruleset_strategy


@pytest.mark.unit
@given(ruleset_strategy())
def test_yaml_roundtrip_preserves_ruleset(ruleset: RuleSet) -> None:
    """
    Property: RuleSet → YAML → RuleSet is an identity function.

    Comprehensive test that serialization to YAML and back preserves all data
    exactly, including:
    - Nested structures (RuleSet → rules list)
    - Enums (ApplicabilityType, ExpertSource)
    - Optional fields (section, anchor_id)
    - List fields (rules, applies_to) with order preserved
    - Float precision (confidence_score)
    - All other field types

    Consolidates: test_yaml_preserves_optional_fields, test_yaml_preserves_list_fields,
    test_yaml_preserves_enum_fields, test_yaml_preserves_float_precision

    Args:
        ruleset: Generated RuleSet instance

    """
    # Serialize to YAML
    yaml_data = ruleset.model_dump(mode="json")
    yaml_str = yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False)

    # Deserialize back to RuleSet
    deserialized_data = yaml.safe_load(yaml_str)
    deserialized_ruleset = RuleSet.model_validate(deserialized_data)

    # Postcondition: original and deserialized are equal (checks ALL fields via Pydantic __eq__)
    assert deserialized_ruleset == ruleset
    assert deserialized_ruleset.schema_version == ruleset.schema_version
    assert len(deserialized_ruleset.rules) == len(ruleset.rules)


@pytest.mark.unit
@given(extracted_rule_strategy())
def test_yaml_roundtrip_preserves_extracted_rule(rule: ExtractedRule) -> None:
    """
    Property: ExtractedRule → YAML → ExtractedRule is an identity function.

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
    """
    Property: Pydantic validation constraints are enforced after YAML roundtrip.

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
@given(ruleset_strategy())
def test_yaml_output_is_valid_utf8(ruleset: RuleSet) -> None:
    """
    Property: YAML output is valid UTF-8 text.

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
