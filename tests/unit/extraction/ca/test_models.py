"""
Unit tests for extraction content type models (Phase 2).

Tests ContentType enum and ExtractedContent model validation.
"""

import pytest
from pydantic import ValidationError
from qe_tax_rag.extraction.ca.models import ContentType, ExtractedContent


@pytest.mark.unit
def test_create_principle_content():
    """
    Test successful creation of PRINCIPLE content.

    Acceptance Criterion 2.1.2:
    Unit test demonstrates ExtractedContent can be created with
    content_type=ContentType.PRINCIPLE
    """
    principle = ExtractedContent(
        citation_id="t4002-6-PRINCIPLE-1",
        content_type=ContentType.PRINCIPLE,
        text="Enter on line 9925 the total business part of the cost of the equipment.",
        source_file="t4002-6.html",
        anchor_id=None,
        references=["LINE-9925"],
    )

    # Validate all fields populated correctly
    assert principle.citation_id == "t4002-6-PRINCIPLE-1"
    assert principle.content_type == ContentType.PRINCIPLE
    assert "line 9925" in principle.text.lower()
    assert principle.source_file == "t4002-6.html"
    assert principle.anchor_id is None
    assert principle.references == ["LINE-9925"]


@pytest.mark.unit
def test_create_rule_content():
    """Test successful creation of RULE content (baseline validation)."""
    rule = ExtractedContent(
        citation_id="LINE-9600",
        content_type=ContentType.RULE,
        text="Other income\n\nInclude any other income...",
        source_file="t4002-5.html",
        anchor_id="tocch2ln9600",
        references=[],
    )

    # Validate all fields populated correctly
    assert rule.citation_id == "LINE-9600"
    assert rule.content_type == ContentType.RULE
    assert "Other income" in rule.text
    assert rule.source_file == "t4002-5.html"
    assert rule.anchor_id == "tocch2ln9600"
    assert rule.references == []


@pytest.mark.unit
def test_invalid_content_type():
    """
    Test that invalid content_type raises ValidationError.

    Acceptance Criterion 2.1.3:
    Unit test confirms invalid content_type string (e.g., "COMMENT")
    raises pydantic.ValidationError
    """
    with pytest.raises(ValidationError) as exc_info:
        ExtractedContent(
            citation_id="test-1",
            content_type="COMMENT",  # type: ignore[arg-type]  # Intentionally invalid
            text="Test content",
            source_file="test.html",
        )

    # Verify error mentions the invalid value
    error_message = str(exc_info.value)
    assert "content_type" in error_message.lower()


@pytest.mark.unit
def test_frozen_model():
    """Test that ExtractedContent is immutable (frozen=True)."""
    principle = ExtractedContent(
        citation_id="t4002-6-PRINCIPLE-1",
        content_type=ContentType.PRINCIPLE,
        text="Test content",
        source_file="t4002-6.html",
    )

    # Attempt to modify should raise ValidationError
    with pytest.raises(ValidationError):
        principle.text = "Modified text"  # type: ignore[misc]


@pytest.mark.unit
def test_extra_fields_forbidden():
    """Test that extra fields are forbidden (extra='forbid')."""
    with pytest.raises(ValidationError) as exc_info:
        ExtractedContent(
            citation_id="test-1",
            content_type=ContentType.PRINCIPLE,
            text="Test content",
            source_file="test.html",
            unexpected_field="not allowed",  # type: ignore[call-arg]
        )

    error_message = str(exc_info.value)
    assert "extra" in error_message.lower() or "unexpected" in error_message.lower()


@pytest.mark.unit
def test_default_values():
    """Test that default values work correctly."""
    content = ExtractedContent(
        citation_id="test-1",
        content_type=ContentType.PRINCIPLE,
        text="Test content",
        source_file="test.html",
    )

    # Default values should be set
    assert content.anchor_id is None
    assert content.references == []
