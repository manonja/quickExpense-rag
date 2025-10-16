"""
Canadian tax rule extraction pipeline.

This package provides a Mixture-of-Experts (MoE) HTML-to-YAML extraction pipeline
for Canadian Revenue Agency (CRA) business expense rules. The pipeline uses multiple
parsing strategies and an adjudicator to ensure high-quality extraction.

Components:
- classic_parse: Rule-based HTML parser (deterministic)
- Schema models: ExtractedRule, RuleSet, ExpertSource, ApplicabilityType
- Exceptions: ParserError, AdjudicationError, YAMLGenerationError
- Settings: Configuration management for API keys and models
"""

from .classic_parser import parse as classic_parse
from .exceptions import (
    AdjudicationError,
    ParserError,
    PipelineError,
    YAMLGenerationError,
)
from .schema import ApplicabilityType, ExpertSource, ExtractedRule, RuleSet
from .settings import settings

__all__ = [
    # Parser
    "classic_parse",
    # Schema
    "ExtractedRule",
    "RuleSet",
    "ExpertSource",
    "ApplicabilityType",
    # Exceptions
    "ParserError",
    "AdjudicationError",
    "YAMLGenerationError",
    "PipelineError",
    # Settings
    "settings",
]
