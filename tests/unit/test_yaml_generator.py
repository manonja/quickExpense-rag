"""
Unit tests for YAML generation module.

Tests cover:
- Happy path: Valid rules → valid YAML file
- Metadata stripping: Internal fields excluded from output
- RuleSet population: Schema version and timestamp added
- File header: Generation metadata present
- Empty rules: Valid YAML with empty rules list
- Error handling: Permission errors, corruption, race conditions
"""

from datetime import datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from pyfakefs.fake_filesystem import FakeFilesystem
from qe_tax_rag.extraction.ca.exceptions import YAMLGenerationError
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
    RuleSet,
)
from qe_tax_rag.extraction.ca.yaml_generator import generate

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_rules() -> list[ExtractedRule]:
    """Create sample ExtractedRule objects for testing."""
    return [
        ExtractedRule(
            rule_number=8523,
            title="Meals and entertainment",
            content="You can deduct 50% of eligible meal and entertainment expenses.",
            applies_to=[ApplicabilityType.BUSINESS],
            source_citation="Line 8523",
            chapter="Chapter 3 – Expenses",
            section="Part 4 – Net income (loss) before adjustments",
            source_file="t4002-5.html",
            expert_source=ExpertSource.CLASSIC,
            anchor_id="tocch3ln8523",
            confidence_score=0.95,
        ),
        ExtractedRule(
            rule_number=9270,
            title="Professional fees",
            content="You can deduct fees paid for professional services.",
            applies_to=[ApplicabilityType.BUSINESS, ApplicabilityType.FARMING],
            source_citation="Line 9270",
            chapter="Chapter 3 – Expenses",
            section="Part 4 – Net income (loss) before adjustments",
            source_file="t4002-5.html",
            expert_source=ExpertSource.ADJUDICATED,
            anchor_id="tocch3ln9270",
            confidence_score=0.88,
        ),
    ]


@pytest.fixture
def empty_rules() -> list[ExtractedRule]:
    """Empty rules list for edge case testing."""
    return []


# ============================================================================
# Test Group 1: Happy Path and Core Functionality
# ============================================================================


@pytest.mark.unit
def test_generate_creates_valid_yaml_file(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that generate() creates a valid YAML file."""
    output_path = "/output/rules.yml"

    # Call the function
    generate(rules=sample_rules, output_path=output_path)

    # Verify file exists
    assert Path(output_path).exists()

    # Verify file is valid YAML
    with open(output_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Verify structure
    assert "rules" in data
    assert len(data["rules"]) == 2
    assert data["rules"][0]["rule_number"] == 8523
    assert data["rules"][1]["rule_number"] == 9270


@pytest.mark.unit
def test_generate_creates_parent_directories(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that generate() creates parent directories if they don't exist."""
    output_path = "/deeply/nested/output/dir/rules.yml"

    # Verify parent directories don't exist
    assert not Path("/deeply").exists()

    generate(rules=sample_rules, output_path=output_path)

    # Verify file and all parent directories were created
    assert Path(output_path).exists()
    assert Path("/deeply/nested/output/dir").exists()


# ============================================================================
# Test Group 2: Metadata Stripping
# ============================================================================


@pytest.mark.unit
def test_generate_strips_expert_source_field(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that expert_source is excluded from output YAML."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Verify expert_source is NOT in any rule
    for rule in data["rules"]:
        assert "expert_source" not in rule


@pytest.mark.unit
def test_generate_strips_anchor_id_field(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that anchor_id is excluded from output YAML."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for rule in data["rules"]:
        assert "anchor_id" not in rule


@pytest.mark.unit
def test_generate_strips_confidence_score_field(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that confidence_score is excluded from output YAML."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for rule in data["rules"]:
        assert "confidence_score" not in rule


# ============================================================================
# Test Group 3: RuleSet Population
# ============================================================================


@pytest.mark.unit
def test_generate_adds_schema_version(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that schema_version is added to RuleSet."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, encoding="utf-8") as f:
        content = f.read()
        yaml_content = content.split("---\n", 1)[1]
        data = yaml.safe_load(yaml_content)

    assert data["schema_version"] == "1.0"


@pytest.mark.unit
def test_generate_adds_extraction_timestamp(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that extraction_timestamp is added and is valid ISO format."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, encoding="utf-8") as f:
        content = f.read()
        yaml_content = content.split("---\n", 1)[1]
        data = yaml.safe_load(yaml_content)

    assert "extraction_timestamp" in data
    # Verify it's valid ISO 8601 format
    datetime.fromisoformat(data["extraction_timestamp"])


# ============================================================================
# Test Group 4: File Header
# ============================================================================


@pytest.mark.unit
def test_generate_adds_file_header(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that file includes generation metadata header."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, encoding="utf-8") as f:
        content = f.read()

    # Verify header is present
    assert content.startswith("# Generated by qe-tax-rag")
    assert "# Do not edit this file manually" in content
    assert "---\n" in content  # YAML document separator


# ============================================================================
# Test Group 5: Edge Cases
# ============================================================================


@pytest.mark.unit
def test_generate_handles_empty_rules_list(
    fs: FakeFilesystem, empty_rules: list[ExtractedRule]
) -> None:
    """Test that empty rules list produces valid YAML with rules: []."""
    output_path = "/output/empty_rules.yml"

    generate(rules=empty_rules, output_path=output_path)

    with open(output_path, encoding="utf-8") as f:
        content = f.read()
        yaml_content = content.split("---\n", 1)[1] if "---\n" in content else content
        data = yaml.safe_load(yaml_content)

    assert data["rules"] == []
    assert data["schema_version"] == "1.0"
    assert "extraction_timestamp" in data


# ============================================================================
# Test Group 6: Error Handling
# ============================================================================


@pytest.mark.unit
def test_generate_raises_error_on_permission_denied(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that PermissionError raises YAMLGenerationError."""
    output_path = "/readonly/rules.yml"

    # Create directory with no write permissions
    fs.create_dir("/readonly")
    fs.chmod("/readonly", 0o444)  # Read-only

    with pytest.raises(YAMLGenerationError, match="Permission denied"):
        generate(rules=sample_rules, output_path=output_path)


@pytest.mark.unit
def test_generate_raises_error_on_invalid_path(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule]
) -> None:
    """Test that invalid output path raises YAMLGenerationError."""
    # Path to non-existent root-level directory (permission issue in fakefs)
    output_path = "/nonexistent/deeply/nested/rules.yml"

    # Make parent unwritable
    fs.create_dir("/nonexistent")
    fs.chmod("/nonexistent", 0o444)

    with pytest.raises(YAMLGenerationError, match="Permission denied"):
        generate(rules=sample_rules, output_path=output_path)


@pytest.mark.unit
def test_generate_raises_error_on_verification_failure(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule], monkeypatch
) -> None:
    """Test that corrupted file detected during verification raises error."""
    output_path = "/output/rules.yml"

    # Mock yaml.safe_load to raise YAMLError during verification
    original_safe_load = yaml.safe_load
    call_count = {"count": 0}

    def mock_safe_load(content):
        call_count["count"] += 1
        if call_count["count"] == 1:  # Verification read
            msg = "Invalid YAML syntax"
            raise yaml.YAMLError(msg)
        return original_safe_load(content)

    monkeypatch.setattr("yaml.safe_load", mock_safe_load)

    with pytest.raises(YAMLGenerationError, match="verification failed"):
        generate(rules=sample_rules, output_path=output_path)


@pytest.mark.unit
def test_generate_raises_error_on_file_disappears(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule], monkeypatch
) -> None:
    """Test that file disappearing during verification raises error."""
    output_path = "/output/rules.yml"

    # Track open calls to differentiate write vs read
    original_open = open
    open_calls = []

    def tracking_open(path, mode="r", *args, **kwargs):
        open_calls.append((str(path), mode))
        # Allow first write, fail on verification read
        if len(open_calls) == 2 and mode == "r":
            # This is the verification read - simulate file vanished
            msg = str(path)
            raise FileNotFoundError(msg)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", tracking_open)

    # Should raise YAMLGenerationError (wrapping FileNotFoundError)
    with pytest.raises(YAMLGenerationError):
        generate(rules=sample_rules, output_path=output_path)


# ============================================================================
# Test Group 7: Read-Back Verification
# ============================================================================


@pytest.mark.unit
def test_generate_performs_readback_verification(
    fs: FakeFilesystem, sample_rules: list[ExtractedRule], monkeypatch
) -> None:
    """Test that generate() reads back and validates the written file."""
    output_path = "/output/rules.yml"

    # First call should succeed
    generate(rules=sample_rules, output_path=output_path)

    # Verify file was created
    assert Path(output_path).exists()

    # Now simulate file corruption during read-back by monkey-patching
    original_open = open
    call_count = {"count": 0}

    def mock_open(*args, **kwargs):
        call_count["count"] += 1
        # First call: write (succeeds)
        # Second call: read-back (return corrupted content)
        if call_count["count"] == 2:
            from io import StringIO
            return StringIO("invalid: yaml: [syntax")
        return original_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    # This should fail during verification
    with pytest.raises(YAMLGenerationError, match="verification failed"):
        generate(rules=sample_rules, output_path=output_path)
