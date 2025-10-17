"""Unit tests for parser validation logic."""

import pytest


def test_citation_regex_valid_patterns():
    """Test citation regex matches valid S#-F#-C#-p#.# patterns."""
    from scripts.parser.validator import validate_citation_format

    # Valid patterns
    assert validate_citation_format("S1-F2-C3-p4.5") is True
    assert validate_citation_format("S3-F2-C1-p1.25") is True
    assert validate_citation_format("S10-F15-C20-p100.999") is True
    assert validate_citation_format("S1-F1-C1-p1.1") is True
    assert validate_citation_format("S1-F1-C1-p1") is True  # No decimal part


def test_citation_regex_invalid_patterns():
    """Test citation regex rejects malformed citations."""
    from scripts.parser.validator import validate_citation_format

    # Invalid patterns
    assert validate_citation_format("S1-F2-C3") is False  # Missing p#
    assert validate_citation_format("S1-F2-p4.5") is False  # Missing C#
    assert validate_citation_format("F2-C3-p4.5") is False  # Missing S#
    assert validate_citation_format("S1-F-C3-p4.5") is False  # Missing F number
    assert validate_citation_format("S-F2-C3-p4.5") is False  # Missing S number
    assert validate_citation_format("S1-F2-C3-p.5") is False  # Missing p number
    assert validate_citation_format("random text") is False
    assert validate_citation_format("") is False


def test_citation_regex_handles_none():
    """Test citation validator handles None gracefully."""
    from scripts.parser.validator import validate_citation_format

    # None should return True (optional citations are allowed)
    assert validate_citation_format(None) is True


def test_validate_citation_format_with_whitespace():
    """Test citation regex rejects citations with surrounding whitespace."""
    from scripts.parser.validator import validate_citation_format

    # Should reject whitespace (citations should be trimmed before validation)
    assert validate_citation_format(" S1-F2-C3-p4.5") is False
    assert validate_citation_format("S1-F2-C3-p4.5 ") is False
    assert validate_citation_format("S1- F2-C3-p4.5") is False


def test_get_citation_regex_pattern():
    """Test that citation regex pattern is accessible."""
    from scripts.parser.validator import CITATION_REGEX_PATTERN

    assert CITATION_REGEX_PATTERN is not None
    assert isinstance(CITATION_REGEX_PATTERN, str)
    # Pattern should match format: S\d+-F\d+-C\d+-p\d+(\.\d+)?
    assert r"S\d+" in CITATION_REGEX_PATTERN
    assert r"F\d+" in CITATION_REGEX_PATTERN
    assert r"C\d+" in CITATION_REGEX_PATTERN
    assert r"p\d+" in CITATION_REGEX_PATTERN


def test_line_citation_format_validates():
    """LINE-{number} format should validate."""
    from scripts.parser.validator import validate_citation_format

    assert validate_citation_format("LINE-8523") is True
    assert validate_citation_format("LINE-9200") is True
    assert validate_citation_format("LINE-12345") is True


def test_invalid_line_format_fails():
    """Invalid LINE formats should fail."""
    from scripts.parser.validator import validate_citation_format

    assert validate_citation_format("LINE-") is False
    assert validate_citation_format("LINE-abc") is False
    assert validate_citation_format("8523") is False  # Missing prefix
    assert validate_citation_format("line-8523") is False  # Lowercase


# Expense Type Validation Tests


def test_validate_expense_types_all_valid():
    """Test expense type validation with all valid types."""
    from scripts.parser.validator import validate_expense_types

    canonical_list = ["meals", "travel", "vehicle", "home_office"]
    expense_types = ["meals", "vehicle"]

    result = validate_expense_types(expense_types, canonical_list)

    assert result["valid"] is True
    assert result["invalid_types"] == []


def test_validate_expense_types_with_invalid():
    """Test expense type validation detects invalid types."""
    from scripts.parser.validator import validate_expense_types

    canonical_list = ["meals", "travel", "vehicle"]
    expense_types = ["meals", "unknown_type", "fake_category"]

    result = validate_expense_types(expense_types, canonical_list)

    assert result["valid"] is False
    assert "unknown_type" in result["invalid_types"]
    assert "fake_category" in result["invalid_types"]
    assert len(result["invalid_types"]) == 2


def test_validate_expense_types_empty_list():
    """Test expense type validation handles empty list."""
    from scripts.parser.validator import validate_expense_types

    canonical_list = ["meals", "travel"]
    expense_types = []

    result = validate_expense_types(expense_types, canonical_list)

    # Empty list is valid (no filtering)
    assert result["valid"] is True
    assert result["invalid_types"] == []


def test_validate_expense_types_case_sensitive():
    """Test expense type validation is case-sensitive."""
    from scripts.parser.validator import validate_expense_types

    canonical_list = ["meals", "travel"]
    expense_types = ["Meals", "TRAVEL"]  # Wrong case

    result = validate_expense_types(expense_types, canonical_list)

    assert result["valid"] is False
    assert "Meals" in result["invalid_types"]
    assert "TRAVEL" in result["invalid_types"]


def test_get_canonical_expense_types():
    """Test canonical expense type list is accessible."""
    from scripts.parser.validator import CANONICAL_EXPENSE_TYPES

    assert CANONICAL_EXPENSE_TYPES is not None
    assert isinstance(CANONICAL_EXPENSE_TYPES, list)
    assert len(CANONICAL_EXPENSE_TYPES) > 0
    # Should include common types
    assert "meals" in CANONICAL_EXPENSE_TYPES
    assert "travel" in CANONICAL_EXPENSE_TYPES
    assert "vehicle" in CANONICAL_EXPENSE_TYPES
