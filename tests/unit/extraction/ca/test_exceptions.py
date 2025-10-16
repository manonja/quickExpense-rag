"""Tests for extraction pipeline exception hierarchy."""

import pytest
from qe_tax_rag.extraction.ca.exceptions import (
    AdjudicationError,
    ParserError,
    PipelineError,
    YAMLGenerationError,
)


def test_pipeline_error_is_base_exception() -> None:
    """Verify PipelineError inherits from Exception."""
    assert issubclass(PipelineError, Exception)


def test_parser_error_inherits_from_pipeline_error() -> None:
    """Verify ParserError inherits from PipelineError."""
    assert issubclass(ParserError, PipelineError)
    assert issubclass(ParserError, Exception)


def test_adjudication_error_inherits_from_pipeline_error() -> None:
    """Verify AdjudicationError inherits from PipelineError."""
    assert issubclass(AdjudicationError, PipelineError)
    assert issubclass(AdjudicationError, Exception)


def test_yaml_generation_error_inherits_from_pipeline_error() -> None:
    """Verify YAMLGenerationError inherits from PipelineError."""
    assert issubclass(YAMLGenerationError, PipelineError)
    assert issubclass(YAMLGenerationError, Exception)


def test_exceptions_can_be_raised_with_message() -> None:
    """Verify exception messages are preserved."""
    test_message = "Test error message"

    with pytest.raises(PipelineError, match=test_message):
        raise PipelineError(test_message)

    with pytest.raises(ParserError, match=test_message):
        raise ParserError(test_message)

    with pytest.raises(AdjudicationError, match=test_message):
        raise AdjudicationError(test_message)

    with pytest.raises(YAMLGenerationError, match=test_message):
        raise YAMLGenerationError(test_message)
