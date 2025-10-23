"""Data schema for the Canadian HTML-to-YAML extraction pipeline."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from qe_tax_rag.data.models import DatabaseChunk
    from qe_tax_rag.search.models import SourceFile


class ExpertSource(StrEnum):
    """Source of the extracted rule."""

    CLASSIC = "classic"
    LLM = "llm"
    ADJUDICATED = "adjudicated"


class ApplicabilityType(StrEnum):
    """Type of business the rule applies to."""

    BUSINESS = "business"
    FARMING = "farming"
    FISHING = "fishing"


class ExtractedRule(BaseModel):
    """
    A single extracted tax rule with metadata.

    Represents a line-numbered expense rule extracted from CRA HTML documents.
    Used in Mixture-of-Experts pipeline where classic and LLM parsers extract
    rules, and an adjudicator resolves conflicts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Core fields for adjudication and final output
    rule_number: int = Field(
        description="Line number, e.g., 8523. Primary key for adjudication."
    )
    title: str = Field(description="Rule title, e.g., 'Meals and entertainment'")
    content: str = Field(description="Full text content of the rule")
    applies_to: list[ApplicabilityType] = Field(
        description="Business types this rule applies to (from icons)"
    )
    source_citation: str = Field(
        description="Human-readable citation, e.g., 'Line 8523'"
    )

    # Context fields for navigation and filtering
    chapter: str = Field(description="Chapter, e.g., 'Chapter 3 – Expenses'")
    section: str | None = Field(
        default=None, description="Section, e.g., 'Part 4 – Net income'"
    )
    source_file: str = Field(description="Source HTML filename, e.g., 't4002-5.html'")

    # Internal pipeline metadata (stripped from final YAML output)
    expert_source: ExpertSource = Field(description="Which expert generated this rule")
    anchor_id: str | None = Field(
        default=None, description="HTML anchor ID, e.g., 'tocch3ln8523'"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Expert confidence. Classic parser = 1.0",
    )


class ExpenseTypeClassifier:
    """Keyword-based expense type classifier.

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
        "utilities": [
            "telephone",
            "utilities",
            "internet",
            "electricity",
            "phone",
            "mobile",
            "telecommunications",
        ],
        "insurance": ["insurance", "premium"],
        "capital": ["capital cost", "cca", "depreciation", "asset"],
        "maintenance": ["maintenance", "repair"],
        "salaries": ["salaries", "wages", "employee"],
        "office_equipment": ["office equipment", "furniture", "computer"],
        "interest": ["interest", "loan", "financing"],
        "bad_debts": ["bad debts", "uncollectible"],
    }

    def infer_expense_types(self, rule: ExtractedRule) -> list[str]:
        """Infer expense types from rule title and content.

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
            if any(
                re.search(r"\b" + re.escape(keyword) + r"\b", text)
                for keyword in keywords
            ):
                matched.append(expense_type)

        # Fallback to "general" if no matches
        return matched if matched else ["general"]


class RuleSet(BaseModel):
    """Collection of extracted rules with schema metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rules: list[ExtractedRule] = Field(description="List of extracted tax rules")
    schema_version: str = Field(description="Schema version (e.g., '1.0')")
    extraction_timestamp: str = Field(
        description="ISO 8601 timestamp of extraction (e.g., '2024-12-15T10:30:00Z')"
    )

    def to_database_chunks(
        self,
        source_files: dict[str, SourceFile],
        expense_classifier: ExpenseTypeClassifier | None = None,
    ) -> list[DatabaseChunk]:
        """Convert rules directly to database-ready chunks.

        REPLACES: YAMLTransformer.transform_yaml_to_jsonl()
        ELIMINATES: ParsedDocument intermediate representation

        This method enables the extraction pipeline to bypass the transformer
        entirely, going directly from YAML to database-ready chunks.

        Args:
            source_files: Mapping of source filename (stem) to SourceFile metadata.
                Example: {"t4002-5": SourceFile(...)}
            expense_classifier: Classifier for inferring expense types.
                Defaults to ExpenseTypeClassifier() if not provided.

        Returns:
            List of DatabaseChunk objects ready for IndexBuilder

        Raises:
            ValueError: If no SourceFile found for a rule's source_file

        Example:
            >>> from qe_tax_rag.search.models import SourceFile
            >>> source_files = {
            ...     "t4002-5": SourceFile(
            ...         path="t4002-5.html",
            ...         url="https://www.canada.ca/...",
            ...         hash="abc123"
            ...     )
            ... }
            >>> ruleset = RuleSet.model_validate(yaml_data)
            >>> chunks = ruleset.to_database_chunks(source_files)
        """
        from pathlib import Path

        from qe_tax_rag.data.models import ChunkMetadata, DatabaseChunk

        classifier = expense_classifier or ExpenseTypeClassifier()
        chunks: list[DatabaseChunk] = []

        for rule in self.rules:
            # Extract source filename stem (e.g., "t4002-5.html" → "t4002-5")
            source_stem = Path(rule.source_file).stem

            # Look up SourceFile metadata
            source_file = source_files.get(source_stem)
            if not source_file:
                raise ValueError(
                    f"No SourceFile found for '{rule.source_file}' "
                    f"(stem: '{source_stem}'). "
                    f"Available keys: {list(source_files.keys())}"
                )

            chunks.append(
                DatabaseChunk(
                    content=f"{rule.title}\n\n{rule.content}",
                    citation_id=f"LINE-{rule.rule_number}",
                    source_url=str(source_file.url),
                    source_hash=source_file.hash,
                    province=None,  # Federal rules have no province
                    business_type=None,  # Not mapped from applies_to
                    expense_types=classifier.infer_expense_types(rule),
                    metadata=ChunkMetadata(
                        income_type=[at.value for at in rule.applies_to],
                        section_title=rule.chapter,
                        document_id=source_stem,
                        extraction_source=rule.expert_source.value,
                        extraction_confidence=rule.confidence_score,
                        source_anchor=rule.anchor_id,
                    ),
                )
            )

        return chunks
