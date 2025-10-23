"""Hypothesis strategies for property-based testing."""

from hypothesis import strategies as st
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
    RuleSet,
)


@st.composite
def extracted_rule_strategy(draw):
    """
    Generate valid ExtractedRule with all required fields.

    Generates rules that pass Pydantic validation with:
    - Valid rule_number (1-9999)
    - Non-empty title and content
    - At least one applicability type
    - Required expert metadata (source, confidence, anchor)

    Optional fields (section, anchor_id) are sometimes None to test
    optional field handling.

    Returns:
        ExtractedRule with all fields populated

    """
    return ExtractedRule(
        rule_number=draw(st.integers(min_value=1, max_value=9999)),
        title=draw(
            st.text(
                min_size=1,
                max_size=100,
                alphabet=st.characters(blacklist_categories=("Cs",)),
            )
        ),
        content=draw(
            st.text(
                min_size=10,
                max_size=500,
                alphabet=st.characters(blacklist_categories=("Cs",)),
            )
        ),
        applies_to=draw(
            st.lists(
                st.sampled_from(ApplicabilityType), min_size=1, max_size=3, unique=True
            )
        ),
        source_citation=draw(st.text(min_size=1, max_size=50)),
        chapter=draw(st.text(min_size=1, max_size=100)),
        section=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        source_file=draw(st.text(min_size=1, max_size=50)),
        expert_source=draw(st.sampled_from(ExpertSource)),
        anchor_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        confidence_score=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


@st.composite
def ruleset_strategy(draw, min_rules=1, max_rules=10):
    """
    Generate valid RuleSet with multiple rules.

    Creates RuleSets that pass Pydantic validation with:
    - 1-10 rules (configurable via min/max parameters)
    - Schema version "1.0"
    - Valid ISO 8601 timestamp

    Use this for property-based testing of:
    - YAML serialization/deserialization
    - DatabaseChunk transformation
    - Database constraint enforcement

    Args:
        draw: Hypothesis draw function
        min_rules: Minimum number of rules to generate (default: 1)
        max_rules: Maximum number of rules to generate (default: 10)

    Returns:
        RuleSet with generated rules

    """
    rules = draw(
        st.lists(
            extracted_rule_strategy(),
            min_size=min_rules,
            max_size=max_rules,
        )
    )

    return RuleSet(
        rules=rules,
        schema_version="1.0",
        extraction_timestamp="2025-10-22T00:00:00Z",
    )
