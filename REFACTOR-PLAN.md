# Package Rename Refactoring Plan

**Project**: QuickExpense RAG → QE Tax RAG
**Date**: 2025-10-16
**Scope**: Complete package rename with atomic commits per phase

## Overview

### Current Names
- **Distribution name (PyPI)**: `quickexpense-rag`
- **Python module name**: `quickexpense_rag`
- **Environment variable prefix**: `QUICKEXPENSE_RAG_`
- **Prose name**: QuickExpense RAG
- **Exception base class**: `QuickExpenseError`

### Target Names
- **Distribution name (PyPI)**: `qe-tax-rag`
- **Python module name**: `qe_tax_rag`
- **Environment variable prefix**: `QE_TAX_RAG_`
- **Prose name**: QE Tax RAG
- **Exception base class**: `QeTaxRagError`

## Impact Analysis

### Files to Modify (~40-50 files)

#### Source Code (17 files)
- `src/quickexpense_rag/` → `src/qe_tax_rag/` (entire directory)
  - `__init__.py` (imports, docstring, exports)
  - `api.py` (imports)
  - `exceptions.py` (class name `QuickExpenseError`)
  - `settings.py` (env_prefix, imports)
  - `embeddings/encoder.py` (imports)
  - `search/enums.py` (imports)
  - `search/models.py` (imports)
  - `search/hybrid.py` (imports)
  - `data/schema.py` (imports)
  - `data/builder.py` (imports)
  - `data/validator.py` (imports)
  - `data/manager.py` (imports)
  - `data/connection.py` (imports)
  - `data/migrations.py` (imports)

#### Test Files (~15 files in tests/)
- All `test_*.py` files:
  - `tests/unit/test_api.py` (imports + patch decorators)
  - `tests/unit/test_builder.py` (imports + exception references)
  - `tests/unit/test_data_manager.py` (imports)
  - `tests/unit/test_hybrid_edge_cases.py` (imports)
  - `tests/unit/test_hybrid_search.py` (imports)
  - `tests/unit/test_models.py` (imports)
  - `tests/unit/test_rrf_fusion.py` (imports)
  - `tests/unit/test_schema.py` (imports)
  - `tests/unit/test_settings.py` (imports + env var names)
  - `tests/unit/test_settings_gemini.py` (imports + env var names)
  - `tests/unit/test_validator.py` (imports)
  - All integration test files

#### Configuration Files (5 files)
- `pyproject.toml` (name, paths, URLs - 9 changes)
- `.github/workflows/test.yml` (coverage path)
- `.env.example` (6 environment variable names)

#### Documentation Files (~15 files)
- `README.md` (badges, install commands, imports, env vars, URLs)
- `CLAUDE.md` (project overview, examples, env vars, URLs)
- `CONTRIBUTING.md` (clone URL, issue tracker)
- `CHANGELOG.md` (release URL)
- `TESTPYPI-UPLOAD.md` (package references)
- `plan.md` (package references)
- `docs/RELEASING.md` (package references, commands, URLs)
- `scripts/README.md` (package name, env vars)
- `scripts/parser/README.md` (env vars)
- `tests/fixtures/README.md` (package name)

#### Script Files (2 files)
- `scripts/cli.py` (help text, console prints - 5 references)
- `scripts/preprocessor/__init__.py` (docstring)

#### Generated/Cache Files (regenerate, not edit)
- `uv.lock` (regenerate via `uv lock --upgrade`)
- `.mypy_cache/` (delete)
- `.ruff_cache/` (delete)
- `.pytest_cache/` (delete)
- `dist/` (delete)
- `.venv/` (optional: recreate or update prompt)

## Execution Plan

### Phase 0: Documentation & Preparation
**Goal**: Create this plan document

**Actions**:
1. Write this comprehensive plan to `REFACTOR-PLAN.md`
2. Include all phases, file counts, validation steps
3. Document rollback strategy

**Commit**: `docs: add package rename refactoring plan`

---

### Phase 1: Directory & File Structure
**Goal**: Rename the source directory

**Actions**:
1. Move `src/quickexpense_rag/` → `src/qe_tax_rag/`
2. Preserve all subdirectory structure
3. Git will track as rename

**Files affected**: 17 Python files + subdirectories

**Validation**:
- Verify directory exists: `ls src/qe_tax_rag/`
- Verify old directory gone: `! test -d src/quickexpense_rag`

**Commit**: `refactor: rename source directory quickexpense_rag → qe_tax_rag`

---

### Phase 2: Python Code - Imports & Core

#### Step 2a: Update Source File Imports
**Goal**: Fix all import statements in source code

**Actions**:
1. Update `src/qe_tax_rag/__init__.py`:
   - Line 2: Docstring "QuickExpense RAG" → "QE Tax RAG"
   - Line 14-26: `from quickexpense_rag.` → `from qe_tax_rag.`
2. Update all `src/qe_tax_rag/**/*.py` files with internal imports

**Files affected**: All 17 source files

**Search commands**:
```bash
grep -r "from quickexpense_rag" src/qe_tax_rag/
grep -r "import quickexpense_rag" src/qe_tax_rag/
```

**Validation**:
- No matches for old import: `! grep -r "quickexpense_rag" src/qe_tax_rag/`
- Python can import: `python -c "import qe_tax_rag"`

**Commit**: `refactor: update imports in source code`

---

#### Step 2b: Update Exception Class
**Goal**: Rename base exception class

**Actions**:
1. In `src/qe_tax_rag/exceptions.py`:
   - Rename `class QuickExpenseError` → `class QeTaxRagError`
2. In `src/qe_tax_rag/__init__.py`:
   - Update import: `QuickExpenseError` → `QeTaxRagError`
   - Update `__all__` list
3. Update all subclass inheritance in `exceptions.py`

**Files affected**: 2 files

**Search command**:
```bash
grep -r "QuickExpenseError" src/qe_tax_rag/
```

**Validation**:
- No old exception name in source: `! grep -r "QuickExpenseError" src/`
- Exception importable: `python -c "from qe_tax_rag import QeTaxRagError"`

**Commit**: `refactor: rename QuickExpenseError → QeTaxRagError`

---

#### Step 2c: Update Test Imports
**Goal**: Fix all imports in test files

**Actions**:
1. Replace `from quickexpense_rag` → `from qe_tax_rag` in all test files
2. Update mock patch decorators:
   - `@patch("quickexpense_rag.api.*")` → `@patch("qe_tax_rag.api.*")`
3. Update exception references: `QuickExpenseError` → `QeTaxRagError`
4. Update environment variable names:
   - `QUICKEXPENSE_RAG_*` → `QE_TAX_RAG_*`

**Files affected**: ~15 test files

**Search commands**:
```bash
grep -r "quickexpense_rag" tests/
grep -r "QuickExpenseError" tests/
grep -r "QUICKEXPENSE_RAG" tests/
```

**Validation**:
- No old imports: `! grep -r "quickexpense_rag" tests/`
- Tests can import: `uv run pytest tests/ --collect-only`

**Commit**: `refactor: update imports in test files`

---

### Phase 3: Configuration Files

#### Step 3a: Update pyproject.toml
**Goal**: Update package metadata and paths

**Actions** (9 changes):
1. Line 6: `name = "qe-tax-rag"`
2. Line 8: Description (optional: update prose name)
3. Line 65: `path = "src/qe_tax_rag/__init__.py"`
4. Line 68: `packages = ["qe_tax_rag"]`
5. Line 73: `src = ["src/qe_tax_rag", "tests"]`
6. Line 103: `"src/qe_tax_rag/data/validator.py"`
7. Line 137: `source = ["src/qe_tax_rag"]`
8. Lines 59-62: Update GitHub URLs (if repo renamed)

**Files affected**: 1 file

**Validation**:
- No old package name: `! grep -i "quickexpense" pyproject.toml`
- Valid TOML: `uv build --check` or parse with Python

**Commit**: `build: update pyproject.toml for qe-tax-rag package`

---

#### Step 3b: Update GitHub Workflows
**Goal**: Update CI/CD configuration

**Actions**:
1. `.github/workflows/test.yml` line 58:
   - `--cov=src/qe_tax_rag`

**Files affected**: 1 file

**Validation**:
- No old package name: `! grep "quickexpense_rag" .github/`
- Valid YAML: `yamllint .github/workflows/test.yml` (if available)

**Commit**: `ci: update workflow coverage path to qe_tax_rag`

---

#### Step 3c: Update Settings & Environment Variables
**Goal**: Update configuration and env var prefix

**Actions**:
1. `src/qe_tax_rag/settings.py` line 19:
   - `env_prefix="QE_TAX_RAG_"`
2. `.env.example` (6 variables):
   - `QUICKEXPENSE_RAG_*` → `QE_TAX_RAG_*`

**Files affected**: 2 files

**Search command**:
```bash
grep -r "QUICKEXPENSE_RAG" .env.example src/qe_tax_rag/settings.py
```

**Validation**:
- No old prefix: `! grep "QUICKEXPENSE_RAG" src/ .env.example`
- Settings load: `python -c "from qe_tax_rag import settings; print(settings)"`

**Commit**: `refactor: update environment variable prefix to QE_TAX_RAG_`

---

### Phase 4: Documentation - User-Facing

#### Step 4a: Update README.md
**Goal**: Update primary user documentation

**Actions**:
1. Title: "# QE Tax RAG"
2. Badges: Update PyPI URLs and package names
3. Installation: `pip install qe-tax-rag`
4. Import examples: `import qe_tax_rag as qe`
5. Environment variables: `QE_TAX_RAG_*`
6. GitHub URLs: Update if repo renamed
7. All prose: "QuickExpense RAG" → "QE Tax RAG"

**Files affected**: 1 file

**Estimated changes**: ~15-20 replacements

**Commit**: `docs: update README for qe-tax-rag package`

---

#### Step 4b: Update CLAUDE.md
**Goal**: Update developer documentation

**Actions**:
1. Project overview: "QE Tax RAG"
2. All installation/import examples
3. Environment variable prefix and examples
4. File structure section
5. All prose references

**Files affected**: 1 file

**Estimated changes**: ~25-30 replacements

**Commit**: `docs: update CLAUDE.md for qe-tax-rag package`

---

### Phase 5: Documentation - Contributor & Process

#### Step 5a: Update CONTRIBUTING.md
**Goal**: Update contributor guide

**Actions**:
1. Clone URL: Update GitHub URL
2. Directory references: `cd qe-tax-rag`
3. Issue tracker URLs

**Files affected**: 1 file

**Estimated changes**: 3-5 replacements

**Commit**: `docs: update CONTRIBUTING.md for qe-tax-rag`

---

#### Step 5b: Update CHANGELOG.md
**Goal**: Document the rename and update URLs

**Actions**:
1. Add new section for version 0.2.0:
   ```markdown
   ## [0.2.0] - 2025-10-16

   ### Changed
   - **BREAKING**: Package renamed from `quickexpense-rag` to `qe-tax-rag`
   - **BREAKING**: Python module renamed from `quickexpense_rag` to `qe_tax_rag`
   - **BREAKING**: Environment variable prefix changed from `QUICKEXPENSE_RAG_` to `QE_TAX_RAG_`
   - **BREAKING**: Base exception class renamed from `QuickExpenseError` to `QeTaxRagError`

   ### Migration Guide
   - Update imports: `from quickexpense_rag` → `from qe_tax_rag`
   - Update environment variables: `QUICKEXPENSE_RAG_*` → `QE_TAX_RAG_*`
   - Update exception handling: `QuickExpenseError` → `QeTaxRagError`
   ```
2. Update release URL at bottom

**Files affected**: 1 file

**Commit**: `docs: update CHANGELOG for package rename`

---

#### Step 5c: Update docs/RELEASING.md
**Goal**: Update release documentation

**Actions**:
1. Package references: `qe-tax-rag`
2. Wheel name examples: `qe_tax_rag-*.whl`
3. Directory references: `cd qe-tax-rag`
4. PyPI URLs

**Files affected**: 1 file

**Commit**: `docs: update RELEASING guide for qe-tax-rag`

---

#### Step 5d: Update Remaining Documentation
**Goal**: Update all other markdown files

**Actions**:
1. `TESTPYPI-UPLOAD.md`: All package/module references
2. `plan.md`: Package name references
3. `scripts/README.md`: Package name, env vars
4. `scripts/parser/README.md`: Environment variables
5. `tests/fixtures/README.md`: Package name

**Files affected**: 5 files

**Search commands**:
```bash
grep -l "quickexpense\|QuickExpense" *.md scripts/*.md tests/fixtures/*.md
```

**Commit**: `docs: update remaining documentation files`

---

### Phase 6: Scripts & Tooling

#### Step 6a: Update CLI Scripts
**Goal**: Update script help text and references

**Actions**:
1. `scripts/cli.py` (5 changes):
   - App help text: "QE Tax RAG Preprocessing CLI"
   - Console prints: "QE Tax RAG" (4 occurrences)
2. `scripts/preprocessor/__init__.py`:
   - Docstring: "Document preprocessing utilities for QE Tax RAG."

**Files affected**: 2 files

**Commit**: `refactor: update script help text and references`

---

### Phase 7: Cleanup & Regeneration

#### Step 7a: Clean Build Artifacts
**Goal**: Remove old caches and build outputs

**Actions**:
```bash
rm -rf .mypy_cache/
rm -rf .ruff_cache/
rm -rf .pytest_cache/
rm -rf dist/
```

**Files affected**: Removes 4 directories

**Validation**:
- Directories gone: `! test -d .mypy_cache`

**Commit**: `chore: remove old caches and build artifacts`

---

#### Step 7b: Regenerate Lock File
**Goal**: Update uv.lock with new package name

**Actions**:
```bash
uv lock --upgrade
```

**Files affected**: 1 file (`uv.lock`)

**Validation**:
- New package name in lock: `grep "qe-tax-rag" uv.lock`
- No old name: `! grep "quickexpense-rag" uv.lock`

**Commit**: `build: regenerate uv.lock with new package name`

---

### Phase 8: Validation & Testing

#### Step 8a: Run Quality Checks
**Goal**: Ensure code quality standards

**Actions**:
```bash
# Format code
uvx ruff format

# Lint with auto-fix
uvx ruff check --fix

# Type check
uv run mypy src/

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

**Expected outcome**:
- All checks pass
- May auto-fix some formatting

**Commit** (if changes made): `style: apply formatting and linting fixes`

---

#### Step 8b: Run Full Test Suite
**Goal**: Verify functionality intact

**Actions**:
```bash
uv run pytest tests/ -v
```

**Expected outcome**:
- All 23 tests pass
- No import errors
- No module not found errors

**Validation**:
- Exit code 0
- Coverage ≥ 85%

**Note**: No commit (validation only)

---

#### Step 8c: Build & Verify Package
**Goal**: Ensure package builds correctly

**Actions**:
```bash
# Build distributions
uv build

# Check wheel name
ls -la dist/

# Verify wheel contents
unzip -l dist/qe_tax_rag-*.whl | grep -E "qe_tax_rag|quickexpense"

# Check wheel size
ls -lh dist/
```

**Expected outcome**:
- Wheel named: `qe_tax_rag-0.1.0-py3-none-any.whl` (or 0.2.0)
- Wheel contains `qe_tax_rag/` directory
- No `quickexpense_rag/` directory
- Wheel size < 5MB

**Validation**:
- Wheel installable: `pip install --dry-run dist/*.whl`
- No old package name: `! unzip -l dist/*.whl | grep quickexpense`

**Note**: No commit (validation only)

---

## Rollback Strategy

### Per-Phase Rollback
Each phase creates an atomic commit. To rollback:

```bash
# Rollback last commit
git reset --hard HEAD~1

# Rollback to specific commit
git reset --hard <commit-hash>

# Rollback multiple commits
git reset --hard HEAD~N
```

### Complete Rollback
To completely undo the refactoring:

```bash
# Find commit before Phase 0
git log --oneline | grep "add package rename refactoring plan"

# Reset to commit before that
git reset --hard <commit-before-phase-0>
```

### Partial Rollback
To rollback only specific files:

```bash
# Restore specific file from previous commit
git checkout HEAD~1 -- path/to/file

# Restore specific file from specific commit
git checkout <commit-hash> -- path/to/file
```

## Risk Assessment

### High Risk
- Import breakage in tests or source code
- Environment variable mismatch causing runtime failures
- Third-party integrations expecting old package name

### Medium Risk
- Documentation out of sync
- Cache files causing confusion
- CI/CD pipeline failures

### Low Risk
- Prose name inconsistencies
- URL redirects (GitHub handles automatically)

## Post-Refactoring Tasks

### Optional but Recommended
1. **Update GitHub repository name**
   - Rename repo: `quickExpense-rag` → `qe-tax-rag`
   - GitHub auto-redirects old URLs
   - Update local remote: `git remote set-url origin <new-url>`

2. **Recreate virtual environment**
   ```bash
   rm -rf .venv
   uv sync
   ```

3. **Publish new version to PyPI**
   - Update version to 0.2.0
   - Build and publish
   - Consider yanking old `quickexpense-rag` versions

4. **Update external references**
   - CI/CD badges
   - Package registry listings
   - Any external documentation

5. **Communicate to users**
   - GitHub release notes
   - Migration guide
   - Deprecation notice for old package name

## Success Criteria

- ✅ All imports use `qe_tax_rag`
- ✅ All environment variables use `QE_TAX_RAG_` prefix
- ✅ All tests pass (23/23)
- ✅ Pre-commit hooks pass
- ✅ Package builds successfully
- ✅ Wheel contains only new package name
- ✅ No `quickexpense` or `QuickExpense` in source code
- ✅ Documentation consistently uses new name
- ✅ ~15-16 atomic commits created

## Timeline Estimate

- **Phase 0**: 5 minutes (documentation)
- **Phase 1**: 2 minutes (directory rename)
- **Phase 2**: 15 minutes (Python code updates)
- **Phase 3**: 10 minutes (config files)
- **Phase 4**: 10 minutes (user docs)
- **Phase 5**: 10 minutes (contributor docs)
- **Phase 6**: 5 minutes (scripts)
- **Phase 7**: 5 minutes (cleanup)
- **Phase 8**: 10 minutes (validation)

**Total estimated time**: ~70 minutes

---

**Last Updated**: 2025-10-16
**Status**: Ready for execution
