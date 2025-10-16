# TICKET 11: PyPI Packaging - Implementation Plan

## Overview
Package quickexpense-rag for PyPI distribution following 80/20 principles - focus on essential packaging quality while deferring non-critical items.

**Total Estimated Time**: 2-2.5 hours
**Commit Strategy**: Small, atomic commits after each logical change

---

## Phase 1: Project Metadata & Configuration (30 min)

### 1.1 Fix `pyproject.toml` Package Configuration
**Issue Found**: Ticket specifies `packages = ["app"]` but project uses `src/quickexpense_rag/` layout

**Actions**:
1. Remove explicit `packages` declaration - rely on hatchling auto-discovery
2. Configure dynamic versioning from `__init__.py`
3. Add complete project metadata (classifiers, URLs, keywords)
4. Verify dependencies are correctly split (runtime vs dev)

**Key Changes to `pyproject.toml`**:
```toml
[project]
name = "quickexpense-rag"
dynamic = ["version"]
description = "Semantic search over CRA business expense rules"
readme = "README.md"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "your.email@example.com"}]
requires-python = ">=3.11"
keywords = ["cra", "rag", "tax", "canada", "semantic-search"]

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]

[project.urls]
Homepage = "https://github.com/<your-org>/quickexpense-rag"
Documentation = "https://github.com/<your-org>/quickexpense-rag/docs"
Repository = "https://github.com/<your-org>/quickexpense-rag"
Changelog = "https://github.com/<your-org>/quickexpense-rag/CHANGELOG.md"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.version]
path = "src/quickexpense_rag/__init__.py"
```

**📝 COMMIT 1**:
```
build: configure pyproject.toml for PyPI packaging

Configure hatchling build system with dynamic versioning:
- Remove explicit packages declaration (rely on auto-discovery)
- Add dynamic version sourced from __init__.py
- Add complete project metadata and classifiers
- Configure project URLs for PyPI landing page

Rationale:
- Hatchling auto-discovers src-layout packages correctly
- Dynamic versioning prevents version mismatch issues
- Complete metadata improves PyPI discoverability

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 1.2 Single-Source Version in `__init__.py`

**Action**:
- Update `src/quickexpense_rag/__init__.py` to define `__version__ = "0.1.0"`
- Hatchling will read it during build

**📝 COMMIT 2**:
```
build: add version 0.1.0 to package __init__

Define single-source version in __init__.py for hatchling:
- Set __version__ = "0.1.0" for initial release
- Hatchling reads this during build via dynamic versioning

Rationale:
- Single source of truth prevents version mismatches
- Follows modern Python packaging best practices

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 1.3 Create `py.typed` Marker File

**Action**:
- Create empty file at `src/quickexpense_rag/py.typed`
- Enables PEP 561 type hint distribution

**📝 COMMIT 3**:
```
build: add py.typed marker for type hint distribution

Create empty py.typed marker file for PEP 561 compliance:
- Enables type checkers to use our type hints
- Required for typed packages on PyPI

Rationale:
- Users running mypy/pyright will get full type checking support
- Standard practice for typed Python libraries

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 2: Essential Documentation Files (45 min)

### 2.1 Create `README.md`

**Structure** (priority order - what users see first):
1. **Title + Badges** (PyPI, Python versions, CI, License)
2. **⚠️ PROMINENT LEGAL DISCLAIMER** (NOT tax advice)
3. **What is this?** (one-sentence description)
4. **Key Features** (including many-to-many expense types)
5. **Installation** (`pip install quickexpense-rag`)
6. **Quick Start** (actual code from User Story 1)
7. **How It Works** (hybrid search explanation)
8. **Documentation** (link to docs)
9. **License** (MIT)

**Content Template**:
```markdown
# QuickExpense RAG

[![PyPI version](https://badge.fury.io/py/quickexpense-rag.svg)](https://badge.fury.io/py/quickexpense-rag)
[![Python versions](https://img.shields.io/pypi/pyversions/quickexpense-rag)](https://pypi.org/project/quickexpense-rag)
[![CI/CD Status](https://github.com/<your-org>/quickexpense-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-org>/quickexpense-rag/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚠️ IMPORTANT: NOT FINANCIAL OR TAX ADVICE

**This software is provided for informational purposes only and is not a substitute for professional financial or tax advice.** Always consult with a qualified tax professional or accountant before making financial decisions. CRA rules are complex, change frequently, and require professional interpretation. The developers assume no liability for any actions taken based on the use of this tool.

## What is this?

A Python library for semantic search over Canadian Revenue Agency (CRA) business expense rules. Built for ML engineers building expense classification agents.

## Key Features

- 🔍 **Hybrid Search**: Combines keyword (FTS5) + semantic search (vector embeddings)
- 🎯 **Smart Filtering**: Filter by province, business type, and expense categories
- 📚 **Authoritative Citations**: Returns CRA source URLs with citation IDs
- 🔗 **Many-to-Many Expense Types**: Rules can match multiple expense categories
- 🔒 **Privacy-First**: No API keys or network calls after initial setup
- 📦 **Lightweight**: Package < 5MB (database downloaded separately)
- ⚡ **Fast**: Local SQLite database with vector search

## Installation

```bash
pip install quickexpense-rag
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install quickexpense-rag
```

## Quick Start

```python
import quickexpense_rag as qe

# Initialize (downloads database on first run)
qe.init()

# Search for expense rules
results = qe.search(
    query="restaurant expense while traveling for training",
    province="BC",
    business_type="sole_proprietorship",
    expense_types=["meals", "travel"]
)

# Access results
for result in results:
    print(f"Citation: {result.citation_id}")
    print(f"Content: {result.content}")
    print(f"Source: {result.source_url}")
    print(f"Expense Types: {result.expense_types}")
    print(f"Disclaimer: {result.disclaimer}")
    print("---")
```

## How It Works

1. **Metadata Filtering**: SQL WHERE clause filters by province/business_type/expense_type
2. **FTS5 Keyword Search**: Exact term matching on filtered candidates
3. **Vector Semantic Search**: BGE-small-en-v1.5 embeddings with cosine similarity
4. **RRF Fusion**: Reciprocal Rank Fusion merges rankings for best results

**Data Distribution**:
- Code distributed via PyPI (`pip install quickexpense-rag`)
- Database downloaded from GitHub Releases on first `init()`
- Version compatibility checked automatically

## Documentation

- [Installation Guide](docs/installation.md)
- [API Reference](docs/reference/api.md)
- [Examples](docs/examples/)

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Remember**: This is informational content only. Always consult a qualified tax professional.
```

**📝 COMMIT 4**:
```
docs: create comprehensive README with legal disclaimers

Add README.md with complete project documentation:
- Prominent legal disclaimer (NOT tax advice)
- Installation instructions (pip and uv)
- Quick start example from User Story 1
- Key features including many-to-many expense types
- How It Works section explaining hybrid search
- Badges for PyPI, Python versions, CI, License

Rationale:
- Legal disclaimer protects users and developers
- Quick start enables immediate user onboarding
- Clear feature list highlights value proposition

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 2.2 Create `LICENSE` File

**Action**:
- Create `LICENSE` file with full MIT License text
- Use standard MIT template with copyright year and author

**📝 COMMIT 5**:
```
docs: add MIT License

Add MIT License file for PyPI distribution:
- Standard MIT License text
- Copyright notice with current year

Rationale:
- MIT License chosen for permissive open-source use
- Required for PyPI classifier "License :: OSI Approved :: MIT License"

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 2.3 Create `CHANGELOG.md`

**Action**:
- Follow [Keep a Changelog](https://keepachangelog.com/) format
- Document all features from tickets 1-10 in v0.1.0 entry

**Content Template**:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-XX

### Added
- Initial release of quickexpense-rag
- Hybrid search combining FTS5 keyword search and vector semantic search
- BGE-small-en-v1.5 embeddings for semantic similarity
- Reciprocal Rank Fusion (RRF) for ranking
- Many-to-many relationship for expense types (rules can have multiple categories)
- Metadata filtering by province (BC, AB, ON, QC)
- Metadata filtering by business type (sole_proprietorship, corporation, partnership)
- Metadata filtering by expense types (meals, travel, vehicle, home_office, etc.)
- SQLite database with FTS5 and sqlite-vec for efficient search
- Automatic database download from GitHub Releases
- SHA256 checksum verification for database integrity
- Version compatibility checking (schema version + data version)
- Legal disclaimers on all user-facing APIs
- Type hints with py.typed marker for PEP 561 compliance
- Comprehensive test suite (unit + integration tests)
- CI/CD with quality gates (ruff, mypy, pyright, pytest)
- Python 3.11+ support

### Documentation
- README with installation and quick start guide
- Legal disclaimers emphasizing this is NOT tax advice
- API reference documentation
- Examples and usage patterns

[0.1.0]: https://github.com/<your-org>/quickexpense-rag/releases/tag/v0.1.0
```

**📝 COMMIT 6**:
```
docs: add CHANGELOG for v0.1.0 release

Create CHANGELOG.md following Keep a Changelog format:
- Document all features from tickets 1-10
- List search capabilities, data handling, and quality features
- Include documentation and testing infrastructure

Rationale:
- Transparent release notes for users
- Required for professional open-source projects
- Referenced in pyproject.toml URLs

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 2.4 Create `RELEASING.md` (Maintainer Guide)

**Action**:
- Document manual TestPyPI and PyPI release process
- Include prerequisites, build steps, upload workflow

**Content Template**:
```markdown
# Release Process

This guide documents the manual release process for quickexpense-rag.

**Note**: Production PyPI releases are automated via GitHub Actions (see TICKET 12).
This guide is for TestPyPI uploads and manual releases if needed.

## Prerequisites

### 1. Accounts & Tokens
- Create account on [TestPyPI](https://test.pypi.org/)
- Create account on [PyPI](https://pypi.org/)
- Generate API tokens from account settings

### 2. Tools
```bash
# Install build and upload tools
uv pip install build twine
```

## Release Workflow

### Step 1: Update Version
1. Update `__version__` in `src/quickexpense_rag/__init__.py`
2. Update `CHANGELOG.md` with release notes
3. Commit changes: `git commit -m "chore: bump version to X.Y.Z"`

### Step 2: Build Package
```bash
# Clean previous builds
rm -rf dist/

# Build wheel and sdist
uv run hatch build
```

### Step 3: Verify Build
```bash
# Check metadata
uv run twine check dist/*

# Verify wheel contents
unzip -l dist/*.whl | grep "quickexpense_rag/"

# Check size < 5MB
ls -lh dist/
```

### Step 4: Test in Clean Environment
```bash
# Create isolated environment
cd ..
uv venv test_env
source test_env/bin/activate

# Install wheel
uv pip install quickexpense-rag/dist/*.whl

# Test import
python -c "import quickexpense_rag; print(quickexpense_rag.__version__)"

# Deactivate and cleanup
deactivate
rm -rf test_env
cd quickexpense-rag
```

### Step 5: Upload to TestPyPI
```bash
# Upload (will prompt for API token)
uv run twine upload --repository testpypi dist/*
```

### Step 6: Verify TestPyPI Installation
```bash
# In a new environment
pip install --index-url https://test.pypi.org/simple/ quickexpense-rag

# Test
python -c "import quickexpense_rag as qe; print(qe.__version__)"
```

### Step 7: Upload to Production PyPI
**For automated releases via GitHub Actions**, see `.github/workflows/release.yml`

**For manual release**:
```bash
uv run twine upload dist/*
```

## Verification Checklist

Before uploading to PyPI:
- [ ] `twine check dist/*` passes
- [ ] Wheel size < 5MB
- [ ] Import works in clean environment
- [ ] Version number displays correctly
- [ ] Legal disclaimer visible in README on PyPI
- [ ] All runtime dependencies listed correctly
- [ ] `py.typed` file present in wheel
- [ ] CHANGELOG.md updated with release notes
- [ ] Git tag created: `git tag v0.1.0 && git push --tags`

## Troubleshooting

### Build fails with "No module named hatchling"
```bash
uv pip install hatchling
```

### Version mismatch after install
- Ensure `__version__` is updated in `__init__.py`
- Clear build cache: `rm -rf dist/ build/ *.egg-info/`
- Rebuild

### Import fails in clean environment
- Check wheel contents: `unzip -l dist/*.whl`
- Verify `src/quickexpense_rag/` structure is preserved
- Check for missing dependencies in `pyproject.toml`
```

**📝 COMMIT 7**:
```
docs: add maintainer release guide

Create RELEASING.md with manual release workflow:
- Prerequisites (accounts, tools)
- Step-by-step build and upload process
- Clean environment testing
- Verification checklist
- Troubleshooting section

Rationale:
- Enables maintainers to perform manual releases
- Complements automated CI/CD (TICKET 12)
- Documents institutional knowledge

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 3: Build Verification (30 min)

### 3.1 Local Build & Checks

**Actions**:
```bash
# 1. Build packages
uv run hatch build

# 2. Validate metadata
uv run twine check dist/*

# 3. Verify wheel structure
unzip -l dist/*.whl | grep "quickexpense_rag/"

# 4. Check size < 5MB
ls -lh dist/

# 5. Inspect wheel contents
unzip -l dist/*.whl
```

**Expected Results**:
- Both `.whl` and `.tar.gz` created in `dist/`
- `twine check` reports "PASSED"
- Wheel contains `quickexpense_rag/` directory structure
- Wheel size < 5MB
- `py.typed` file present in wheel

**📝 COMMIT 8** (if any fixes needed):
```
build: fix package structure issues

Fix issues found during build verification:
- [List specific fixes made]

Rationale:
- Ensures clean package structure for PyPI

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 3.2 Clean Environment Test

**Actions**:
```bash
# Create isolated environment outside project
cd ..
uv venv clean_env
source clean_env/bin/activate

# Install wheel
uv pip install quickexpense-rag/dist/*.whl

# Test import & version
python -c "import quickexpense_rag; print(quickexpense_rag.__version__)"

# Test basic import of public API
python -c "from quickexpense_rag import init, search, get_version; print('OK')"

# Cleanup
deactivate
rm -rf clean_env
cd quickexpense-rag
```

**Expected Results**:
- Installation succeeds without errors
- Version prints correctly: `0.1.0`
- All public APIs importable
- No import errors or missing dependencies

**📝 COMMIT 9** (if dependency fixes needed):
```
build: fix missing runtime dependencies

Add missing dependencies to pyproject.toml:
- [List added dependencies]

Rationale:
- Clean environment test revealed missing imports
- Ensures package is self-contained

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 4: TestPyPI Upload (20 min)

### 4.1 Prerequisites Check

**Actions**:
1. Verify TestPyPI account created
2. Generate API token from TestPyPI account settings
3. Install twine: `uv pip install twine`

### 4.2 Upload & Verify

**Actions**:
```bash
# Upload to TestPyPI (will prompt for API token)
uv run twine upload --repository testpypi dist/*

# Test installation from TestPyPI in new environment
cd ..
uv venv testpypi_env
source testpypi_env/bin/activate

pip install --index-url https://test.pypi.org/simple/ quickexpense-rag

# Verify
python -c "import quickexpense_rag; print(quickexpense_rag.__version__)"

# Cleanup
deactivate
rm -rf testpypi_env
cd quickexpense-rag
```

**Expected Results**:
- Upload succeeds with "Upload complete" message
- Package visible on https://test.pypi.org/project/quickexpense-rag/
- Installation from TestPyPI succeeds
- Import and version check pass

**📝 COMMIT 10** (documentation update):
```
docs: add TestPyPI upload verification notes

Update RELEASING.md with TestPyPI upload results:
- Confirm successful upload to TestPyPI
- Document any issues encountered and resolutions
- Add TestPyPI package URL

Rationale:
- Documents successful completion of TICKET 11
- Provides reference for future releases

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Phase 5: Final Documentation (15 min)

### 5.1 Update Main Documentation

**Actions**:
1. Ensure all references to package name are correct
2. Update any placeholder URLs with actual GitHub repo URLs
3. Verify all badges link to correct URLs
4. Add TestPyPI link to README (for pre-release testing)

**📝 COMMIT 11**:
```
docs: finalize documentation for v0.1.0 release

Final documentation updates:
- Update all placeholder URLs to actual repo
- Verify badge links are correct
- Add TestPyPI installation instructions
- Polish README formatting

Rationale:
- Ensures professional presentation on PyPI
- All links functional for users

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Critical Verification Checklist

### Must Pass Before TestPyPI Upload:
- [ ] `twine check dist/*` passes without errors
- [ ] Wheel size < 5MB
- [ ] Import works in clean environment
- [ ] Version number displays correctly (`0.1.0`)
- [ ] Legal disclaimer prominent in README
- [ ] All runtime dependencies in `[project.dependencies]`
- [ ] No dev dependencies leak into runtime deps
- [ ] `py.typed` file present in wheel
- [ ] All URLs in pyproject.toml are valid (or use placeholders)
- [ ] LICENSE file contains full MIT text
- [ ] CHANGELOG.md has v0.1.0 entry

### Post-Upload Verification:
- [ ] Package visible on TestPyPI
- [ ] Installation from TestPyPI succeeds
- [ ] README renders correctly on TestPyPI
- [ ] All badges display (if links are live)
- [ ] Legal disclaimer visible on package page

---

## 80/20 Decisions

### ✅ Include in v0.1.0:
- Essential packaging metadata
- Clear README with legal disclaimers
- Working installation & import
- TestPyPI verification
- Manual release process documentation

### ⏭️ Defer to Later:
- Full documentation website (Sphinx/MkDocs)
- Extended tutorials and guides
- Advanced usage examples
- Automated PyPI releases (TICKET 12 handles this)
- Package signing/verification
- Multi-language README

---

## Timeline Summary

| Phase | Task | Time | Commits |
|-------|------|------|---------|
| 1 | Project Metadata & Config | 30 min | 3 commits |
| 2 | Documentation Files | 45 min | 4 commits |
| 3 | Build Verification | 30 min | 1-2 commits |
| 4 | TestPyPI Upload | 20 min | 1 commit |
| 5 | Final Documentation | 15 min | 1 commit |
| **Total** | **Full Implementation** | **2-2.5 hours** | **10-11 commits** |

---

## Success Criteria

Package successfully installs from TestPyPI and users can run:

```python
import quickexpense_rag as qe

# Check version
print(qe.__version__)  # Output: 0.1.0

# Initialize and search
qe.init()
results = qe.search("restaurant expense", province="BC")

# Verify legal disclaimer visible
print(results[0].disclaimer)  # Output: ⚠️ INFORMATIONAL ONLY - NOT TAX ADVICE...
```

---

## Notes for TICKET 12 (Next Step)

TICKET 12 will handle automated production PyPI releases via GitHub Actions:
- `.github/workflows/release.yml` for PyPI publishing on git tags
- Automated build, test, and upload on version tags
- GitHub Release creation with CHANGELOG

This ticket (11) establishes the manual release foundation that TICKET 12 will automate.
