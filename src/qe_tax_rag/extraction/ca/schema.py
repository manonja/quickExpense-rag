"""Data schema for the Canadian HTML-to-YAML extraction pipeline."""

from enum import StrEnum


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
