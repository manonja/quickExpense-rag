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


class ParserValidator:
    """Validator for parsed CRA documents with error collection and reporting."""

    def __init__(self, canonical_expense_types: list[str] | None = None):
        """
        Initialize validator.

        Args:
            canonical_expense_types: Optional canonical list (defaults to CANONICAL_EXPENSE_TYPES)
        """
        self.canonical_expense_types = canonical_expense_types or CANONICAL_EXPENSE_TYPES

    def validate_parsed_document(
        self, parsed_doc: "ParsedDocument"
    ) -> dict[str, bool | list[str] | dict]:
        """
        Run all validation checks on a parsed document.

        Args:
            parsed_doc: ParsedDocument instance to validate

        Returns:
            Validation report with 'valid', 'errors', 'warnings', and 'statistics'
        """
        from scripts.parser.schema import ListChunk, ParsedDocument, TextChunk

        errors: list[str] = []
        warnings: list[str] = []

        # Validate expense types (warnings, not errors)
        expense_validation = validate_expense_types(
            parsed_doc.metadata.expense_type, self.canonical_expense_types
        )
        if not expense_validation["valid"]:
            for invalid_type in expense_validation["invalid_types"]:
                warnings.append(
                    f"Unknown expense type '{invalid_type}' not in canonical list"
                )

        # Validate citations in all content items
        total_content_items = 0
        for section in parsed_doc.sections:
            for content_item in section.content:
                total_content_items += 1

                if isinstance(content_item, TextChunk):
                    if not validate_citation_format(content_item.citation_id):
                        errors.append(
                            f"Invalid citation format: '{content_item.citation_id}' "
                            f"in section '{section.section_title}'"
                        )
                elif isinstance(content_item, ListChunk):
                    # Validate citations in list items
                    for item in content_item.items:
                        if not validate_citation_format(item.citation_id):
                            errors.append(
                                f"Invalid citation format in list item: '{item.citation_id}' "
                                f"in section '{section.section_title}'"
                            )
                        # Also check sub-items
                        for sub_item in item.sub_items:
                            if not validate_citation_format(sub_item.citation_id):
                                errors.append(
                                    f"Invalid citation format in sub-item: '{sub_item.citation_id}' "
                                    f"in section '{section.section_title}'"
                                )
                else:  # TableChunk
                    if not validate_citation_format(content_item.citation_id):
                        errors.append(
                            f"Invalid citation format in table: '{content_item.citation_id}' "
                            f"in section '{section.section_title}'"
                        )

        # Generate statistics
        statistics = {
            "total_sections": len(parsed_doc.sections),
            "total_content_items": total_content_items,
            "error_count": len(errors),
            "warning_count": len(warnings),
        }

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "statistics": statistics,
        }
