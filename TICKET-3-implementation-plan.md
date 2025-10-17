# TICKET 3 Implementation Plan: Text-Based LLM Parser

**Approach**: Test-Driven Development (TDD) with frequent, atomic commits
**Branch**: `feat/TICKET-3-llm-parser`
**No Regressions**: All existing tests must pass after each commit

---

## Pre-Implementation Checklist

- [ ] Review TICKET 2 PR #22 for patterns and conventions
- [ ] Verify all dependencies in `pyproject.toml` indexing section
- [ ] Create feature branch: `git checkout -b feat/TICKET-3-llm-parser`
- [ ] Sync dependencies: `uv sync --extra indexing`

---

## Phase 1: Package Structure Setup (TDD Foundation)

**Goal**: Restructure code to `src/qe_tax_rag/extraction/ca/` for proper packaging

### Step 1.1: Create Package Structure

**Actions**:
```bash
mkdir -p src/qe_tax_rag/extraction
mkdir -p src/qe_tax_rag/extraction/ca
touch src/qe_tax_rag/extraction/__init__.py
touch src/qe_tax_rag/extraction/ca/__init__.py
```

**Test**: Verify imports work
```python
uv run python -c "import qe_tax_rag.extraction.ca"
```

**Commit**:
```
feat(extraction): create Canada extraction package structure

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
```

### Step 1.2: Move and Test schemas.py

**TDD Cycle**:

1. **RED**: Update test imports (tests will fail)
   - Edit `tests/unit/test_classic_parser.py`
   - Change: `from scripts.parser.yaml_schema import ...`
   - To: `from qe_tax_rag.extraction.ca.schemas import ...`
   - Run: `uv run pytest tests/unit/test_classic_parser.py -v`
   - Expected: ImportError

2. **GREEN**: Move schemas.py
   - Copy `scripts/parser/yaml_schema.py` → `src/qe_tax_rag/extraction/ca/schemas.py`
   - Run: `uv run pytest tests/unit/test_classic_parser.py -v`
   - Expected: Tests pass

3. **REFACTOR**: Verify type checking
   - Run: `uv run mypy src/qe_tax_rag/extraction/ca/schemas.py`
   - Run: `uvx ruff check src/qe_tax_rag/extraction/ca/schemas.py`
   - Run: `uvx ruff format src/qe_tax_rag/extraction/ca/schemas.py`

**Commit**:
```
feat(extraction): move schemas to src package

Move Pydantic models from scripts/parser/ to src/qe_tax_rag/extraction/ca/
for proper packaging and distribution.

- Move yaml_schema.py → schemas.py
- Update imports in test_classic_parser.py
- Maintain exact same data structures (no breaking changes)
- All existing tests pass

Rationale:
- Schemas are part of runtime library, not scripts
- Enables packaging and distribution via PyPI
- Aligns with src-layout pattern
```

### Step 1.3: Move and Test exceptions.py

**TDD Cycle**:

1. **RED**: Update test imports
   - Edit all test files importing from `scripts.parser.exceptions`
   - Change to: `from qe_tax_rag.extraction.ca.exceptions import ...`
   - Run: `uv run pytest tests/unit/ -v`
   - Expected: ImportError

2. **GREEN**: Move exceptions.py
   - Copy `scripts/parser/exceptions.py` → `src/qe_tax_rag/extraction/ca/exceptions.py`
   - Run: `uv run pytest tests/unit/ -v`
   - Expected: Tests pass

3. **REFACTOR**: Quality checks
   - Run: `uv run mypy src/qe_tax_rag/extraction/ca/exceptions.py`
   - Run: `uvx ruff check src/qe_tax_rag/extraction/ca/`

**Commit**:
```
feat(extraction): move exceptions to src package

Move custom exception hierarchy to src/qe_tax_rag/extraction/ca/ for
proper packaging.

- Move exceptions.py from scripts/parser/
- Update all test imports
- Maintain same exception hierarchy (no breaking changes)
- All tests pass

Rationale:
- Exceptions are part of public API
- Required for proper error handling in packaged library
```

### Step 1.4: Move and Test settings.py

**TDD Cycle**:

1. **RED**: Update test imports
   - Edit files importing from `scripts.parser.settings`
   - Change to: `from qe_tax_rag.extraction.ca.settings import settings`
   - Run: `uv run pytest tests/unit/ -v`
   - Expected: ImportError

2. **GREEN**: Move settings.py
   - Copy `scripts/parser/settings.py` → `src/qe_tax_rag/extraction/ca/settings.py`
   - Run: `uv run pytest tests/unit/ -v`
   - Expected: Tests pass

3. **REFACTOR**: Verify .env integration
   - Test: `uv run python -c "from qe_tax_rag.extraction.ca.settings import settings; print(settings.gemini_api_key)"`
   - Run: `uv run mypy src/qe_tax_rag/extraction/ca/settings.py`

**Commit**:
```
feat(extraction): move settings to src package

Move configuration management to src/qe_tax_rag/extraction/ca/ for
proper packaging.

- Move settings.py from scripts/parser/
- Update all imports
- Maintain .env file compatibility
- All tests pass

Rationale:
- Settings are part of runtime configuration
- Enables proper API key management in packaged library
- Follows pydantic-settings pattern
```

### Step 1.5: Move and Test classic_parser.py

**TDD Cycle**:

1. **RED**: Update imports in classic_parser.py
   - Copy `scripts/parser/classic_parser.py` → `src/qe_tax_rag/extraction/ca/classic_parser.py`
   - Update internal imports:
     - `from scripts.parser.yaml_schema import ...` → `from qe_tax_rag.extraction.ca.schemas import ...`
     - `from scripts.parser.exceptions import ...` → `from qe_tax_rag.extraction.ca.exceptions import ...`
   - Run: `uv run pytest tests/unit/test_classic_parser.py -v`
   - Expected: May have import errors

2. **GREEN**: Update test imports
   - Edit `tests/unit/test_classic_parser.py`
   - Change: `from scripts.parser.classic_parser import parse`
   - To: `from qe_tax_rag.extraction.ca.classic_parser import parse`
   - Run: `uv run pytest tests/unit/test_classic_parser.py -v`
   - Expected: All tests pass

3. **REFACTOR**: Quality checks
   - Run: `uv run mypy src/qe_tax_rag/extraction/ca/classic_parser.py`
   - Run: `uvx ruff check src/qe_tax_rag/extraction/ca/classic_parser.py`
   - Run: `uv run pytest tests/unit/test_classic_parser.py -v -m unit`

**Commit**:
```
feat(extraction): move classic parser to src package

Move classic HTML parser (TICKET 2) to src/qe_tax_rag/extraction/ca/ for
proper packaging.

- Move classic_parser.py from scripts/parser/
- Update all internal imports to use new package structure
- Update test imports
- All TICKET 2 tests pass (no regressions)

Rationale:
- Classic parser is core extraction logic, not orchestration
- Required for packaging and distribution
- Enables import: from qe_tax_rag.extraction.ca import classic_parser
```

### Step 1.6: Full Test Suite Verification

**Actions**:
```bash
# Run all tests
uv run pytest tests/ -v

# Run type checking
uv run mypy src/qe_tax_rag/

# Run linting
uvx ruff check src/qe_tax_rag/
uvx ruff format src/qe_tax_rag/

# Run pre-commit hooks
uv run pre-commit run --all-files
```

**Expected**: All pass ✅

**Commit**:
```
refactor(extraction): complete package restructure for TICKET 3

Finalize migration of extraction pipeline components to src/ package.

Phase 1 complete:
- ✅ schemas.py moved and tested
- ✅ exceptions.py moved and tested
- ✅ settings.py moved and tested
- ✅ classic_parser.py moved and tested
- ✅ All imports updated
- ✅ All TICKET 1 & 2 tests pass
- ✅ Type checking passes (mypy + pyright)
- ✅ Linting passes (ruff)
- ✅ Pre-commit hooks pass

Ready for TICKET 3 LLM parser implementation.
```

---

## Phase 2: LLM Parser Implementation (TDD)

**Goal**: Implement `llm_parser.py` with production-ready error handling

### Step 2.1: Write Failing Tests for Basic Parsing

**TDD Cycle**:

1. **RED**: Create test file with failing test
   - Create: `tests/unit/test_llm_parser.py`
   - Implement: `test_parses_valid_llm_response()`
   - Mock `genai.GenerativeModel` to return valid JSON
   - Import: `from qe_tax_rag.extraction.ca.llm_parser import parse`
   - Run: `uv run pytest tests/unit/test_llm_parser.py -v`
   - Expected: ImportError (module doesn't exist yet)

**Test Code**:
```python
# tests/unit/test_llm_parser.py
from unittest.mock import MagicMock, patch
import pytest
from qe_tax_rag.extraction.ca.llm_parser import parse
from qe_tax_rag.extraction.ca.schemas import ExpertSource
from qe_tax_rag.extraction.ca.exceptions import ParserError

@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_parses_valid_llm_response(mock_genai, tmp_path):
    """Test LLM parser extracts valid JSON response."""
    # Arrange: Create minimal HTML fixture
    html_file = tmp_path / "test.html"
    html_file.write_text("""
    <html>
        <main>
            <h1>Chapter 3 – Expenses</h1>
            <h2>Part 4 – Net income</h2>
            <h3><a id="tocch3ln8523">Line 8523 – Meals</a>
                <img alt="business icon">
            </h3>
            <p>Some content about meals.</p>
        </main>
    </html>
    """)

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.text = """
    {
        "rules": [
            {
                "rule_number": 8523,
                "title": "Meals",
                "content": "Some content about meals.",
                "applies_to": ["business"],
                "source_citation": "Line 8523 – Meals",
                "chapter": "Chapter 3 – Expenses",
                "section": "Part 4 – Net income",
                "anchor_id": "tocch3ln8523"
            }
        ]
    }
    """
    mock_model = mock_genai.return_value
    mock_model.generate_content.return_value = mock_response

    # Act
    rules = parse(str(html_file))

    # Assert
    assert len(rules) == 1
    assert rules[0].rule_number == 8523
    assert rules[0].title == "Meals"
    assert rules[0].source_expert == ExpertSource.LLM
```

**Commit**:
```
test(extraction): add failing test for LLM parser basic parsing

TDD RED phase: Create test for valid LLM response parsing.

- Create tests/unit/test_llm_parser.py
- Mock genai.GenerativeModel
- Test expects parse() to return list[ExtractedRule]
- Test verifies source_expert=LLM
- Expected: ImportError (module not implemented)

Part of TDD cycle for TICKET 3.
```

2. **GREEN**: Implement minimal parse() function

**Create**: `src/qe_tax_rag/extraction/ca/llm_parser.py`

```python
"""LLM-based parser for CRA tax documents using Gemini API."""

import json
import logging
from pathlib import Path

import google.generativeai as genai
from bs4 import BeautifulSoup

from qe_tax_rag.extraction.ca.exceptions import ParserError
from qe_tax_rag.extraction.ca.schemas import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
)
from qe_tax_rag.extraction.ca.settings import settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
You are an expert data extraction agent specializing in Canadian tax law documents. Your task is to extract all line-numbered expense rules from the provided HTML content of a CRA guide.

Follow these rules precisely:
1. Identify `<h3>` tags that match the pattern "Line XXXX –", where XXXX is a number.
2. SKIP any `<h3>` tags that do not match this pattern (e.g., "Prepaid expenses").
3. For each matched rule, extract the following fields:
   - `rule_number`: The integer from the "Line XXXX" pattern.
   - `title`: The text immediately following "–" in the `<h3>` tag.
   - `content`: All text from the subsequent `<p>`, `<ul>`, and `<ol>` tags, up to the next `<h3>` tag.
   - `applies_to`: A list of income types derived from `<img>` tags within the `<h3>`. Map the `alt` text as follows: "business icon" -> "business", "farm icon" -> "farming", "fish icon" -> "fishing". If no icons are present, the list should be empty.
   - `chapter`: The text content of the `<h1>` tag.
   - `section`: The text content of the nearest preceding `<h2>` tag. If none, this should be null.
   - `anchor_id`: The `id` attribute of the `<a>` tag inside the `<h3>`. If none, this should be null.
4. The `source_citation` should be the full text of the `<h3>` tag (e.g., "Line 8523 – Meals and entertainment").

Respond with a single JSON object containing a "rules" key, which holds a list of the extracted rule objects.
"""


def parse(html_path: str) -> list[ExtractedRule]:
    """
    Parse HTML file using text-based LLM to extract line-numbered expense rules.

    Uses Gemini (Flash/Pro) to semantically understand HTML structure and extract
    rules matching "Line XXXX –" pattern. More resilient to HTML changes than
    rule-based parsing. Serves as the "LLM" expert in the Mixture-of-Experts pipeline.

    Extracts same fields as classic parser: line number, title, applies_to list,
    content, and context fields (chapter, section, source_file, anchor_id).

    Args:
        html_path: Absolute path to the local HTML file.

    Returns:
        List of ExtractedRule objects with source_expert set to LLM.
        Returns empty list if no line-numbered rules are found.

    Raises:
        ParserError: If file cannot be read, API call fails, or JSON response
                     cannot be parsed.
    """
    # Read HTML file
    try:
        html_content = Path(html_path).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        msg = f"HTML file not found: {html_path}"
        logger.error(msg)
        raise ParserError(msg) from e
    except OSError as e:
        msg = f"Failed to read HTML file: {html_path}"
        logger.error(msg, exc_info=True)
        raise ParserError(msg) from e

    # Extract <main> content using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    main_tag = soup.find("main")
    if not main_tag:
        msg = f"No <main> tag found in {html_path}"
        logger.warning(msg)
        main_content_text = soup.get_text()
    else:
        main_content_text = main_tag.get_text()

    # Configure Gemini
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.llm_model_name)

    # Call LLM with JSON mode
    try:
        response = model.generate_content(
            [EXTRACTION_PROMPT, main_content_text],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            ),
        )
    except Exception as e:
        msg = f"API call failed for {html_path}"
        logger.error(msg, exc_info=True)
        raise ParserError(msg) from e

    # Parse JSON response
    try:
        data = json.loads(response.text)
        rules_data = data.get("rules", [])
    except json.JSONDecodeError as e:
        msg = f"Failed to parse JSON response for {html_path}"
        logger.error(f"{msg}. Raw response: {response.text}", exc_info=True)
        raise ParserError(msg) from e

    # Convert to ExtractedRule objects
    rules = []
    source_file = Path(html_path).name

    for rule_dict in rules_data:
        try:
            # Map applies_to strings to enum
            applies_to_str = rule_dict.get("applies_to", [])
            applies_to_enum = [
                ApplicabilityType(s) for s in applies_to_str
            ]

            rule = ExtractedRule(
                rule_number=rule_dict["rule_number"],
                title=rule_dict["title"],
                content=rule_dict["content"],
                applies_to=applies_to_enum,
                source_citation=rule_dict["source_citation"],
                chapter=rule_dict["chapter"],
                section=rule_dict.get("section"),
                source_file=source_file,
                source_expert=ExpertSource.LLM,
                anchor_id=rule_dict.get("anchor_id"),
            )
            rules.append(rule)
        except (KeyError, ValueError) as e:
            msg = f"Failed to validate rule data in {html_path}"
            logger.error(f"{msg}. Invalid data: {rule_dict}", exc_info=True)
            raise ParserError(msg) from e

    logger.info(f"LLM parser extracted {len(rules)} rules from {html_path}")
    return rules
```

**Run Test**:
```bash
uv run pytest tests/unit/test_llm_parser.py::test_parses_valid_llm_response -v
```

**Expected**: Test passes ✅

**Commit**:
```
feat(extraction): implement basic LLM parser with JSON mode

TDD GREEN phase: Minimal implementation to pass basic parsing test.

- Create src/qe_tax_rag/extraction/ca/llm_parser.py
- Implement parse(html_path) -> list[ExtractedRule]
- Use Gemini JSON mode for reliable output
- BeautifulSoup extracts <main> tag content
- Set source_expert=ExpertSource.LLM
- Basic error handling for file I/O and JSON parsing

Test status: test_parses_valid_llm_response ✅

Next: Add retry logic and comprehensive error handling.
```

### Step 2.2: Add Tests for Error Handling (Retry Logic)

**TDD Cycle**:

1. **RED**: Write tests for API retry behavior

Add to `tests/unit/test_llm_parser.py`:

```python
from google.api_core import exceptions as google_exceptions

@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
@patch("qe_tax_rag.extraction.ca.llm_parser.time.sleep")  # Mock sleep
def test_retries_on_rate_limit_then_succeeds(mock_sleep, mock_genai, tmp_path):
    """Test parser retries on 429 and succeeds on 2nd attempt."""
    # Arrange
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_response = MagicMock()
    mock_response.text = '{"rules": []}'

    mock_model = mock_genai.return_value
    # Fail on first call, succeed on second
    mock_model.generate_content.side_effect = [
        google_exceptions.ResourceExhausted("Rate limited"),
        mock_response,
    ]

    # Act
    rules = parse(str(html_file))

    # Assert
    assert mock_model.generate_content.call_count == 2
    assert mock_sleep.call_count == 1
    assert rules == []

@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
@patch("qe_tax_rag.extraction.ca.llm_parser.time.sleep")
def test_raises_error_after_max_retries(mock_sleep, mock_genai, tmp_path):
    """Test parser raises ParserError after 3 failed retries."""
    # Arrange
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_model = mock_genai.return_value
    mock_model.generate_content.side_effect = google_exceptions.ResourceExhausted("Rate limited")

    # Act & Assert
    with pytest.raises(ParserError, match="API call failed permanently"):
        parse(str(html_file))

    assert mock_model.generate_content.call_count == 3
    assert mock_sleep.call_count == 2  # Sleep between retries
```

**Run**:
```bash
uv run pytest tests/unit/test_llm_parser.py::test_retries_on_rate_limit_then_succeeds -v
uv run pytest tests/unit/test_llm_parser.py::test_raises_error_after_max_retries -v
```

**Expected**: Both fail ❌ (retry logic not implemented)

**Commit**:
```
test(extraction): add failing tests for LLM parser retry logic

TDD RED phase: Tests for API error retry with exponential backoff.

- test_retries_on_rate_limit_then_succeeds: Expect 2 API calls, 1 sleep
- test_raises_error_after_max_retries: Expect ParserError after 3 attempts
- Mock time.sleep to avoid actual delays
- Mock google_exceptions.ResourceExhausted (429)

Expected: Tests fail (retry logic not implemented)

Part of TDD cycle for robust error handling.
```

2. **GREEN**: Implement retry logic with exponential backoff

**Update** `src/qe_tax_rag/extraction/ca/llm_parser.py`:

```python
import time
from google.api_core import exceptions as google_exceptions

# Inside parse() function, replace the try block for API call:

    # Call LLM with retry logic
    retries = 3
    backoff_factor = 2
    last_exception = None

    for attempt in range(retries):
        try:
            response = model.generate_content(
                [EXTRACTION_PROMPT, main_content_text],
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                ),
            )
            break  # Success - exit retry loop
        except (
            google_exceptions.ResourceExhausted,    # 429
            google_exceptions.ServiceUnavailable,   # 503
            google_exceptions.InternalServerError,  # 500
        ) as e:
            last_exception = e
            if attempt + 1 == retries:
                msg = f"API call failed permanently for {html_path} after {retries} attempts"
                logger.error(msg, exc_info=True)
                raise ParserError(msg) from e

            wait_time = backoff_factor ** attempt
            logger.warning(
                f"API error for {html_path}, attempt {attempt + 1}/{retries}. "
                f"Retrying in {wait_time} seconds... Error: {e}"
            )
            time.sleep(wait_time)
    else:
        # If we exhausted retries without success
        msg = f"API call failed for {html_path}"
        logger.error(msg, exc_info=True)
        raise ParserError(msg) from last_exception
```

**Run**:
```bash
uv run pytest tests/unit/test_llm_parser.py -v
```

**Expected**: All tests pass ✅

**Commit**:
```
feat(extraction): add retry logic with exponential backoff to LLM parser

TDD GREEN phase: Implement robust error handling for transient API failures.

- Retry up to 3 times on 429/503/500 errors
- Exponential backoff: 1s, 2s, 4s
- Log warnings on retries with attempt count
- Raise ParserError after max retries exceeded
- Handle ResourceExhausted, ServiceUnavailable, InternalServerError

Test status:
- test_parses_valid_llm_response ✅
- test_retries_on_rate_limit_then_succeeds ✅
- test_raises_error_after_max_retries ✅

Resilience: Handles transient network issues common in LLM APIs.
```

### Step 2.3: Add Tests for Multiple Icons and Edge Cases

**TDD Cycle**:

1. **RED**: Write tests for edge cases

Add to `tests/unit/test_llm_parser.py`:

```python
@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_extracts_multiple_applies_to_values(mock_genai, tmp_path):
    """Test parser handles multiple icons (business + fishing)."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_response = MagicMock()
    mock_response.text = """
    {
        "rules": [{
            "rule_number": 9999,
            "title": "Test",
            "content": "Test content",
            "applies_to": ["business", "fishing"],
            "source_citation": "Line 9999 – Test",
            "chapter": "Chapter 1",
            "section": null,
            "anchor_id": null
        }]
    }
    """
    mock_genai.return_value.generate_content.return_value = mock_response

    rules = parse(str(html_file))

    assert len(rules) == 1
    assert rules[0].applies_to == [
        ApplicabilityType.BUSINESS,
        ApplicabilityType.FISHING,
    ]

@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_handles_empty_applies_to_list(mock_genai, tmp_path):
    """Test parser handles rules with no icons."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_response = MagicMock()
    mock_response.text = """
    {
        "rules": [{
            "rule_number": 9999,
            "title": "Test",
            "content": "Test content",
            "applies_to": [],
            "source_citation": "Line 9999 – Test",
            "chapter": "Chapter 1",
            "section": null,
            "anchor_id": null
        }]
    }
    """
    mock_genai.return_value.generate_content.return_value = mock_response

    rules = parse(str(html_file))

    assert len(rules) == 1
    assert rules[0].applies_to == []

@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_raises_parser_error_on_malformed_json(mock_genai, tmp_path):
    """Test parser handles malformed JSON from LLM."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><main><p>Test</p></main></html>")

    mock_response = MagicMock()
    mock_response.text = "NOT VALID JSON {"
    mock_genai.return_value.generate_content.return_value = mock_response

    with pytest.raises(ParserError, match="Failed to parse JSON"):
        parse(str(html_file))

@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_raises_parser_error_on_invalid_file_path(mock_genai):
    """Test parser raises error on non-existent file."""
    with pytest.raises(ParserError, match="HTML file not found"):
        parse("/nonexistent/path.html")
```

**Run**:
```bash
uv run pytest tests/unit/test_llm_parser.py -v
```

**Expected**: All new tests pass ✅ (implementation already handles these)

**Commit**:
```
test(extraction): add comprehensive edge case tests for LLM parser

TDD validation: Verify parser handles edge cases correctly.

Tests added:
- test_extracts_multiple_applies_to_values: Multiple icons
- test_handles_empty_applies_to_list: No icons
- test_raises_parser_error_on_malformed_json: Invalid JSON
- test_raises_parser_error_on_invalid_file_path: Missing file

All tests pass ✅ - existing implementation is robust.

Coverage: Icon extraction, JSON parsing, file I/O errors.
```

### Step 2.4: Add Token Safety Check

**TDD Cycle**:

1. **RED**: Write test for token limit warning

Add to `tests/unit/test_llm_parser.py`:

```python
@patch("qe_tax_rag.extraction.ca.llm_parser.genai.GenerativeModel")
def test_logs_warning_for_large_content(mock_genai, tmp_path, caplog):
    """Test parser logs warning for content exceeding token limit."""
    import logging

    html_file = tmp_path / "test.html"
    # Create large HTML content
    large_content = "<html><main>" + ("x" * 800_000) + "</main></html>"
    html_file.write_text(large_content)

    mock_response = MagicMock()
    mock_response.text = '{"rules": []}'

    mock_model = mock_genai.return_value
    mock_model.count_tokens.return_value = MagicMock(total_tokens=1_100_000)
    mock_model.generate_content.return_value = mock_response

    with caplog.at_level(logging.WARNING):
        parse(str(html_file))

    assert "exceeds token limit" in caplog.text
    assert mock_model.count_tokens.called
```

**Run**:
```bash
uv run pytest tests/unit/test_llm_parser.py::test_logs_warning_for_large_content -v
```

**Expected**: Fails ❌ (token check not implemented)

**Commit**:
```
test(extraction): add failing test for token limit warning

TDD RED phase: Test for large content warning.

- test_logs_warning_for_large_content: Expect warning log
- Mock model.count_tokens() to return > 1M tokens
- Use caplog fixture to capture log messages

Expected: Test fails (token check not implemented)

Part of defensive programming for token management.
```

2. **GREEN**: Implement token safety check

**Update** `src/qe_tax_rag/extraction/ca/llm_parser.py`:

```python
# Add after extracting main_content_text, before API call:

    # Token safety check
    try:
        token_count = model.count_tokens(main_content_text)
        if token_count.total_tokens > 1_000_000:
            logger.warning(
                f"Content of {html_path} exceeds token limit: "
                f"{token_count.total_tokens} tokens (max: 1M). "
                "Extraction may fail or be incomplete."
            )
    except Exception as e:
        # Don't fail on token counting errors - it's a safety check
        logger.debug(f"Token counting failed for {html_path}: {e}")
```

**Run**:
```bash
uv run pytest tests/unit/test_llm_parser.py -v
```

**Expected**: All tests pass ✅

**Commit**:
```
feat(extraction): add token safety check to LLM parser

TDD GREEN phase: Implement defensive check for large documents.

- Use model.count_tokens() for accurate token counting
- Log warning if content > 1M tokens (Gemini Flash limit)
- Non-fatal: Don't fail pipeline on token counting errors
- Provides visibility into potential API failures

Test status: test_logs_warning_for_large_content ✅

Defensive programming: Warns before expensive API calls fail.
```

3. **REFACTOR**: Code cleanup and documentation

**Actions**:
- Add comprehensive docstrings
- Format with ruff
- Type check with mypy

```bash
uvx ruff format src/qe_tax_rag/extraction/ca/llm_parser.py
uvx ruff check src/qe_tax_rag/extraction/ca/llm_parser.py
uv run mypy src/qe_tax_rag/extraction/ca/llm_parser.py
```

**Commit**:
```
refactor(extraction): polish LLM parser implementation

TDD REFACTOR phase: Code cleanup and quality improvements.

- Add comprehensive module and function docstrings
- Format code with ruff
- Pass strict type checking (mypy + pyright)
- Add inline comments for complex logic
- Improve error messages

Quality gates:
- ✅ ruff format
- ✅ ruff check
- ✅ mypy (strict mode)
- ✅ All tests pass
```

---

## Phase 3: Integration Testing

**Goal**: Test against real HTML files from cra_documents/

### Step 3.1: Create Integration Test

**Actions**:

1. Create `tests/integration/test_llm_parser_integration.py`:

```python
"""Integration tests for LLM parser against real CRA HTML files."""

import pytest
from pathlib import Path

from qe_tax_rag.extraction.ca.llm_parser import parse
from qe_tax_rag.extraction.ca.schemas import ExpertSource

# Skip if no API key configured
pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not Path("cra_documents/cra_t4002e_rev24_dump").exists(),
    reason="CRA HTML dump not found"
)
def test_parse_real_html_file():
    """Test LLM parser against real CRA HTML file."""
    # Find first HTML file in dump
    html_dir = Path("cra_documents/cra_t4002e_rev24_dump")
    html_files = list(html_dir.glob("*.html"))

    if not html_files:
        pytest.skip("No HTML files found in dump directory")

    # Parse first file
    rules = parse(str(html_files[0]))

    # Basic assertions
    assert isinstance(rules, list)
    assert all(rule.source_expert == ExpertSource.LLM for rule in rules)

    # Log results for manual inspection
    print(f"\nParsed {len(rules)} rules from {html_files[0].name}")
    if rules:
        print(f"First rule: {rules[0].rule_number} - {rules[0].title}")
```

2. Run (requires API key):

```bash
# Set API key if not in .env
export PARSER_GEMINI_API_KEY="your-key-here"

# Run integration test
uv run pytest tests/integration/test_llm_parser_integration.py -v -s
```

**Commit**:
```
test(extraction): add integration test for LLM parser

Integration test against real CRA HTML files.

- Test parses actual HTML from cra_documents/cra_t4002e_rev24_dump/
- Validates source_expert=LLM set correctly
- Skips if dump directory missing or no API key
- Marked with @pytest.mark.integration

Run: uv run pytest tests/integration/ -v -m integration

Manual validation: Check rule_number, title extraction quality.
```

---

## Phase 4: Documentation and Final Quality Checks

### Step 4.1: Add Module Documentation

**Actions**:

1. Update `src/qe_tax_rag/extraction/ca/__init__.py`:

```python
"""
Canadian tax document extraction pipeline.

This package provides HTML-to-YAML extraction for CRA tax documents using
a Mixture-of-Experts approach with grounded adjudication.

Modules:
    schemas: Pydantic models for extraction data structures
    settings: Configuration management with pydantic-settings
    exceptions: Custom exception hierarchy
    classic_parser: Rule-based HTML parser (BeautifulSoup)
    llm_parser: LLM-based semantic parser (Gemini)
"""

__all__ = [
    "classic_parser",
    "llm_parser",
    "schemas",
    "settings",
    "exceptions",
]
```

**Commit**:
```
docs(extraction): add package documentation

Document extraction package structure and modules.

- Add __init__.py docstring
- List all modules with brief descriptions
- Explain MoE approach

Improves discoverability and API clarity.
```

### Step 4.2: Run Full Test Suite

**Actions**:

```bash
# Run all tests (unit + integration)
uv run pytest tests/ -v

# Run only unit tests (fast)
uv run pytest tests/unit -v -m unit

# Check coverage
uv run pytest tests/ --cov=src/qe_tax_rag/extraction/ca --cov-report=html
```

**Commit**:
```
test(extraction): verify full test suite passes

Complete test coverage validation for TICKET 3.

Test results:
- Unit tests: X/X passed
- Integration tests: X/X passed (requires API key)
- Coverage: XX% for extraction.ca package

All quality gates pass:
- ✅ pytest (unit + integration)
- ✅ ruff format
- ✅ ruff check
- ✅ mypy strict
- ✅ pyright strict
```

### Step 4.3: Pre-commit Hook Verification

**Actions**:

```bash
# Run all pre-commit hooks
uv run pre-commit run --all-files

# If any hooks fail, fix and re-run
uvx ruff format .
uvx ruff check --fix .
uv run mypy src/
```

**Commit**:
```
chore(extraction): pass all pre-commit hooks

Final quality validation for TICKET 3.

Pre-commit results:
- ✅ ruff (linting with auto-fix)
- ✅ ruff-format (code formatting)
- ✅ mypy (strict type checking)
- ✅ pyright (strict type checking)
- ✅ mdformat (markdown formatting)
- ✅ trailing-whitespace, end-of-file-fixer, check-yaml
- ✅ check-added-large-files, check-merge-conflict

Ready for PR review.
```

---

## Phase 5: PR Preparation

### Step 5.1: Update CHANGELOG.md

**Actions**:

Add to `CHANGELOG.md`:

```markdown
## [Unreleased]

### Added (TICKET 3)
- **LLM Parser**: Text-based semantic parser using Gemini API for HTML extraction
  - Resilient to HTML structure changes through semantic understanding
  - Retry logic with exponential backoff for transient API errors (429, 503, 500)
  - Token safety checks to prevent oversized API calls
  - Comprehensive error handling for API, JSON, and validation failures
  - Uses Gemini JSON mode for reliable structured output

### Changed (TICKET 3)
- **Package Restructure**: Moved extraction pipeline to `src/qe_tax_rag/extraction/ca/`
  - `schemas.py`: Pydantic models (ExtractedRule, RuleSet, enums)
  - `settings.py`: Configuration with pydantic-settings
  - `exceptions.py`: Custom exception hierarchy
  - `classic_parser.py`: Migrated from scripts/parser/
  - `llm_parser.py`: New LLM-based parser

### Testing (TICKET 3)
- 10+ unit tests for LLM parser with mocked Gemini client
- Integration tests against real CRA HTML files
- Test coverage: XX% for extraction.ca package
- All tests use TDD approach (RED-GREEN-REFACTOR)
```

**Commit**:
```
docs: update CHANGELOG for TICKET 3

Document new features and changes for LLM parser implementation.

- Added: LLM parser with retry logic and error handling
- Changed: Package restructure to src/ layout
- Testing: TDD approach with comprehensive coverage

Follows Keep a Changelog format.
```

### Step 5.2: Final Integration Test

**Actions**:

```bash
# Test end-to-end import
uv run python -c "
from qe_tax_rag.extraction.ca import llm_parser, classic_parser, schemas
from qe_tax_rag.extraction.ca.settings import settings
from qe_tax_rag.extraction.ca.exceptions import ParserError
print('✅ All imports successful')
"

# Verify no regressions in main package
uv run pytest tests/unit/test_search.py -v
uv run pytest tests/integration/ -v
```

**Commit**:
```
test: verify no regressions in main package

Ensure TICKET 3 changes don't break existing functionality.

- ✅ All extraction.ca imports work
- ✅ qe_tax_rag.search tests pass (no regressions)
- ✅ Integration tests pass

Package is stable and ready for PR.
```

### Step 5.3: Create PR Description

**Actions**:

Create `PR-TICKET-3-description.md`:

```markdown
# TICKET 3: Text-Based LLM Parser Module

Implements the second "expert" in the Mixture-of-Experts HTML-to-YAML extraction pipeline using Gemini API for semantic parsing.

## 🎯 Objectives

- ✅ Create LLM-based parser resilient to HTML structure changes
- ✅ Implement production-ready error handling with retries
- ✅ Move extraction pipeline to `src/` for proper packaging
- ✅ Maintain 100% test pass rate (no regressions)
- ✅ Follow TDD approach with comprehensive coverage

## 📦 Changes

### New Features

1. **LLM Parser** (`src/qe_tax_rag/extraction/ca/llm_parser.py`)
   - Semantic extraction using Gemini Flash/Pro
   - Retry logic with exponential backoff (3 attempts, 2^n seconds)
   - Token safety checks using `model.count_tokens()`
   - Gemini JSON mode for reliable structured output
   - Comprehensive error handling: API failures, malformed JSON, validation errors

2. **Package Restructure** (Proper `src/` layout)
   - Moved `schemas.py` from scripts/parser/
   - Moved `settings.py` from scripts/parser/
   - Moved `exceptions.py` from scripts/parser/
   - Moved `classic_parser.py` from scripts/parser/
   - All code now in `src/qe_tax_rag/extraction/ca/`

### Testing

- **Unit Tests**: 10+ tests with mocked Gemini client
  - Valid response parsing
  - Retry logic (429, 503, 500 errors)
  - Multiple icons extraction
  - Empty applies_to list
  - Malformed JSON handling
  - Token limit warnings
  - File I/O errors

- **Integration Tests**: Real CRA HTML files (requires API key)

- **Coverage**: XX% for extraction.ca package

## 🏗️ Architecture Decisions

1. **Retry Logic**: Exponential backoff for transient errors (429, 503, 500)
   - Improves reliability for batch processing
   - No new dependencies (uses stdlib `time.sleep`)

2. **Gemini JSON Mode**: Forces structured output
   - Eliminates prompt engineering for JSON format
   - Reduces parsing errors

3. **Token Safety Check**: Non-fatal warning for large documents
   - Uses `model.count_tokens()` for accuracy
   - Provides visibility before expensive API calls fail

4. **Package Structure**: `src/qe_tax_rag/extraction/ca/`
   - Runtime library (distributed via PyPI)
   - Enables: `from qe_tax_rag.extraction.ca import llm_parser`
   - Follows project's src-layout pattern

## ✅ Quality Gates

- [x] All unit tests pass (XX tests)
- [x] All integration tests pass
- [x] ruff format (code formatting)
- [x] ruff check (linting - strict)
- [x] mypy (strict type checking)
- [x] pyright (strict type checking)
- [x] pre-commit hooks pass
- [x] No regressions in main package
- [x] CHANGELOG.md updated

## 🔗 Dependencies

All dependencies in `pyproject.toml` `[project.optional-dependencies.indexing]`:
- google-generativeai>=0.8.5 ✅
- beautifulsoup4>=4.12 ✅
- lxml>=5.0 ✅
- pyyaml>=6.0 ✅

## 📝 Testing Instructions

```bash
# Sync dependencies
uv sync --extra indexing

# Run unit tests (fast, no API key needed)
uv run pytest tests/unit/test_llm_parser.py -v

# Run integration tests (requires API key)
export PARSER_GEMINI_API_KEY="your-key"
uv run pytest tests/integration/test_llm_parser_integration.py -v

# Run all tests
uv run pytest tests/ -v

# Check types
uv run mypy src/qe_tax_rag/extraction/ca/

# Check linting
uvx ruff check src/qe_tax_rag/extraction/ca/
```

## 🚀 Next Steps

- **TICKET 4**: Implement adjudicator to merge classic + LLM results
- **TICKET 5**: YAML generation and verification
- **TICKET 6**: Orchestration script (CLI)

## 🎓 TDD Approach

This implementation followed strict TDD:
- 15+ commits (RED-GREEN-REFACTOR cycles)
- Each feature started with failing tests
- Minimal implementation to pass tests
- Refactor for quality and maintainability

---

Closes #TICKET-3
Related: #TICKET-1, #TICKET-2
```

**Commit**:
```
docs: create PR description for TICKET 3

Comprehensive PR documentation with:
- Objectives and changes summary
- Architecture decisions and rationale
- Quality gates checklist
- Testing instructions
- Next steps and related tickets

Ready for team review.
```

---

## Final Checklist Before PR

- [ ] All commits follow conventional commits format
- [ ] Each commit is atomic and buildable
- [ ] Commit messages explain WHY, not WHAT
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Type checking passes: `uv run mypy src/`
- [ ] Linting passes: `uvx ruff check src/`
- [ ] Formatting passes: `uvx ruff format src/`
- [ ] Pre-commit hooks pass: `uv run pre-commit run --all-files`
- [ ] No regressions in main package
- [ ] CHANGELOG.md updated
- [ ] PR description complete with testing instructions
- [ ] Branch rebased on main (if needed)
- [ ] Ready for review

---

## Commit Summary Template

**Phase 1: Package Restructure**
1. Create package structure
2. Move schemas.py + tests pass
3. Move exceptions.py + tests pass
4. Move settings.py + tests pass
5. Move classic_parser.py + tests pass
6. Full test suite verification

**Phase 2: LLM Parser (TDD)**
7. RED: Add failing test for basic parsing
8. GREEN: Implement minimal parse() function
9. RED: Add failing tests for retry logic
10. GREEN: Implement retry with exponential backoff
11. Add tests for edge cases (already pass)
12. RED: Add failing test for token check
13. GREEN: Implement token safety check
14. REFACTOR: Code cleanup and documentation

**Phase 3: Integration**
15. Add integration test against real HTML

**Phase 4: Documentation**
16. Add package documentation
17. Run full test suite
18. Pass all pre-commit hooks

**Phase 5: PR Prep**
19. Update CHANGELOG.md
20. Verify no regressions
21. Create PR description

**Total: ~21 commits** (atomic, tested, buildable)

---

## Success Criteria

✅ **Functionality**: LLM parser extracts rules from CRA HTML files
✅ **Reliability**: Retry logic handles transient API errors
✅ **Quality**: All tests pass, 100% type checking, linting clean
✅ **Packaging**: Code in src/ for PyPI distribution
✅ **Testing**: TDD approach with comprehensive coverage
✅ **Documentation**: Clear docstrings, CHANGELOG, PR description
✅ **No Regressions**: All existing tests still pass

---

## Notes

- **API Key Management**: Use `.env` file with `PARSER_GEMINI_API_KEY`
- **Integration Tests**: Require API key and real HTML files
- **Token Limits**: Gemini Flash 1.5 has 1M token context window
- **JSON Mode**: Requires `google-generativeai>=0.8.5`
- **TDD Discipline**: RED-GREEN-REFACTOR for every feature
- **Commit Frequency**: After each TDD cycle (every 15-30 minutes)

---

**Implementation Time Estimate**: 4-6 hours (with TDD + testing + documentation)

**Branch**: `feat/TICKET-3-llm-parser`
**Target**: `main`
**Assignee**: Claude Code + Human Review
