"""
YAML-to-JSONL transformer for TICKET T2.1: Core Transformer Module.

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

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from qe_tax_rag.extraction.ca.schema import ExtractedRule, RuleSet
    from qe_tax_rag.parser.schema import (
        Metadata,
        ParsedDocument,
        Section,
        TextChunk,
    )


# ============================================================================
# Exception Hierarchy
# ============================================================================


class CriticalTransformationError(Exception):
    """
    Fatal transformation error that halts processing.

    Raised when:
    - Input YAML is malformed or invalid schema
    - Required fields are missing
    - Output validation fails
    - I/O errors (cannot read/write files)

    When raised: Processing stops immediately, error logged, exit with non-zero code.
    """

    pass


class SkippableTransformationError(Exception):
    """
    Non-fatal transformation warning (processing continues).

    Raised when:
    - Optional fields are missing
    - Non-critical validation warnings
    - Recoverable data inconsistencies

    When raised: Warning logged, problematic record skipped, processing continues.
    """

    pass


# ============================================================================
# Expense Type Classifier
# ============================================================================


class ExpenseTypeClassifier:
    """
    Keyword-based expense type classifier.

    Simple, deterministic classifier using keyword matching.
    Good enough for MVP - can be replaced with ML model later if needed.

    Follows 80/20 principle: delivers immediate value without ML complexity.
    """

    # Canonical expense types from database schema
    EXPENSE_TYPE_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        "meals": ["meal", "food", "restaurant", "dining", "entertainment"],
        "travel": ["travel", "transportation", "airfare", "hotel", "lodging"],
        "vehicle": ["vehicle", "automobile", "car", "motor", "mileage", "fuel"],
        "home_office": ["home office", "workspace", "rent"],
        "advertising": ["advertising", "marketing", "promotion"],
        "supplies": ["supplies", "materials", "stationery"],
        "professional_fees": ["professional fees", "legal", "accounting"],
        "utilities": ["telephone", "utilities", "internet", "electricity"],
        "insurance": ["insurance", "premium"],
        "capital": ["capital cost", "cca", "depreciation", "asset"],
        "maintenance": ["maintenance", "repair"],
        "salaries": ["salaries", "wages", "employee"],
        "office_equipment": ["office equipment", "furniture", "computer"],
        "telecommunications": ["telecommunications", "phone", "mobile"],
        "interest": ["interest", "loan", "financing"],
        "bad_debts": ["bad debts", "uncollectible"],
    }

    def infer_expense_types(self, rule: "ExtractedRule") -> list[str]:
        """
        Infer expense types from rule title and content.

        Args:
            rule: ExtractedRule to classify

        Returns:
            List of expense types (can be multiple).
            Falls back to ["general"] if no matches.

        """
        # Combine title and content for matching
        text = (rule.title + " " + rule.content).lower()

        matched: list[str] = []

        for expense_type, keywords in self.EXPENSE_TYPE_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                matched.append(expense_type)

        # Fallback to "general" if no matches
        return matched if matched else ["general"]


# ============================================================================
# Transformation Report
# ============================================================================


class TransformationReport(BaseModel):
    """Report on transformation success/failures."""

    timestamp: str
    input_file: str
    output_file: str
    total_rules: int
    successful: int
    skipped: int
    errors: list[dict[str, str]]


# ============================================================================
# YAML Transformer
# ============================================================================


class YAMLTransformer:
    """Transform ExtractedRule YAML to ParsedDocument JSONL."""

    def _group_by_source_file(
        self,
        rules: list["ExtractedRule"],
    ) -> dict[str, list["ExtractedRule"]]:
        """
        Group rules by source_file.

        Args:
            rules: List of ExtractedRule objects

        Returns:
            Dictionary mapping source_file → list of rules

        """
        grouped: dict[str, list["ExtractedRule"]] = defaultdict(list)

        for rule in rules:
            grouped[rule.source_file].append(rule)

        return dict(grouped)

    def _rule_to_text_chunk(self, rule: "ExtractedRule") -> "TextChunk":
        """
        Transform ExtractedRule to TextChunk with metadata.

        Args:
            rule: ExtractedRule object from YAML

        Returns:
            TextChunk with citation ID, extraction metadata, and source anchor

        """
        # Import at runtime to avoid circular dependency
        from qe_tax_rag.parser.schema import TextChunk

        # Generate citation ID: LINE-{rule_number}
        citation_id = f"LINE-{rule.rule_number}"

        # Map expert_source enum to lowercase string
        extraction_source = rule.expert_source.value.lower()

        # Generate source anchor: {chapter}{section}ln{rule_number} (normalized)
        # Remove spaces, lowercase, keep alphanumeric
        chapter_part = self._normalize_anchor(rule.chapter)
        section_part = self._normalize_anchor(rule.section) if rule.section else ""
        source_anchor = f"{chapter_part}{section_part}ln{rule.rule_number}"

        return TextChunk(
            type="paragraph",
            text=rule.content,
            citation_id=citation_id,
            extraction_source=extraction_source,
            extraction_confidence=rule.confidence_score,
            source_anchor=source_anchor,
        )

    def _normalize_anchor(self, text: str) -> str:
        """
        Normalize text for HTML anchor generation.

        Args:
            text: Text to normalize (e.g., "Chapter 1", "General Rules")

        Returns:
            Normalized text (e.g., "ch1", "generalrules")

        Examples:
            "Chapter 1" → "ch1"
            "General Rules" → "generalrules"
            "Chapter 2" → "ch2"

        """
        # Remove spaces and convert to lowercase
        normalized = text.lower().replace(" ", "")

        # Replace "chapter" with "ch" for brevity
        normalized = normalized.replace("chapter", "ch")

        return normalized
