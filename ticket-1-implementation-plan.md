# TICKET 1 Implementation Plan: Foundational Setup & Data Schema

## Overview

This ticket establishes the foundation for the HTML-to-YAML extraction pipeline with:
- Package structure (`src/qe_tax_rag/extraction/ca/`)
- Data schemas (Pydantic models)
- Configuration management (pydantic-settings)
- Exception hierarchy
- **Approach**: Test-Driven Development (TDD) with frequent, atomic commits

## Architecture

**Code Location**: `src/qe_tax_rag/extraction/ca/` (runtime library, distributed via PyPI)
- Makes HTML-to-YAML extraction a first-class library feature
- `ca/` subdirectory = Canada-specific extraction (extensible for other jurisdictions)
- Users can programmatically import: `from qe_tax_rag.extraction.ca import ...`

**Test Location**: `tests/unit/extraction/ca/`

**Dependencies**: All in `[project.optional-dependencies.indexing]` section ✅

## Implementation Strategy

### TDD Workflow
1. **Write test first** - Define expected behavior
2. **Run test (should fail)** - Verify test detects missing functionality
3. **Implement minimal code** - Make test pass
4. **Commit** - Small, atomic commit with passing tests
5. **Refactor if needed** - Improve code while keeping tests green
6. **Commit** - Another small commit if refactoring was done

### Commit Strategy
- **One logical change per commit**
- **All commits must pass pre-commit hooks** (ruff, mypy, pyright)
- **Conventional commit messages** with detailed body
- **Commit after each passing test suite**

---

## Step-by-Step Implementation

### Phase 1: Package Structure & Dependencies

#### Step 1.1: Update pyproject.toml
**Action**: Move google-generativeai to indexing deps, add pyyaml

**Changes**:
- Remove `google-generativeai>=0.8.5` from main `dependencies`
- Add `google-generativeai>=0.8.5` to `[project.optional-dependencies.indexing]`
- Add `pyyaml>=6.0` to `[project.optional-dependencies.indexing]`

**Rationale**: Runtime library (src/qe_tax_rag/) doesn't use google-generativeai; only extraction pipeline needs it

**Verification**:
```bash
uv sync --extra indexing
```

**Commit**:
```
build: move google-generativeai to indexing deps, add pyyaml

Move google-generativeai from main dependencies to indexing optional
dependencies since it's only used by the HTML-to-YAML extraction
pipeline, not the runtime search library. Add pyyaml for YAML
serialization in extraction pipeline.

- Remove google-generativeai>=0.8.5 from main dependencies
- Add google-generativeai>=0.8.5 to indexing dependencies
- Add pyyaml>=6.0 to indexing dependencies

Rationale:
- Runtime library (src/qe_tax_rag/) doesn't use google-generativeai
- Extraction pipeline (src/qe_tax_rag/extraction/) needs it for LLM parsing
- Keeps PyPI package minimal (architecture principle)
- pyyaml required for TICKET 5 (YAML generation)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 1.2: Create extraction package structure
**Action**: Initialize Canada extraction package

**Changes**:
- Create `src/qe_tax_rag/extraction/` directory
- Create `src/qe_tax_rag/extraction/__init__.py` (empty)
- Create `src/qe_tax_rag/extraction/ca/` directory
- Create `src/qe_tax_rag/extraction/ca/__init__.py` (empty)

**Verification**:
```bash
ls -la src/qe_tax_rag/extraction/ca/
uv run python -c "from qe_tax_rag.extraction import ca; print('Import successful')"
```

**Commit**:
```
feat: create Canada extraction package structure

Initialize src/qe_tax_rag/extraction/ca/ package to house HTML-to-YAML
extraction pipeline for Canadian tax documents (schemas, parsers,
adjudicator, YAML generator).

- Create src/qe_tax_rag/extraction/ parent package
- Create src/qe_tax_rag/extraction/ca/ for Canada-specific extraction
- Add __init__.py files for package initialization

Rationale:
- Part of runtime library (distributed via PyPI)
- ca/ subdirectory allows future extension to other jurisdictions
- Clean namespace: qe_tax_rag.extraction.ca.*
- Supports TICKET 1-6 implementation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Phase 2: Exception Hierarchy (TDD)

#### Step 2.1: Write tests for exceptions
**File**: `tests/unit/extraction/ca/test_exceptions.py`

**Test cases**:
1. `test_pipeline_error_is_base_exception` - Verify PipelineError inherits from Exception
2. `test_parser_error_inherits_from_pipeline_error` - Verify inheritance chain
3. `test_adjudication_error_inherits_from_pipeline_error` - Verify inheritance chain
4. `test_yaml_generation_error_inherits_from_pipeline_error` - Verify inheritance chain
5. `test_exceptions_can_be_raised_with_message` - Verify exception messages work

**Run tests (should fail)**:
```bash
uv run pytest tests/unit/extraction/ca/test_exceptions.py -v
```

**Commit**:
```
test: add tests for extraction exception hierarchy

Add comprehensive tests for custom exception classes
that will form the error handling foundation for the
HTML-to-YAML extraction pipeline.

Tests verify:
- PipelineError is base exception
- ParserError, AdjudicationError, YAMLGenerationError inherit correctly
- Exception messages are preserved

Related to: TICKET 1

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 2.2: Implement exceptions
**File**: `src/qe_tax_rag/extraction/ca/exceptions.py`

**Implementation**:
```python
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
```

**Run tests (should pass)**:
```bash
uv run pytest tests/unit/extraction/ca/test_exceptions.py -v
```

**Commit**:
```
feat: implement extraction exception hierarchy

Add custom exception classes for HTML-to-YAML pipeline error handling:
- PipelineError: Base exception for all pipeline errors
- ParserError: Expert parser failures (classic/LLM)
- AdjudicationError: Grounded adjudication failures
- YAMLGenerationError: YAML generation/verification failures

All tests passing.

Rationale:
- Common base class enables catch-all error handling in orchestrator
- Specific subclasses allow granular error handling in components
- Supports robust error reporting in TICKET 6

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Phase 3: Settings Management (TDD)

#### Step 3.1: Write tests for settings
**File**: `tests/unit/extraction/ca/test_settings.py`

**Test cases**:
1. `test_settings_requires_gemini_api_key` - Verify ValidationError when key missing
2. `test_settings_loads_from_environment` - Verify env var loading with QE_TAX_RAG_EXTRACTION_ prefix
3. `test_settings_has_default_model_names` - Verify default Flash/Pro models
4. `test_settings_can_override_model_names` - Verify custom model names from env
5. `test_settings_singleton_pattern` - Verify singleton instance works

**Setup**:
- Use `monkeypatch` fixture to set environment variables
- Test with/without API key

**Run tests (should fail)**:
```bash
uv run pytest tests/unit/extraction/ca/test_settings.py -v
```

**Commit**:
```
test: add tests for extraction settings management

Add comprehensive tests for pydantic-settings configuration
that will manage API keys and model selection for Gemini
parsers and adjudicator.

Tests verify:
- Required field validation (gemini_api_key)
- Environment variable loading (QE_TAX_RAG_EXTRACTION_ prefix)
- Default model names (Flash for parsing, Pro for adjudication)
- Model name overrides via env vars
- Singleton instance pattern

Related to: TICKET 1

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 3.2: Implement settings
**File**: `src/qe_tax_rag/extraction/ca/settings.py`

**Implementation**:
```python
"""Configuration settings for the Canadian HTML-to-YAML extraction pipeline."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the data extraction pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QE_TAX_RAG_EXTRACTION_",
    )

    # Gemini API Configuration
    gemini_api_key: str  # Required field - no default
    llm_model_name: str = "gemini-1.5-flash-latest"
    adjudicator_model_name: str = "gemini-1.5-pro-latest"


# Singleton instance
settings = Settings()
```

**Run tests (should pass)**:
```bash
uv run pytest tests/unit/extraction/ca/test_settings.py -v
```

**Commit**:
```
feat: implement extraction settings with pydantic-settings

Add configuration management for HTML-to-YAML pipeline:
- Required gemini_api_key (fail-fast, no placeholder default)
- Default models: Flash for parsing, Pro for adjudication
- Environment variable support with QE_TAX_RAG_EXTRACTION_ prefix
- .env file support for local development

All tests passing.

Rationale:
- Required API key prevents runtime failures with invalid credentials
- QE_TAX_RAG_EXTRACTION_ prefix aligns with library namespace
- Consistent with existing QE_TAX_RAG_ prefix pattern
- Singleton pattern simplifies access across pipeline modules

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Phase 4: Data Schema (TDD)

#### Step 4.1: Write tests for enums
**File**: `tests/unit/extraction/ca/test_schema.py`

**Test cases for enums**:
1. `test_expert_source_enum_values` - Verify CLASSIC, LLM, ADJUDICATED values
2. `test_applicability_type_enum_values` - Verify BUSINESS, FARMING, FISHING values
3. `test_enums_are_string_enums` - Verify str subclass behavior

**Run tests (should fail)**:
```bash
uv run pytest tests/unit/extraction/ca/test_schema.py::test_expert_source_enum_values -v
```

**Commit**:
```
test: add tests for extraction schema enums

Add tests for ExpertSource and ApplicabilityType enums
that will track rule provenance and income type applicability
in the extraction pipeline.

Tests verify:
- ExpertSource has CLASSIC, LLM, ADJUDICATED values
- ApplicabilityType has BUSINESS, FARMING, FISHING values
- Both enums inherit from str for JSON serialization

Related to: TICKET 1

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 4.2: Implement enums
**File**: `src/qe_tax_rag/extraction/ca/schema.py` (partial)

**Implementation**:
```python
"""Pydantic models for HTML-to-YAML extraction pipeline."""

from enum import Enum


class ExpertSource(str, Enum):
    """Identifies the source of an extracted rule."""

    CLASSIC = "classic"
    LLM = "llm"
    ADJUDICATED = "adjudicated"


class ApplicabilityType(str, Enum):
    """Indicates which type of income/business this rule applies to."""

    BUSINESS = "business"
    FARMING = "farming"
    FISHING = "fishing"
```

**Run tests (should pass)**:
```bash
uv run pytest tests/unit/extraction/ca/test_schema.py -k enum -v
```

**Commit**:
```
feat: implement extraction schema enums

Add ExpertSource and ApplicabilityType enums for data schema:
- ExpertSource: Tracks rule provenance (classic/llm/adjudicated)
- ApplicabilityType: Income type applicability (business/farming/fishing)

Both inherit from str for JSON/YAML serialization compatibility.

Enum tests passing.

Rationale:
- ExpertSource enables adjudicator to track which expert generated each rule
- ApplicabilityType maps to CRA form icons (business/farm/fish)
- str inheritance ensures clean serialization to YAML output

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 4.3: Write tests for ExtractedRule model
**File**: `tests/unit/extraction/ca/test_schema.py` (add to existing)

**Test cases for ExtractedRule**:
1. `test_extracted_rule_with_all_fields` - Valid rule with all fields
2. `test_extracted_rule_is_frozen` - Verify immutability
3. `test_extracted_rule_forbids_extra_fields` - Verify extra="forbid"
4. `test_extracted_rule_requires_core_fields` - Verify ValidationError when missing required fields
5. `test_extracted_rule_allows_none_for_optional_fields` - Verify section, source_expert, anchor_id can be None
6. `test_extracted_rule_validates_applies_to_list` - Verify list[ApplicabilityType] validation

**Run tests (should fail)**:
```bash
uv run pytest tests/unit/extraction/ca/test_schema.py::test_extracted_rule_with_all_fields -v
```

**Commit**:
```
test: add tests for ExtractedRule model

Add comprehensive tests for ExtractedRule Pydantic model
that represents a single line-item expense rule extracted
from CRA HTML documents.

Tests verify:
- All fields (core + context + internal metadata)
- Immutability (frozen=True)
- Strict validation (extra="forbid")
- Required vs optional fields
- Type validation for list[ApplicabilityType]

Related to: TICKET 1

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 4.4: Implement ExtractedRule model
**File**: `src/qe_tax_rag/extraction/ca/schema.py` (add to existing)

**Implementation**:
```python
from pydantic import BaseModel, ConfigDict


class ExtractedRule(BaseModel):
    """
    Represents a single line-item expense rule from CRA forms T2125/T2042/T2121.

    Only extracts h3 headings with 'Line XXXX –' pattern.
    Includes core data fields for the final output and optional metadata
    for internal pipeline processing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Core fields for the final YAML output
    rule_number: int  # e.g., 8523 from "Line 8523"
    title: str  # e.g., "Meals and entertainment"
    content: str  # Full text description
    applies_to: list[ApplicabilityType]  # ["business", "fishing"] from icons
    source_citation: str  # e.g., "Line 8523"

    # Context fields for navigation and filtering
    chapter: str  # e.g., "Chapter 3 – Expenses"
    section: str | None = None  # e.g., "Part 4 – Net income (loss)..."
    source_file: str  # e.g., "t4002-5.html"

    # Internal pipeline metadata (stripped out during final YAML generation)
    source_expert: ExpertSource | None = None  # Tracks which expert generated this
    anchor_id: str | None = None  # e.g., "tocch3ln8523" for debugging
```

**Run tests (should pass)**:
```bash
uv run pytest tests/unit/extraction/ca/test_schema.py -k ExtractedRule -v
```

**Commit**:
```
feat: implement ExtractedRule Pydantic model

Add ExtractedRule model representing a single line-item expense rule:
- Core fields: rule_number, title, content, applies_to, source_citation
- Context fields: chapter, section, source_file
- Internal metadata: source_expert, anchor_id

Model configuration:
- frozen=True for immutability
- extra="forbid" for strict validation
- Modern Python 3.12+ type hints (str | None, list[T])

All ExtractedRule tests passing.

Rationale:
- Core fields provide user-facing tax rule data
- Context fields enable RAG navigation and filtering
- Internal metadata supports adjudication (TICKET 4) and debugging
- Frozen/forbid aligns with CLAUDE.md standards for API contracts

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 4.5: Write tests for RuleSet model
**File**: `tests/unit/extraction/ca/test_schema.py` (add to existing)

**Test cases for RuleSet**:
1. `test_ruleset_with_multiple_rules` - Valid RuleSet with list of rules
2. `test_ruleset_with_empty_list` - Valid RuleSet with empty rules list
3. `test_ruleset_is_frozen` - Verify immutability
4. `test_ruleset_forbids_extra_fields` - Verify extra="forbid"
5. `test_ruleset_validates_rules_list_type` - Verify list[ExtractedRule] validation

**Run tests (should fail)**:
```bash
uv run pytest tests/unit/extraction/ca/test_schema.py::test_ruleset_with_multiple_rules -v
```

**Commit**:
```
test: add tests for RuleSet model

Add tests for RuleSet wrapper model that represents
the final, validated collection of extracted rules.

Tests verify:
- Rules list with multiple ExtractedRule objects
- Empty rules list handling
- Immutability (frozen=True)
- Strict validation (extra="forbid")
- Type validation for list[ExtractedRule]

Related to: TICKET 1

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Step 4.6: Implement RuleSet model
**File**: `src/qe_tax_rag/extraction/ca/schema.py` (add to existing)

**Implementation**:
```python
class RuleSet(BaseModel):
    """A collection of extracted rules, representing the final, validated dataset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rules: list[ExtractedRule]
```

**Run tests (should pass)**:
```bash
uv run pytest tests/unit/extraction/ca/test_schema.py -k RuleSet -v
```

**Commit**:
```
feat: implement RuleSet wrapper model

Add RuleSet model to wrap list of ExtractedRule objects
for final YAML output:
- Single field: rules (list[ExtractedRule])
- frozen=True for immutability
- extra="forbid" for strict validation

All RuleSet tests passing.

Rationale:
- Provides clean container for YAML serialization
- Enables schema validation on entire dataset
- Aligns with Pydantic best practices for collection models

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Phase 5: Integration Verification

#### Step 5.1: Run all TICKET 1 tests
**Action**: Comprehensive test suite run

**Commands**:
```bash
# Run all extraction/ca tests
uv run pytest tests/unit/extraction/ca/ -v

# Verify all modules can be imported
uv run python -c "from qe_tax_rag.extraction.ca.schema import ExtractedRule, RuleSet, ExpertSource, ApplicabilityType"
uv run python -c "from qe_tax_rag.extraction.ca.settings import settings"
uv run python -c "from qe_tax_rag.extraction.ca.exceptions import PipelineError, ParserError"
```

**Commit**:
```
test: verify TICKET 1 integration and imports

Run full test suite for extraction.ca package and verify all
modules can be imported successfully.

Test results:
- All exception tests passing
- All settings tests passing
- All schema tests passing
- Import verification successful

TICKET 1 COMPLETE: Foundational setup ready for TICKET 2-6.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Summary

### Total Commits: ~10-12 atomic commits
1. Build: Update pyproject.toml dependencies
2. Feat: Create extraction package structure
3. Test: Add exception tests
4. Feat: Implement exceptions
5. Test: Add settings tests
6. Feat: Implement settings
7. Test: Add enum tests
8. Feat: Implement enums
9. Test: Add ExtractedRule tests
10. Feat: Implement ExtractedRule model
11. Test: Add RuleSet tests
12. Feat: Implement RuleSet model
13. Test: Integration verification

### Pre-commit Hooks
All commits must pass:
- `ruff check` (linting)
- `ruff format` (code formatting)
- `mypy` (type checking - strict mode)
- `pyright` (type checking - strict mode)
- `mdformat` (markdown formatting)

### Test Coverage
- **Exceptions**: 5 tests
- **Settings**: 5 tests
- **Schema (Enums)**: 3 tests
- **Schema (ExtractedRule)**: 6 tests
- **Schema (RuleSet)**: 5 tests
- **Total**: ~24 unit tests

### Verification Checklist
- [ ] All tests passing
- [ ] All imports working
- [ ] Pre-commit hooks passing
- [ ] Dependencies synced (`uv sync --extra indexing`)
- [ ] No type errors (mypy + pyright)
- [ ] Code formatted (ruff format)

---

## Next Steps (Future Tickets)

After TICKET 1 completion:
- **TICKET 2**: Implement classic HTML parser (BeautifulSoup)
- **TICKET 3**: Implement text-based LLM parser (Gemini Flash)
- **TICKET 4**: Implement grounded adjudication (Gemini Pro)
- **TICKET 5**: Implement YAML generation and verification
- **TICKET 6**: Create pipeline orchestration CLI
