# TICKET 6 Implementation Plan: Pipeline Orchestration Script

**Status**: Planning
**Created**: 2025-10-16
**Approach**: Test-Driven Development (TDD) with Atomic Commits
**Consultation**: Zen (gemini-2.5-pro) for architecture review

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Decisions](#architecture-decisions)
3. [Key Findings from PR Review](#key-findings-from-pr-review)
4. [TDD Workflow](#tdd-workflow)
5. [Implementation Steps](#implementation-steps)
6. [Commit Strategy](#commit-strategy)
7. [Quality Gates](#quality-gates)
8. [Testing Strategy](#testing-strategy)

---

## Overview

**Goal**: Create the user-facing CLI that orchestrates the complete HTML-to-YAML extraction pipeline, connecting all modules (parsers, adjudicator, YAML generator) into a single command.

**Scope**:
- CLI using typer framework with rich formatted output
- Process single HTML file OR directory of HTML files
- Layered error handling (pre-flight, per-file, top-level)
- Generate main rules YAML + manual review YAML
- Display statistics summary report
- Support `--dry-run` and `--verbose` flags

**Constraints**:
- All code must go in `src/qe_tax_rag/extraction/ca/` (not `scripts/`)
- Dependencies must be in pyproject.toml `indexing` section
- Zero regressions on existing 79+ unit tests
- Follow 80/20 principle: robust core, avoid over-engineering

---

## Architecture Decisions

### 1. File Structure (Zen-Approved)

**Decision**: Adopt modern Python packaging with src-layout
- **Path**: `src/qe_tax_rag/extraction/ca/orchestrator.py` (business logic)
- **Path**: `src/qe_tax_rag/extraction/ca/cli.py` (typer wrapper)
- **Registration**: `[project.scripts]` in pyproject.toml
  ```toml
  extract-rules = "qe_tax_rag.extraction.ca.cli:app"
  ```

**Rationale**:
- Modern packaging standard (all importable code in src/)
- Clean separation from RAG indexing CLI
- Fully testable (orchestrator is pure logic, no typer coupling)
- Discoverable by developers and testing tools

### 2. Separation of Concerns

**Orchestrator Module** (`orchestrator.py`):
- Pure business logic, NO typer/rich imports
- Signature: `run_extraction(...) -> dict[str, Any]`
- Responsibilities:
  - File discovery (single file vs directory)
  - Pre-flight validation (paths exist, writable)
  - File processing loop with error handling
  - Call parsers → adjudicator → accumulate results
  - Generate YAML files (conditional on dry_run)
  - Return statistics + error details

**CLI Module** (`cli.py`):
- Thin typer wrapper for presentation
- Responsibilities:
  - Define CLI arguments/options
  - Setup logging with RichHandler
  - Call orchestrator
  - Render rich summary report
  - Handle exit codes (0=success, 1=failures)

**Benefits**:
- 95% of logic testable without CLI framework
- Fast unit tests (no process spawning)
- Clear interface boundaries

### 3. Manual Review Output

**Decision**: Orchestrator writes manual_review.yml only if items exist

**Flow**:
1. Adjudicator returns `(resolved_rules, manual_review_items, stats)`
2. Orchestrator accumulates items across all files
3. If `len(manual_review_items) > 0`, write separate YAML file
4. Report presence/count in summary

**Rationale**: Avoids clutter (no empty files), maintains transparency

### 4. Enhanced Features

**--dry-run Flag**:
- Execute full pipeline (parsing, adjudication)
- Skip final YAML generation
- Display summary report
- Use case: Validate input, estimate costs, check for errors

**--verbose Flag**:
- Default: INFO level logging with rich progress bars
- Verbose: DEBUG level logging with detailed traces
- Implementation: `logging.basicConfig(level=...)` + RichHandler

**Rationale**: Low-cost features with high usability value (80/20)

### 5. Error Handling (Layered Approach)

**Layer 1: Pre-flight Checks**
- Validate input_path exists and is readable
- Verify output directories are writable
- Create directories if needed
- Exit with code 1 and clear message on failure

**Layer 2: Per-File Processing**
- Wrap each file in try/except
- On error: log, add to `failed_files` list, continue
- Collect statistics for successful files
- One bad file doesn't crash the batch

**Layer 3: Top-Level Handler**
- Catch catastrophic errors (e.g., output write failure)
- Always produce summary report (even on partial failure)
- Exit code 1 if any files failed, 0 if all succeeded

**Rationale**: Fail fast on setup, fail gracefully during processing

---

## Key Findings from PR Review

### ✅ Already Implemented (TICKETS 1-5)

**Adjudicator (PR #24)**:
- Signature: `adjudicate(classic_rules, llm_rules, source_html_content, source_file) -> tuple[list[ExtractedRule], list[ManualReviewItem], dict[str, int]]`
- Returns manual review items as Pydantic models (NO file I/O side effects)
- Returns stats dict with keys: `perfect_matches`, `auto_corrected`, `manual_review`
- Exported from `src/qe_tax_rag/extraction/ca/__init__.py`

**YAML Generator (PR #25)**:
- Signature: `generate(rules: list[ExtractedRule], output_path: str) -> None`
- Strips internal metadata: `expert_source`, `anchor_id`, `confidence_score`
- Adds schema_version and extraction_timestamp
- Read-back verification for integrity
- Raises `YAMLGenerationError` on failures
- Exported from `src/qe_tax_rag/extraction/ca/__init__.py`

**Parsers (TICKETS 2-3)**:
- Classic: `classic_parser.parse(html_path) -> list[ExtractedRule]`
- LLM: `llm_parser.parse(html_path) -> list[ExtractedRule]`
- Both raise `ParserError` on failures

**Schema (TICKET 1)**:
- `ExtractedRule`: All fields documented, frozen Pydantic model
- `RuleSet`: Container with schema_version, extraction_timestamp, rules
- `ManualReviewItem`: Pydantic model for failed adjudications

**Data**:
- 13 HTML files in `cra_documents/cra_t4002e_rev24_dump/`
- Files: t4002-1.html through t4002-13.html

### ⚠️ Missing Dependency

**Issue**: `rich` is NOT in pyproject.toml but required by TICKET 6 plan
**Solution**: Add `rich>=13.0` to `[project.optional-dependencies.indexing]`

---

## TDD Workflow

### Test-Driven Development Cycle

For each feature, follow the **Red-Green-Refactor** cycle:

1. **RED**: Write a failing test that specifies desired behavior
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Clean up code while keeping tests green
4. **COMMIT**: Atomic commit with clear message

### Testing Pyramid

**Unit Tests** (fast, isolated):
- `test_orchestrator.py`: Mock parsers/adjudicator, test business logic
- Test file discovery, stats accumulation, error handling
- Use `unittest.mock.patch` for external dependencies
- Target: 95%+ coverage of orchestrator logic

**Integration Tests** (slower, I/O):
- `test_cli_integration.py`: Use `typer.testing.CliRunner`
- Test with real HTML fixtures (small subset)
- Verify YAML output structure
- Test error scenarios (missing files, permissions)

**Manual Tests** (exploratory):
- Run against full HTML dump (13 files)
- Verify summary report accuracy
- Test edge cases discovered during development

### Test Organization

```
tests/
├── unit/
│   ├── test_orchestrator.py       # NEW: Orchestrator business logic
│   └── test_adjudicator.py         # Existing: 22 tests (from TICKET 4)
│
└── integration/
    └── test_cli_integration.py     # NEW: CLI end-to-end tests
```

---

## Implementation Steps

### Phase 1: Foundation (Steps 1-3)

#### Step 1: Add Rich Dependency
**Test**: None (configuration change)
**Code**: Update `pyproject.toml`
**Commit**: "build: add rich>=13.0 to indexing dependencies"

**Changes**:
```toml
[project.optional-dependencies]
indexing = [
    "sentence-transformers>=2.2",
    "google-generativeai>=0.8.5",
    "pyyaml>=6.0",
    "pdfplumber>=0.10",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "typer>=0.9",
    "rich>=13.0",  # NEW: For CLI output formatting and progress bars
]
```

**Verification**:
```bash
uv sync --extra indexing
uv run python -c "from rich.console import Console; Console().print('[green]✓ Rich installed')"
```

---

#### Step 2: Create Orchestrator Module (Skeleton)
**Test**: `test_orchestrator.py::test_orchestrator_module_imports`
**Code**: Create empty `orchestrator.py` with signature
**Commit**: "feat(extraction): add orchestrator module skeleton"

**Test Code** (`tests/unit/test_orchestrator.py`):
```python
"""Unit tests for extraction pipeline orchestrator."""
import pytest
from src.qe_tax_rag.extraction.ca.orchestrator import run_extraction


def test_orchestrator_module_imports() -> None:
    """Verify orchestrator module and function can be imported."""
    assert callable(run_extraction)
```

**Implementation** (`src/qe_tax_rag/extraction/ca/orchestrator.py`):
```python
"""
Pipeline orchestrator for HTML-to-YAML extraction.

This module provides the core business logic for the extraction pipeline,
coordinating file discovery, parsing, adjudication, and YAML generation.
Designed to be testable without CLI framework dependencies.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def run_extraction(
    input_path: Path,
    output_yaml: Path,
    manual_review_yaml: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Execute the HTML-to-YAML extraction pipeline.

    Args:
        input_path: Path to HTML file or directory of HTML files
        output_yaml: Path for output YAML file
        manual_review_yaml: Path for manual review YAML file
        dry_run: If True, skip YAML file generation

    Returns:
        Dictionary with keys:
        - total_files: Total HTML files discovered
        - processed_files: Successfully processed files
        - failed_files: List of (filename, error_message) tuples
        - total_rules: Total rules extracted
        - stats: Adjudication statistics
        - manual_review_count: Items requiring manual review

    Raises:
        ValueError: If input_path doesn't exist or no HTML files found
        PermissionError: If output directories aren't writable
    """
    # TODO: Implement
    return {
        "total_files": 0,
        "processed_files": 0,
        "failed_files": [],
        "total_rules": 0,
        "stats": {"perfect_matches": 0, "auto_corrected": 0, "manual_review": 0},
        "manual_review_count": 0,
    }
```

**Run**: `uv run pytest tests/unit/test_orchestrator.py::test_orchestrator_module_imports -v`

---

#### Step 3: Implement File Discovery
**Test**: `test_orchestrator.py::test_file_discovery_*` (4 tests)
**Code**: File discovery logic in orchestrator
**Commit**: "feat(orchestrator): implement file discovery for single file and directory"

**Test Code**:
```python
from pathlib import Path
import pytest
from src.qe_tax_rag.extraction.ca.orchestrator import run_extraction


def test_file_discovery_single_file(tmp_path: Path) -> None:
    """Test file discovery for single HTML file."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Execute
    result = run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["total_files"] == 1


def test_file_discovery_directory(tmp_path: Path) -> None:
    """Test file discovery for directory of HTML files."""
    # Setup
    (tmp_path / "file1.html").write_text("<html></html>")
    (tmp_path / "file2.html").write_text("<html></html>")
    (tmp_path / "readme.txt").write_text("not html")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Execute
    result = run_extraction(tmp_path, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["total_files"] == 2


def test_file_discovery_nonexistent_path(tmp_path: Path) -> None:
    """Test error handling for nonexistent input path."""
    nonexistent = tmp_path / "does_not_exist.html"
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    with pytest.raises(ValueError, match="does not exist"):
        run_extraction(nonexistent, output_yaml, manual_yaml, dry_run=True)


def test_file_discovery_empty_directory(tmp_path: Path) -> None:
    """Test error handling for directory with no HTML files."""
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    with pytest.raises(ValueError, match="No HTML files found"):
        run_extraction(tmp_path, output_yaml, manual_yaml, dry_run=True)
```

**Implementation** (update `orchestrator.py`):
```python
def run_extraction(
    input_path: Path,
    output_yaml: Path,
    manual_review_yaml: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute the HTML-to-YAML extraction pipeline."""
    logger.info(f"Starting extraction pipeline for {input_path}")

    # Step 1: File discovery
    html_files = _discover_html_files(input_path)

    # TODO: Implement processing logic

    return {
        "total_files": len(html_files),
        "processed_files": 0,
        "failed_files": [],
        "total_rules": 0,
        "stats": {"perfect_matches": 0, "auto_corrected": 0, "manual_review": 0},
        "manual_review_count": 0,
    }


def _discover_html_files(input_path: Path) -> list[Path]:
    """
    Discover HTML files from input path.

    Args:
        input_path: Path to single file or directory

    Returns:
        Sorted list of HTML file paths

    Raises:
        ValueError: If path doesn't exist or no HTML files found
    """
    if not input_path.exists():
        raise ValueError(f"Input path does not exist: {input_path}")

    if input_path.is_file():
        if input_path.suffix.lower() != ".html":
            raise ValueError(f"Input file is not an HTML file: {input_path}")
        return [input_path]

    if input_path.is_dir():
        html_files = sorted(input_path.glob("*.html"))
        if not html_files:
            raise ValueError(f"No HTML files found in directory: {input_path}")
        logger.info(f"Discovered {len(html_files)} HTML files")
        return html_files

    raise ValueError(f"Input path is neither file nor directory: {input_path}")
```

**Run**: `uv run pytest tests/unit/test_orchestrator.py -v`

---

### Phase 2: Processing Logic (Steps 4-6)

#### Step 4: Implement Pre-flight Directory Creation
**Test**: `test_orchestrator.py::test_preflight_*` (2 tests)
**Code**: Directory creation logic
**Commit**: "feat(orchestrator): add pre-flight directory creation"

**Test Code**:
```python
def test_preflight_creates_output_directories(tmp_path: Path) -> None:
    """Test that output directories are created if they don't exist."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    output_yaml = tmp_path / "nested" / "output" / "rules.yml"
    manual_yaml = tmp_path / "nested" / "manual.yml"

    # Execute
    run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert output_yaml.parent.exists()
    assert manual_yaml.parent.exists()


def test_preflight_validates_write_permissions(tmp_path: Path) -> None:
    """Test error handling for read-only output directory."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)  # Read-only
    output_yaml = readonly_dir / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Execute & Assert
    with pytest.raises(PermissionError, match="not writable"):
        run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    # Cleanup
    readonly_dir.chmod(0o755)
```

**Implementation**: Add `_preflight_checks()` helper function

---

#### Step 5: Implement File Processing Loop with Mocked Parsers
**Test**: `test_orchestrator.py::test_processing_*` (4 tests)
**Code**: Processing loop with parser/adjudicator calls
**Commit**: "feat(orchestrator): implement file processing loop with parser integration"

**Test Code** (using mocks):
```python
from unittest.mock import patch, MagicMock
from src.qe_tax_rag.extraction.ca.schema import ExtractedRule, ExpertSource, ApplicabilityType


@patch("src.qe_tax_rag.extraction.ca.orchestrator.adjudicate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.llm_parse")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_processing_single_file_success(
    mock_classic: MagicMock,
    mock_llm: MagicMock,
    mock_adjudicate: MagicMock,
    tmp_path: Path,
) -> None:
    """Test successful processing of single HTML file."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><h3>Line 8523 – Test</h3><p>Content</p></html>")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Mock parser outputs
    test_rule = ExtractedRule(
        rule_number=8523,
        title="Test Rule",
        content="Test content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id=None,
        confidence_score=1.0,
    )
    mock_classic.return_value = [test_rule]
    mock_llm.return_value = [test_rule]
    mock_adjudicate.return_value = (
        [test_rule],  # resolved_rules
        [],  # manual_review_items
        {"perfect_matches": 1, "auto_corrected": 0, "manual_review": 0},
    )

    # Execute
    result = run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["total_files"] == 1
    assert result["processed_files"] == 1
    assert result["failed_files"] == []
    assert result["total_rules"] == 1
    assert result["stats"]["perfect_matches"] == 1

    # Verify calls
    mock_classic.assert_called_once_with(str(html_file))
    mock_llm.assert_called_once_with(str(html_file))
    mock_adjudicate.assert_called_once()


@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_processing_handles_parser_error(
    mock_classic: MagicMock,
    tmp_path: Path,
) -> None:
    """Test graceful handling of parser errors."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html>malformed</html>")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Mock parser error
    from src.qe_tax_rag.extraction.ca.exceptions import ParserError
    mock_classic.side_effect = ParserError("Parse failed")

    # Execute
    result = run_extraction(html_file, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["total_files"] == 1
    assert result["processed_files"] == 0
    assert len(result["failed_files"]) == 1
    assert "test.html" in result["failed_files"][0][0]
    assert "Parse failed" in result["failed_files"][0][1]
```

**Implementation**: Add processing loop with try/except blocks

---

#### Step 6: Implement Statistics Accumulation
**Test**: `test_orchestrator.py::test_stats_accumulation` (1 test)
**Code**: Stats accumulation across multiple files
**Commit**: "feat(orchestrator): implement statistics accumulation across files"

**Test Code**:
```python
@patch("src.qe_tax_rag.extraction.ca.orchestrator.adjudicate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.llm_parse")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_stats_accumulation_multiple_files(
    mock_classic: MagicMock,
    mock_llm: MagicMock,
    mock_adjudicate: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that statistics are correctly accumulated across multiple files."""
    # Setup
    (tmp_path / "file1.html").write_text("<html></html>")
    (tmp_path / "file2.html").write_text("<html></html>")
    output_yaml = tmp_path / "output.yml"
    manual_yaml = tmp_path / "manual.yml"

    # Mock returns
    mock_classic.return_value = []
    mock_llm.return_value = []

    # File 1: 2 perfect matches, 1 auto-corrected
    # File 2: 1 perfect match, 1 manual review
    mock_adjudicate.side_effect = [
        ([], [], {"perfect_matches": 2, "auto_corrected": 1, "manual_review": 0}),
        ([], [], {"perfect_matches": 1, "auto_corrected": 0, "manual_review": 1}),
    ]

    # Execute
    result = run_extraction(tmp_path, output_yaml, manual_yaml, dry_run=True)

    # Assert
    assert result["stats"]["perfect_matches"] == 3
    assert result["stats"]["auto_corrected"] == 1
    assert result["stats"]["manual_review"] == 1
```

**Implementation**: Accumulate stats dict in processing loop

---

### Phase 3: YAML Generation (Steps 7-8)

#### Step 7: Implement YAML Generation (Non-Dry-Run)
**Test**: `test_orchestrator.py::test_yaml_generation_*` (3 tests)
**Code**: Call `generate()` for main YAML and manual review
**Commit**: "feat(orchestrator): integrate YAML generation with conditional manual review"

**Test Code**:
```python
@patch("src.qe_tax_rag.extraction.ca.orchestrator.generate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.adjudicate")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.llm_parse")
@patch("src.qe_tax_rag.extraction.ca.orchestrator.classic_parse")
def test_yaml_generation_dry_run_skips_files(
    mock_classic: MagicMock,
    mock_llm: MagicMock,
    mock_adjudicate: MagicMock,
    mock_generate: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that dry_run=True skips YAML file generation."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    mock_classic.return_value = []
    mock_llm.return_value = []
    mock_adjudicate.return_value = ([], [], {"perfect_matches": 0, "auto_corrected": 0, "manual_review": 0})

    # Execute
    run_extraction(html_file, tmp_path / "out.yml", tmp_path / "manual.yml", dry_run=True)

    # Assert
    mock_generate.assert_not_called()


@patch("src.qe_tax_rag.extraction.ca.orchestrator.generate")
def test_yaml_generation_creates_files(mock_generate: MagicMock, tmp_path: Path) -> None:
    """Test that YAML files are generated when dry_run=False."""
    # ... (similar to above but dry_run=False)
    # Assert mock_generate called twice (main + manual review)


def test_yaml_generation_skips_empty_manual_review(tmp_path: Path) -> None:
    """Test that manual review YAML is not created when no items exist."""
    # ... test that only one generate() call happens when manual_review_items is empty
```

**Implementation**: Add YAML generation logic with conditional manual review

---

#### Step 8: Implement Orchestrator Error Handling
**Test**: `test_orchestrator.py::test_error_handling_*` (2 tests)
**Code**: Top-level error handling for YAML generation failures
**Commit**: "feat(orchestrator): add robust error handling for YAML generation"

**Test Code**:
```python
@patch("src.qe_tax_rag.extraction.ca.orchestrator.generate")
def test_error_handling_yaml_generation_failure(
    mock_generate: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that YAMLGenerationError is propagated to caller."""
    from src.qe_tax_rag.extraction.ca.exceptions import YAMLGenerationError

    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")

    # Mock YAML generation failure
    mock_generate.side_effect = YAMLGenerationError("Disk full")

    # Execute & Assert
    with pytest.raises(YAMLGenerationError, match="Disk full"):
        run_extraction(html_file, tmp_path / "out.yml", tmp_path / "manual.yml", dry_run=False)
```

---

### Phase 4: CLI Implementation (Steps 9-11)

#### Step 9: Create CLI Module Skeleton
**Test**: `test_cli_integration.py::test_cli_imports`
**Code**: Create `cli.py` with typer app skeleton
**Commit**: "feat(extraction): add CLI module skeleton with typer app"

**Test Code** (`tests/integration/test_cli_integration.py`):
```python
"""Integration tests for extraction pipeline CLI."""
import pytest
from typer.testing import CliRunner
from src.qe_tax_rag.extraction.ca.cli import app


runner = CliRunner()


def test_cli_imports() -> None:
    """Verify CLI module and app can be imported."""
    from src.qe_tax_rag.extraction.ca.cli import app
    assert app is not None


def test_cli_help_command() -> None:
    """Test that --help displays usage information."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "HTML-to-YAML" in result.stdout
    assert "input-path" in result.stdout.lower()
```

**Implementation** (`src/qe_tax_rag/extraction/ca/cli.py`):
```python
"""
CLI for HTML-to-YAML extraction pipeline.

Provides a user-friendly command-line interface for extracting CRA tax rules
from HTML documents using the Mixture-of-Experts pipeline.
"""

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler

from src.qe_tax_rag.extraction.ca.orchestrator import run_extraction

app = typer.Typer(
    name="extract-rules",
    help="HTML-to-YAML rule extraction pipeline for CRA T4002 documents.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def main(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Path to HTML file or directory of HTML files",
            exists=True,
        ),
    ],
    output_yaml: Annotated[
        Path,
        typer.Argument(
            help="Path for output YAML file with extracted rules",
        ),
    ],
    manual_review_file: Annotated[
        Path,
        typer.Option(
            "--manual-review-file",
            "-m",
            help="Path for YAML file with items requiring manual review",
        ),
    ] = Path("manual_review.yml"),
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Run pipeline without generating output files"),
    ] = False,
) -> None:
    """
    Extract tax rules from CRA HTML documents to structured YAML.

    Uses a Mixture-of-Experts approach:
    1. Classic HTML parser (rule-based, fast)
    2. LLM parser (semantic, resilient to changes)
    3. Grounded adjudicator (resolves conflicts with evidence)

    Examples:
        # Process single file
        $ extract-rules cra_documents/t4002-5.html output/rules.yml

        # Process entire directory
        $ extract-rules cra_documents/cra_t4002e_rev24_dump/ output/rules.yml

        # Dry run (validate without writing files)
        $ extract-rules cra_documents/ output.yml --dry-run

        # Verbose logging for debugging
        $ extract-rules cra_documents/ output.yml --verbose
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    # TODO: Call orchestrator and render summary
    console.print("[yellow]CLI implementation in progress...[/yellow]")
```

**Run**: `uv run pytest tests/integration/test_cli_integration.py -v`

---

#### Step 10: Implement CLI Orchestrator Integration
**Test**: `test_cli_integration.py::test_cli_execution_*` (3 tests)
**Code**: Call orchestrator and handle results
**Commit**: "feat(cli): integrate orchestrator execution and error handling"

**Test Code**:
```python
from pathlib import Path


def test_cli_execution_single_file_dry_run(tmp_path: Path) -> None:
    """Test CLI execution with single file and dry run."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><h3>Line 8523 – Test</h3></html>")
    output_yaml = tmp_path / "output.yml"

    # Execute
    result = runner.invoke(app, [
        str(html_file),
        str(output_yaml),
        "--dry-run",
    ])

    # Assert
    assert result.exit_code == 0
    assert not output_yaml.exists()  # Dry run doesn't create files


def test_cli_execution_missing_input_file(tmp_path: Path) -> None:
    """Test CLI error handling for missing input file."""
    nonexistent = tmp_path / "missing.html"
    output_yaml = tmp_path / "output.yml"

    result = runner.invoke(app, [str(nonexistent), str(output_yaml)])

    assert result.exit_code != 0
    assert "does not exist" in result.stdout.lower() or "error" in result.stdout.lower()
```

**Implementation**: Call `run_extraction()` and handle exceptions

---

#### Step 11: Implement Summary Report
**Test**: `test_cli_integration.py::test_cli_summary_report` (1 test)
**Code**: Rich-formatted summary report
**Commit**: "feat(cli): add rich-formatted summary report"

**Test Code**:
```python
def test_cli_summary_report_displays_stats(tmp_path: Path, monkeypatch) -> None:
    """Test that summary report displays statistics correctly."""
    # Setup
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    output_yaml = tmp_path / "output.yml"

    # Mock orchestrator to return controlled stats
    def mock_run_extraction(*args, **kwargs):
        return {
            "total_files": 5,
            "processed_files": 4,
            "failed_files": [("file5.html", "Parse error")],
            "total_rules": 247,
            "stats": {"perfect_matches": 210, "auto_corrected": 31, "manual_review": 6},
            "manual_review_count": 6,
        }

    monkeypatch.setattr(
        "src.qe_tax_rag.extraction.ca.cli.run_extraction",
        mock_run_extraction,
    )

    # Execute
    result = runner.invoke(app, [str(html_file), str(output_yaml), "--dry-run"])

    # Assert
    assert result.exit_code == 0
    assert "Files Processed:" in result.stdout
    assert "247" in result.stdout  # Total rules
    assert "210" in result.stdout  # Perfect matches
    assert "31" in result.stdout   # Auto-corrected
```

**Implementation** (in `cli.py`):
```python
from rich.table import Table

def _render_summary_report(result: dict[str, Any]) -> None:
    """Render rich-formatted summary report."""
    console.print("\n")
    console.rule("[bold]CRA Rule Extraction Complete[/bold]")
    console.print()

    # Files processed
    console.print(
        f"Files Processed: [green]{result['processed_files']}[/green] / {result['total_files']}"
    )
    console.print(f"Total Rules Extracted: [cyan]{result['total_rules']}[/cyan]")
    console.print()

    # Adjudication breakdown
    stats = result["stats"]
    total = sum(stats.values())
    console.print("[bold]Adjudication Breakdown:[/bold]")
    console.print(
        f"  ✓ Perfect Matches:    {stats['perfect_matches']:>3} "
        f"({stats['perfect_matches']/total*100:.0f}%)"
    )
    console.print(
        f"  ⚡ Auto-corrected:     {stats['auto_corrected']:>3} "
        f"({stats['auto_corrected']/total*100:.0f}%)"
    )
    console.print(
        f"  ⚠️  Manual Review:      {stats['manual_review']:>3} "
        f"({stats['manual_review']/total*100:.0f}%)"
    )
    console.print()

    # Errors
    if result["failed_files"]:
        console.print(f"[red]Errors: {len(result['failed_files'])} files failed[/red]")
        for filename, error in result["failed_files"]:
            console.print(f"  - {filename}: {error}")
    else:
        console.print("[green]Errors: 0 files failed[/green]")
```

---

### Phase 5: Integration & Polish (Steps 12-14)

#### Step 12: Register Console Script
**Test**: Manual verification
**Code**: Update `pyproject.toml`
**Commit**: "build: register extract-rules console script"

**Changes** (`pyproject.toml`):
```toml
[project.scripts]
extract-rules = "qe_tax_rag.extraction.ca.cli:app"
```

**Verification**:
```bash
uv sync --extra indexing
uv run extract-rules --help
```

---

#### Step 13: Export CLI from Package
**Test**: Import test
**Code**: Update `__init__.py`
**Commit**: "feat(extraction): export CLI app from package"

**Changes** (`src/qe_tax_rag/extraction/ca/__init__.py`):
```python
"""
Canadian tax document extraction pipeline.

This package provides HTML-to-YAML extraction for CRA tax documents using
a Mixture-of-Experts approach with grounded adjudication.
"""

from src.qe_tax_rag.extraction.ca.adjudicator import adjudicate
from src.qe_tax_rag.extraction.ca.cli import app as cli_app
from src.qe_tax_rag.extraction.ca.yaml_generator import generate

__all__ = [
    "adjudicate",
    "generate",
    "cli_app",
]
```

---

#### Step 14: Add Ruff Configuration
**Test**: `uvx ruff check` passes
**Code**: Update `pyproject.toml`
**Commit**: "build: add ruff ignores for CLI and orchestrator complexity"

**Changes** (`pyproject.toml`):
```toml
[tool.ruff.lint.per-file-ignores]
# ... existing ignores ...
"src/qe_tax_rag/extraction/ca/cli.py" = ["PLR0913", "T201"]  # CLI naturally has many options; uses rich for output
"src/qe_tax_rag/extraction/ca/orchestrator.py" = ["PLR0915", "C901"]  # Orchestrator complexity is inherent
```

---

### Phase 6: End-to-End Testing (Steps 15-16)

#### Step 15: Integration Test with Real HTML
**Test**: Manual execution
**Code**: None (testing only)
**Commit**: N/A

**Commands**:
```bash
# Test single file
uv run extract-rules \
  cra_documents/cra_t4002e_rev24_dump/t4002-5.html \
  output/test_single.yml \
  --dry-run \
  --verbose

# Test full directory
uv run extract-rules \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/cra_rules.yml \
  --manual-review-file output/manual_review.yml \
  --dry-run

# Actual run (generates files)
uv run extract-rules \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/cra_rules.yml \
  --verbose
```

**Validation**:
- Summary report displays correct counts
- YAML files are created with correct structure
- Manual review file only created if items exist
- All parsers/adjudicator are called correctly

---

#### Step 16: Regression Testing
**Test**: All existing tests pass
**Code**: None (verification only)
**Commit**: N/A

**Commands**:
```bash
# Run all unit tests (should be 90+ tests now)
uv run pytest tests/unit/ -v -m unit

# Run all tests including integration
uv run pytest tests/ -v

# Quality checks
uvx ruff check src/qe_tax_rag/extraction/ca/
uv run pre-commit run --all-files
```

**Expected**: Zero regressions, all checks pass

---

## Commit Strategy

### Atomic Commit Principles

Each commit should:
1. **Focus on one logical change** (single feature, fix, or refactor)
2. **Pass all quality gates** (tests, linting, type checking)
3. **Be reversible** (can be cherry-picked or reverted independently)
4. **Include clear context** (why the change was made, not just what)

### Commit Message Format

Follow conventional commits with detailed body:

```
<type>: <short summary (50 chars max)>

<detailed description of WHY this change was made>
- Use bullet points for multiple aspects
- Explain context and motivation
- Reference ticket numbers or design decisions

Technical details:
- Implementation approach if non-obvious
- Trade-offs considered
- Future considerations

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `test`: Adding or updating tests
- `build`: Build system or dependency changes
- `docs`: Documentation only

### Commit Frequency

**Target**: 15-20 commits for TICKET 6

**Checkpoints**:
- After each test suite passes (Steps 1-11)
- After each integration milestone (Steps 12-14)
- After fixing any regressions discovered during testing

### Example Commit Messages

**Good**:
```
feat(orchestrator): implement file processing loop with parser integration

Add core processing logic that iterates over discovered HTML files and
calls classic parser, LLM parser, and adjudicator for each file.
Includes per-file error handling to ensure one bad file doesn't crash
the entire batch.

Technical approach:
- Use try/except blocks around each file's processing
- Accumulate results and errors in separate lists
- Continue processing on individual file failures
- Log errors with full context for debugging

Enables: End-to-end extraction pipeline execution
Follows: 80/20 principle (robust core, graceful degradation)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Bad**:
```
feat: add orchestrator

Added orchestrator module with file processing.
```

---

## Quality Gates

### Per-Commit Gates

**Before each commit**:
```bash
# 1. Run affected tests
uv run pytest tests/unit/test_orchestrator.py -v

# 2. Check formatting
uvx ruff format src/qe_tax_rag/extraction/ca/

# 3. Check linting
uvx ruff check src/qe_tax_rag/extraction/ca/

# 4. Type check (if applicable)
uv run mypy src/qe_tax_rag/extraction/ca/orchestrator.py

# 5. Run pre-commit hooks (final check)
uv run pre-commit run --files src/qe_tax_rag/extraction/ca/*
```

### Phase Gates

**After Phase 2** (Orchestrator complete):
- All orchestrator unit tests pass
- No regressions in existing tests
- Type checking passes
- Linting clean

**After Phase 4** (CLI complete):
- All integration tests pass
- Manual smoke test successful
- Help text displays correctly
- Error messages are clear

**Final Gate** (before merge):
- All tests pass (unit + integration)
- Coverage > 90% for new code
- All pre-commit hooks pass
- Documentation complete
- Manual end-to-end test successful

---

## Testing Strategy

### Test Coverage Targets

**Orchestrator** (`test_orchestrator.py`):
- Target: 95%+ coverage
- Test count: ~20 tests
- Categories:
  - File discovery: 4 tests
  - Pre-flight checks: 2 tests
  - Processing logic: 6 tests
  - Stats accumulation: 2 tests
  - YAML generation: 3 tests
  - Error handling: 3 tests

**CLI** (`test_cli_integration.py`):
- Target: 85%+ coverage (harder to test CLI presentation)
- Test count: ~8 tests
- Categories:
  - Basic invocation: 2 tests
  - Argument validation: 2 tests
  - Execution flow: 2 tests
  - Summary report: 2 tests

### Mocking Strategy

**What to mock**:
- Parsers (classic_parse, llm_parse)
- Adjudicator (adjudicate)
- YAML generator (generate)
- File I/O (when testing error conditions)

**What NOT to mock**:
- Path operations (use tmp_path fixture)
- Logging (verify logs with caplog)
- Statistics accumulation (test actual logic)

### Fixture Organization

**Shared fixtures** (`tests/conftest.py`):
```python
@pytest.fixture
def sample_extracted_rule() -> ExtractedRule:
    """Reusable ExtractedRule for tests."""
    return ExtractedRule(
        rule_number=8523,
        title="Test Rule",
        content="Test content",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3",
        section=None,
        source_file="test.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id=None,
        confidence_score=1.0,
    )
```

---

## Success Criteria

### Functional Requirements

- [ ] CLI accepts single file or directory input
- [ ] Processes all HTML files in directory
- [ ] Calls parsers and adjudicator correctly
- [ ] Generates main YAML with rules
- [ ] Generates manual review YAML (conditional)
- [ ] Displays summary report with statistics
- [ ] Supports `--dry-run` flag
- [ ] Supports `--verbose` flag
- [ ] Exits with code 0 on success, 1 on failures

### Quality Requirements

- [ ] All unit tests pass (90+ tests total)
- [ ] All integration tests pass
- [ ] Code coverage > 90% for new code
- [ ] Ruff linting passes
- [ ] Pyright type checking passes
- [ ] Pre-commit hooks pass
- [ ] Zero regressions on existing tests

### Documentation Requirements

- [ ] Orchestrator module has comprehensive docstrings
- [ ] CLI command has detailed help text
- [ ] README updated with usage examples
- [ ] This implementation plan completed

### User Experience Requirements

- [ ] Clear error messages for common failures
- [ ] Progress indication for long operations
- [ ] Summary report is readable and informative
- [ ] Dry run shows what would happen without side effects

---

## Risk Mitigation

### Risk: API Rate Limits During Testing

**Mitigation**:
- Use mocks for all unit tests (no real API calls)
- Keep integration tests to small fixture subset
- Add `--dry-run` for validation without API costs

### Risk: Large HTML Files Exceed Token Limits

**Mitigation**:
- Already handled by adjudicator's `_truncate_html_for_prompt()`
- Test with real HTML files (t4002-*.html are ~20-30KB each)
- Monitor truncation warnings in logs

### Risk: Incomplete Error Handling

**Mitigation**:
- Test all error paths with dedicated test cases
- Use layered error handling (pre-flight, per-file, top-level)
- Log all errors with full context

### Risk: Breaking Existing Code

**Mitigation**:
- Run full test suite after each commit
- No changes to existing modules (adjudicator, parsers, generator)
- Only additions to package __init__.py

---

## Next Steps After TICKET 6

### Immediate Follow-ups

1. **Documentation**: Update README with extraction pipeline usage
2. **CI/CD**: Add extraction pipeline tests to GitHub Actions
3. **Performance**: Profile extraction on full HTML dump
4. **Monitoring**: Add metrics collection for adjudication success rates

### Future Enhancements

1. **Parallel Processing**: Use multiprocessing for large batches
2. **Resume Support**: Checkpoint progress for interrupted runs
3. **Validation Mode**: Verify extracted rules against known ground truth
4. **Web UI**: Simple web interface for non-technical users

---

## References

- **TICKET 1**: Foundation (Schema, Settings, Exceptions)
- **TICKET 2**: Classic Parser (PR #22)
- **TICKET 3**: LLM Parser (PR #23)
- **TICKET 4**: Adjudicator (PR #24) - Returns tuple, no file I/O
- **TICKET 5**: YAML Generator (PR #25) - Strips metadata, verification
- **CLAUDE.md**: Project conventions and standards
- **Zen Consultation**: Architecture review (gemini-2.5-pro)

---

**End of Implementation Plan**
