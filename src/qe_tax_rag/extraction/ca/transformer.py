"""YAML-to-JSONL transformer for TICKET T2.1: Core Transformer Module.

This module transforms ExtractedRule YAML files (from adjudicator) into
ParsedDocument JSONL files (for database builder).

Architecture:
    Input:  YAML files with ExtractedRule schema (qe_tax_rag.extraction.ca.schema)
    Output: JSONL files with ParsedDocument schema (qe_tax_rag.parser.schema)

Transformation pipeline:
    1. Load ExtractedRule YAML → RuleSet
    2. Group rules by section_title
    3. Transform each rule to TextChunk with LINE-{number} citation
    4. Classify expense_type using keyword matching
    5. Aggregate metadata (province, business_type, expense_type, income_type)
    6. Build Section objects with content
    7. Create ParsedDocument with all sections
    8. Write to JSONL (one document per line)

Exception handling:
    - CriticalTransformationError: Fatal errors that halt processing
    - SkippableTransformationError: Non-fatal warnings (logged, processing continues)
"""


# ============================================================================
# Exception Hierarchy
# ============================================================================


class CriticalTransformationError(Exception):
    """Fatal transformation error that halts processing.

    Raised when:
    - Input YAML is malformed or invalid schema
    - Required fields are missing
    - Output validation fails
    - I/O errors (cannot read/write files)

    When raised: Processing stops immediately, error logged, exit with non-zero code.
    """

    pass


class SkippableTransformationError(Exception):
    """Non-fatal transformation warning (processing continues).

    Raised when:
    - Optional fields are missing
    - Non-critical validation warnings
    - Recoverable data inconsistencies

    When raised: Warning logged, problematic record skipped, processing continues.
    """

    pass
