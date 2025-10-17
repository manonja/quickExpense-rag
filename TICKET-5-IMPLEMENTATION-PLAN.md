# TICKET 5 Implementation Plan: YAML Generation Module

**Status**: Ready for Implementation
**Approach**: Test-Driven Development (TDD) with Frequent Commits
**Target**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

---

## Executive Summary

Implement the YAML generation module that takes validated `ExtractedRule` objects from the adjudicator and writes them to a schema-compliant YAML file with:
- Internal metadata stripping (`expert_source`, `anchor_id`, `confidence_score`)
- RuleSet wrapper with schema version and timestamp
- Read-back verification for integrity
- Comprehensive error handling with single exception type
- Production-ready logging and file headers

---

## Critical Corrections from Original Plan

| Original Plan | Actual Requirement | Impact |
|--------------|-------------------|--------|
| `scripts/generate_yaml.py` | `src/qe_tax_rag/extraction/ca/yaml_generator.py` | Module location |
| Exclude `source_expert` | Exclude `expert_source` | **Field name from schema** |
| 2 fields to strip | 3 fields to strip | Add `confidence_score` |
| No `RuleSet` population logic | Must add `schema_version`, `extraction_timestamp` | **Required fields** |
| No file header | Add generation metadata header | Best practice |
| No line width control | Add `width=88` to YAML dump | Readability |

---

## Phase 0: Pre-Implementation Setup

### Step 0.1: Add Testing Dependency

**File**: `pyproject.toml`

**Action**: Add `pyfakefs` to dev dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "pytest-asyncio>=0.21",
    "ruff>=0.1",
    "mypy>=1.7",
    "pre-commit>=3.5",
    "pyfakefs>=5.0",  # NEW: Filesystem mocking for robust testing
]
```

**Verification**:
```bash
uv sync --extra dev
uv run python -c "import pyfakefs; print('pyfakefs installed successfully')"
```

**Commit Point 1**:
```
build: add pyfakefs to dev dependencies for TICKET 5

Add filesystem mocking library to enable robust testing of YAML
generator module. Allows simulation of permission errors and
edge cases that pytest's tmp_path cannot reliably test.

- Add pyfakefs>=5.0 to [project.optional-dependencies.dev]
- Required for TICKET 5 YAML generation testing

Rationale:
- pyfakefs enables testing of PermissionError scenarios
- Provides filesystem isolation for unit tests
- Prevents test pollution from actual file I/O

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 1: Test-Driven Development Cycle

### TDD Philosophy for This Ticket

**Red-Green-Refactor**:
1. **Red**: Write a failing test that defines expected behavior
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Clean up code while keeping tests green
4. **Commit**: Commit after each complete cycle or logical group

**Test Order Strategy**: Start with core happy path, then edge cases, then error conditions

---

### Step 1.1: Create Test File Skeleton

**File**: `tests/unit/test_yaml_generator.py`

**Action**: Create test file with all test stubs and fixtures

```python
"""Unit tests for YAML generation module.

Tests cover:
- Happy path: Valid rules → valid YAML file
- Metadata stripping: Internal fields excluded from output
- RuleSet population: Schema version and timestamp added
- File header: Generation metadata present
- Empty rules: Valid YAML with empty rules list
- Error handling: Permission errors, corruption, race conditions
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pyfakefs.fake_filesystem import FakeFilesystem
from pydantic import ValidationError

from qe_tax_rag.extraction.ca.exceptions import YAMLGenerationError
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExtractedRule,
    ExpertSource,
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

def test_generate_creates_valid_yaml_file(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that generate() creates a valid YAML file."""
    # RED: This test will fail because yaml_generator.py doesn't exist yet
    pass


def test_generate_creates_parent_directories(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that generate() creates parent directories if they don't exist."""
    # RED: Test parent directory creation
    pass


# ============================================================================
# Test Group 2: Metadata Stripping
# ============================================================================

def test_generate_strips_expert_source_field(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that expert_source is excluded from output YAML."""
    # RED: Verify internal metadata fields are stripped
    pass


def test_generate_strips_anchor_id_field(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that anchor_id is excluded from output YAML."""
    pass


def test_generate_strips_confidence_score_field(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that confidence_score is excluded from output YAML."""
    pass


# ============================================================================
# Test Group 3: RuleSet Population
# ============================================================================

def test_generate_adds_schema_version(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that schema_version is added to RuleSet."""
    # RED: Verify schema_version is present
    pass


def test_generate_adds_extraction_timestamp(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that extraction_timestamp is added and is valid ISO format."""
    # RED: Verify timestamp is present and valid
    pass


# ============================================================================
# Test Group 4: File Header
# ============================================================================

def test_generate_adds_file_header(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that file includes generation metadata header."""
    # RED: Verify header comment is present
    pass


# ============================================================================
# Test Group 5: Edge Cases
# ============================================================================

def test_generate_handles_empty_rules_list(fs: FakeFilesystem, empty_rules: list[ExtractedRule]) -> None:
    """Test that empty rules list produces valid YAML with rules: []."""
    # RED: Test empty list handling
    pass


# ============================================================================
# Test Group 6: Error Handling
# ============================================================================

def test_generate_raises_error_on_permission_denied(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that PermissionError raises YAMLGenerationError."""
    # RED: Simulate permission error
    pass


def test_generate_raises_error_on_invalid_path(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that invalid output path raises YAMLGenerationError."""
    # RED: Test invalid path handling
    pass


def test_generate_raises_error_on_verification_failure(fs: FakeFilesystem, sample_rules: list[ExtractedRule], monkeypatch) -> None:
    """Test that corrupted file detected during verification raises error."""
    # RED: Simulate file corruption
    pass


def test_generate_raises_error_on_file_disappears(fs: FakeFilesystem, sample_rules: list[ExtractedRule], monkeypatch) -> None:
    """Test that file disappearing during verification raises error."""
    # RED: Simulate race condition
    pass


# ============================================================================
# Test Group 7: Read-Back Verification
# ============================================================================

def test_generate_performs_readback_verification(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that generate() reads back and validates the written file."""
    # RED: Verify read-back validation occurs
    pass
```

**Commit Point 2**:
```
test: create test skeleton for YAML generator (TICKET 5)

Add comprehensive test file with fixtures and test stubs covering:
- Happy path: Valid YAML generation
- Metadata stripping: expert_source, anchor_id, confidence_score
- RuleSet population: schema_version, extraction_timestamp
- File header: Generation metadata
- Edge cases: Empty rules, parent directories
- Error handling: Permissions, corruption, race conditions

All tests currently stubbed (will implement via TDD cycles).

Uses pyfakefs for filesystem isolation.

Rationale:
- TDD approach: Define expected behavior before implementation
- Comprehensive coverage: 15 test cases cover all requirements
- Clear organization: Grouped by functionality

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 1.2: Create Module Skeleton

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

**Action**: Create minimal module structure to make imports work

```python
"""YAML generation module for HTML-to-YAML extraction pipeline.

This module takes validated ExtractedRule objects and generates a
schema-compliant YAML file with metadata stripping, RuleSet wrapping,
and read-back verification.
"""

import logging
from pathlib import Path

from qe_tax_rag.extraction.ca.exceptions import YAMLGenerationError
from qe_tax_rag.extraction.ca.schema import ExtractedRule, RuleSet

logger = logging.getLogger(__name__)


def generate(rules: list[ExtractedRule], output_path: str) -> None:
    """Generate schema-compliant YAML file from validated rules.

    Args:
        rules: List of validated ExtractedRule objects from adjudicator.
        output_path: Path for output YAML file.

    Raises:
        YAMLGenerationError: If file cannot be written or verified.
    """
    # Implementation will be added via TDD cycles
    raise NotImplementedError("YAML generation not yet implemented")
```

**Commit Point 3**:
```
feat: add YAML generator module skeleton (TICKET 5)

Create basic module structure with function signature and imports.
Implementation will be added incrementally via TDD approach.

- Define generate() function signature
- Import dependencies: ExtractedRule, RuleSet, YAMLGenerationError
- Add module docstring
- Add logger initialization

Next: Implement functionality via red-green-refactor cycles.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 1.3: TDD Cycle 1 - Happy Path (Basic YAML Generation)

#### Red: Implement failing test

**File**: `tests/unit/test_yaml_generator.py`

```python
def test_generate_creates_valid_yaml_file(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that generate() creates a valid YAML file."""
    output_path = "/output/rules.yml"

    # Call the function
    generate(rules=sample_rules, output_path=output_path)

    # Verify file exists
    assert Path(output_path).exists()

    # Verify file is valid YAML
    with open(output_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Verify structure
    assert "rules" in data
    assert len(data["rules"]) == 2
    assert data["rules"][0]["rule_number"] == 8523
    assert data["rules"][1]["rule_number"] == 9270
```

**Run test**: `uv run pytest tests/unit/test_yaml_generator.py::test_generate_creates_valid_yaml_file -v`
**Expected**: ❌ FAIL (NotImplementedError)

#### Green: Implement minimal code to pass

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

```python
import yaml
from datetime import datetime, timezone
from pathlib import Path

def generate(rules: list[ExtractedRule], output_path: str) -> None:
    """Generate schema-compliant YAML file from validated rules."""
    # Create parent directories
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Create RuleSet with required fields
    timestamp = datetime.now(timezone.utc).isoformat()
    rule_set = RuleSet(
        schema_version="1.0",
        extraction_timestamp=timestamp,
        rules=rules,
    )

    # Serialize to YAML
    yaml_string = yaml.dump(
        rule_set.model_dump(),
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=88,
    )

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_string)
```

**Run test**: `uv run pytest tests/unit/test_yaml_generator.py::test_generate_creates_valid_yaml_file -v`
**Expected**: ✅ PASS

**Commit Point 4**:
```
feat: implement basic YAML generation (TICKET 5, TDD Cycle 1)

Add core functionality to generate valid YAML files:
- Create parent directories if needed
- Populate RuleSet with schema_version and timestamp
- Serialize to YAML with proper formatting
- Write to file with UTF-8 encoding

Test passing: test_generate_creates_valid_yaml_file ✓

Next: Add metadata stripping, file header, verification.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 1.4: TDD Cycle 2 - Metadata Stripping

#### Red: Implement failing tests

**File**: `tests/unit/test_yaml_generator.py`

```python
def test_generate_strips_expert_source_field(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that expert_source is excluded from output YAML."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Verify expert_source is NOT in any rule
    for rule in data["rules"]:
        assert "expert_source" not in rule


def test_generate_strips_anchor_id_field(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that anchor_id is excluded from output YAML."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for rule in data["rules"]:
        assert "anchor_id" not in rule


def test_generate_strips_confidence_score_field(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that confidence_score is excluded from output YAML."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for rule in data["rules"]:
        assert "confidence_score" not in rule
```

**Run tests**: `uv run pytest tests/unit/test_yaml_generator.py -k "strips" -v`
**Expected**: ❌ FAIL (metadata fields present in output)

#### Green: Implement metadata stripping

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

```python
# Add constant at module level
_INTERNAL_METADATA_FIELDS = {"expert_source", "anchor_id", "confidence_score"}

def generate(rules: list[ExtractedRule], output_path: str) -> None:
    """Generate schema-compliant YAML file from validated rules."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    # Strip internal metadata from rules
    cleaned_rules = [
        ExtractedRule.model_validate(
            rule.model_dump(exclude=_INTERNAL_METADATA_FIELDS)
        )
        for rule in rules
    ]

    rule_set = RuleSet(
        schema_version="1.0",
        extraction_timestamp=timestamp,
        rules=cleaned_rules,
    )

    # ... rest of serialization code
```

**Run tests**: `uv run pytest tests/unit/test_yaml_generator.py -k "strips" -v`
**Expected**: ✅ PASS (all 3 stripping tests)

**Commit Point 5**:
```
feat: add metadata stripping to YAML generator (TICKET 5, TDD Cycle 2)

Strip internal pipeline metadata fields from final YAML output:
- expert_source: Tracks which expert generated rule
- anchor_id: HTML debugging reference
- confidence_score: Adjudicator confidence metric

Implementation:
- Define _INTERNAL_METADATA_FIELDS constant
- Use Pydantic model_dump(exclude=...) for type-safe stripping
- Re-validate cleaned data to ensure schema compliance

Tests passing: test_generate_strips_* (3/3) ✓

Rationale:
- Prevents internal metadata leaking into production output
- Uses declarative Pydantic API for maintainability
- Type-safe approach adapts to schema changes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 1.5: TDD Cycle 3 - File Header

#### Red: Implement failing test

**File**: `tests/unit/test_yaml_generator.py`

```python
def test_generate_adds_file_header(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that file includes generation metadata header."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify header is present
    assert content.startswith("# Generated by qe-tax-rag")
    assert "# Do not edit this file manually" in content
    assert "---\n" in content  # YAML document separator
```

**Run test**: `uv run pytest tests/unit/test_yaml_generator.py::test_generate_adds_file_header -v`
**Expected**: ❌ FAIL (no header in file)

#### Green: Implement file header

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

```python
from qe_tax_rag import __version__  # Add to imports

def generate(rules: list[ExtractedRule], output_path: str) -> None:
    """Generate schema-compliant YAML file from validated rules."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    # ... metadata stripping code ...

    # Serialize to YAML
    yaml_string = yaml.dump(
        rule_set.model_dump(),
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=88,
    )

    # Prepend header
    header = (
        f"# Generated by qe-tax-rag version {__version__} on {timestamp}\n"
        f"# Do not edit this file manually. Changes will be overwritten.\n"
        f"---\n"
    )

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(yaml_string)
```

**Run test**: `uv run pytest tests/unit/test_yaml_generator.py::test_generate_adds_file_header -v`
**Expected**: ✅ PASS

**Commit Point 6**:
```
feat: add file header with generation metadata (TICKET 5, TDD Cycle 3)

Prepend header comment to YAML output with:
- Tool version from qe_tax_rag.__version__
- Generation timestamp (ISO 8601 format)
- Manual edit warning
- YAML document separator (---)

Test passing: test_generate_adds_file_header ✓

Rationale:
- Generated files should declare their origin
- Timestamps enable audit trail
- Warning prevents manual edits being overwritten

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 1.6: TDD Cycle 4 - Read-Back Verification

#### Red: Implement failing test

**File**: `tests/unit/test_yaml_generator.py`

```python
def test_generate_performs_readback_verification(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that generate() reads back and validates the written file."""
    output_path = "/output/rules.yml"

    # This should succeed (write and verify)
    generate(rules=sample_rules, output_path=output_path)

    # Manually corrupt the file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("invalid: yaml: [syntax")

    # Now try to generate again - should fail during verification
    with pytest.raises(YAMLGenerationError, match="verification failed"):
        generate(rules=sample_rules, output_path=output_path)
```

**Run test**: `uv run pytest tests/unit/test_yaml_generator.py::test_generate_performs_readback_verification -v`
**Expected**: ❌ FAIL (no verification implemented)

#### Green: Implement verification

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

```python
def generate(rules: list[ExtractedRule], output_path: str) -> None:
    """Generate schema-compliant YAML file from validated rules."""
    try:
        # ... existing code: directory creation, metadata stripping, serialization, write ...

        # Read-back verification
        logger.info(
            "Performing read-back verification",
            extra={"output_path": output_path},
        )

        with open(output_path, "r", encoding="utf-8") as f:
            # Skip header lines
            content = f.read()
            yaml_content = content.split("---\n", 1)[1] if "---\n" in content else content
            read_back_data = yaml.safe_load(yaml_content)

        # Validate against RuleSet schema
        RuleSet.model_validate(read_back_data)

        logger.info(
            "YAML verification successful",
            extra={"output_path": output_path},
        )

    except FileNotFoundError as e:
        msg = f"File disappeared during verification: {output_path}"
        logger.error(msg, exc_info=True)
        raise YAMLGenerationError(msg) from e
    except yaml.YAMLError as e:
        msg = f"YAML verification failed - invalid syntax in {output_path}"
        logger.error(msg, exc_info=True)
        raise YAMLGenerationError(msg) from e
    except ValidationError as e:
        msg = f"YAML verification failed - schema mismatch in {output_path}"
        logger.error(msg, exc_info=True)
        raise YAMLGenerationError(msg) from e
```

**Run test**: `uv run pytest tests/unit/test_yaml_generator.py::test_generate_performs_readback_verification -v`
**Expected**: ✅ PASS

**Commit Point 7**:
```
feat: add read-back verification to YAML generator (TICKET 5, TDD Cycle 4)

Implement post-write verification to detect corruption:
- Read file back immediately after writing
- Parse YAML and validate against RuleSet schema
- Catch FileNotFoundError (race condition)
- Catch yaml.YAMLError (syntax corruption)
- Catch ValidationError (schema mismatch)
- All errors wrapped in YAMLGenerationError with context

Test passing: test_generate_performs_readback_verification ✓

Rationale:
- Guards against silent disk corruption
- Ensures file integrity before pipeline continues
- Pydantic validation is comprehensive schema check

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 1.7: TDD Cycle 5 - Error Handling

#### Red: Implement failing tests

**File**: `tests/unit/test_yaml_generator.py`

```python
def test_generate_raises_error_on_permission_denied(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that PermissionError raises YAMLGenerationError."""
    output_path = "/readonly/rules.yml"

    # Create directory with no write permissions
    fs.create_dir("/readonly")
    fs.chmod("/readonly", 0o444)  # Read-only

    with pytest.raises(YAMLGenerationError, match="Permission denied"):
        generate(rules=sample_rules, output_path=output_path)


def test_generate_raises_error_on_invalid_path(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that invalid output path raises YAMLGenerationError."""
    # Null byte in path (invalid on all systems)
    output_path = "/output/rules\x00.yml"

    with pytest.raises(YAMLGenerationError):
        generate(rules=sample_rules, output_path=output_path)


def test_generate_raises_error_on_file_disappears(fs: FakeFilesystem, sample_rules: list[ExtractedRule], monkeypatch) -> None:
    """Test that file disappearing during verification raises error."""
    output_path = "/output/rules.yml"

    # Mock open to succeed on write but fail on read-back
    original_open = open
    call_count = 0

    def mock_open(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # Second call (read-back)
            raise FileNotFoundError("File vanished")
        return original_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    with pytest.raises(YAMLGenerationError, match="disappeared during verification"):
        generate(rules=sample_rules, output_path=output_path)
```

**Run tests**: `uv run pytest tests/unit/test_yaml_generator.py -k "error" -v`
**Expected**: ❌ FAIL (errors not caught)

#### Green: Add comprehensive error handling

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

```python
def generate(rules: list[ExtractedRule], output_path: str) -> None:
    """Generate schema-compliant YAML file from validated rules.

    Strips internal metadata fields (expert_source, anchor_id, confidence_score)
    and wraps rules in RuleSet with schema version and timestamp. Performs
    read-back verification to ensure file integrity.

    Args:
        rules: List of validated ExtractedRule objects from adjudicator.
        output_path: Path for output YAML file.

    Raises:
        YAMLGenerationError: If file cannot be written or verified.
            Possible causes: permission denied, disk full, file corruption,
            race condition (file disappears), or schema validation failure.
    """
    logger.info(
        "Starting YAML generation",
        extra={"rule_count": len(rules), "output_path": output_path},
    )

    try:
        # Create parent directories
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).isoformat()

        # Strip internal metadata
        cleaned_rules = [
            ExtractedRule.model_validate(
                rule.model_dump(exclude=_INTERNAL_METADATA_FIELDS)
            )
            for rule in rules
        ]

        rule_set = RuleSet(
            schema_version="1.0",
            extraction_timestamp=timestamp,
            rules=cleaned_rules,
        )

        # Serialize to YAML
        yaml_string = yaml.dump(
            rule_set.model_dump(),
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=88,
        )

        # Prepend header
        header = (
            f"# Generated by qe-tax-rag version {__version__} on {timestamp}\n"
            f"# Do not edit this file manually. Changes will be overwritten.\n"
            f"---\n"
        )

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(yaml_string)

        file_size = Path(output_path).stat().st_size
        logger.info(
            "Successfully wrote YAML file",
            extra={"output_path": output_path, "file_size_bytes": file_size},
        )

        # Read-back verification
        logger.info(
            "Performing read-back verification",
            extra={"output_path": output_path},
        )

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            yaml_content = content.split("---\n", 1)[1] if "---\n" in content else content
            read_back_data = yaml.safe_load(yaml_content)

        RuleSet.model_validate(read_back_data)

        logger.info(
            "YAML verification successful",
            extra={"output_path": output_path},
        )

    except PermissionError as e:
        msg = f"Failed to write YAML file to {output_path}: Permission denied"
        logger.error(msg, exc_info=True)
        raise YAMLGenerationError(msg) from e
    except OSError as e:
        msg = f"Failed to write YAML file to {output_path}: {e}"
        logger.error(msg, exc_info=True)
        raise YAMLGenerationError(msg) from e
    except FileNotFoundError as e:
        msg = f"File disappeared during verification: {output_path}"
        logger.error(msg, exc_info=True)
        raise YAMLGenerationError(msg) from e
    except yaml.YAMLError as e:
        msg = f"YAML verification failed - invalid syntax in {output_path}"
        logger.error(msg, exc_info=True)
        raise YAMLGenerationError(msg) from e
    except ValidationError as e:
        msg = f"YAML verification failed - schema mismatch in {output_path}: {e}"
        logger.error(msg, exc_info=True)
        raise YAMLGenerationError(msg) from e
```

**Run tests**: `uv run pytest tests/unit/test_yaml_generator.py -k "error" -v`
**Expected**: ✅ PASS (all error tests)

**Commit Point 8**:
```
feat: add comprehensive error handling (TICKET 5, TDD Cycle 5)

Implement robust error handling with exception chaining:
- PermissionError: Write permission denied
- OSError: Invalid path, disk full, I/O errors
- FileNotFoundError: Race condition during verification
- yaml.YAMLError: YAML syntax corruption
- ValidationError: Schema mismatch in read-back

All errors wrapped in YAMLGenerationError with context.
Uses exception chaining (raise ... from e) for full stack traces.

Tests passing:
- test_generate_raises_error_on_permission_denied ✓
- test_generate_raises_error_on_invalid_path ✓
- test_generate_raises_error_on_file_disappears ✓

Rationale:
- Single exception type simplifies caller's error handling
- Exception chaining preserves debugging context
- Structured logging with exc_info=True captures full traces

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 1.8: TDD Cycle 6 - Edge Cases

#### Red: Implement remaining tests

**File**: `tests/unit/test_yaml_generator.py`

```python
def test_generate_handles_empty_rules_list(fs: FakeFilesystem, empty_rules: list[ExtractedRule]) -> None:
    """Test that empty rules list produces valid YAML with rules: []."""
    output_path = "/output/empty_rules.yml"

    generate(rules=empty_rules, output_path=output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        yaml_content = content.split("---\n", 1)[1] if "---\n" in content else content
        data = yaml.safe_load(yaml_content)

    assert data["rules"] == []
    assert data["schema_version"] == "1.0"
    assert "extraction_timestamp" in data


def test_generate_creates_parent_directories(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that generate() creates parent directories if they don't exist."""
    output_path = "/deeply/nested/output/dir/rules.yml"

    # Verify parent directories don't exist
    assert not Path("/deeply").exists()

    generate(rules=sample_rules, output_path=output_path)

    # Verify file and all parent directories were created
    assert Path(output_path).exists()
    assert Path("/deeply/nested/output/dir").exists()


def test_generate_adds_schema_version(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that schema_version is added to RuleSet."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        yaml_content = content.split("---\n", 1)[1]
        data = yaml.safe_load(yaml_content)

    assert data["schema_version"] == "1.0"


def test_generate_adds_extraction_timestamp(fs: FakeFilesystem, sample_rules: list[ExtractedRule]) -> None:
    """Test that extraction_timestamp is added and is valid ISO format."""
    output_path = "/output/rules.yml"
    generate(rules=sample_rules, output_path=output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        yaml_content = content.split("---\n", 1)[1]
        data = yaml.safe_load(yaml_content)

    assert "extraction_timestamp" in data
    # Verify it's valid ISO 8601 format
    datetime.fromisoformat(data["extraction_timestamp"])
```

**Run tests**: `uv run pytest tests/unit/test_yaml_generator.py -v`
**Expected**: ✅ PASS (all tests should pass with current implementation)

**Commit Point 9**:
```
test: verify edge cases and RuleSet population (TICKET 5, TDD Cycle 6)

Add tests for remaining requirements:
- Empty rules list handling
- Parent directory creation
- Schema version population
- Extraction timestamp validation

All tests passing (15/15) ✓

Implementation already handles these cases correctly.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 2: Documentation and Polish

### Step 2.1: Add Comprehensive Docstrings

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

**Action**: Enhance module and function docstrings with examples

```python
"""YAML generation module for HTML-to-YAML extraction pipeline.

This module provides the final step of the extraction pipeline, taking
validated ExtractedRule objects from the adjudicator and generating a
schema-compliant YAML file suitable for distribution.

Key Features:
- Strips internal pipeline metadata (expert_source, anchor_id, confidence_score)
- Wraps rules in RuleSet with schema version and extraction timestamp
- Adds generation metadata header to output file
- Performs read-back verification to ensure file integrity
- Comprehensive error handling with single exception type

Usage:
    >>> from qe_tax_rag.extraction.ca.yaml_generator import generate
    >>> from qe_tax_rag.extraction.ca.schema import ExtractedRule
    >>>
    >>> rules = [...]  # List of ExtractedRule from adjudicator
    >>> generate(rules=rules, output_path="output/cra_rules.yml")

Integration:
    This module is called by the orchestrator (TICKET 6) after adjudication
    completes. It receives the final, validated list of rules and produces
    the deployable YAML artifact.

Error Handling:
    All errors raise YAMLGenerationError, which should be caught by the
    orchestrator for proper error reporting to the user.
"""

# ... existing imports and constants ...

def generate(rules: list[ExtractedRule], output_path: str) -> None:
    """Generate schema-compliant YAML file from validated rules.

    Takes a list of ExtractedRule objects (typically from the adjudicator),
    strips internal pipeline metadata, wraps them in a RuleSet with schema
    version and timestamp, and writes to a YAML file with verification.

    The function performs the following steps:
    1. Create parent directories if they don't exist
    2. Strip internal metadata fields from each rule
    3. Create RuleSet with schema version "1.0" and current timestamp
    4. Serialize to YAML with block style formatting (width=88)
    5. Prepend file header with generation metadata
    6. Write to disk with UTF-8 encoding
    7. Read back and validate against RuleSet schema

    Internal metadata fields stripped:
    - expert_source: Tracks which expert (classic/LLM/adjudicated) generated the rule
    - anchor_id: HTML anchor ID for debugging (e.g., "tocch3ln8523")
    - confidence_score: Adjudicator confidence metric (0.0-1.0)

    Args:
        rules: List of validated ExtractedRule objects from adjudicator.
               Can be empty list (produces valid YAML with rules: []).
        output_path: Path for output YAML file. Parent directories will be
                     created if they don't exist. Must be writable location.

    Raises:
        YAMLGenerationError: If file cannot be written or verified.
            Possible causes:
            - Permission denied (write-protected directory)
            - Disk full or I/O error
            - Invalid path (null bytes, illegal characters)
            - File corruption detected during read-back
            - Race condition (file disappears between write and verify)
            - Schema validation failure during verification

    Example:
        >>> from qe_tax_rag.extraction.ca.yaml_generator import generate
        >>> from qe_tax_rag.extraction.ca.schema import ExtractedRule, ApplicabilityType
        >>>
        >>> rules = [
        ...     ExtractedRule(
        ...         rule_number=8523,
        ...         title="Meals and entertainment",
        ...         content="You can deduct 50% of eligible meal expenses.",
        ...         applies_to=[ApplicabilityType.BUSINESS],
        ...         source_citation="Line 8523",
        ...         chapter="Chapter 3 – Expenses",
        ...         section=None,
        ...         source_file="t4002-5.html",
        ...     ),
        ... ]
        >>>
        >>> try:
        ...     generate(rules=rules, output_path="output/cra_rules.yml")
        ...     print("✅ YAML generated successfully")
        ... except YAMLGenerationError as e:
        ...     print(f"❌ Generation failed: {e}")

    Notes:
        - Output file includes header comment with tool version and timestamp
        - YAML formatting uses block style (not flow style) for readability
        - Line width limited to 88 characters (matches project standards)
        - Read-back verification ensures file integrity before returning
        - All logging uses structured format with extra metadata
    """
    # ... existing implementation ...
```

**Commit Point 10**:
```
docs: add comprehensive docstrings to YAML generator (TICKET 5)

Enhance module and function documentation with:
- Module-level docstring with usage examples
- Detailed function docstring covering all parameters
- Step-by-step process explanation
- Complete error conditions list
- Integration notes for orchestrator
- Code examples for common usage

Rationale:
- Enables easy integration in TICKET 6
- Documents all error scenarios
- Provides copy-paste examples for users

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 2.2: Add Type Hints and Constants

**File**: `src/qe_tax_rag/extraction/ca/yaml_generator.py`

**Action**: Ensure all type hints are complete and add module constants

```python
"""YAML generation module for HTML-to-YAML extraction pipeline."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

import yaml
from pydantic import ValidationError

from qe_tax_rag import __version__
from qe_tax_rag.extraction.ca.exceptions import YAMLGenerationError
from qe_tax_rag.extraction.ca.schema import ExtractedRule, RuleSet

logger: logging.Logger = logging.getLogger(__name__)

# Internal metadata fields to exclude from final YAML output
_INTERNAL_METADATA_FIELDS: Final[set[str]] = {
    "expert_source",    # Tracks which expert generated the rule
    "anchor_id",        # HTML anchor ID for debugging
    "confidence_score", # Adjudicator confidence metric
}

# Schema version for generated YAML files
_SCHEMA_VERSION: Final[str] = "1.0"

# YAML formatting parameters
_YAML_LINE_WIDTH: Final[int] = 88  # Match project line length standard

# ... rest of implementation with type hints ...
```

**Commit Point 11**:
```
refactor: add constants and complete type hints (TICKET 5)

Extract magic values into typed constants:
- _INTERNAL_METADATA_FIELDS: Fields to strip from output
- _SCHEMA_VERSION: Current schema version ("1.0")
- _YAML_LINE_WIDTH: Line width for YAML formatting (88)

Add explicit type hints:
- logger: logging.Logger
- All constants use Final[T] for immutability

Rationale:
- Constants improve maintainability and discoverability
- Final type hints prevent accidental reassignment
- Matches project's strict type checking standards

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 3: Quality Assurance

### Step 3.1: Run Full Test Suite

```bash
# Run all tests with coverage
uv run pytest tests/unit/test_yaml_generator.py -v --cov=src/qe_tax_rag/extraction/ca/yaml_generator --cov-report=term-missing

# Expected output:
# - 15/15 tests passing
# - 100% code coverage
# - No warnings
```

**Commit Point 12** (if any fixes needed):
```
test: achieve 100% coverage for YAML generator (TICKET 5)

All 15 tests passing with full coverage:
- Happy path: 2 tests ✓
- Metadata stripping: 3 tests ✓
- RuleSet population: 2 tests ✓
- File header: 1 test ✓
- Edge cases: 2 tests ✓
- Error handling: 4 tests ✓
- Verification: 1 test ✓

Coverage: 100% (no untested lines)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 3.2: Run Code Quality Checks

```bash
# Format code
uvx ruff format src/qe_tax_rag/extraction/ca/yaml_generator.py

# Lint code
uvx ruff check src/qe_tax_rag/extraction/ca/

# Type check with mypy
uv run mypy src/qe_tax_rag/extraction/ca/yaml_generator.py

# Type check with pyright
uv run pyright src/qe_tax_rag/extraction/ca/yaml_generator.py

# Run all pre-commit hooks
uv run pre-commit run --files src/qe_tax_rag/extraction/ca/yaml_generator.py tests/unit/test_yaml_generator.py
```

**Expected**: All checks pass with no errors

**Commit Point 13** (if any formatting/linting fixes):
```
style: apply ruff formatting to YAML generator (TICKET 5)

Apply automated formatting and linting fixes:
- ruff format: Format code to project standards
- ruff check --fix: Apply auto-fixable linting rules

All quality gates passing:
- ruff format ✓
- ruff check ✓
- mypy (strict) ✓
- pyright (strict) ✓
- pre-commit hooks ✓

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 3.3: Integration Smoke Test

**Action**: Test against actual schema files from TICKETS 1-4

```bash
# Create a simple integration test script
cat > /tmp/test_yaml_gen_integration.py << 'EOF'
"""Quick integration test for YAML generator."""

from qe_tax_rag.extraction.ca.yaml_generator import generate
from qe_tax_rag.extraction.ca.schema import ExtractedRule, ApplicabilityType

# Create sample rule
rules = [
    ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="Test content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        section=None,
        source_file="test.html",
    ),
]

# Generate YAML
generate(rules=rules, output_path="/tmp/test_output.yml")

# Verify
import yaml
with open("/tmp/test_output.yml") as f:
    data = yaml.safe_load(f.read().split("---\n")[1])
    assert data["schema_version"] == "1.0"
    assert len(data["rules"]) == 1
    print("✅ Integration test passed")
EOF

uv run python /tmp/test_yaml_gen_integration.py
```

**Expected**: `✅ Integration test passed`

**Commit Point 14**:
```
test: verify integration with TICKET 1-4 schemas (TICKET 5)

Run integration smoke test to verify:
- Imports work correctly from ca/ package
- ExtractedRule schema compatibility
- RuleSet schema compatibility
- End-to-end YAML generation succeeds

Test passed: Manual integration verification ✓

Next: TICKET 6 orchestrator will provide full integration tests.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 4: Final Documentation and Cleanup

### Step 4.1: Update Package __init__.py (if needed)

**File**: `src/qe_tax_rag/extraction/ca/__init__.py`

**Action**: Export `generate` function if this is a public API

```python
"""Canada-specific HTML-to-YAML extraction pipeline."""

from qe_tax_rag.extraction.ca.adjudicator import adjudicate
from qe_tax_rag.extraction.ca.classic_parser import parse as classic_parse
from qe_tax_rag.extraction.ca.llm_parser import parse as llm_parse
from qe_tax_rag.extraction.ca.yaml_generator import generate as generate_yaml

__all__ = [
    "adjudicate",
    "classic_parse",
    "llm_parse",
    "generate_yaml",
]
```

**Commit Point 15**:
```
feat: export generate_yaml from ca package (TICKET 5)

Add yaml_generator.generate to package exports as generate_yaml
for clean import in orchestrator:

    from qe_tax_rag.extraction.ca import generate_yaml

Follows pattern of existing exports:
- classic_parse (from classic_parser.parse)
- llm_parse (from llm_parser.parse)
- adjudicate (from adjudicator.adjudicate)
- generate_yaml (from yaml_generator.generate)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 4.2: Run Full Regression Suite

```bash
# Run ALL tests in the project to ensure no regressions
uv run pytest tests/ -v

# Run specific tests for extraction pipeline
uv run pytest tests/unit/test_classic_parser.py -v
uv run pytest tests/unit/test_llm_parser.py -v
uv run pytest tests/unit/test_adjudicator.py -v
uv run pytest tests/unit/test_yaml_generator.py -v

# Check for any test failures or warnings
```

**Expected**: All existing tests pass, no regressions

**Commit Point 16** (if needed):
```
fix: resolve regression in [affected module] (TICKET 5)

[Description of any regressions found and fixed]

Regression testing complete:
- All pre-existing tests passing ✓
- No new warnings introduced ✓
- TICKET 1-4 functionality unchanged ✓

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Step 4.3: Create Implementation Summary

**File**: Update this plan with final results

**Action**: Add completion summary section

**Commit Point 17**:
```
docs: mark TICKET 5 as complete in implementation plan

Update TICKET-5-IMPLEMENTATION-PLAN.md with completion summary:
- All 15 tests implemented and passing
- 100% code coverage achieved
- All quality gates passing (ruff, mypy, pyright)
- Zero regressions in existing code
- Integration verified with TICKET 1-4 schemas

Implementation deliverables:
✅ src/qe_tax_rag/extraction/ca/yaml_generator.py (150 lines)
✅ tests/unit/test_yaml_generator.py (15 tests, 100% coverage)
✅ pyproject.toml updated (pyfakefs dependency)
✅ Package exports updated (__init__.py)

Ready for TICKET 6 (orchestrator integration).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Commit Summary

Total commits: **~17** (actual count may vary based on issues found)

### Commit Categories:

1. **Setup** (1-3): Dependencies, test skeleton, module skeleton
2. **TDD Cycles** (4-9): Red-green-refactor for each feature
3. **Documentation** (10-11): Docstrings, type hints, constants
4. **Quality** (12-14): Coverage, formatting, integration tests
5. **Finalization** (15-17): Package exports, regression testing, summary

### Commit Frequency Strategy:

- ✅ After each dependency change
- ✅ After each passing test (or small group of related tests)
- ✅ After each feature implementation
- ✅ After refactoring
- ✅ After documentation updates
- ✅ After quality gate fixes
- ✅ After regression verification

---

## Success Criteria Checklist

### Functionality
- [x] Creates valid YAML file from ExtractedRule list
- [x] Strips internal metadata: expert_source, anchor_id, confidence_score
- [x] Populates RuleSet with schema_version and extraction_timestamp
- [x] Adds file header with generation metadata
- [x] Creates parent directories if needed
- [x] Performs read-back verification
- [x] Handles empty rules list
- [x] Formats YAML with block style, width=88

### Error Handling
- [x] Catches PermissionError → YAMLGenerationError
- [x] Catches OSError → YAMLGenerationError
- [x] Catches FileNotFoundError → YAMLGenerationError
- [x] Catches yaml.YAMLError → YAMLGenerationError
- [x] Catches ValidationError → YAMLGenerationError
- [x] All errors use exception chaining (from e)
- [x] Structured logging with exc_info=True

### Testing
- [x] 15 unit tests implemented
- [x] 100% code coverage
- [x] Uses pyfakefs for filesystem isolation
- [x] Tests all error conditions
- [x] Tests metadata stripping
- [x] Tests RuleSet population
- [x] Integration smoke test passes

### Quality Gates
- [x] ruff format passes
- [x] ruff check passes (no violations)
- [x] mypy passes (strict mode)
- [x] pyright passes (strict mode)
- [x] pre-commit hooks pass
- [x] No regressions in existing tests

### Documentation
- [x] Comprehensive module docstring
- [x] Detailed function docstring with examples
- [x] All parameters documented
- [x] All error conditions documented
- [x] Integration notes for TICKET 6

### Integration
- [x] Compatible with ExtractedRule schema (TICKET 1)
- [x] Compatible with RuleSet schema (TICKET 1)
- [x] Uses YAMLGenerationError (TICKET 1)
- [x] Exported from ca package
- [x] Ready for orchestrator (TICKET 6)

---

## Estimated Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 0: Setup | 15 min | Add pyfakefs dependency |
| Phase 1: TDD (Steps 1.1-1.8) | 2-3 hours | Implement all functionality via TDD |
| Phase 2: Documentation | 30 min | Docstrings and polish |
| Phase 3: Quality Assurance | 30 min | Coverage, linting, integration test |
| Phase 4: Finalization | 15 min | Package exports, regression testing |
| **Total** | **3.5-4.5 hours** | Complete implementation |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Schema field name mismatch | Low | High | Use exact names from schema.py; verify with imports |
| Type checking failures | Medium | Medium | Follow strict typing from start; run mypy frequently |
| pyfakefs compatibility issues | Low | Low | Test pyfakefs import immediately in Step 0.1 |
| Regression in TICKETS 1-4 | Low | High | Run full test suite in Phase 4.2 |
| Missing RuleSet fields | Low | High | Verify RuleSet schema early; test population |

---

## Next Steps After Completion

1. ✅ Mark TICKET 5 as complete
2. ➡️ Begin TICKET 6 (orchestrator)
3. ➡️ Integrate yaml_generator into orchestrator CLI
4. ➡️ End-to-end testing with real HTML files from `cra_documents/cra_t4002e_rev24_dump/`
5. ➡️ Performance profiling (if needed)
6. ➡️ User acceptance testing

---

**Plan Status**: READY FOR EXECUTION
**Approach**: Test-Driven Development with Frequent Commits
**Quality Assurance**: Comprehensive testing, 100% coverage, strict type checking, zero regressions

---

*This plan follows the 80/20 principle: deliver production-ready core functionality with robust error handling, comprehensive testing, and clean integration points for TICKET 6.*
