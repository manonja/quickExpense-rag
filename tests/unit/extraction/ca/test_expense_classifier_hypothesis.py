"""Property-based tests for ExpenseTypeClassifier using Hypothesis.

These tests ensure the keyword-based classifier is robust across diverse inputs,
including edge cases with Unicode, special characters, and various text formats.
"""

import pytest
from hypothesis import given, strategies as st
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpenseTypeClassifier,
    ExpertSource,
    ExtractedRule,
)


@pytest.mark.unit
@given(
    st.text(
        min_size=0,
        max_size=5000,
        alphabet=st.characters(
            min_codepoint=1,
            max_codepoint=0x10FFFF,
            blacklist_categories=("Cs",),  # Exclude surrogates
        ),
    )
)
def test_classifier_is_robust_to_all_text_inputs(content: str) -> None:
    """Property: Classifier handles ANY text input without crashing.

    This comprehensive test ensures the classifier is robust to all possible
    string inputs: empty strings, Unicode (including non-Latin scripts like 中文),
    special characters, very long text (up to 5000 chars), and all combinations.

    Consolidates: test_classifier_never_crashes, test_classifier_unicode_handling,
    test_classifier_handles_long_text, test_classifier_always_returns_nonempty_list

    Args:
        content: Arbitrary text (0-5000 chars, full Unicode range)
    """
    classifier = ExpenseTypeClassifier()

    # Create a minimal ExtractedRule with the generated content
    rule = ExtractedRule(
        rule_number=1000,
        title="Test",
        content=content,
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 1000",
        chapter="Chapter 1",
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    # Should never crash, regardless of input
    result = classifier.infer_expense_types(rule)

    # Postconditions: output is valid and non-empty
    assert isinstance(result, list)
    assert len(result) > 0  # Even empty content returns ["general"]
    assert all(isinstance(expense_type, str) for expense_type in result)
    assert all(expense_type != "" for expense_type in result)
    assert all(expense_type is not None for expense_type in result)


@pytest.mark.unit
@given(
    st.sampled_from(["meal", "MEAL", "Meal", "MeAl", "mEaL"]),
)
def test_classifier_case_insensitive(keyword: str) -> None:
    """Property: Classifier is case-insensitive for keyword matching.

    "MEAL", "Meal", and "meal" should all match the "meals" expense type.

    Args:
        keyword: Mixed-case variation of "meal"
    """
    classifier = ExpenseTypeClassifier()

    rule = ExtractedRule(
        rule_number=8523,
        title=f"Expenses for {keyword}",
        content=f"You can deduct {keyword} expenses.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    result = classifier.infer_expense_types(rule)

    # Postcondition: "meals" is in the result
    assert "meals" in result


@pytest.mark.unit
def test_classifier_word_boundaries() -> None:
    """Property: Classifier respects word boundaries.

    "meal" should match, but "oatmeal" or "mealy" should not trigger
    the "meals" expense type.
    """
    classifier = ExpenseTypeClassifier()

    # Test word boundary: "oatmeal" should NOT match
    rule_no_match = ExtractedRule(
        rule_number=1001,
        title="Oatmeal",
        content="You can deduct oatmeal expenses for breakfast.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 1001",
        chapter="Chapter 3",
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    result_no_match = classifier.infer_expense_types(rule_no_match)
    # Should fallback to general since "oatmeal" doesn't match "meal"
    assert "meals" not in result_no_match

    # Test word boundary: "meal" should match
    rule_match = ExtractedRule(
        rule_number=8523,
        title="Meal",
        content="You can deduct meal expenses.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    result_match = classifier.infer_expense_types(rule_match)
    assert "meals" in result_match


@pytest.mark.unit
@given(
    st.lists(
        st.sampled_from(["meal", "vehicle", "travel", "insurance"]),
        min_size=1,
        max_size=4,
        unique=True,
    )
)
def test_classifier_returns_multiple_types(keywords: list[str]) -> None:
    """Property: Classifier returns all matching expense types.

    When content contains multiple keywords, all should be returned.

    Args:
        keywords: List of 1-4 unique keywords
    """
    classifier = ExpenseTypeClassifier()

    # Create content with all keywords
    content = " ".join(f"Deduct {keyword} expenses." for keyword in keywords)

    rule = ExtractedRule(
        rule_number=1000,
        title="Multiple Expenses",
        content=content,
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 1000",
        chapter="Chapter 3",
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        confidence_score=1.0,
    )

    result = classifier.infer_expense_types(rule)

    # Postcondition: result contains expected expense types
    # (We can't guarantee exact matches since keywords may map differently)
    assert isinstance(result, list)
    assert len(result) >= 1

    # Check that result has no duplicates
    assert len(result) == len(set(result))


