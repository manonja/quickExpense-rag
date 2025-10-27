"""YAML corpus builder for PDF coverage validation.

Builds in-memory text corpus from extracted YAML files (rules, principles, tables).
This corpus represents the ground truth of content already processed by the
extraction pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from scripts.pdf_coverage.normalizer import normalize_text, serialize_table_row

logger = logging.getLogger(__name__)


class YAMLCorpus:
    """YAML corpus builder and manager.

    Discovers and loads YAML files, extracts text content, and builds
    a normalized corpus for fuzzy matching.

    Attributes:
        yaml_dir: Root directory to search for YAML files
        yaml_files: List of YAML file paths found
        corpus_text: Concatenated normalized text from all YAML files
        stats: Statistics about loaded content

    """

    def __init__(self, yaml_dir: str | Path) -> None:
        """Initialize corpus builder.

        Args:
            yaml_dir: Root directory containing YAML files

        """
        self.yaml_dir = Path(yaml_dir)
        self.yaml_files: list[Path] = []
        self.corpus_text: str = ""
        self.stats: dict[str, int] = {
            "rules": 0,
            "principles": 0,
            "tables": 0,
            "table_rows": 0,
        }

    def discover_yaml_files(self) -> list[Path]:
        """Discover all YAML files in yaml_dir.

        Searches for:
        - rules.yml
        - principles.yml
        - tables.yml

        Returns:
            List of YAML file paths

        """
        yaml_files: list[Path] = []

        # Discover YAML files using glob patterns
        patterns = ["**/rules.yml", "**/principles.yml", "**/tables.yml"]

        for pattern in patterns:
            found = list(self.yaml_dir.glob(pattern))
            yaml_files.extend(found)
            logger.info(f"Found {len(found)} files matching {pattern}")

        self.yaml_files = sorted(yaml_files)
        logger.info(f"Total YAML files discovered: {len(self.yaml_files)}")

        return self.yaml_files

    def build_corpus(self) -> str:
        """Build normalized text corpus from all YAML files.

        Extracts text from rules, principles, and tables, applies normalization,
        and concatenates into single corpus string.

        Returns:
            Normalized corpus text

        Raises:
            FileNotFoundError: If no YAML files found
            ValueError: If YAML parsing fails

        """
        if not self.yaml_files:
            self.discover_yaml_files()

        if not self.yaml_files:
            raise FileNotFoundError(f"No YAML files found in {self.yaml_dir}")

        corpus_parts: list[str] = []

        for yaml_file in self.yaml_files:
            logger.info(f"Processing {yaml_file.name}...")

            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                # Extract text from rules
                rules = data.get("rules", [])
                self.stats["rules"] += len(rules)
                for rule in rules:
                    text = self._extract_rule_text(rule)
                    corpus_parts.append(normalize_text(text))

                # Extract text from principles
                principles = data.get("principles", [])
                self.stats["principles"] += len(principles)
                for principle in principles:
                    text = self._extract_principle_text(principle)
                    corpus_parts.append(normalize_text(text))

                # Extract text from tables
                tables = data.get("tables", [])
                self.stats["tables"] += len(tables)
                for table in tables:
                    table_text = self._extract_table_text(table)
                    corpus_parts.append(normalize_text(table_text))

            except Exception as e:
                logger.error(f"Failed to process {yaml_file}: {e}")
                raise ValueError(f"YAML parsing failed for {yaml_file}") from e

        # Concatenate all text parts
        self.corpus_text = " ".join(corpus_parts)

        logger.info(f"Corpus built: {len(self.corpus_text)} characters")
        logger.info(f"Stats: {self.stats}")

        return self.corpus_text

    def _extract_rule_text(self, rule: dict[str, Any]) -> str:
        """Extract text from a rule entry.

        Args:
            rule: Rule dictionary from YAML

        Returns:
            Combined text from title and content fields

        """
        title = rule.get("title", "")
        content = rule.get("content", "")
        return f"{title} {content}"

    def _extract_principle_text(self, principle: dict[str, Any]) -> str:
        """Extract text from a principle entry.

        Args:
            principle: Principle dictionary from YAML

        Returns:
            Text from the principle's text field

        """
        return principle.get("text", "")

    def _extract_table_text(self, table: dict[str, Any]) -> str:
        """Extract text from a table entry.

        Uses order-independent serialization for table rows to handle
        column order differences between PDF and YAML.

        Args:
            table: Table dictionary from YAML

        Returns:
            Concatenated text from all table rows

        """
        table_data = table.get("table_data", [])
        self.stats["table_rows"] += len(table_data)

        # Serialize each row using order-independent method
        row_texts = [serialize_table_row(row) for row in table_data]

        return " ".join(row_texts)

    def get_yaml_file_paths(self) -> list[str]:
        """Get list of YAML file paths as strings.

        Returns:
            List of YAML file paths (for reporting)

        """
        return [str(f) for f in self.yaml_files]


def build_yaml_corpus(yaml_dir: str | Path) -> tuple[str, list[str], dict[str, int]]:
    """Build YAML corpus from directory (convenience function).

    Args:
        yaml_dir: Directory containing YAML files

    Returns:
        Tuple of (corpus_text, yaml_file_paths, stats)

    Examples:
        >>> corpus, files, stats = build_yaml_corpus("output/")
        >>> print(f"Loaded {stats['rules']} rules")
        Loaded 18 rules

    """
    builder = YAMLCorpus(yaml_dir)
    corpus_text = builder.build_corpus()
    return corpus_text, builder.get_yaml_file_paths(), builder.stats
