"""Data schema for the Canadian HTML-to-YAML extraction pipeline."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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
    """A single extracted tax rule with metadata.

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
    source_file: str = Field(
        description="Source HTML filename, e.g., 't4002-5.html'"
    )

    # Internal pipeline metadata (stripped from final YAML output)
    expert_source: ExpertSource = Field(
        description="Which expert generated this rule"
    )
    anchor_id: str | None = Field(
        default=None, description="HTML anchor ID, e.g., 'tocch3ln8523'"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Expert confidence. Classic parser = 1.0",
    )


class RuleSet(BaseModel):
    """Collection of extracted rules with schema metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rules: list[ExtractedRule] = Field(
        description="List of extracted tax rules"
    )
    schema_version: str = Field(
        description="Schema version (e.g., '1.0')"
    )
    extraction_timestamp: str = Field(
        description="ISO 8601 timestamp of extraction (e.g., '2024-12-15T10:30:00Z')"
    )
