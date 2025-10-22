"""Property-based tests for Adjudicator using Hypothesis.

These tests ensure the adjudicator correctly merges Classic and LLM parser
outputs while maintaining citation_id uniqueness and data integrity.
"""

import pytest
from hypothesis import given, strategies as st
from qe_tax_rag.extraction.ca.adjudicator import _triage_rules, _normalize_rule_for_comparison
from qe_tax_rag.extraction.ca.schema import ExtractedRule
from tests.strategies import extracted_rule_strategy


@pytest.mark.unit
@given(
    st.lists(extracted_rule_strategy(), min_size=0, max_size=20),
    st.lists(extracted_rule_strategy(), min_size=0, max_size=20),
)
def test_triage_produces_no_duplicate_rule_numbers(
    classic_rules: list[ExtractedRule],
    llm_rules: list[ExtractedRule],
) -> None:
    """Property: Triage categorization produces no duplicate rule_numbers.

    After triaging rules into perfect_matches, conflicts, and orphans,
    each rule_number should appear exactly once across all categories.

    Args:
        classic_rules: List of rules from classic parser
        llm_rules: List of rules from LLM parser
    """
    # Run triage
    triage_result = _triage_rules(classic_rules, llm_rules)

    # Collect all rule_numbers from all categories
    all_rule_numbers = []

    for rule in triage_result.perfect_matches:
        all_rule_numbers.append(rule.rule_number)

    for classic_rule, llm_rule in triage_result.conflicts:
        # Conflicts should have same rule_number from both parsers
        assert classic_rule.rule_number == llm_rule.rule_number
        all_rule_numbers.append(classic_rule.rule_number)

    for orphan in triage_result.orphans:
        all_rule_numbers.append(orphan.rule_number)

    # Postcondition: No duplicates
    assert len(all_rule_numbers) == len(set(all_rule_numbers))


@pytest.mark.unit
@given(st.lists(extracted_rule_strategy(), min_size=1, max_size=20, unique_by=lambda r: r.rule_number))
def test_triage_handles_empty_llm_rules(
    classic_rules: list[ExtractedRule],
) -> None:
    """Property: Triage handles empty LLM rules list gracefully.

    When LLM parser produces no output, all classic rules should be
    categorized as orphans.

    Args:
        classic_rules: List of unique rules from classic parser
    """
    # Run triage with empty LLM list
    triage_result = _triage_rules(classic_rules, [])

    # Postconditions
    assert len(triage_result.perfect_matches) == 0
    assert len(triage_result.conflicts) == 0
    assert len(triage_result.orphans) == len(classic_rules)

    # All orphans should match classic_rules
    orphan_numbers = {r.rule_number for r in triage_result.orphans}
    classic_numbers = {r.rule_number for r in classic_rules}
    assert orphan_numbers == classic_numbers


@pytest.mark.unit
@given(st.lists(extracted_rule_strategy(), min_size=1, max_size=20, unique_by=lambda r: r.rule_number))
def test_triage_handles_empty_classic_rules(
    llm_rules: list[ExtractedRule],
) -> None:
    """Property: Triage handles empty Classic rules list gracefully.

    When Classic parser produces no output, all LLM rules should be
    categorized as orphans.

    Args:
        llm_rules: List of unique rules from LLM parser
    """
    # Run triage with empty Classic list
    triage_result = _triage_rules([], llm_rules)

    # Postconditions
    assert len(triage_result.perfect_matches) == 0
    assert len(triage_result.conflicts) == 0
    assert len(triage_result.orphans) == len(llm_rules)

    # All orphans should match llm_rules
    orphan_numbers = {r.rule_number for r in triage_result.orphans}
    llm_numbers = {r.rule_number for r in llm_rules}
    assert orphan_numbers == llm_numbers


@pytest.mark.unit
@given(st.lists(extracted_rule_strategy(), min_size=0, max_size=20, unique_by=lambda r: r.rule_number))
def test_triage_perfect_matches_when_both_parsers_agree(
    rules: list[ExtractedRule],
) -> None:
    """Property: When both parsers produce identical rules, they are perfect matches.

    If Classic and LLM return the same normalized rules, triage should
    categorize them as perfect matches, not conflicts.

    Args:
        rules: List of unique rules to duplicate across both parsers
    """
    # Use same rules for both parsers
    classic_rules = list(rules)
    llm_rules = list(rules)

    # Run triage
    triage_result = _triage_rules(classic_rules, llm_rules)

    # Postconditions
    assert len(triage_result.perfect_matches) == len(rules)
    assert len(triage_result.conflicts) == 0
    assert len(triage_result.orphans) == 0


@pytest.mark.unit
@given(extracted_rule_strategy())
def test_normalize_rule_is_deterministic(rule: ExtractedRule) -> None:
    """Property: Rule normalization is deterministic.

    Normalizing the same rule multiple times should produce identical results.

    Args:
        rule: An ExtractedRule to normalize
    """
    # Normalize twice
    normalized_1 = _normalize_rule_for_comparison(rule)
    normalized_2 = _normalize_rule_for_comparison(rule)

    # Postcondition: Results are identical
    assert normalized_1 == normalized_2


@pytest.mark.unit
@given(extracted_rule_strategy())
def test_normalize_rule_collapses_whitespace(rule: ExtractedRule) -> None:
    """Property: Normalization collapses consecutive whitespace.

    Multiple spaces, tabs, and newlines should be collapsed to single spaces.

    Args:
        rule: An ExtractedRule to normalize
    """
    normalized = _normalize_rule_for_comparison(rule)

    # Postconditions
    assert "  " not in normalized["content"]  # No double spaces
    assert "\n" not in normalized["content"]  # No newlines
    assert "\t" not in normalized["content"]  # No tabs
    assert normalized["content"] == normalized["content"].strip()  # Trimmed


@pytest.mark.unit
@given(extracted_rule_strategy())
def test_normalize_rule_sorts_applies_to(rule: ExtractedRule) -> None:
    """Property: Normalization sorts applies_to list.

    Different orderings of applies_to should normalize to the same result.

    Args:
        rule: An ExtractedRule to normalize
    """
    normalized = _normalize_rule_for_comparison(rule)

    # Postcondition: applies_to is sorted
    applies_to = normalized["applies_to"]
    assert applies_to == sorted(applies_to)


@pytest.mark.unit
@given(
    st.lists(extracted_rule_strategy(), min_size=1, max_size=10, unique_by=lambda r: r.rule_number)
)
def test_triage_no_null_rule_numbers_in_output(
    rules: list[ExtractedRule],
) -> None:
    """Property: Triage never produces None or 0 rule_numbers.

    All rules in triage output should have valid, positive rule_numbers.

    Args:
        rules: List of unique rules (by rule_number)
    """
    # Duplicate rules for both parsers
    classic_rules = list(rules)
    llm_rules = list(rules)

    # Run triage
    triage_result = _triage_rules(classic_rules, llm_rules)

    # Postcondition: No None or 0 rule_numbers
    for rule in triage_result.perfect_matches:
        assert rule.rule_number is not None
        assert rule.rule_number > 0

    for classic_rule, llm_rule in triage_result.conflicts:
        assert classic_rule.rule_number is not None
        assert classic_rule.rule_number > 0
        assert llm_rule.rule_number is not None
        assert llm_rule.rule_number > 0

    for orphan in triage_result.orphans:
        assert orphan.rule_number is not None
        assert orphan.rule_number > 0


@pytest.mark.unit
@given(
    st.lists(
        extracted_rule_strategy(),
        min_size=2,
        max_size=10,
        unique_by=lambda r: r.rule_number,
    )
)
def test_triage_total_count_matches_input(
    classic_rules: list[ExtractedRule],
) -> None:
    """Property: Total triage output count matches unique input rule_numbers.

    The sum of perfect_matches + conflicts + orphans should equal the
    number of unique rule_numbers across both parser outputs.

    Args:
        classic_rules: List of unique classic rules
    """
    # Create some overlapping, some unique rules
    # Take first half of classic_rules as LLM rules
    llm_rules = classic_rules[: len(classic_rules) // 2]

    # Run triage
    triage_result = _triage_rules(classic_rules, llm_rules)

    # Calculate total unique rule_numbers in input
    all_input_numbers = {r.rule_number for r in classic_rules} | {
        r.rule_number for r in llm_rules
    }

    # Calculate total in output
    total_output = (
        len(triage_result.perfect_matches)
        + len(triage_result.conflicts)
        + len(triage_result.orphans)
    )

    # Postcondition: Counts match
    assert total_output == len(all_input_numbers)


@pytest.mark.unit
@given(
    st.lists(extracted_rule_strategy(), min_size=0, max_size=20),
    st.lists(extracted_rule_strategy(), min_size=0, max_size=20),
)
def test_triage_never_crashes(
    classic_rules: list[ExtractedRule],
    llm_rules: list[ExtractedRule],
) -> None:
    """Property: Triage handles all valid rule lists without crashing.

    Any combination of valid ExtractedRule lists should be triageable
    without raising exceptions.

    Args:
        classic_rules: Arbitrary list of classic rules
        llm_rules: Arbitrary list of LLM rules
    """
    # Should not crash regardless of input
    triage_result = _triage_rules(classic_rules, llm_rules)

    # Postcondition: Returns valid TriageResult
    assert isinstance(triage_result.perfect_matches, list)
    assert isinstance(triage_result.conflicts, list)
    assert isinstance(triage_result.orphans, list)
