"""Custom exceptions for the HTML-to-YAML extraction pipeline."""


class PipelineError(Exception):
    """Base exception for all errors raised by the parsing pipeline."""

    pass


class ParserError(PipelineError):
    """Raised when an expert parser fails to extract data."""

    pass


class AdjudicationError(PipelineError):
    """Raised during the adjudication and self-correction phase."""

    pass


class YAMLGenerationError(PipelineError):
    """Raised when the final YAML file cannot be generated or verified."""

    pass
