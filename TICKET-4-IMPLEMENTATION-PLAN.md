# TICKET 4 Implementation Plan: Grounded Adjudication & Self-Correction Module

## Overview
Implement `src/qe_tax_rag/extraction/ca/adjudicator.py` to merge results from classic and LLM parsers, identify conflicts, and use Gemini Pro to resolve discrepancies with full audit trail.

**Implementation Approach**: Test-Driven Development (TDD) with frequent, atomic commits

## Key Design Decisions (from Zen Consultation)

### 1. Refined Function Signature
**Change from original plan**: Return tuple instead of just list[ExtractedRule]
```python
def adjudicate(
    classic_rules: list[ExtractedRule],
    llm_rules: list[ExtractedRule],
    source_html_content: str,
    source_file: str,  # Added for ManualReviewItem
) -> tuple[list[ExtractedRule], list[ManualReviewItem], dict[str, int]]
```
**Rationale**: Aligns with TICKET 6 orchestrator expectations (line 849 in html-to-yaml-plan.md)

### 2. Data Structures
**Introduce two helper structures:**
- `TriageResult` (NamedTuple): Clean separation of triage outputs
- `ManualReviewItem` (Pydantic model): Ensures consistent YAML format

### 3. Module Decomposition
Break into testable units:
- `_triage_rules()`: Categorize rules into perfect/conflict/orphan
- `_normalize_rule_for_comparison()`: Normalize for comparison
- `_adjudicate_item_with_llm()`: Single adjudication with error handling
- `_build_adjudication_prompt()`: Construct grounded prompt
- `_truncate_html_for_prompt()`: Context-aware HTML truncation

### 4. Performance Strategy
**Sequential API calls** (not parallel/batched):
- Robustness > speed for data quality pipeline
- Expected low volume (10-20% discrepancies = ~20 calls)
- Easier error attribution and audit trail
- No premature optimization (YAGNI principle)

### 5. Critical Field Names (VERIFIED in schema.py)
- Use `expert_source` (NOT `source_expert`) - line 56 in schema.py
- Set `confidence_score=0.95` for adjudicated rules (classic parser=1.0)

---

## TDD Implementation Workflow

### Phase 1: Data Structures & Normalization (TDD)

#### Step 1.1: Write tests for normalization function
**File**: `tests/unit/test_adjudicator.py`

**Tests to write**:
```python
def test_normalize_rule_strips_whitespace_from_title()
def test_normalize_rule_collapses_whitespace_in_content()
def test_normalize_rule_sorts_applies_to_list()
def test_normalize_rule_handles_empty_applies_to()
```

**Commit**: `test: add normalization tests for adjudicator`

#### Step 1.2: Implement normalization function
**File**: `src/qe_tax_rag/extraction/ca/adjudicator.py`

**Implementation**:
```python
def _normalize_rule_for_comparison(rule: ExtractedRule) -> dict:
    """Normalizes a rule for comparison."""
    normalized_content = re.sub(r'\s+', ' ', rule.content).strip()
    return {
        "title": rule.title.strip(),
        "content": normalized_content,
        "applies_to": sorted([item.value for item in rule.applies_to])
    }
```

**Run tests**: `uv run pytest tests/unit/test_adjudicator.py -v -k normalize`

**Commit**: `feat: implement rule normalization for adjudicator`

#### Step 1.3: Write tests for data structures
**Tests to write**:
```python
def test_triage_result_structure()
def test_manual_review_item_required_fields()
def test_manual_review_item_for_conflict()
def test_manual_review_item_for_orphan()
```

**Commit**: `test: add data structure tests for adjudicator`

#### Step 1.4: Implement data structures
**Implementation**:
```python
class TriageResult(NamedTuple):
    perfect_matches: list[ExtractedRule]
    conflicts: list[tuple[ExtractedRule, ExtractedRule]]
    orphans: list[ExtractedRule]

class ManualReviewItem(BaseModel):
    rule_number: int
    discrepancy_type: str  # "CONFLICT" or "ORPHAN"
    failure_reason: str
    source_file: str
    timestamp: str
    classic_version: dict | None = None
    llm_version: dict | None = None
    orphan_version: dict | None = None
    found_by: str | None = None
```

**Run tests**: `uv run pytest tests/unit/test_adjudicator.py -v -k "data_structure"`

**Commit**: `feat: add TriageResult and ManualReviewItem data structures`

---

### Phase 2: Triage Logic (TDD)

#### Step 2.1: Write tests for triage function
**Tests to write**:
```python
def test_triage_perfect_match_identical_rules()
def test_triage_perfect_match_prefers_classic_parser()
def test_triage_conflict_when_title_differs()
def test_triage_conflict_when_content_differs()
def test_triage_conflict_when_applies_to_differs()
def test_triage_orphan_classic_only()
def test_triage_orphan_llm_only()
def test_triage_multiple_orphans_from_both_parsers()
def test_triage_empty_input_lists()
def test_triage_logs_summary_correctly()
```

**Commit**: `test: add comprehensive triage logic tests`

#### Step 2.2: Implement triage function
**Implementation**:
```python
def _triage_rules(
    classic_rules: list[ExtractedRule],
    llm_rules: list[ExtractedRule]
) -> TriageResult:
    """Categorizes rules into perfect matches, conflicts, and orphans."""
    logger.info("[Adjudicator] Starting triage...")

    # Create lookup dictionaries
    classic_map = {r.rule_number: r for r in classic_rules}
    llm_map = {r.rule_number: r for r in llm_rules}

    # Find all rule numbers
    all_rule_numbers = set(classic_map.keys()) | set(llm_map.keys())

    perfect_matches: list[ExtractedRule] = []
    conflicts: list[tuple[ExtractedRule, ExtractedRule]] = []
    orphans: list[ExtractedRule] = []

    for rule_number in all_rule_numbers:
        classic_rule = classic_map.get(rule_number)
        llm_rule = llm_map.get(rule_number)

        if classic_rule and llm_rule:
            # Both parsers found this rule - compare normalized versions
            classic_normalized = _normalize_rule_for_comparison(classic_rule)
            llm_normalized = _normalize_rule_for_comparison(llm_rule)

            if classic_normalized == llm_normalized:
                # Perfect match - trust classic parser
                perfect_matches.append(classic_rule)
            else:
                # Conflict detected
                conflicts.append((classic_rule, llm_rule))
        else:
            # Orphan - only one parser found this rule
            orphan_rule = classic_rule or llm_rule
            if orphan_rule:
                orphans.append(orphan_rule)

    logger.info(
        f"[Adjudicator] Triage complete: {len(perfect_matches)} perfect matches, "
        f"{len(conflicts)} conflicts, {len(orphans)} orphans"
    )

    return TriageResult(
        perfect_matches=perfect_matches,
        conflicts=conflicts,
        orphans=orphans
    )
```

**Run tests**: `uv run pytest tests/unit/test_adjudicator.py -v -k triage`

**Commit**: `feat: implement triage logic for rule categorization`

---

### Phase 3: HTML Truncation (TDD)

#### Step 3.1: Write tests for HTML truncation
**Tests to write**:
```python
def test_truncate_html_no_truncation_for_small_content()
def test_truncate_html_with_anchor_id_extracts_context()
def test_truncate_html_without_anchor_id_takes_first_and_last()
def test_truncate_html_handles_missing_anchor_id()
def test_truncate_html_includes_truncation_warning()
```

**Commit**: `test: add HTML truncation tests for adjudicator`

#### Step 3.2: Implement HTML truncation function
**Implementation**:
```python
def _truncate_html_for_prompt(
    html_content: str,
    anchor_id: str | None
) -> str:
    """Truncates HTML content if needed, preserving context around anchor_id."""
    # Safe character limit (roughly <100k tokens)
    MAX_CHARS = 300_000
    CONTEXT_WINDOW_CHARS = 150_000

    if len(html_content) <= MAX_CHARS:
        return html_content

    if anchor_id:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            target_tag = soup.find(id=anchor_id)

            if target_tag:
                # Find parent h3
                h3_tag = target_tag.find_parent('h3')
                if h3_tag:
                    # Extract contextual window
                    context_parts = []

                    # Go back 2-3 siblings or until h2
                    prev_count = 0
                    for prev_sibling in h3_tag.previous_siblings:
                        if prev_sibling.name in ['h2', 'h3'] and prev_count >= 1:
                            break
                        if prev_sibling.name:
                            context_parts.insert(0, str(prev_sibling))
                            prev_count += 1
                        if prev_count >= 3:
                            break

                    # Add the target h3
                    context_parts.append(str(h3_tag))

                    # Go forward until next h3
                    for next_sibling in h3_tag.next_siblings:
                        if next_sibling.name == 'h3':
                            break
                        if next_sibling.name:
                            context_parts.append(str(next_sibling))

                    truncated_content = '\n'.join(context_parts)
                    return (
                        "[...CONTENT TRUNCATED...]\n"
                        "The following is the most relevant section of the HTML "
                        "based on the rule's anchor ID.\n\n"
                        f"{truncated_content}"
                    )
        except Exception as e:
            logger.warning(f"[Adjudicator] Failed to extract context for anchor {anchor_id}: {e}")

    # Fallback: first and last chunks
    half_window = CONTEXT_WINDOW_CHARS // 2
    return (
        f"{html_content[:half_window]}\n\n"
        "[...CONTENT TRUNCATED - MIDDLE SECTION OMITTED...]\n\n"
        f"{html_content[-half_window:]}"
    )
```

**Run tests**: `uv run pytest tests/unit/test_adjudicator.py -v -k truncate`

**Commit**: `feat: implement context-aware HTML truncation`

---

### Phase 4: Adjudication Prompt (TDD)

#### Step 4.1: Write tests for prompt building
**Tests to write**:
```python
def test_build_prompt_for_conflict_includes_both_versions()
def test_build_prompt_for_orphan_includes_single_version()
def test_build_prompt_includes_structured_metadata()
def test_build_prompt_includes_full_html_content()
```

**Commit**: `test: add prompt building tests for adjudicator`

#### Step 4.2: Implement prompt building function
**Implementation**:
```python
ADJUDICATION_PROMPT_TEMPLATE = """You are an expert adjudicator for a Canadian tax law data extraction pipeline. Two parsers (classic rule-based and LLM semantic) have extracted expense rules from CRA HTML documents, and you must resolve discrepancies.

You will be given:
1. The full HTML content from the source document
2. Details about the discrepancy (conflict or orphan)

Your task is to determine the CORRECT extraction by examining the source HTML evidence.

CRITICAL REQUIREMENTS:
- Base your decision ONLY on evidence from the provided HTML
- Provide an exact quote (citation) from the HTML that supports your decision
- Explain your reasoning step-by-step
- If you cannot find sufficient evidence, say so explicitly

--- DISCREPANCY DETAILS ---
Discrepancy Type: {discrepancy_type}
Rule Number: {rule_number}
Source File: {source_file}
Anchor ID: {anchor_id}

{discrepancy_details}

--- FULL HTML SOURCE ---
{html_content}

Respond ONLY with a single JSON object (no markdown, no explanatory text):

{{
  "analysis": "<Brief 1-2 sentence explanation of what discrepancy you found>",
  "reasoning": "<Step-by-step explanation of how you analyzed the HTML to resolve it>",
  "citation": "<Exact quote from the HTML that justifies your decision>",
  "corrected_rule": {{
    "rule_number": <integer>,
    "title": "<string>",
    "content": "<string>",
    "applies_to": [<list of strings: 'business', 'farming', or 'fishing'>],
    "source_citation": "<string>",
    "chapter": "<string>",
    "section": "<string or null>",
    "source_file": "<string>",
    "anchor_id": "<string or null>"
  }}
}}

If you cannot resolve the discrepancy with confidence, set "analysis" to start with "INSUFFICIENT_EVIDENCE:" and explain why.
"""

def _build_adjudication_prompt(
    discrepancy_type: str,
    rule_number: int,
    source_file: str,
    anchor_id: str | None,
    html_content: str,
    classic_rule: ExtractedRule | None = None,
    llm_rule: ExtractedRule | None = None,
) -> str:
    """Builds a grounded adjudication prompt with structured details."""
    if discrepancy_type == "CONFLICT" and classic_rule and llm_rule:
        import yaml
        classic_yaml = yaml.dump(classic_rule.model_dump(exclude={'expert_source', 'confidence_score'}))
        llm_yaml = yaml.dump(llm_rule.model_dump(exclude={'expert_source', 'confidence_score'}))

        discrepancy_details = f"""A conflict was found for this rule. Here are the two versions.

[CLASSIC PARSER VERSION]
{classic_yaml}

[LLM PARSER VERSION]
{llm_yaml}"""
    else:  # ORPHAN
        orphan_rule = classic_rule or llm_rule
        found_by = "classic" if classic_rule else "llm"
        import yaml
        orphan_yaml = yaml.dump(orphan_rule.model_dump(exclude={'expert_source', 'confidence_score'}))

        discrepancy_details = f"""This rule was found only by the {found_by} parser. Please verify if it is a valid rule based on the HTML source.

[ORPHAN RULE DATA]
{orphan_yaml}"""

    return ADJUDICATION_PROMPT_TEMPLATE.format(
        discrepancy_type=discrepancy_type,
        rule_number=rule_number,
        source_file=source_file,
        anchor_id=anchor_id or "N/A",
        discrepancy_details=discrepancy_details,
        html_content=html_content,
    )
```

**Run tests**: `uv run pytest tests/unit/test_adjudicator.py -v -k prompt`

**Commit**: `feat: implement grounded adjudication prompt builder`

---

### Phase 5: LLM Adjudication with Error Handling (TDD)

#### Step 5.1: Write tests for LLM adjudication
**Tests to write**:
```python
@patch('google.generativeai.GenerativeModel')
def test_adjudicate_item_success_returns_extracted_rule(mock_genai)
def test_adjudicate_item_api_failure_returns_manual_review(mock_genai)
def test_adjudicate_item_timeout_returns_manual_review(mock_genai)
def test_adjudicate_item_bad_json_returns_manual_review(mock_genai)
def test_adjudicate_item_validation_error_returns_manual_review(mock_genai)
def test_adjudicate_item_insufficient_evidence_returns_manual_review(mock_genai)
def test_adjudicate_item_sets_expert_source_adjudicated(mock_genai)
def test_adjudicate_item_sets_confidence_score_095(mock_genai)
```

**Commit**: `test: add LLM adjudication tests with error scenarios`

#### Step 5.2: Implement LLM adjudication function
**Implementation**:
```python
def _adjudicate_item_with_llm(
    discrepancy_type: str,
    rule_number: int,
    source_file: str,
    html_content: str,
    classic_rule: ExtractedRule | None = None,
    llm_rule: ExtractedRule | None = None,
) -> ExtractedRule | ManualReviewItem:
    """Adjudicates a single conflict or orphan using Gemini Pro."""
    from datetime import datetime, timezone
    import google.generativeai as genai

    # Get anchor_id from whichever rule we have
    anchor_id = (classic_rule or llm_rule).anchor_id if (classic_rule or llm_rule) else None

    try:
        # Truncate HTML if needed
        truncated_html = _truncate_html_for_prompt(html_content, anchor_id)

        # Build prompt
        prompt = _build_adjudication_prompt(
            discrepancy_type=discrepancy_type,
            rule_number=rule_number,
            source_file=source_file,
            anchor_id=anchor_id,
            html_content=truncated_html,
            classic_rule=classic_rule,
            llm_rule=llm_rule,
        )

        # Call Gemini API
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.adjudicator_model_name)

        # 30-second timeout
        response = model.generate_content(
            prompt,
            request_options={"timeout": 30}
        )

        # Parse JSON
        data = json.loads(response.text)

        # Check for insufficient evidence
        if data.get("analysis", "").startswith("INSUFFICIENT_EVIDENCE:"):
            raise AdjudicationError(f"LLM reported insufficient evidence: {data['analysis']}")

        # Validate and create ExtractedRule
        corrected_rule_data = data["corrected_rule"]
        corrected_rule_data["expert_source"] = ExpertSource.ADJUDICATED
        corrected_rule_data["confidence_score"] = 0.95

        corrected_rule = ExtractedRule.model_validate(corrected_rule_data)

        # Log success
        logger.info(
            f"[Adjudicator] Adjudicated rule {rule_number}: {data['analysis']}",
            extra={
                "reasoning": data.get("reasoning"),
                "citation": data.get("citation"),
                "rule_number": rule_number,
            }
        )

        return corrected_rule

    except (Exception) as e:
        # Determine specific failure reason
        if isinstance(e, (genai.types.generation_types.StopCandidateException,
                         genai.types.generation_types.BlockedPromptException)):
            failure_reason = f"API call blocked or stopped: {type(e).__name__}"
        elif isinstance(e, TimeoutError):
            failure_reason = "API timeout after 30s"
        elif isinstance(e, json.JSONDecodeError):
            failure_reason = f"Failed to parse LLM JSON response: {str(e)}"
            logger.error(f"[Adjudicator] Raw LLM response: {response.text if 'response' in locals() else 'N/A'}")
        elif isinstance(e, (ValidationError, KeyError)):
            failure_reason = f"LLM response failed schema validation: {str(e)}"
        elif isinstance(e, AdjudicationError):
            failure_reason = str(e)
        else:
            failure_reason = f"Unexpected error: {type(e).__name__}: {str(e)}"

        logger.error(
            f"[Adjudicator] Failed to adjudicate rule {rule_number}: {failure_reason}",
            exc_info=True
        )

        # Create ManualReviewItem
        manual_item = ManualReviewItem(
            rule_number=rule_number,
            discrepancy_type=discrepancy_type,
            failure_reason=failure_reason,
            source_file=source_file,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if discrepancy_type == "CONFLICT" and classic_rule and llm_rule:
            manual_item.classic_version = classic_rule.model_dump(
                exclude={'expert_source', 'confidence_score', 'anchor_id'}
            )
            manual_item.llm_version = llm_rule.model_dump(
                exclude={'expert_source', 'confidence_score', 'anchor_id'}
            )
        else:
            orphan_rule = classic_rule or llm_rule
            manual_item.orphan_version = orphan_rule.model_dump(
                exclude={'expert_source', 'confidence_score', 'anchor_id'}
            )
            manual_item.found_by = "classic" if classic_rule else "llm"

        return manual_item
```

**Run tests**: `uv run pytest tests/unit/test_adjudicator.py -v -k adjudicate_item`

**Commit**: `feat: implement LLM adjudication with comprehensive error handling`

---

### Phase 6: Main Adjudicate Function (TDD)

#### Step 6.1: Write integration tests for main function
**Tests to write**:
```python
def test_adjudicate_returns_tuple_of_three_elements()
def test_adjudicate_returns_sorted_rules_by_rule_number()
def test_adjudicate_includes_perfect_matches_in_output()
def test_adjudicate_successful_conflicts_in_output()
def test_adjudicate_failed_conflicts_in_manual_review()
def test_adjudicate_stats_calculation_correct()
def test_adjudicate_logs_final_summary()
def test_adjudicate_with_empty_inputs()
```

**Commit**: `test: add integration tests for main adjudicate function`

#### Step 6.2: Implement main adjudicate function
**Implementation**:
```python
def adjudicate(
    classic_rules: list[ExtractedRule],
    llm_rules: list[ExtractedRule],
    source_html_content: str,
    source_file: str,
) -> tuple[list[ExtractedRule], list[ManualReviewItem], dict[str, int]]:
    """
    Merges, adjudicates, and self-corrects rules from classic and LLM parsers.

    Uses a Mixture-of-Experts approach with grounded LLM adjudication:
    1. Triage rules into perfect matches, conflicts, and orphans
    2. Trust classic parser for perfect matches (deterministic source of truth)
    3. Use Gemini Pro to resolve conflicts/orphans with full HTML context
    4. Return clean list of rules plus manual review items for failed adjudications

    Args:
        classic_rules: Rules extracted by classic HTML parser
        llm_rules: Rules extracted by LLM-based parser
        source_html_content: Full HTML content for grounding
        source_file: Source filename for audit trail

    Returns:
        Tuple of:
        - Resolved rules (sorted by rule_number)
        - Manual review items (failed adjudications)
        - Statistics dict with counts

    Raises:
        AdjudicationError: Only for catastrophic failures (not individual items)
    """
    logger.info("[Adjudicator] Starting adjudication process...")

    # Step 1: Triage
    triage_result = _triage_rules(classic_rules, llm_rules)

    # Step 2: Start with perfect matches
    final_rules: list[ExtractedRule] = list(triage_result.perfect_matches)
    manual_review_items: list[ManualReviewItem] = []

    stats = {
        "perfect_matches": len(triage_result.perfect_matches),
        "auto_corrected": 0,
        "manual_review": 0,
    }

    # Step 3: Adjudicate conflicts
    logger.info(f"[Adjudicator] Adjudicating {len(triage_result.conflicts)} conflicts...")
    for classic_rule, llm_rule in triage_result.conflicts:
        result = _adjudicate_item_with_llm(
            discrepancy_type="CONFLICT",
            rule_number=classic_rule.rule_number,
            source_file=source_file,
            html_content=source_html_content,
            classic_rule=classic_rule,
            llm_rule=llm_rule,
        )

        if isinstance(result, ExtractedRule):
            final_rules.append(result)
            stats["auto_corrected"] += 1
        else:
            manual_review_items.append(result)
            stats["manual_review"] += 1
            logger.warning(
                f"[Adjudicator] Added rule {result.rule_number} to manual review: "
                f"{result.failure_reason}"
            )

    # Step 4: Adjudicate orphans
    logger.info(f"[Adjudicator] Adjudicating {len(triage_result.orphans)} orphans...")
    for orphan_rule in triage_result.orphans:
        # Determine which parser found it
        is_classic = orphan_rule.expert_source == ExpertSource.CLASSIC

        result = _adjudicate_item_with_llm(
            discrepancy_type="ORPHAN",
            rule_number=orphan_rule.rule_number,
            source_file=source_file,
            html_content=source_html_content,
            classic_rule=orphan_rule if is_classic else None,
            llm_rule=orphan_rule if not is_classic else None,
        )

        if isinstance(result, ExtractedRule):
            final_rules.append(result)
            stats["auto_corrected"] += 1
        else:
            manual_review_items.append(result)
            stats["manual_review"] += 1
            logger.warning(
                f"[Adjudicator] Added rule {result.rule_number} to manual review: "
                f"{result.failure_reason}"
            )

    # Step 5: Sort and log final summary
    final_rules_sorted = sorted(final_rules, key=lambda r: r.rule_number)

    total_rules = len(final_rules_sorted)
    manual_count = len(manual_review_items)

    logger.info(
        f"[Adjudicator] Adjudication complete: {total_rules} rules in output, "
        f"{manual_count} sent for manual review"
    )

    return final_rules_sorted, manual_review_items, stats
```

**Run tests**: `uv run pytest tests/unit/test_adjudicator.py -v`

**Commit**: `feat: implement main adjudicate function with full pipeline`

---

### Phase 7: Final Integration & Documentation

#### Step 7.1: Add module docstring and exports
**File**: `src/qe_tax_rag/extraction/ca/adjudicator.py`

Add comprehensive module docstring at the top:
```python
"""
Grounded adjudication and self-correction for HTML-to-YAML extraction pipeline.

This module implements the core intelligence of the Mixture-of-Experts (MoE) pipeline.
It merges results from two expert parsers (classic HTML parser and LLM parser),
identifies discrepancies, and uses Gemini Pro to resolve conflicts with full audit trail.

Key Features:
- Triage algorithm: categorizes rules into perfect matches, conflicts, and orphans
- Trust classic parser for perfect matches (deterministic source of truth)
- Grounded LLM adjudication with full HTML context for evidence-based decisions
- Comprehensive error handling: all failures lead to manual review, not crashes
- Structured logging for audit trail with reasoning and citations

Usage:
    from qe_tax_rag.extraction.ca.adjudicator import adjudicate

    resolved_rules, manual_items, stats = adjudicate(
        classic_rules=classic_parser_output,
        llm_rules=llm_parser_output,
        source_html_content=html_content,
        source_file="t4002-5.html",
    )
"""
```

**Commit**: `docs: add comprehensive module docstring for adjudicator`

#### Step 7.2: Update package __init__.py
**File**: `src/qe_tax_rag/extraction/ca/__init__.py`

Export adjudicator function:
```python
from qe_tax_rag.extraction.ca.adjudicator import adjudicate

__all__ = ["adjudicate"]
```

**Run full test suite**: `uv run pytest tests/unit/test_adjudicator.py -v`

**Commit**: `feat: export adjudicate function from ca package`

#### Step 7.3: Run full quality checks
```bash
# Format code
uvx ruff format src/qe_tax_rag/extraction/ca/adjudicator.py tests/unit/test_adjudicator.py

# Lint
uvx ruff check src/qe_tax_rag/extraction/ca/adjudicator.py tests/unit/test_adjudicator.py

# Type check
uv run mypy src/qe_tax_rag/extraction/ca/adjudicator.py

# Run all tests
uv run pytest tests/unit/test_adjudicator.py -v --cov=src/qe_tax_rag/extraction/ca/adjudicator
```

**Commit**: `style: format and lint adjudicator module`

#### Step 7.4: Run regression check
```bash
# Ensure no existing tests broke
uv run pytest tests/ -v
```

**If all pass, commit**: `test: verify zero regressions after adjudicator implementation`

---

## Commit Strategy

### Principle: Small, Atomic, Testable Commits
Each commit should:
1. Represent one logical change
2. Pass all pre-commit hooks (ruff, mypy, pyright)
3. Pass relevant tests (if implementation commit)
4. Have a clear, descriptive message

### Commit Message Format
```
<type>: <short summary (50 chars)>

<detailed description explaining WHY, not WHAT>
- Use bullet points for multiple changes
- Focus on motivation and context

Rationale:
- Explain technical decisions made
- Document trade-offs considered

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**:
- `feat`: New feature/functionality
- `test`: Adding or modifying tests
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `style`: Formatting/linting changes

### Expected Commit Sequence
1. `test: add normalization tests for adjudicator`
2. `feat: implement rule normalization for adjudicator`
3. `test: add data structure tests for adjudicator`
4. `feat: add TriageResult and ManualReviewItem data structures`
5. `test: add comprehensive triage logic tests`
6. `feat: implement triage logic for rule categorization`
7. `test: add HTML truncation tests for adjudicator`
8. `feat: implement context-aware HTML truncation`
9. `test: add prompt building tests for adjudicator`
10. `feat: implement grounded adjudication prompt builder`
11. `test: add LLM adjudication tests with error scenarios`
12. `feat: implement LLM adjudication with comprehensive error handling`
13. `test: add integration tests for main adjudicate function`
14. `feat: implement main adjudicate function with full pipeline`
15. `docs: add comprehensive module docstring for adjudicator`
16. `feat: export adjudicate function from ca package`
17. `style: format and lint adjudicator module`
18. `test: verify zero regressions after adjudicator implementation`

**Total**: ~18 commits for complete TICKET 4 implementation

---

## Detailed Implementation Guide

### Data Structures Implementation

#### TriageResult (NamedTuple)
```python
from typing import NamedTuple

class TriageResult(NamedTuple):
    """Results from the triage phase of adjudication."""
    perfect_matches: list[ExtractedRule]
    conflicts: list[tuple[ExtractedRule, ExtractedRule]]
    orphans: list[ExtractedRule]
```

**Design notes**:
- NamedTuple provides immutability and clear field access
- Cleaner than returning tuple of lists
- Type hints make function contract explicit

#### ManualReviewItem (Pydantic Model)
```python
from pydantic import BaseModel, Field

class ManualReviewItem(BaseModel):
    """Represents a failed adjudication requiring manual review."""
    model_config = ConfigDict(frozen=False, extra="forbid")

    rule_number: int = Field(description="Rule number requiring review")
    discrepancy_type: str = Field(description="CONFLICT or ORPHAN")
    failure_reason: str = Field(description="Why adjudication failed")
    source_file: str = Field(description="Source HTML filename")
    timestamp: str = Field(description="ISO 8601 timestamp of failure")

    # For conflicts: both versions
    classic_version: dict | None = Field(default=None, description="Classic parser version")
    llm_version: dict | None = Field(default=None, description="LLM parser version")

    # For orphans: single version
    orphan_version: dict | None = Field(default=None, description="Orphan rule data")
    found_by: str | None = Field(default=None, description="Which parser found orphan")
```

**Design notes**:
- Pydantic ensures consistent YAML serialization
- Explicit field descriptions aid debugging
- Separate fields for conflict vs orphan scenarios
- `frozen=False` allows orchestrator to modify if needed

---

### Triage Algorithm Implementation

**Pseudocode**:
```
1. Create dictionaries: rule_number → ExtractedRule for both parsers
2. Find union of all rule numbers from both parsers
3. For each rule_number:
   a. If in both parsers:
      - Normalize both versions
      - If identical: add classic version to perfect_matches
      - If different: add (classic, llm) tuple to conflicts
   b. If in only one parser:
      - Add to orphans
4. Return TriageResult with categorized rules
```

**Key implementation details**:
- Use dictionary lookup for O(1) access: `classic_map[rule_number]`
- Normalize BEFORE comparison: `_normalize_rule_for_comparison(rule)`
- Trust classic parser for perfect matches (deterministic)
- Log counts for audit trail

---

### Normalization Function Implementation

**Normalization steps**:
1. Strip leading/trailing whitespace from `title`
2. Collapse consecutive whitespace to single space in `content` (regex: `\s+` → ` `)
3. Strip leading/trailing whitespace from `content`
4. Sort `applies_to` list alphabetically (to handle different orderings)
5. Return dictionary with only compared fields: `title`, `content`, `applies_to`

**Example**:
```python
# Input rule
rule = ExtractedRule(
    rule_number=8523,
    title="  Meals and entertainment  ",
    content="You can deduct\n\n  the cost  of meals...",
    applies_to=[ApplicabilityType.FISHING, ApplicabilityType.BUSINESS],
    ...
)

# Normalized output
{
    "title": "Meals and entertainment",
    "content": "You can deduct the cost of meals...",
    "applies_to": ["business", "fishing"]  # Sorted!
}
```

---

### HTML Truncation Algorithm

**Decision tree**:
```
if len(html_content) <= 300,000 chars:
    return full content
else:
    if anchor_id is available:
        try:
            - Find tag with id=anchor_id using BeautifulSoup
            - Find parent <h3> tag
            - Extract 2-3 preceding siblings (or until h2)
            - Extract following siblings until next <h3>
            - Return contextual window with truncation notice
        except:
            fall through to fallback

    # Fallback
    return first 150K + "[TRUNCATED]" + last 150K
```

**Context window example**:
```html
[...CONTENT TRUNCATED...]
The following is the most relevant section of the HTML based on the rule's anchor ID.

<h2>Part 4 – Net income (loss) before adjustments</h2>
<p>This section covers...</p>
<h3 id="tocch3ln8523"><a id="tocch3ln8523"></a>Line 8523 – Meals and entertainment</h3>
<p>You can deduct the cost of meals...</p>
<ul>...</ul>
```

---

### Adjudication Prompt Structure

**Sections**:
1. **Role & Task**: Explain adjudicator role
2. **Critical Requirements**: Grounding rules (evidence-only, citations, step-by-step)
3. **Discrepancy Details**: Structured metadata (type, rule number, file, anchor)
4. **Comparison Data**: YAML-formatted rule versions
5. **HTML Source**: Full or truncated HTML content
6. **Response Format**: JSON schema with analysis, reasoning, citation, corrected_rule
7. **Insufficient Evidence Clause**: Escape hatch for unclear cases

**Key design points**:
- Structured sections make LLM's task clear
- YAML format for rules (human-readable)
- Explicit JSON schema prevents malformed responses
- "INSUFFICIENT_EVIDENCE:" prefix provides escape hatch

---

### Error Handling Strategy

**Comprehensive try-except block**:
```python
try:
    # 1. Build prompt
    # 2. Call API
    # 3. Parse JSON
    # 4. Check for "INSUFFICIENT_EVIDENCE:"
    # 5. Validate with Pydantic
    # 6. Return ExtractedRule
except GoogleAPICallError:
    # API failure (network, auth, rate limit)
except TimeoutError:
    # 30s timeout exceeded
except json.JSONDecodeError:
    # LLM returned invalid JSON
except ValidationError:
    # JSON doesn't match ExtractedRule schema
except AdjudicationError:
    # LLM reported insufficient evidence
```

**All exceptions → ManualReviewItem**:
- Capture failure reason
- Log with full context (exc_info=True)
- Return structured manual review item
- Pipeline continues (fail gracefully)

---

### Statistics Calculation

**Tracked metrics**:
```python
stats = {
    "perfect_matches": len(perfect_matches),  # From triage
    "auto_corrected": 0,  # Successful adjudications (conflicts + orphans)
    "manual_review": 0,   # Failed adjudications
}
```

**Update logic**:
- Perfect matches: counted during triage
- Auto-corrected: increment when `_adjudicate_item_with_llm` returns `ExtractedRule`
- Manual review: increment when it returns `ManualReviewItem`

**Final validation**:
```python
total_input_rules = len(classic_rules) + len(llm_rules)
total_output = stats["perfect_matches"] + stats["auto_corrected"] + stats["manual_review"]
# Note: total_output may be less than total_input due to de-duplication
```

---

## Testing Strategy

### Test Organization

**File structure**:
```
tests/unit/test_adjudicator.py
  - TestNormalization (4 tests)
  - TestDataStructures (4 tests)
  - TestTriage (10 tests)
  - TestHTMLTruncation (5 tests)
  - TestPromptBuilding (4 tests)
  - TestLLMAdjudication (8 tests)
  - TestMainFunction (8 tests)
Total: ~43 tests
```

### Mocking Strategy

**For Gemini API**:
```python
from unittest.mock import patch, MagicMock

@patch('google.generativeai.GenerativeModel')
def test_adjudicate_item_success(mock_genai):
    # Setup mock
    mock_model = MagicMock()
    mock_genai.return_value = mock_model
    mock_model.generate_content.return_value.text = json.dumps({
        "analysis": "Found correct version in HTML",
        "reasoning": "Classic parser missed icon",
        "citation": "<img alt='fishing icon'>",
        "corrected_rule": {
            "rule_number": 8523,
            "title": "Meals and entertainment",
            "content": "You can deduct...",
            "applies_to": ["business", "fishing"],
            "source_citation": "Line 8523",
            "chapter": "Chapter 3",
            "section": "Part 4",
            "source_file": "t4002-5.html",
            "anchor_id": "tocch3ln8523",
        }
    })

    # Call function
    result = _adjudicate_item_with_llm(...)

    # Assertions
    assert isinstance(result, ExtractedRule)
    assert result.expert_source == ExpertSource.ADJUDICATED
    assert result.confidence_score == 0.95
```

### Test Data Fixtures

**Create sample rules**:
```python
@pytest.fixture
def sample_classic_rule():
    return ExtractedRule(
        rule_number=8523,
        title="Meals and entertainment",
        content="You can deduct the cost of meals and entertainment.",
        applies_to=[ApplicabilityType.BUSINESS],
        source_citation="Line 8523",
        chapter="Chapter 3 – Expenses",
        section="Part 4 – Net income (loss) before adjustments",
        source_file="t4002-5.html",
        expert_source=ExpertSource.CLASSIC,
        anchor_id="tocch3ln8523",
        confidence_score=1.0,
    )

@pytest.fixture
def sample_llm_rule():
    # Same as classic but with different applies_to
    return ExtractedRule(
        ...,
        applies_to=[ApplicabilityType.BUSINESS, ApplicabilityType.FISHING],
        expert_source=ExpertSource.LLM,
        confidence_score=0.85,
    )
```

---

## Edge Cases & Gotchas

### 1. Empty Input Lists
**Scenario**: Both parsers return empty lists
**Handling**: Return empty results with zero stats
**Test**: `test_adjudicate_with_empty_inputs`

### 2. All Perfect Matches
**Scenario**: No conflicts or orphans
**Handling**: No LLM calls, fast path
**Test**: Ensure no API calls made

### 3. All Conflicts
**Scenario**: Every rule differs between parsers
**Handling**: Sequential LLM calls, may be slow
**Test**: Mock all API calls, verify count

### 4. Duplicate Rule Numbers
**Scenario**: Same rule_number appears twice in one parser's output
**Handling**: Dict creation will keep last occurrence (non-deterministic)
**Prevention**: Add validation in triage to check for duplicates, log warning

### 5. Missing Required Fields
**Scenario**: LLM returns JSON missing `rule_number`
**Handling**: Pydantic ValidationError → ManualReviewItem
**Test**: `test_adjudicate_item_validation_error`

### 6. Very Large HTML Files
**Scenario**: HTML > 1MB
**Handling**: Truncation algorithm keeps context
**Test**: `test_truncate_html_with_large_content`

### 7. Missing Anchor ID
**Scenario**: Orphan rule has `anchor_id=None`
**Handling**: Truncation falls back to first/last chunks
**Test**: `test_truncate_html_handles_missing_anchor_id`

### 8. Rate Limiting
**Scenario**: Gemini API returns 429 (rate limit)
**Handling**: Caught as API error → ManualReviewItem
**Note**: No retry logic (fail gracefully, user can re-run)

### 9. Token Limit Exceeded
**Scenario**: Even truncated HTML exceeds model's context window
**Handling**: API will reject, caught as API error → ManualReviewItem
**Future**: Could implement more aggressive truncation

### 10. Unicode Characters
**Scenario**: HTML contains special characters (en dash, em dash)
**Handling**: PyYAML with `allow_unicode=True`, BeautifulSoup handles encoding
**Test**: Include unicode in test fixtures

---

## Dependencies Verification

**Required packages (all in pyproject.toml indexing section)**:
- ✅ `pydantic>=2.0` (BaseModel, ConfigDict, Field)
- ✅ `google-generativeai>=0.8.5` (genai client)
- ✅ `beautifulsoup4>=4.12` (HTML parsing for truncation)
- ✅ `pyyaml>=6.0` (YAML formatting in prompts)

**Standard library**:
- `typing` (NamedTuple, TypeAlias)
- `json` (JSON parsing)
- `re` (Regex for whitespace normalization)
- `logging` (Structured logging)
- `datetime` (Timestamps for ManualReviewItem)

**No new dependencies required** ✅

---

## Performance Expectations

### Sequential API Calls
- **Expected conflicts/orphans**: 10-20% of total rules (~20-40 calls per file)
- **API latency**: ~1-3 seconds per call
- **Total adjudication time**: ~30-120 seconds per file
- **Acceptable for batch pipeline**: ✅ (not real-time system)

### Optimization Opportunities (Future)
- Batch API calls (if Gemini supports)
- Async/await for parallel requests
- Caching of adjudication results

**Current decision**: YAGNI - implement simple sequential first

---

## Success Criteria Checklist

- [ ] All data structures implemented (TriageResult, ManualReviewItem)
- [ ] Normalization function passes all tests
- [ ] Triage logic correctly categorizes all scenarios
- [ ] HTML truncation preserves context around anchor_id
- [ ] Adjudication prompt includes structured details
- [ ] LLM adjudication handles all error scenarios gracefully
- [ ] Main function returns correct tuple format
- [ ] All 43+ tests pass
- [ ] No regressions in existing tests
- [ ] Code passes ruff, mypy, pyright
- [ ] Function signature matches TICKET 6 expectations
- [ ] Field names match schema.py (expert_source, confidence_score)
- [ ] Structured logging provides full audit trail
- [ ] ~18 small, atomic commits with clear messages

---

## Next Steps After TICKET 4

1. **TICKET 5**: Implement YAML generation module
   - Receives output from adjudicator
   - Strips internal metadata (expert_source, anchor_id, confidence_score)
   - Writes to YAML with PyYAML
   - Generates manual_review.yml separately

2. **TICKET 6**: Create orchestration script
   - Calls classic parser → llm parser → adjudicator → YAML generator
   - Handles directory processing (batch HTML files)
   - Provides summary report with statistics

3. **End-to-end testing**:
   - Test with real CRA HTML files from cra_documents/cra_t4002e_rev24_dump/
   - Verify manual review YAML is parseable
   - Validate final output YAML against schema

---

## Conclusion

This implementation plan provides:
- **Robust design** validated by Zen consultation
- **TDD approach** ensuring quality and testability
- **Atomic commits** enabling easy rollback and review
- **Comprehensive error handling** for production readiness
- **Zero regressions** through isolation and testing
- **Clear path forward** to complete TICKET 4 with confidence

Follow the phases sequentially, commit frequently, and run tests after each implementation step. The modular design ensures each piece can be tested and verified independently before integration.
