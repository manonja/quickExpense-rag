"""Validation utilities for parsed documents."""

import re

# Citation pattern: S#-F#-C#-p#.# (decimal part is optional)
# Example: S3-F2-C1-p1.25 or S1-F1-C1-p1
CITATION_REGEX_PATTERN = r"^S\d+-F\d+-C\d+-p\d+(\.\d+)?$"

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
