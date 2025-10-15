"""Validation utilities for parsed documents."""

import re

# Citation pattern: S#-F#-C#-p#.# (decimal part is optional)
# Example: S3-F2-C1-p1.25 or S1-F1-C1-p1
CITATION_REGEX_PATTERN = r"^S\d+-F\d+-C\d+-p\d+(\.\d+)?$"

# Canonical expense types list (matches database schema from TICKET 4.6)
CANONICAL_EXPENSE_TYPES = [
    "meals",
    "travel",
    "vehicle",
    "home_office",
    "advertising",
    "supplies",
    "professional_fees",
    "utilities",
    "rent",
    "insurance",
    "salaries",
    "office_equipment",
    "telecommunications",
    "maintenance",
    "interest",
    "bad_debts",
]

_citation_regex = re.compile(CITATION_REGEX_PATTERN)


def validate_citation_format(citation_id: str | None) -> bool:
    """
    Validate citation ID matches the expected S#-F#-C#-p#.# pattern.

    Args:
        citation_id: Citation ID to validate (None is allowed for optional citations)

    Returns:
        True if citation is valid or None, False otherwise
    """
    if citation_id is None:
        # None is allowed for optional citations (footnotes, etc.)
        return True

    if not isinstance(citation_id, str):
        return False

    return _citation_regex.match(citation_id) is not None


def validate_expense_types(
    expense_types: list[str], canonical_list: list[str] | None = None
) -> dict[str, bool | list[str]]:
    """
    Validate expense types against canonical list.

    Args:
        expense_types: List of expense types to validate
        canonical_list: Optional canonical list (defaults to CANONICAL_EXPENSE_TYPES)

    Returns:
        Dictionary with 'valid' boolean and 'invalid_types' list
    """
    if canonical_list is None:
        canonical_list = CANONICAL_EXPENSE_TYPES

    canonical_set = set(canonical_list)
    invalid_types = [et for et in expense_types if et not in canonical_set]

    return {"valid": len(invalid_types) == 0, "invalid_types": invalid_types}
