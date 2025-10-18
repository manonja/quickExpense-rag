# TICKET T3.2: Auto-Transform Flag - Implementation Plan

**Status**: Ready for Implementation
**Date**: 2025-10-17
**Based on**: Zen MCP Planning Analysis + TRANSFORMER_IMPLEMENTATION_PLAN.md

---

## Executive Summary

Add `--auto-transform` and `--output-jsonl` flags to the `extract-rules run` command, enabling users to extract HTML → YAML → JSONL in a single command. This improves UX by eliminating the need for a separate `transform` command call.

**80/20 Focus**: Deliver core convenience feature (one-command workflow) without over-engineering edge cases.

---

## Implementation Steps (with Commit Strategy)

### STEP 1: Update `scripts/extract_rules.py` - Add CLI Flags

**File**: `scripts/extract_rules.py`

**Changes**:
1. Add imports for transformer classes at top of file (lines 48-52)
2. Add two new parameters to `run()` function (lines 118-132):
   - `auto_transform: bool` (default `False`)
   - `output_jsonl: Path | None` (default `None`)
3. Update docstring with auto-transform example (line 151)
4. Update pre-flight checks to create `output_jsonl` parent directory (line 197-198)

**Commit**:
```bash
git add scripts/extract_rules.py
git commit -m "feat(T3.2): add --auto-transform and --output-jsonl CLI flags

Add two new optional parameters to extract-rules run command:
- --auto-transform: Enable automatic YAML→JSONL transformation
- --output-jsonl: Specify output path for transformed JSONL

Changes:
- Import YAMLTransformer, CriticalTransformationError, TransformationReport
- Add typer.Option parameters with type hints and help text
- Update docstring with usage example
- Add output_jsonl directory creation in pre-flight checks

Part of TICKET T3.2 (Auto-Transform Flag)
Follows 80/20 principle: simple flag addition, no complex logic yet

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Verification**:
```bash
uv run python scripts/extract_rules.py run --help
# Should show new flags in help output
```

---

### STEP 2: Update `scripts/extract_rules.py` - Add Transformation Logic

**File**: `scripts/extract_rules.py`

**Changes**:
1. Insert "Phase 4.5: Auto-Transformation" section after Phase 4 (lines 338-379)
   - Validate `--output-jsonl` is provided when `--auto-transform` is set
   - Call `YAMLTransformer.transform_yaml_to_jsonl()`
   - Handle `CriticalTransformationError` and unexpected exceptions
   - Store `transformation_report` for summary

**Commit**:
```bash
git add scripts/extract_rules.py
git commit -m "feat(T3.2): implement auto-transformation logic in extract-rules

Add Phase 4.5 to run() function that executes YAML→JSONL transformation
when --auto-transform flag is enabled.

Implementation:
- Validate --output-jsonl is provided (fail with clear error if missing)
- Initialize YAMLTransformer and call transform_yaml_to_jsonl()
- Store transformation report for summary display
- Handle CriticalTransformationError and unexpected exceptions
- Print transformation status with rich console formatting

Error handling:
- Clear user-facing error: '❌ --output-jsonl is required'
- Exit code 1 on transformation failure
- Graceful error messages with exception chaining

Part of TICKET T3.2 (Auto-Transform Flag)
Dependency: T2.1 (YAMLTransformer class)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Verification**:
```bash
# Test error handling (should fail with clear message)
uv run python scripts/extract_rules.py run test_html/ test.yml --auto-transform
```

---

### STEP 3: Update `scripts/extract_rules.py` - Enhance Summary Report

**File**: `scripts/extract_rules.py`

**Changes**:
1. Add transformation breakdown to summary report (lines 426-432)
2. Add transformed JSONL to outputs section (lines 442-443)
3. Update exit code logic to include transformation errors (lines 446-451)

**Commit**:
```bash
git add scripts/extract_rules.py
git commit -m "feat(T3.2): add transformation report to summary output

Enhance Phase 5 (Summary Report) to include transformation statistics
when auto-transform flag is enabled.

Changes:
- Display transformation breakdown (total/successful/skipped/errors)
- List transformed JSONL file in outputs section
- Set exit code to 1 if transformation report contains errors

Exit code strategy:
- 0: All extraction and transformation succeeded
- 1: Any extraction failures OR transformation errors

Follows commit-often strategy: summary reporting separated from core logic

Part of TICKET T3.2 (Auto-Transform Flag)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Verification**:
```bash
uv run mypy scripts/extract_rules.py
uvx ruff check scripts/extract_rules.py
```

---

### STEP 4: Create Integration Test File

**File**: `tests/integration/test_cli_integration.py` (NEW)

**Changes**:
1. Create test file with two integration tests:
   - `test_auto_transform_flag_success`: Verifies full pipeline works
   - `test_auto_transform_without_output_jsonl_fails`: Validates error handling

2. Add `html_test_dir` pytest fixture for minimal test HTML

**Commit**:
```bash
git add tests/integration/test_cli_integration.py
git commit -m "test(T3.2): add integration tests for auto-transform flag

Create comprehensive integration tests for --auto-transform functionality:

Tests:
1. test_auto_transform_flag_success
   - Runs full pipeline: HTML → YAML → JSONL
   - Validates both output files exist and contain correct data
   - Checks CLI stdout for success messages
   - Verifies JSONL structure (document_id, sections, LINE-* citations)

2. test_auto_transform_without_output_jsonl_fails
   - Validates error handling when --output-jsonl is missing
   - Checks exit code is 1
   - Verifies clear error message in stderr
   - Confirms YAML file still created (fail after extraction)

Fixtures:
- html_test_dir: Creates minimal HTML with Line 8523 rule

Test strategy:
- Uses subprocess.run for true CLI integration testing
- Minimal HTML content to avoid parser implementation details
- Clear assertions with helpful error messages

Part of TICKET T3.2 (Auto-Transform Flag)
Follows CLAUDE.md testing strategy (integration marker)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Verification**:
```bash
uv run mypy tests/integration/test_cli_integration.py
uvx ruff check tests/integration/test_cli_integration.py
```

---

### STEP 5: Run Integration Tests

**Commands**:
```bash
# Run the new integration tests
uv run pytest tests/integration/test_cli_integration.py -v -m integration

# Run all integration tests to ensure no regressions
uv run pytest tests/integration/ -v -m integration

# Skip slow tests for faster feedback
uv run pytest tests/integration/ -v -m "integration and not slow"
```

**Expected Outcomes**:
- ✅ `test_auto_transform_flag_success` passes
- ✅ `test_auto_transform_without_output_jsonl_fails` passes
- ✅ No regressions in existing tests

**If Tests Fail**:
- Check that upstream extraction parsers are implemented
- Verify transformer classes are importable
- Adjust minimal HTML content if needed for parser compatibility
- Review error messages and fix bugs iteratively

**No Commit**: Test runs don't generate code changes

---

### STEP 6: End-to-End Manual Testing

**Test Case 1: Success Path**
```bash
# Create test HTML directory
mkdir -p test_input
echo '<html><body><h2>Line 8523</h2><p>Meals</p></body></html>' > test_input/test.html

# Run with auto-transform
uv run python scripts/extract_rules.py run \
  test_input/ \
  output/rules.yml \
  --auto-transform \
  --output-jsonl output/chunks.jsonl

# Verify outputs exist
ls -lh output/rules.yml output/chunks.jsonl

# Verify JSONL format
cat output/chunks.jsonl | jq '.'
```

**Expected**:
- Exit code: 0
- Files created: `output/rules.yml`, `output/chunks.jsonl`
- Console output includes: "Auto-transforming YAML to JSONL"
- Console output includes: "Pipeline completed successfully"

---

**Test Case 2: Validation Error**
```bash
# Run with auto-transform but missing --output-jsonl
uv run python scripts/extract_rules.py run \
  test_input/ \
  output/rules.yml \
  --auto-transform

# Should fail with clear error
echo "Exit code: $?"
```

**Expected**:
- Exit code: 1
- Error message: "❌ Error: --output-jsonl is required when using --auto-transform"
- File created: `output/rules.yml` (extraction succeeded)
- File NOT created: `output/chunks.jsonl` (transformation not attempted)

---

**Test Case 3: Help Text**
```bash
uv run python scripts/extract_rules.py run --help
```

**Expected**:
- Help text includes `--auto-transform` flag description
- Help text includes `--output-jsonl` flag description
- Example usage shows auto-transform command

**No Commit**: Manual testing verification only

---

### STEP 7: Run Pre-commit Hooks

**Commands**:
```bash
# Run all pre-commit hooks on changed files
uv run pre-commit run --files scripts/extract_rules.py tests/integration/test_cli_integration.py

# Or run on all files
uv run pre-commit run --all-files
```

**Expected**:
- ✅ ruff (linting)
- ✅ ruff-format (formatting)
- ✅ mypy (type checking)
- ✅ pyright (type checking)
- ✅ trailing whitespace
- ✅ end-of-file fixer
- ✅ YAML syntax

**If Hooks Fail**:
- Fix linting errors: `uvx ruff check --fix scripts/extract_rules.py`
- Fix formatting: `uvx ruff format scripts/extract_rules.py`
- Fix type errors: Review mypy/pyright output and add type hints

**Commit** (if fixes were needed):
```bash
git add scripts/extract_rules.py tests/integration/test_cli_integration.py
git commit -m "style(T3.2): fix linting and formatting issues

Apply pre-commit hook fixes:
- Ruff auto-fixes for linting
- Format with ruff-format
- Fix type hints for mypy/pyright

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### STEP 8: Update Documentation (Optional - Can be separate PR)

**File**: `CLAUDE.md` (add auto-transform section)

**Changes**:
Add section under "Development Commands" or create new "Transformer Pipeline" section:

```markdown
## Transformer Pipeline (YAML to JSONL)

The transformer bridges the extraction pipeline with the RAG database.

### Usage

**Option 1: Manual transformation**
```bash
uv run extract-rules transform output/rules.yml data/chunks.jsonl
```

**Option 2: Auto-transform (One command)**
```bash
uv run extract-rules run HTML_DIR output/rules.yml \
  --auto-transform --output-jsonl data/chunks.jsonl
```
```

**Commit**:
```bash
git add CLAUDE.md
git commit -m "docs(T3.2): document auto-transform flag usage

Add documentation for --auto-transform flag in CLAUDE.md:
- Explain transformer pipeline purpose
- Show manual vs auto-transform usage
- Provide clear examples

Part of TICKET T3.2 (Auto-Transform Flag)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### STEP 9: Final Validation

**Run Full Test Suite**:
```bash
# Unit tests (fast)
uv run pytest tests/unit -v -m unit

# Integration tests
uv run pytest tests/integration -v -m integration

# All tests
uv run pytest tests/ -v
```

**Type Checking**:
```bash
uv run mypy src/ scripts/ tests/
```

**Linting**:
```bash
uvx ruff check .
```

**Expected**: All checks pass ✅

**No Commit**: Final validation only

---

### STEP 10: Clean Up

**Remove Generated Code File**:
```bash
rm zen_generated.code
```

**No Commit**: Cleanup of temporary file

---

## Commit Strategy Summary

### Principle: Small, Atomic Commits

Each commit should:
1. ✅ Represent ONE logical change
2. ✅ Pass all pre-commit hooks
3. ✅ Have a clear, descriptive message
4. ✅ Be independently reviewable

### Commit Sequence

1. **Add CLI flags** - Just parameter definitions, no logic
2. **Add transformation logic** - Core functionality
3. **Add summary reporting** - Enhanced output
4. **Add integration tests** - Validation
5. **(Optional) Fix pre-commit issues** - If hooks fail
6. **(Optional) Update documentation** - Can be separate

**Total Commits**: 4-6 commits (depending on pre-commit fixes)

### Benefits of This Strategy

- **Easy to review**: Each commit is small and focused
- **Easy to revert**: If one change is problematic, revert just that commit
- **Clear history**: Git log tells a story of incremental improvements
- **CI/CD friendly**: Each commit should be deployable
- **Collaboration**: Team members can review and understand changes easily

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Upstream parsers not implemented** | High | Tests will fail gracefully; implement mock parsers for testing |
| **Type checking errors** | Low | Run mypy after each change; fix type hints incrementally |
| **Transform errors affect UX** | Medium | Clear error messages, exit code 1, preserve YAML even if transform fails |
| **Integration tests are slow** | Low | Mark as `@pytest.mark.integration`, skip with `-m "not integration"` |
| **Pre-commit hooks fail** | Low | Run hooks before committing; auto-fix with ruff |

---

## Acceptance Criteria Checklist

### Implementation
- [ ] `--auto-transform` flag added to `run` command
- [ ] `--output-jsonl` flag added to `run` command
- [ ] Validation: `--auto-transform` without `--output-jsonl` fails with clear error
- [ ] Transformation logic calls `YAMLTransformer.transform_yaml_to_jsonl()`
- [ ] Transformation report displayed in summary
- [ ] Exit code 1 if transformation fails

### Testing
- [ ] `test_auto_transform_flag_success` passes
- [ ] `test_auto_transform_without_output_jsonl_fails` passes
- [ ] Manual testing: Success path works end-to-end
- [ ] Manual testing: Error handling works correctly
- [ ] Help text shows new flags

### Quality
- [ ] All pre-commit hooks pass
- [ ] Type checking passes (mypy, pyright)
- [ ] Linting passes (ruff)
- [ ] No regressions in existing tests

### Documentation
- [ ] Docstring updated with auto-transform example
- [ ] (Optional) CLAUDE.md updated with usage guide

---

## Dependencies

**Requires** (already implemented):
- ✅ T1.1: Citation ID Pattern Relaxation
- ✅ T1.2: Metadata Schema Extension
- ✅ T2.1: Core Transformer Module
- ✅ T2.2: Expense Type Classifier
- ✅ T2.3: Error Handling & Validation
- ✅ T3.1: Transform Command

**Enables**:
- T3.3: Pipeline-Extraction Command (uses auto-transform logic)
- User convenience: One-command workflow

---

## Timeline Estimate

**Solo Developer**: 1-2 hours
- Step 1-3 (Code changes): 30 minutes
- Step 4 (Tests): 20 minutes
- Step 5-7 (Validation): 30 minutes
- Step 8 (Docs): 20 minutes (optional)

**With Reviews**: Add 30-60 minutes for code review feedback

---

## Success Metrics

### Short-Term (After Implementation)
- [ ] Can run: `extract-rules run HTML_DIR output.yml --auto-transform --output-jsonl data.jsonl`
- [ ] Validation errors are clear and actionable
- [ ] All tests pass
- [ ] Code review approved

### Long-Term (After User Testing)
- [ ] Users prefer `--auto-transform` over separate commands
- [ ] No bug reports related to flag validation
- [ ] Pipeline-extraction command (T3.3) builds on this successfully

---

## Next Steps After Completion

1. **Mark TICKET T3.2 as complete** in TRANSFORMER_IMPLEMENTATION_PLAN.md
2. **Update progress tracking**: Document what was learned
3. **Prepare for TICKET T3.3**: Pipeline-Extraction Command
4. **Gather feedback**: Share with users, iterate if needed

---

**Status**: Ready to implement
**Complexity**: Low (flag addition + orchestration)
**80/20 Focus**: Core convenience feature delivered, no over-engineering
