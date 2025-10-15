# TICKET 9D: Maintainer CLI - Implementation Plan

## Overview

Implement a Typer-based CLI to orchestrate the full indexing pipeline (preprocess → parse → build → validate). This is the final maintainer-facing tool that enables User Story 2.

## Development Approach

### Test-Driven Development (TDD)

Follow **Red-Green-Refactor** cycle for all implementations:

1. **Red**: Write failing test first (define expected behavior)
2. **Green**: Write minimal code to make test pass
3. **Refactor**: Improve code quality while keeping tests green

### Commit Strategy

**Commit frequently** with atomic, meaningful commits:

- After each passing test suite (Red → Green transition)
- After each refactoring step
- After each command implementation
- Include detailed commit messages following conventional commits format

**Example commit sequence**:
```
test: add IndexValidator schema check test (RED)
feat: implement IndexValidator.check_schema() (GREEN)
refactor: extract SQL queries to constants (REFACTOR)
test: add IndexValidator embedding dimension test (RED)
feat: implement IndexValidator.check_embeddings() (GREEN)
...
```

## Design Decisions (Based on Zen Consultation)

### 1. Architecture

- **Single file**: `scripts/cli.py` (extend existing file)
- **Explicit imports**: Direct function calls to TICKET 9A-9C modules (no dependency injection)
- **Error handling**: Two-tier (modules raise exceptions, CLI catches and formats)

### 2. Module Locations

- **IndexValidator**: Create `src/quickexpense_rag/data/validator.py` (part of library, not scripts)
- **Rationale**: Validation is core data integrity logic, should be reusable in tests and other contexts

### 3. Progress Reporting

- Use `rich.progress` (already in dependencies via Typer)
- **preprocess**: File-level (already implemented ✅)
- **parse**: File-level progress bar
- **build**: Chunk-level progress bar (already implemented in IndexBuilder ✅)

### 4. Validation Strategy

- **Smoke test approach** (not comprehensive evaluation)
- Checks: Schema exists, row counts match, embeddings valid dimensions, search executes without error
- **Test query**: Generic "what is an expense" (works with any DB content)

### 5. Pipeline Behavior

- **Stateless**: Always runs from beginning, overwrites artifacts
- **Confirmation prompt**: Ask before overwriting (with `--force` flag to skip)
- **No resume-from-failure** (deferred as premature optimization)

## Implementation Tasks (TDD Order)

### Task 1: Create IndexValidator (TDD)

**File**: `src/quickexpense_rag/data/validator.py`
**Test File**: `tests/unit/test_validator.py`

**TDD Cycle**:

1. **Test 1a (RED)**: Write test for `check_schema()` - verify tables exist
2. **Implement 1a (GREEN)**: Implement `check_schema()` method
3. **Refactor 1a**: Extract table names to constants

4. **Test 1b (RED)**: Write test for `check_row_counts()` - verify rules, rules_vec, rules_fts match
5. **Implement 1b (GREEN)**: Implement `check_row_counts()` method
6. **Commit**: `feat: add IndexValidator row count validation`

7. **Test 1c (RED)**: Write test for `check_embeddings()` - sample embedding has 384 dims
8. **Implement 1c (GREEN)**: Implement `check_embeddings()` method
9. **Commit**: `feat: add IndexValidator embedding dimension check`

10. **Test 1d (RED)**: Write test for `check_search()` - generic query executes without error
11. **Implement 1d (GREEN)**: Implement `check_search()` method using HybridSearchEngine
12. **Commit**: `feat: add IndexValidator live search test`

13. **Test 1e (RED)**: Write test for `validate()` - returns comprehensive report dict
14. **Implement 1e (GREEN)**: Implement `validate()` that calls all checks
15. **Commit**: `feat: add IndexValidator.validate() orchestration method`

**Features**:
- Schema check (tables exist)
- Row count check (rules, rules_vec, rules_fts)
- Embedding dimension check (sample one random embedding)
- Live search test (generic query executes without error)
- Statistics report (chunk count, expense type coverage)

**Returns**: Dict with validation report (pass/fail + details)

**Commit after completion**: `feat: implement IndexValidator for database smoke tests (TICKET-9D)`

---

### Task 2: Add `parse` Command (TDD)

**File**: `scripts/cli.py` (extend existing)
**Test File**: `tests/integration/test_cli_parse.py`

**TDD Cycle**:

1. **Test 2a (RED)**: Write test for parse command - verify JSONL output created
2. **Implement 2a (GREEN)**: Add `@app.command() def parse()` skeleton
3. **Commit**: `test: add parse command integration test`

4. **Test 2b (RED)**: Write test verifying ParsedDocument JSONL format
5. **Implement 2b (GREEN)**: Implement file iteration + GeminiParser call + JSONL write
6. **Commit**: `feat: add parse command for Gemini document parsing`

7. **Test 2c (RED)**: Write test for missing API key error
8. **Implement 2c (GREEN)**: Add API key validation with clear error message
9. **Commit**: `feat: add API key validation to parse command`

10. **Test 2d (RED)**: Write test for token usage tracking
11. **Implement 2d (GREEN)**: Accumulate token usage, display cost estimate
12. **Commit**: `feat: add token usage tracking and cost estimation to parse`

**Features**:
- Process all `.txt` files in `data/preprocessed/`
- Call `GeminiParser` for each file
- Write `ParsedDocument` objects to `data/processed/chunks.jsonl` (one JSON per line)
- Show file-level progress bar
- Track and display token usage + estimated cost
- Require `GEMINI_API_KEY` environment variable (fail fast if missing)

**Error handling**:
- Catch API errors, show clear message
- Option to continue on error with `--force` flag

**Commit after completion**: `feat: implement parse command with progress tracking (TICKET-9D)`

---

### Task 3: Add `build` Command (TDD)

**File**: `scripts/cli.py`
**Test File**: `tests/integration/test_cli_build.py`

**TDD Cycle**:

1. **Test 3a (RED)**: Write test for build command - verify DB + manifest created
2. **Implement 3a (GREEN)**: Add `@app.command() def build()` calling IndexBuilder
3. **Commit**: `test: add build command integration test`

4. **Test 3b (RED)**: Write test for error handling (corrupt JSONL)
5. **Implement 3b (GREEN)**: Add try/except with rich error formatting
6. **Commit**: `feat: add build command with error handling`

7. **Test 3c (RED)**: Write test verifying source_files parameter passed correctly
8. **Implement 3c (GREEN)**: Load source files from preprocess manifest
9. **Commit**: `feat: integrate preprocess manifest into build command`

**Features**:
- Load chunks from `data/processed/chunks.jsonl`
- Load source files from `data/raw/manifest.json` (created by preprocess)
- Call `IndexBuilder.build_from_jsonl()`
- Output to `data/cra_rules.db` + `data/manifest.json`
- Progress bar already implemented in IndexBuilder ✅

**Error handling**:
- Catch database errors, embedding errors
- Show clear error messages with `rich`

**Commit after completion**: `feat: implement build command for database creation (TICKET-9D)`

---

### Task 4: Add `validate` Command (TDD)

**File**: `scripts/cli.py`
**Test File**: `tests/integration/test_cli_validate.py`

**TDD Cycle**:

1. **Test 4a (RED)**: Write test for validate command - verify exit code 0 on success
2. **Implement 4a (GREEN)**: Add `@app.command() def validate()` calling IndexValidator
3. **Commit**: `test: add validate command integration test`

4. **Test 4b (RED)**: Write test for validation failure (exit code 1)
5. **Implement 4b (GREEN)**: Raise typer.Exit(code=1) on validation failure
6. **Commit**: `feat: add validate command with pass/fail exit codes`

7. **Test 4c (RED)**: Write test verifying rich output formatting
8. **Implement 4c (GREEN)**: Add rich panels for validation report
9. **Commit**: `feat: add rich formatting to validate command output`

**Features**:
- Call `IndexValidator.validate(db_path)`
- Display validation report with `rich` panels
- Exit code 0 if passed, 1 if failed
- Show statistics (chunk count, expense types, provinces)

**Commit after completion**: `feat: implement validate command for DB smoke tests (TICKET-9D)`

---

### Task 5: Add `pipeline` Command (TDD)

**File**: `scripts/cli.py`
**Test File**: `tests/integration/test_cli_pipeline.py`

**TDD Cycle**:

1. **Test 5a (RED)**: Write test for full pipeline execution
2. **Implement 5a (GREEN)**: Add `@app.command() def pipeline()` calling all stages
3. **Commit**: `test: add pipeline command integration test`

4. **Test 5b (RED)**: Write test for overwrite confirmation prompt
5. **Implement 5b (GREEN)**: Add typer.confirm() before overwriting artifacts
6. **Commit**: `feat: add confirmation prompt to pipeline command`

7. **Test 5c (RED)**: Write test for --force flag bypass
8. **Implement 5c (GREEN)**: Add --force option to skip confirmation
9. **Commit**: `feat: add --force flag to pipeline command`

10. **Test 5d (RED)**: Write test for fail-fast behavior (stop on first error)
11. **Implement 5d (GREEN)**: Don't catch exceptions, let them propagate
12. **Commit**: `feat: implement fail-fast error handling in pipeline`

**Features**:
- Run: preprocess → parse → build → validate
- Check for existing artifacts, prompt for confirmation (unless `--force`)
- Stop on first error (fail fast)
- Display summary at end with all stages

**Arguments**:
- `--force`: Skip confirmation prompts and continue on non-critical errors
- `--output-db`: Database output path (default: `data/cra_rules.db`)

**Commit after completion**: `feat: implement pipeline command for full workflow (TICKET-9D)`

---

### Task 6: Integration Test

**File**: `tests/integration/test_cli_full_pipeline.py`

**TDD Cycle**:

1. **Test 6a (RED)**: E2E test with 3 HTML files → full pipeline → validation passes
2. **Implement 6a (GREEN)**: Ensure all commands work together end-to-end
3. **Commit**: `test: add end-to-end CLI pipeline integration test`

**Test scenario**:
- 3 test HTML files → full pipeline → validation passes
- Verify database created, manifest exists, search works

**Commit after completion**: `test: add comprehensive CLI integration tests (TICKET-9D)`

---

### Task 7: Documentation

**File**: `scripts/README.md`

**Contents**:
- Maintainer guide with step-by-step instructions
- Manual download process (Step 1)
- CLI commands with examples
- Error troubleshooting guide
- Cost estimation notes

**Commit**: `docs: add maintainer guide for CLI usage (TICKET-9D)`

---

## Implementation Order Summary

1. ✅ **preprocess** (already done)
2. **IndexValidator** (TDD: 5 test cycles, ~5 commits)
3. **parse** command (TDD: 4 test cycles, ~4 commits)
4. **build** command (TDD: 3 test cycles, ~3 commits)
5. **validate** command (TDD: 3 test cycles, ~3 commits)
6. **pipeline** command (TDD: 4 test cycles, ~4 commits)
7. Integration test (TDD: 1 test cycle, ~1 commit)
8. Documentation (~1 commit)

**Total estimated commits**: ~21 atomic commits

## Edge Cases Handled

✅ **Now**:
- Missing input directories (fail fast with clear message)
- Missing API key (fail fast)
- Corrupt files (log error, continue or stop based on `--force`)
- Duplicate citation_ids (fail fast in builder)
- Overwriting artifacts (confirmation prompt)

⏸️ **Deferred**:
- Resume from failure (pipeline is stateless)
- Incremental indexing (always full rebuild)
- Parallel processing (sequential is simple and sufficient)
- Cost pre-estimation (show actual cost after completion)

## Success Criteria

All acceptance criteria from TICKET 9D satisfied:

- [x] 5 CLI commands implemented (preprocess ✅, parse, build, validate, pipeline)
- [x] IndexValidator with comprehensive checks
- [x] Clear error messages with rich formatting
- [x] Progress bars for long operations
- [x] `--force` flag for automation
- [x] Integration test with 3 HTML files
- [x] Maintainer documentation
- [x] TDD approach with frequent commits
- [x] All tests passing (unit + integration)

## Dependencies

- TICKET 9A: TextExtractor (✅ done)
- TICKET 9B: GeminiParser (✅ done)
- TICKET 9C: IndexBuilder (✅ done)

## Commit Message Template

```
<type>: <short summary (50 chars)>

<detailed description explaining WHY, not WHAT>
- Use bullet points for multiple changes
- Focus on motivation and context
- Reference TICKET-9D

Rationale:
- Explain technical decisions made
- Document trade-offs considered

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**: test, feat, refactor, docs, fix
