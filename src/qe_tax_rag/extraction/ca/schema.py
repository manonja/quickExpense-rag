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
    """A single extracted tax rule with metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    citation_id: str = Field(
        description="Unique identifier in format S{section}-F{form}-C{chapter}-p{page}"
    )
    rule_text: str = Field(description="The extracted rule content")
    expert_source: ExpertSource = Field(
        description="Source of the rule extraction (classic, LLM, or adjudicated)"
    )
    applicability: ApplicabilityType = Field(
        description="Type of business this rule applies to"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the extraction (0.0 to 1.0)",
    )
    section: str = Field(description="Section number or identifier")
    form: str = Field(description="Form number or identifier")
    chapter: str = Field(description="Chapter number or identifier")
    page: str = Field(description="Page reference")


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
