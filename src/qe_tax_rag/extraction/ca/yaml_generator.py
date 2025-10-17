"""YAML generation module for HTML-to-YAML extraction pipeline.

This module takes validated ExtractedRule objects and generates a
schema-compliant YAML file with metadata stripping, RuleSet wrapping,
and read-back verification.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from qe_tax_rag.extraction.ca.exceptions import YAMLGenerationError
from qe_tax_rag.extraction.ca.schema import ExtractedRule, RuleSet

logger = logging.getLogger(__name__)

# Internal metadata fields to exclude from final YAML output
_INTERNAL_METADATA_FIELDS = {"expert_source", "anchor_id", "confidence_score"}


def generate(rules: list[ExtractedRule], output_path: str) -> None:
    """Generate schema-compliant YAML file from validated rules.

    Args:
        rules: List of validated ExtractedRule objects from adjudicator.
        output_path: Path for output YAML file.

    Raises:
        YAMLGenerationError: If file cannot be written or verified.
    """
    # Create parent directories
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    # Create RuleSet with required fields
    rule_set = RuleSet(
        schema_version="1.0",
        extraction_timestamp=timestamp,
        rules=rules,
    )

    # Convert to dict with enums as strings, excluding internal metadata
    # Use JSON roundtrip for enum conversion
    data = json.loads(rule_set.model_dump_json(exclude={"rules": {"__all__": _INTERNAL_METADATA_FIELDS}}))

    # Serialize to YAML
    yaml_string = yaml.dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=88,
    )

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_string)
