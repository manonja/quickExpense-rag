# Release Process

This guide documents the manual release process for qe-tax-rag.

**Note**: Production PyPI releases will be automated via GitHub Actions (see TICKET 12).
This guide is for TestPyPI uploads and manual releases if needed.

## Prerequisites

### 1. Accounts & Tokens

- Create account on [TestPyPI](https://test.pypi.org/)
- Create account on [PyPI](https://pypi.org/)
- Generate API tokens from account settings:
  - TestPyPI: Account settings → API tokens → Add API token
  - PyPI: Account settings → API tokens → Add API token (scope: Entire account or
    specific project)

### 2. Tools

```bash
# Install build and upload tools
uv pip install build twine hatchling
```

## Release Workflow

### Step 1: Update Version

1. Update `__version__` in `src/qe_tax_rag/__init__.py`
   ```python
   __version__ = "X.Y.Z"
   ```
1. Update `CHANGELOG.md` with release notes
   - Add new `## [X.Y.Z] - YYYY-MM-DD` section
   - Document all changes under Added/Changed/Fixed/Removed
   - Add link at bottom:
     `[X.Y.Z]: https://github.com/manonja/qe-tax-rag/releases/tag/vX.Y.Z`
1. Commit version bump:
   ```bash
   git add src/qe_tax_rag/__init__.py CHANGELOG.md
   git commit -m "chore: bump version to X.Y.Z"
   git push
   ```

### Step 2: Build Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build wheel and sdist using hatchling
uv run hatchling build
```

This creates:

- `dist/qe_tax_rag-X.Y.Z-py3-none-any.whl` (wheel)
- `dist/qe_tax_rag-X.Y.Z.tar.gz` (source distribution)

### Step 3: Verify Build

```bash
# 1. Check metadata compliance
uv run twine check dist/*

# 2. Verify wheel contents (should show qe_tax_rag/ structure)
unzip -l dist/*.whl | grep "qe_tax_rag/"

# 3. Check wheel size (should be < 5MB)
ls -lh dist/

# 4. Inspect full wheel contents
unzip -l dist/*.whl
```

**Expected Results**:

- `twine check` shows "PASSED" for all files
- Wheel contains `qe_tax_rag/` directory with all modules
- `qe_tax_rag/py.typed` marker file present
- Wheel size < 5MB
- No `tests/`, `scripts/`, or `data/` directories in wheel

### Step 4: Test in Clean Environment

```bash
# Create isolated environment outside project directory
cd ..
uv venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install the wheel
uv pip install qe-tax-rag/dist/qe_tax_rag-*.whl

# Test import and version
python -c "import qe_tax_rag; print(qe_tax_rag.__version__)"

# Test basic import of public APIs
python -c "from qe_tax_rag import init, search, get_version; print('OK')"

# Test type hints are available
python -c "from qe_tax_rag import SearchResult; import typing; print(typing.get_type_hints(SearchResult))"

# Cleanup
deactivate
cd qe-tax-rag
rm -rf ../test_env
```

**Expected Results**:

- Installation succeeds without errors
- Version prints correctly (e.g., `0.1.0`)
- All public APIs importable
- Type hints available (py.typed working)
- No import errors or missing dependencies

### Step 5: Upload to TestPyPI

```bash
# Upload using API token (will prompt for username + token)
uv run twine upload --repository testpypi dist/*
```

**Authentication**:

- Username: `__token__`
- Password: Your TestPyPI API token (starts with `pypi-`)

**Alternative**: Use `.pypirc` file for credentials:

```ini
# ~/.pypirc
[testpypi]
  repository = https://test.pypi.org/legacy/
  username = __token__
  password = pypi-YOUR_TESTPYPI_TOKEN_HERE

[pypi]
  repository = https://upload.pypi.org/legacy/
  username = __token__
  password = pypi-YOUR_PYPI_TOKEN_HERE
```

### Step 6: Verify TestPyPI Installation

```bash
# In a new environment
cd ..
uv venv testpypi_verify
source testpypi_verify/bin/activate

# Install from TestPyPI
# Note: Dependencies must be available on PyPI (not TestPyPI)
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            qe-tax-rag

# Test
python -c "import qe_tax_rag as qe; print(qe.__version__)"

# Cleanup
deactivate
cd qe-tax-rag
rm -rf ../testpypi_verify
```

**Verify on TestPyPI**:

- Visit https://test.pypi.org/project/qe-tax-rag/
- Check README renders correctly
- Verify badges display
- Check classifiers and metadata

### Step 7: Create Git Tag

```bash
# Create annotated tag
git tag -a v0.1.0 -m "Release v0.1.0"

# Push tag to GitHub
git push origin v0.1.0
```

### Step 8: Upload to Production PyPI

**For automated releases via GitHub Actions**, see `.github/workflows/release.yml`
(TICKET 12)

**For manual release**:

```bash
# Upload to production PyPI
uv run twine upload dist/*
```

**Authentication**: Same as TestPyPI, but use your PyPI API token

### Step 9: Create GitHub Release

1. Go to https://github.com/manonja/qe-tax-rag/releases
1. Click "Create a new release"
1. Select tag: `v0.1.0`
1. Release title: `v0.1.0`
1. Description: Copy relevant section from CHANGELOG.md
1. Attach `dist/*.whl` and `dist/*.tar.gz` as release assets (optional)
1. Click "Publish release"

## Verification Checklist

Before uploading to PyPI, ensure:

- [ ] `twine check dist/*` passes without errors
- [ ] Wheel size < 5MB
- [ ] Import works in clean environment
- [ ] Version number displays correctly
- [ ] Legal disclaimer visible in README on PyPI/TestPyPI
- [ ] All runtime dependencies listed correctly in pyproject.toml
- [ ] No dev dependencies leak into runtime
- [ ] `py.typed` file present in wheel
- [ ] CHANGELOG.md updated with release notes
- [ ] Git tag created and pushed: `git tag v0.1.0 && git push --tags`
- [ ] All tests passing: `uv run pytest`
- [ ] All quality checks passing: `uv run pre-commit run --all-files`

## Troubleshooting

### Build fails with "No module named hatchling"

```bash
uv pip install hatchling
```

### Version mismatch after install

- Ensure `__version__` is updated in `src/qe_tax_rag/__init__.py`
- Clear build cache: `rm -rf dist/ build/ *.egg-info/`
- Rebuild: `uv run hatchling build`

### Import fails in clean environment

- Check wheel contents: `unzip -l dist/*.whl`
- Verify `qe_tax_rag/` structure is preserved (not `src/qe_tax_rag/`)
- Check for missing dependencies in `pyproject.toml` [project.dependencies]
- Ensure dependencies are pure Python or have wheels for target platform

### "Repository does not allow updating asset" error

- Package already exists with same version on PyPI/TestPyPI
- Bump version number in `__init__.py`
- Rebuild and retry

### README doesn't render on PyPI

- Check markdown formatting with `mdformat README.md`
- Verify no unsupported GitHub-specific syntax
- Test locally:
  `python -m readme_renderer README.md -o /tmp/readme.html && open /tmp/readme.html`

### Wheel size > 5MB

- Check for accidentally included data files:
  `unzip -l dist/*.whl | grep -E '\.(db|json|txt)$'`
- Verify `[tool.hatchling.build.targets.wheel]` excludes tests, scripts, data
- Check `.gitignore` patterns are respected

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking API changes
- **MINOR** (0.X.0): New features, backward-compatible
- **PATCH** (0.0.X): Bug fixes, backward-compatible

Examples:

- `0.1.0` → `0.1.1`: Bug fix
- `0.1.1` → `0.2.0`: New search filter option
- `0.2.0` → `1.0.0`: Change public API signature (breaking)

## Post-Release Checklist

After successful PyPI release:

- [ ] Update README badges if needed
- [ ] Announce on project channels (if applicable)
- [ ] Monitor PyPI project page for first 24 hours
- [ ] Test installation from PyPI in fresh environment
- [ ] Document any installation issues reported by early adopters
- [ ] Create GitHub Milestone for next release

## Emergency Rollback

If a release has critical issues:

1. **Cannot delete from PyPI** - versions are permanent
1. **Yank the release** (marks as unsuitable):
   ```bash
   # Via web UI: PyPI project page → Manage → Options → Yank release
   # Or via twine:
   twine yank qe-tax-rag <version>
   ```
1. **Release a patch version** with fixes (e.g., 0.1.1)
1. **Document the issue** in CHANGELOG under the fixed version

## Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Hatchling Documentation](https://hatch.pypa.io/latest/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [PyPI Help](https://pypi.org/help/)
- [TestPyPI](https://test.pypi.org/)
