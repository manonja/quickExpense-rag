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
