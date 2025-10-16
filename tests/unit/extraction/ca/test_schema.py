"""Tests for extraction pipeline data schema."""

import pytest

from qe_tax_rag.extraction.ca.schema import ApplicabilityType, ExpertSource


def test_expert_source_enum_values() -> None:
    """Verify ExpertSource enum has expected values."""
    assert ExpertSource.CLASSIC.value == "classic"
    assert ExpertSource.LLM.value == "llm"
    assert ExpertSource.ADJUDICATED.value == "adjudicated"


def test_applicability_type_enum_values() -> None:
    """Verify ApplicabilityType enum has expected values."""
    assert ApplicabilityType.BUSINESS.value == "business"
    assert ApplicabilityType.FARMING.value == "farming"
    assert ApplicabilityType.FISHING.value == "fishing"


def test_enums_are_string_enums() -> None:
    """Verify enums inherit from str for JSON serialization."""
    assert isinstance(ExpertSource.CLASSIC, str)
    assert isinstance(ExpertSource.LLM, str)
    assert isinstance(ApplicabilityType.BUSINESS, str)

    # Verify string comparison works
    assert ExpertSource.CLASSIC == "classic"
    assert ApplicabilityType.FARMING == "farming"
