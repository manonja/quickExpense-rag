# Implementation Plan: HTML-to-YAML Grounded Extraction Pipeline

## Architecture Summary

- **Structure**: A series of scripts in the `scripts/` directory, orchestrated by a main CLI script.
- **Extraction**: A Mixture-of-Experts (MoE) approach using a classic HTML parser and a text-based LLM parser.
- **Scope**: Extracts only line-numbered expense rules (h3 tags matching "Line XXXX –" pattern) from CRA T4002 guide.
- **Grounding**: A self-correction loop where a third LLM ("The Adjudicator") resolves conflicts between the experts based on source evidence, providing an auditable trail.
- **Output**: A single, schema-verified YAML file containing the extracted line-item business expense rules.
- **Tech Stack**: Python 3.11+, Pydantic v2, BeautifulSoup4, PyYAML, Google Gemini (Flash/Pro).

---

## TICKET 1: Foundational Setup & Data Schema Definition

**Scope**: Initialize the environment with all required dependencies and define the canonical Pydantic schemas that govern all data exchange within the pipeline. Includes settings management and custom exception hierarchy to support downstream tickets.

### Acceptance Criteria

- [ ] Verify `pyproject.toml` has required dependencies in `[project.optional-dependencies.indexing]`:
  ```toml
  [project.optional-dependencies]
  indexing = [
      "beautifulsoup4>=4.12",
      "pyyaml>=6.0",
      "google-generativeai>=0.3",
      # No additional dependencies needed - text-based parsing only
  ]
  ```
  **Note**: Playwright and Pillow are NOT needed for this pipeline (text-based LLM parsing, not multimodal).

- [ ] A new file `scripts/parser/yaml_schema.py` is created with modernized Pydantic models following Python 3.12+ standards:
  ```python
  from enum import Enum
  from pydantic import BaseModel, ConfigDict


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


  class ExtractedRule(BaseModel):
      """
      Represents a single line-item expense rule from CRA forms T2125/T2042/T2121.

      Only extracts h3 headings with 'Line XXXX –' pattern.
      Includes core data fields for the final output and optional metadata
      for internal pipeline processing.
      """
      model_config = ConfigDict(frozen=True, extra="forbid")

      # Core fields for the final YAML output
      rule_number: int                          # e.g., 8523 from "Line 8523"
      title: str                                # e.g., "Meals and entertainment"
      content: str                              # Full text description
      applies_to: list[ApplicabilityType]       # ["business", "fishing"] from icons
      source_citation: str                      # e.g., "Line 8523"

      # Context fields for navigation and filtering
      chapter: str                              # e.g., "Chapter 3 – Expenses"
      section: str | None = None                # e.g., "Part 4 – Net income (loss) before adjustments"
      source_file: str                          # e.g., "t4002-5.html"

      # Internal pipeline metadata (stripped out during final YAML generation)
      source_expert: ExpertSource | None = None  # Tracks which expert generated this rule
      anchor_id: str | None = None               # e.g., "tocch3ln8523" for debugging


  class RuleSet(BaseModel):
      """A collection of extracted rules, representing the final, validated dataset."""
      model_config = ConfigDict(frozen=True, extra="forbid")

      rules: list[ExtractedRule]
  ```

- [ ] A new file `scripts/parser/settings.py` is created for configuration management:
  ```python
  from pydantic_settings import BaseSettings, SettingsConfigDict


  class Settings(BaseSettings):
      """Configuration settings for the data extraction pipeline."""
      model_config = SettingsConfigDict(
          env_file=".env", env_file_encoding="utf-8", env_prefix="PARSER_"
      )

      # Gemini API Configuration
      gemini_api_key: str = "your-api-key-here"
      llm_model_name: str = "gemini-1.5-flash-latest"  # Text-based LLM for parsing
      adjudicator_model_name: str = "gemini-1.5-pro-latest"


  # Singleton instance
  settings = Settings()
  ```

- [ ] A new file `scripts/parser/exceptions.py` is created with custom exception hierarchy:
  ```python
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

- [ ] Verification commands pass without error:
  ```bash
  # Sync dependencies
  uv sync --extra indexing

  # Verify all modules can be imported
  uv run python -c "from scripts.parser.yaml_schema import ExtractedRule, RuleSet, ExpertSource, ApplicabilityType"
  uv run python -c "from scripts.parser.settings import settings"
  uv run python -c "from scripts.parser.exceptions import PipelineError, ParserError"
  ```

**Dependency**: None
**Enables**: All subsequent tickets

**Design Rationale**:
- **Line-only extraction**: Focus on form line items (80/20 principle) - delivers core value without over-engineering
- **Context fields**: `chapter`, `section`, `source_file` enable RAG navigation and debugging without complexity
- **`applies_to` field**: Correct semantic meaning (income type, not business structure) extracted from icon alt text
- **`source_expert` field**: Required for adjudicator (TICKET 4) to track rule provenance and resolve conflicts
- **Settings management**: Prevents hardcoded API keys; follows existing project pattern
- **Custom exceptions**: Enables robust error handling in orchestrator (TICKET 6)
- **Modern types**: Aligns with CLAUDE.md standards (`str | None`, `list[T]`, frozen models)
- **No Playwright/Pillow**: Text-based parsing eliminates browser automation complexity

---

## TICKET 2: Implement Classic HTML Parser Module

**Scope**: Create the first of two "experts" in the MoE pipeline. This expert uses traditional, rule-based methods for fast and reliable extraction from known document structures. Extracts only line-numbered rules (h3 tags matching "Line XXXX –" pattern) with context fields for navigation.

### Acceptance Criteria

- [ ] A new module, `scripts/parser/classic_parser.py`, is created containing a `parse(html_path: str) -> list[ExtractedRule]` function with comprehensive docstring:
  ```python
  from bs4 import BeautifulSoup
  from scripts.parser.yaml_schema import ExtractedRule, ExpertSource, ApplicabilityType
  from scripts.parser.exceptions import ParserError
  import logging
  import re
  from pathlib import Path

  logger = logging.getLogger(__name__)

  def parse(html_path: str) -> list[ExtractedRule]:
      """
      Parses HTML file from CRA T4002 guide to extract line-numbered expense rules.

      Extracts only h3 tags matching "Line XXXX –" pattern (e.g., "Line 8523 – Meals").
      Uses rule-based approach with BeautifulSoup to identify rule boundaries,
      extract icons for applicability, and collect content. Serves as the "classic"
      expert in the Mixture-of-Experts pipeline.

      The parser extracts context fields (chapter, section) for RAG navigation
      and is resilient to individual rule failures.

      Args:
          html_path: Absolute path to the local HTML file.

      Returns:
          List of ExtractedRule objects with source_expert set to CLASSIC.
          Returns empty list if no line-numbered rules are found.

      Raises:
          ParserError: If file cannot be read or no line-numbered rule headers
                       are found, suggesting major structural change.
      """
  ```

- [ ] The `parse` function reads the HTML file from disk and uses `BeautifulSoup` to parse it.

- [ ] The parser finds **only** `<h3>` tags matching the pattern `Line \d+ –` using regex:
  - Extract `rule_number` (int) and `title` (str) from the header text
  - Example: "Line 8523 – Meals and entertainment" → `rule_number=8523`, `title="Meals and entertainment"`
  - Skip h3 tags without "Line XXXX –" pattern (conceptual sections)

- [ ] For each matched line item, the parser:
  - **Extracts icons**: Find all `<img>` tags within the h3 header, extract `alt` text, map to `ApplicabilityType` enum values (e.g., "business icon" → `ApplicabilityType.BUSINESS`), build `applies_to` list
  - **Collects content**: Gather all text from `<p>`, `<ul>`, `<ol>` tags in subsequent sibling elements until the next `<h3>` tag
  - **Cleans content**: Normalize whitespace (max 2 consecutive newlines, strip leading/trailing whitespace)

- [ ] The parser extracts **context fields** for each rule:
  - `chapter`: Extract from h1 tag or filename (e.g., "Chapter 3 – Expenses")
  - `section`: Find the immediately preceding h2 tag (e.g., "Part 4 – Net income (loss) before adjustments")
  - `source_file`: Extract filename from `html_path` (e.g., "t4002-5.html")
  - `anchor_id`: Extract `id` attribute from the `<a>` tag within the h3 (e.g., "tocch3ln8523")

- [ ] Every `ExtractedRule` object returned has its `source_expert` field set to `ExpertSource.CLASSIC`. This is **mandatory** for the adjudicator (TICKET 4) to differentiate inputs.

- [ ] The function is resilient to individual rule failures:
  - If a rule block is malformed (e.g., header with no parsable content), the parser skips it and logs a warning using `logger.warning()`
  - Malformed rules do not cause the entire parse to fail

- [ ] The function raises a `ParserError` if:
  - File cannot be read from `html_path`
  - No `<h3>` tags matching "Line \d+ –" pattern are found
  - Error message: "No line-numbered rules found matching pattern 'Line XXXX –'. The source HTML structure may have changed."

- [ ] Unit tests are created in `tests/unit/test_classic_parser.py` with a dedicated HTML fixture at `tests/fixtures/classic_parser_test.html` covering:
  1. **Standard line item**: `<h3>Line 8523 – ...</h3>` + single `<p>`
  2. **Line with single icon**: `<h3>` with `<img alt="business icon">` + content
  3. **Line with multiple icons**: `<h3>` with both business and fishing icons
  4. **Line with no icons**: `<h3>Line 8910 – ...</h3>` + content (applies_to list is empty)
  5. **Complex line item**: Multiple `<p>` tags + `<ul>` list + context fields extracted
  6. **Conceptual h3 without Line pattern**: Should be skipped (e.g., `<h3>Prepaid expenses</h3>`)
  7. **Context extraction**: Verify chapter, section, source_file, anchor_id are correctly extracted
  8. **Malformed line to skip**: `<h3>Line 9999 –</h3>` with no content
  9. **Extraneous HTML**: Content before/after main section to ensure parser ignores it

- [ ] Test cases verify all parsing behaviors:
  ```python
  def test_parses_standard_line_item_correctly()
  def test_extracts_applies_to_list_from_icons()
  def test_extracts_multiple_applies_to_values()  # business + fishing
  def test_handles_missing_icons_gracefully()  # applies_to = []
  def test_parses_line_with_multiple_paragraphs_and_list()
  def test_skips_conceptual_h3_without_line_pattern()
  def test_extracts_context_fields_correctly()  # chapter, section, source_file, anchor_id
  def test_skips_malformed_line_and_logs_warning()
  def test_raises_parser_error_when_no_line_items_found()
  def test_raises_parser_error_on_invalid_file_path()
  ```

**Dependency**: TICKET 1
**Enables**: TICKET 4

**Design Rationale**:
- **Line pattern matching**: Focus on form line items (80/20) - delivers core value without extracting conceptual guidance
- **Regex-based filtering**: `Line \d+ –` pattern ensures we only extract rules that map to tax form fields
- **Icon mapping to applies_to**: Correct semantic meaning (income type) - multiple icons create list of applicable income types
- **Context extraction**: Chapter/section fields enable RAG navigation; source_file/anchor_id aid debugging
- **File-based input**: `parse(html_path)` simplifies I/O handling and testing; consistent with LLM parser signature
- **Graceful degradation**: Skipping malformed line items (not crashing) allows partial extraction
- **source_expert=CLASSIC**: Critical for TICKET 4's adjudicator to track rule provenance and resolve conflicts
- **Comprehensive test coverage**: 10 test scenarios cover line pattern matching, icon extraction, context fields, and error cases
- **Logging warnings**: Provides visibility into parsing issues without failing the entire pipeline

---

## TICKET 3: Implement Text-Based LLM Parser Module

**Scope**: Create the second, more advanced "expert." This expert uses a text-based LLM (Gemini Flash/Pro) to parse HTML content, making it resilient to structural changes through semantic understanding. Uses BeautifulSoup to extract the `<main>` content and sends it to the LLM for intelligent extraction.

### Acceptance Criteria

- [ ] A new module, `scripts/parser/llm_parser.py`, is created containing a `parse(html_path: str) -> list[ExtractedRule]` function with comprehensive docstring:
  ```python
  from bs4 import BeautifulSoup
  from scripts.parser.yaml_schema import ExtractedRule, ExpertSource, ApplicabilityType
  from scripts.parser.exceptions import ParserError
  from scripts.parser.settings import settings
  import google.generativeai as genai
  import logging
  import json
  from pathlib import Path

  logger = logging.getLogger(__name__)

  def parse(html_path: str) -> list[ExtractedRule]:
      """
      Parses HTML file using text-based LLM to extract line-numbered expense rules.

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
  ```

- [ ] The function reads the HTML file from disk and uses `BeautifulSoup` to extract only the `<main>` tag content. This reduces token usage and focuses the LLM on core content (removes headers, footers, navigation).

- [ ] A structured prompt constant `EXTRACTION_PROMPT` is defined in the module:
  ```python
  EXTRACTION_PROMPT = """You are an expert data extraction agent specializing in Canadian tax law documents. You will be given HTML from a CRA (Canada Revenue Agency) guide on business expenses.

Your task is to identify and extract every line-numbered expense rule within the provided HTML.

- A rule starts with an `<h3>` tag containing a line number (e.g., "Line 8523 – Meals and entertainment").
- Extract ONLY rules matching the pattern "Line XXXX –" where XXXX is a number.
- SKIP h3 tags without this pattern (e.g., "Prepaid expenses").
- The content follows in `<p>`, `<ul>`, and `<ol>` tags until the next `<h3>`.
- Look for `<img>` tags within the h3 header. Their `alt` attribute indicates applicability:
  - "business icon" → "business"
  - "farm icon" → "farming"
  - "fish icon" → "fishing"
  - Multiple icons mean the rule applies to multiple income types.

Respond ONLY with a single JSON object. Do not include explanatory text, markdown, or other content.

Root object format:
{
  "rules": [
    {
      "rule_number": <integer>,
      "title": "<string>",
      "content": "<string>",
      "applies_to": [<list of strings: "business", "farming", or "fishing">],
      "source_citation": "<string>",
      "chapter": "<string>",
      "section": "<string or null>",
      "anchor_id": "<string or null>"
    }
  ]
}

Field instructions:
- rule_number: Extract only the integer (e.g., "Line 8523" → 8523)
- title: Text after the dash (e.g., "Meals and entertainment")
- applies_to: List of income types from icon alt text. Empty list if no icons.
- chapter: Extract from h1 tag (e.g., "Chapter 3 – Expenses")
- section: Extract from immediately preceding h2 tag (e.g., "Part 4 – Net income (loss) before adjustments"). Null if no h2 before the rule.
- anchor_id: Extract from the <a> tag id attribute within the h3 (e.g., "tocch3ln8523"). Null if not present.
"""
  ```

- [ ] The function sends the extracted `<main>` HTML content and the prompt to the Gemini model specified in `settings.llm_model_name`.

- [ ] The function robustly handles errors:
  - **API failures**: Catch `genai` exceptions, log error with details, raise `ParserError`
  - **JSON parsing errors**: Catch `json.JSONDecodeError`, log raw LLM response for debugging, raise `ParserError`
  - **Pydantic validation errors**: Catch `ValidationError`, log invalid data, raise `ParserError`
  - All errors include clear messages indicating the failure point

- [ ] The function parses the JSON response:
  - Extract the "rules" array from the response
  - For each rule dict, convert to `ExtractedRule` using Pydantic
  - Map `applies_to` strings to `ApplicabilityType` enum values
  - Add `source_file` from `html_path` (filename only)
  - Set `source_expert=ExpertSource.LLM`

- [ ] Unit tests are created in `tests/unit/test_llm_parser.py` mocking the Gemini client:
  1. **Valid response**: Mock returns proper JSON matching schema → verify correct ExtractedRule list
  2. **Multiple icons**: Mock response with rule having ["business", "fishing"] → verify applies_to list
  3. **No icons**: Mock response with empty applies_to list → verify empty list handling
  4. **Context fields**: Mock response includes chapter, section, anchor_id → verify all context fields
  5. **API error**: Mock raises genai exception → verify ParserError raised
  6. **Malformed JSON**: Mock returns invalid JSON → verify ParserError raised with logged response
  7. **Schema mismatch**: Mock returns JSON missing required fields → verify ValidationError caught, ParserError raised

- [ ] Test cases verify all behaviors:
  ```python
  @patch('google.generativeai.GenerativeModel')
  def test_parses_valid_llm_response(mock_genai)
  def test_extracts_multiple_applies_to_values()
  def test_handles_empty_applies_to_list()
  def test_extracts_all_context_fields()
  def test_raises_parser_error_on_api_failure()
  def test_raises_parser_error_on_malformed_json()
  def test_raises_parser_error_on_schema_validation_failure()
  def test_raises_parser_error_on_invalid_file_path()
  ```

**Dependency**: TICKET 1
**Enables**: TICKET 4

**Design Rationale**:
- **Text-based LLM**: Massive simplification vs multimodal - no browser, no screenshots, no image processing
- **BeautifulSoup pre-processing**: Extracting `<main>` tag reduces tokens and focuses LLM on relevant content
- **Structured prompt**: Clear instructions with JSON schema ensure consistent, parsable output
- **Same extraction scope**: Only "Line XXXX –" rules, matching classic parser for easy adjudication
- **Error handling**: Comprehensive error handling with logging aids debugging without exposing raw errors to orchestrator
- **Context extraction**: LLM can semantically understand document structure to extract chapter/section
- **Testing strategy**: Mock Gemini client only - no browser automation complexity
- **Consistency**: `parse(html_path)` signature matches classic parser for clean orchestrator design

---

## TICKET 4: Implement Grounded Adjudication & Self-Correction Module

**Scope**: Create the core intelligence of the pipeline. This module merges the results from the two expert parsers, identifies conflicts, and uses a grounded LLM call to resolve them, providing a full audit trail.

### Acceptance Criteria

#### 1. Module Structure

- [ ] A new module, `scripts/parser/adjudicator.py`, is created.
- [ ] It contains a function with signature: `adjudicate(classic_rules: list[ExtractedRule], llm_rules: list[ExtractedRule], source_html_content: str) -> list[ExtractedRule]`.
- [ ] The function uses `logger = logging.getLogger(__name__)` for audit trail logging.
- [ ] All ExtractedRule objects returned have `source_expert` set to `ADJUDICATED` for corrected rules, or original value preserved for perfect matches.

#### 2. Triage Algorithm

- [ ] The function aligns rules from both lists by `rule_number` (the unique identifier).
- [ ] A helper function `_normalize_for_comparison(rule: ExtractedRule) -> dict` normalizes fields for comparison:
  - Strip leading/trailing whitespace from `title` and `content`
  - Normalize consecutive whitespace to single space in `content`
  - Sort `applies_to` list alphabetically
  - Compare only: `title`, `content`, `applies_to` (ignore context fields like chapter, section)
- [ ] Rules are triaged into three categories:
  - **Perfect Match**: `rule_number` exists in both lists AND normalized comparison is identical → Accept classic parser version (trust deterministic parser)
  - **Conflict**: `rule_number` exists in both lists BUT normalized comparison differs → Send to LLM adjudicator
  - **Orphan**: `rule_number` exists in only one list → Send to LLM adjudicator
- [ ] Triage results are logged: `logger.info(f"Triage complete: {perfect_matches} perfect matches, {conflicts} conflicts, {orphans} orphans")`

#### 3. Grounding Prompt Design

- [ ] A prompt template constant `ADJUDICATION_PROMPT` is defined in the module with this structure:

```python
ADJUDICATION_PROMPT = """You are an expert adjudicator for a Canadian tax law data extraction pipeline. Two parsers (classic rule-based and LLM semantic) have extracted expense rules from CRA HTML documents, and you must resolve discrepancies.

You will be given:
1. The full HTML content from the source document
2. Details about the discrepancy (conflict or orphan)

Your task is to determine the CORRECT extraction by examining the source HTML evidence.

CRITICAL REQUIREMENTS:
- Base your decision ONLY on evidence from the provided HTML
- Provide an exact quote (citation) from the HTML that supports your decision
- Explain your reasoning step-by-step
- If you cannot find sufficient evidence, say so explicitly

Respond ONLY with a single JSON object (no markdown, no explanatory text):

{
  "analysis": "<Brief 1-2 sentence explanation of what discrepancy you found>",
  "reasoning": "<Step-by-step explanation of how you analyzed the HTML to resolve it>",
  "citation": "<Exact quote from the HTML that justifies your decision>",
  "corrected_rule": {
    "rule_number": <integer>,
    "title": "<string>",
    "content": "<string>",
    "applies_to": [<list of strings: 'business', 'farming', or 'fishing'>],
    "source_citation": "<string>",
    "chapter": "<string>",
    "section": "<string or null>",
    "source_file": "<string>",
    "anchor_id": "<string or null>"
  }
}

If you cannot resolve the discrepancy with confidence, set "analysis" to start with "INSUFFICIENT_EVIDENCE:" and explain why.
"""
```

- [ ] For each conflict/orphan, the prompt includes:
  - The full `source_html_content` (entire `<main>` tag from source file)
  - Discrepancy type: "CONFLICT" or "ORPHAN"
  - If CONFLICT: Both classic and LLM versions with diff summary
  - If ORPHAN: Which parser found it, the rule details
  - Token budget: If `source_html_content` exceeds 100K tokens, truncate with note and include only relevant section around the rule's anchor_id

#### 4. LLM Adjudication Implementation

- [ ] For each conflict/orphan, make a synchronous call to `settings.adjudicator_model_name` (Gemini Pro)
- [ ] API calls are sequential (not batched) for robustness - acceptable performance trade-off for correctness
- [ ] Comprehensive error handling:
  - **API Failures**: Catch `genai` exceptions, log error with full context, append to manual review
  - **Rate Limiting**: Catch 429 errors, log warning, append to manual review (don't retry - fail gracefully)
  - **Timeouts**: Set 30-second timeout, catch timeout exceptions, append to manual review
  - **JSON Parse Errors**: Catch `json.JSONDecodeError`, log raw LLM response, append to manual review
  - **Pydantic Validation Errors**: Catch `ValidationError` on corrected_rule, log invalid data, append to manual review
  - **Insufficient Evidence**: If response["analysis"] starts with "INSUFFICIENT_EVIDENCE:", log warning, append to manual review
- [ ] For each successful adjudication:
  - Log audit trail: `logger.info(f"Adjudicated rule {rule_number}: {analysis}", extra={"reasoning": reasoning, "citation": citation})`
  - Create new ExtractedRule from `corrected_rule` dict
  - Set `source_expert=ExpertSource.ADJUDICATED`
  - Add to final output list

#### 5. Manual Review File Generation

- [ ] Failed adjudications are written to `manual_review.yml` in YAML format
- [ ] File structure:
```yaml
# Manual Review Required - Generated by Adjudicator
# Review these cases and manually add corrected rules to the final YAML

- rule_number: 8523
  discrepancy_type: CONFLICT
  classic_version:
    title: "Meals and entertainment"
    content: "..."
    applies_to: ["business", "fishing"]
  llm_version:
    title: "Meals & entertainment"
    content: "..."
    applies_to: ["business"]
  failure_reason: "LLM returned INSUFFICIENT_EVIDENCE: Icon extraction ambiguous"
  source_file: "t4002-5.html"
  timestamp: "2025-10-16T10:30:00Z"

- rule_number: 9270
  discrepancy_type: ORPHAN
  found_by: LLM
  rule_data:
    title: "Professional fees"
    content: "..."
  failure_reason: "API timeout after 30s"
  source_file: "t4002-4.html"
  timestamp: "2025-10-16T10:30:05Z"
```
- [ ] If `manual_review.yml` already exists, append (don't overwrite)
- [ ] Log manual review file write: `logger.warning(f"Added {count} rules to manual_review.yml for human inspection")`

#### 6. Output and Validation

- [ ] The function returns a single, clean `list[ExtractedRule]` containing:
  - All perfect matches (from classic parser)
  - All successfully adjudicated conflicts/orphans (with source_expert=ADJUDICATED)
  - Manual review cases are NOT included in output (must be resolved by human)
- [ ] Output list is sorted by `rule_number` ascending
- [ ] Function logs final summary: `logger.info(f"Adjudication complete: {total} rules in output, {manual_review_count} sent for manual review")`

#### 7. Testing Strategy

- [ ] Unit tests are created in `tests/unit/test_adjudicator.py` with mocked Gemini client:

  1. **Perfect match scenario**: Both parsers return identical normalized rules → Accept classic version, no LLM call
  2. **Simple conflict - title mismatch**: rule_number matches, title differs → LLM adjudication succeeds
  3. **Conflict - applies_to mismatch**: Classic has ["business"], LLM has ["business", "fishing"] → LLM resolves with citation
  4. **Orphan - missing in classic**: LLM found rule, classic didn't → LLM validates it exists in HTML
  5. **Orphan - missing in LLM**: Classic found rule, LLM didn't → LLM validates classic extraction
  6. **LLM adjudication success**: Mock returns valid JSON → Verify corrected_rule created with source_expert=ADJUDICATED
  7. **LLM returns INSUFFICIENT_EVIDENCE**: Mock returns analysis starting with "INSUFFICIENT_EVIDENCE:" → Added to manual review
  8. **API failure**: Mock raises genai exception → Added to manual review, exception logged
  9. **Invalid JSON response**: Mock returns malformed JSON → Added to manual review, raw response logged
  10. **Pydantic validation failure**: Mock returns JSON with invalid rule_number (string instead of int) → Added to manual review

- [ ] Test cases verify audit trail logging using `caplog` fixture
- [ ] Test cases verify manual_review.yml structure matches specification

#### 8. Error Messages and Logging

- [ ] All log messages use consistent format: `[Adjudicator] <message>`
- [ ] INFO level: Triage results, successful adjudications, final summary
- [ ] WARNING level: Manual review additions, rate limit warnings
- [ ] ERROR level: API failures, validation failures
- [ ] Structured logging: Use `extra={}` parameter to attach metadata (reasoning, citation, rule_number)

**Dependency**: TICKET 2, TICKET 3
**Enables**: TICKET 5

**Design Rationale**:
- **Sequential API calls**: Prioritizes robustness over speed - acceptable for initial implementation
- **Trust classic on perfect match**: Deterministic parser is source of truth when both agree
- **Full HTML context**: Provides complete grounding for LLM decisions
- **Fail gracefully**: All error paths lead to manual review, not pipeline crash
- **Audit trail**: Structured logging enables debugging and compliance verification
- **Human-in-the-loop**: Manual review file ensures no data is silently dropped
- **80/20 alignment**: This is the core intelligence (20%) that ensures quality (80% of value)

---

## TICKET 5: Implement YAML Generation and Verification Module

**Scope**: Create the final artifact generation step, which takes the validated list of rules and writes it to a persistent, schema-compliant YAML file. This module strips internal pipeline metadata, formats output for readability, and performs read-back verification to ensure integrity.

### Acceptance Criteria

#### 1. Module Structure

- [ ] A new module, `scripts/generate_yaml.py`, is created.
- [ ] It contains a function with signature: `generate(rules: list[ExtractedRule], output_path: str) -> None`.
- [ ] The function uses `logger = logging.getLogger(__name__)` for structured logging.
- [ ] All exceptions are wrapped in `YAMLGenerationError` (from TICKET 1) for consistent error handling.

#### 2. Data Stripping (Critical)

- [ ] **Internal metadata fields MUST be excluded** from the final YAML output:
  - `source_expert`: Pipeline tracking field (which expert generated the rule)
  - `anchor_id`: Debugging field (HTML anchor ID)
- [ ] Use Pydantic's `model_dump(exclude={"source_expert", "anchor_id"})` to strip these fields.
- [ ] A constant `_INTERNAL_METADATA_FIELDS = {"source_expert", "anchor_id"}` is defined in the module.
- [ ] The cleaned rule data is wrapped in a `RuleSet` object before serialization.

#### 3. YAML Serialization

- [ ] The function uses `PyYAML` to serialize the `RuleSet` object with the following formatting parameters:
  ```python
  yaml.dump(
      rule_set.model_dump(),
      sort_keys=False,          # Preserve Pydantic field order
      default_flow_style=False, # Block style for readability
      allow_unicode=True,       # Handle special characters
  )
  ```
- [ ] The output file's parent directories are created if they don't exist (`Path.mkdir(parents=True, exist_ok=True)`).
- [ ] The YAML content is written to the specified `output_path` with UTF-8 encoding.

#### 4. Error Handling

- [ ] The function handles all error conditions and re-raises them as `YAMLGenerationError`:
  - **Pydantic ValidationError**: If input rules are invalid before serialization
  - **yaml.YAMLError**: If serialization fails
  - **IOError / PermissionError**: If file write fails due to permissions or I/O errors
  - **FileNotFoundError**: If file disappears during verification (race condition)
  - **ValidationError**: If read-back verification detects corruption or schema mismatch
- [ ] Each error handler logs the full exception context using `logger.error(..., exc_info=True)`.
- [ ] Error messages are clear and actionable (e.g., "Permission denied writing to /path/to/file").

#### 5. Read-Back Verification

- [ ] After writing the file, the function immediately reads it back from disk.
- [ ] The read-back data is parsed with `yaml.safe_load()`.
- [ ] The parsed data is validated against the `RuleSet` Pydantic model using `RuleSet.model_validate(read_back_data)`.
- [ ] If verification succeeds, log: `logger.info("YAML verification successful: file integrity confirmed.")`
- [ ] If verification fails, raise `YAMLGenerationError` with details about the corruption or schema mismatch.

#### 6. Logging

- [ ] Log messages use consistent format: `[YAMLGenerator] <message>`
- [ ] INFO level: Generation start (with rule count), successful write, successful verification
- [ ] ERROR level: All failure conditions with full exception context
- [ ] Example log flow:
  ```
  [INFO] Starting YAML generation for 127 rules...
  [INFO] Successfully wrote YAML file to /data/cra_rules.yml
  [INFO] YAML verification successful: file integrity confirmed.
  ```

#### 7. Testing Strategy

- [ ] Unit tests are created in `tests/unit/test_generate_yaml.py` using `pyfakefs` for filesystem isolation:
  1. **Happy path**: Valid rules → valid file with correct content
  2. **Metadata stripping**: Verify `source_expert` and `anchor_id` are NOT in output YAML
  3. **Empty rules list**: Empty list produces valid YAML with `rules: []`
  4. **Write permission denied**: Raises `YAMLGenerationError` with clear message
  5. **Verification detects corruption**: Simulated corrupted file triggers error
  6. **File disappears during verification**: Race condition handled gracefully

- [ ] Test cases verify all behaviors:
  ```python
  def test_generate_success_and_verification_passes(fs)
  def test_generate_strips_internal_metadata(fs)
  def test_generate_with_empty_rules_list(fs)
  def test_raise_error_on_write_permission_denied(fs)
  def test_raise_error_on_verification_failure_corrupt_file(fs, monkeypatch)
  def test_raise_error_on_verification_failure_file_disappears(fs, monkeypatch)
  ```

#### 8. Integration Points

- [ ] **Input from TICKET 4**: Receives `list[ExtractedRule]` from adjudicator's output
- [ ] **Output to TICKET 6**: Provides clean interface for orchestrator:
  ```python
  try:
      generate(rules=final_rules, output_path=str(output_yaml))
      print("✅ Pipeline complete")
  except YAMLGenerationError as e:
      print(f"❌ Generation failed: {e}")
      exit(1)
  ```

**Dependency**: TICKET 4 (adjudicator outputs validated rules)
**Enables**: TICKET 6 (orchestrator needs this to finalize pipeline)

**Design Rationale**:
- **Data stripping**: Prevents internal pipeline metadata from leaking into final artifact
- **Read-back verification**: Guards against silent corruption from disk errors or incomplete writes
- **Comprehensive error handling**: Single exception type (`YAMLGenerationError`) simplifies orchestrator error handling
- **YAML formatting**: Block-style output with preserved field order ensures human readability
- **80/20 testing**: Six test cases cover all critical paths without over-engineering
- **YAGNI compliance**: No custom YAML representers, no complex formatting logic - uses PyYAML defaults with minimal configuration

---

## TICKET 6: Create Pipeline Orchestration Script

**Scope**: Create the user-facing command-line interface (CLI) that connects all the independent modules into a single, cohesive, and easy-to-run process. This orchestrator follows the 80/20 principle: focus on robust directory processing with graceful error handling, avoiding feature creep.

### Architectural Decisions

#### 1. File Location and Naming

- **File**: `scripts/extract_rules.py` (separate from existing `scripts/cli.py` for RAG indexing)
- **Rationale**: Clear separation of concerns - the RAG indexing pipeline and HTML-to-YAML extraction pipeline are fundamentally different workflows with different dependencies, configurations, and evolution paths. A dedicated script prevents coupling and aligns with "simplicity over cleverness" principle.

#### 2. CLI Interface Design

**Primary command signature**:
```bash
uv run extract-rules INPUT_PATH OUTPUT_YAML [OPTIONS]
```

**Arguments**:
- `input_path`: Path to HTML file or directory of HTML files (required, positional)
- `output_yaml`: Path for output YAML file with extracted rules (required, positional)

**Options**:
- `--manual-review-file, -m`: Path for YAML file with items requiring manual review (default: `manual_review.yml`)
- `--verbose, -v`: Enable verbose logging for debugging

**Input flexibility**: Support both single file and directory processing
- Primary use case: Directory of HTML files (`cra_documents/cra_t4002e_rev24_dump/`)
- Also supported: Single file processing for targeted extraction
- Implementation: Use `pathlib.Path.is_dir()` and `Path.is_file()` to detect input type

#### 3. Error Handling Strategy (Layered Approach)

Following the 80/20 principle: implement robust error handling without over-engineering recovery mechanisms.

**Layer 1: Pre-flight Checks (Fail Fast)**
- Validate `input_path` exists and is readable
- Verify `output_yaml` parent directory is writable
- Create output directories if needed
- Exit with clear error message and non-zero code if any check fails

**Layer 2: Per-File Processing (Fail Gracefully)**
- Wrap each file's processing in `try...except` blocks
- On error: log filename and error, add to `failed_files` list, continue to next file
- Collect statistics for summary report (perfect matches, auto-corrected, manual review)
- Don't let one bad file crash the entire batch

**Layer 3: Top-Level Handler**
- Catch catastrophic errors outside the file loop (e.g., output file write failures)
- Always produce a summary report, even on partial failure
- Exit with code 1 if any files failed, code 0 if all succeeded

#### 4. Summary Report Format

**Design**: Concise, text-based report with Rich formatting for colored output and clear visual hierarchy.

**Key metrics**:
- Files processed vs. total files
- Total rules extracted
- Adjudication breakdown: Perfect Matches (count, %), Auto-corrected (count, %), Manual Review (count, %)
- Output file paths
- Files with errors (count and list)

**Example output**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CRA Rule Extraction Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files Processed: 15 / 15
Total Rules Extracted: 247

Adjudication Breakdown:
  ✓ Perfect Matches:    210 (85%)
  ⚡ Auto-corrected:     31 (13%)
  ⚠️  Manual Review:      6 (2%)

Outputs:
  📄 Ruleset: output/cra_rules.yml
  ⚠️  Manual Review: output/manual_review.yml (6 items)

Errors: 0 files failed
```

#### 5. Manual Review File Handling

- Treat `manual_review.yml` as a first-class output of the pipeline
- Only create the file if manual review items exist (avoid clutter)
- Adjudicator returns two distinct lists: `resolved_rules` and `manual_review_items`
- Generate main YAML with `resolved_rules`
- Generate manual review YAML separately with `manual_review_items`
- Report in summary: presence of manual review file and item count

### Acceptance Criteria

#### 1. Module Structure and Imports

- [ ] New file `scripts/extract_rules.py` is created
- [ ] Uses `typer` for CLI framework (already in `[project.optional-dependencies.indexing]`)
- [ ] Uses `rich.console.Console` for formatted output
- [ ] Uses `rich.progress.track()` for progress bar during file processing
- [ ] Imports pipeline modules from TICKETS 1-5:
  ```python
  from parser.classic_parser import parse as classic_parse
  from parser.llm_parser import parse as llm_parse
  from parser.adjudicator import adjudicate
  from parser.generate_yaml import generate as generate_yaml
  from parser.exceptions import PipelineError
  ```
- [ ] Configures structured logging with `logging.basicConfig()`

#### 2. Main Command Implementation

- [ ] A typer app is initialized: `app = typer.Typer(help="HTML-to-YAML rule extraction pipeline for CRA T4002 documents.")`
- [ ] A `run()` command is defined with signature:
  ```python
  @app.command()
  def run(
      input_path: Annotated[Path, typer.Argument(...)],
      output_yaml: Annotated[Path, typer.Argument(...)],
      manual_review_yaml: Annotated[Path, typer.Option("--manual-review-file", "-m")] = Path("manual_review.yml"),
      verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
  ) -> None:
  ```
- [ ] Comprehensive docstring with usage examples

#### 3. Input Resolution Logic

- [ ] Check if `input_path.is_dir()` or `input_path.is_file()`
- [ ] If directory: collect all `*.html` files with `sorted(input_path.glob("*.html"))`
- [ ] If file: create single-item list `[input_path]`
- [ ] Exit with error if directory contains no HTML files
- [ ] Log number of files found

#### 4. Pre-flight Checks

- [ ] Validate input path exists (handled by typer's `exists=True`)
- [ ] Create output directory: `output_yaml.parent.mkdir(parents=True, exist_ok=True)`
- [ ] Create manual review directory: `manual_review_yaml.parent.mkdir(parents=True, exist_ok=True)`
- [ ] Test write permissions by creating and deleting a test file
- [ ] Exit with clear error message on permission errors

#### 5. Main Processing Loop

- [ ] Initialize collectors:
  - `all_resolved_rules: list[ExtractedRule] = []`
  - `all_manual_review_items: list = []`
  - `failed_files: list[tuple[str, str]] = []`
  - `stats: dict = {"total_rules": 0, "perfect_matches": 0, "auto_corrected": 0, "manual_review": 0}`

- [ ] For each HTML file (with progress bar using `rich.progress.track()`):
  - Read HTML content: `html_content = html_file.read_text(encoding="utf-8")`
  - Call classic parser: `classic_rules = classic_parse(str(html_file))`
  - Call LLM parser: `llm_rules = llm_parse(str(html_file))`
  - Call adjudicator: `resolved_rules, manual_items, file_stats = adjudicate(classic_rules, llm_rules, html_content)`
  - Accumulate results: extend `all_resolved_rules` and `all_manual_review_items`
  - Update statistics: add `file_stats` counts to `stats`

- [ ] Error handling per file:
  - Catch `PipelineError` (expected pipeline errors): log, add to `failed_files`, continue
  - Catch `Exception` (unexpected errors): log with `logger.exception()`, add to `failed_files`, continue
  - If `verbose`, print warning to console with filename and error

#### 6. YAML Output Generation

- [ ] Generate main ruleset:
  ```python
  generate_yaml(rules=all_resolved_rules, output_path=str(output_yaml))
  ```
- [ ] Generate manual review YAML only if items exist:
  ```python
  if all_manual_review_items:
      generate_yaml(rules=all_manual_review_items, output_path=str(manual_review_yaml))
  ```
- [ ] Catch `PipelineError` and exit with code 1 on generation failure
- [ ] Log each successful generation

#### 7. Summary Report

- [ ] Print formatted report using `rich.console.Console`:
  - Separator line (`━` * 60)
  - Header: "CRA Rule Extraction Complete"
  - Files processed: `{processed} / {total}`
  - Failed files count (with list if `verbose`)
  - Total rules extracted
  - Adjudication breakdown with counts and percentages
  - Output file paths
  - Manual review status (file path and item count if exists)

- [ ] Exit with appropriate code:
  - `raise typer.Exit(code=0)` if no failed files
  - `raise typer.Exit(code=1)` if any files failed

#### 8. pyproject.toml Registration

- [ ] Add new section to `pyproject.toml`:
  ```toml
  [project.scripts]
  extract-rules = "scripts.extract_rules:app"
  ```
- [ ] Verify script can be invoked: `uv run extract-rules --help`

#### 9. Integration Testing

- [ ] Test single file processing:
  ```bash
  uv run extract-rules cra_documents/cra_t4002e_rev24_dump/t4002-5.html test_output.yml
  ```
- [ ] Test directory processing:
  ```bash
  uv run extract-rules cra_documents/cra_t4002e_rev24_dump/ output/cra_rules.yml
  ```
- [ ] Test error handling:
  - Non-existent input path
  - Read-only output directory
  - Empty directory
- [ ] Verify YAML outputs are valid and match `RuleSet` schema
- [ ] Verify summary report shows accurate counts

#### 10. Documentation

- [ ] Command includes comprehensive docstring with:
  - Description of MoE approach and grounded adjudication
  - Usage examples for both single file and directory
  - Explanation of manual review output
- [ ] Help text is clear: `uv run extract-rules --help` shows all options

**Dependency**: TICKET 5 (YAML generator), TICKET 4 (adjudicator), TICKET 3 (LLM parser), TICKET 2 (classic parser), TICKET 1 (schemas and exceptions)
**Enables**: End-to-end execution of the HTML-to-YAML pipeline with single command

### Design Rationale

- **Separate script**: Avoids coupling with RAG indexing pipeline, follows single responsibility principle
- **Directory as primary use case**: Aligns with 80/20 - most common scenario is batch processing all HTML files
- **Layered error handling**: Balances robustness (don't crash) with simplicity (don't over-engineer recovery)
- **Rich formatting**: Provides professional CLI experience without external dependencies (Rich already used in existing CLI)
- **Manual review as first-class output**: Transparency - failed adjudications are visible, not silently dropped
- **No feature creep**: No retry logic, no parallel processing, no resume-from-checkpoint - deliver core value first
- **Follows existing patterns**: Matches structure and style of `scripts/cli.py` for consistency
