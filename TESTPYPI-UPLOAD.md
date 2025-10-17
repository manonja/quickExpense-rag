# TestPyPI Upload Instructions

This document provides step-by-step instructions for uploading `qe-tax-rag` v0.1.0 to
TestPyPI.

## Status

✅ **Package Built and Verified**

- Wheel: `dist/qe_tax_rag-0.1.0-py3-none-any.whl` (36 KB)
- Source: `dist/qe_tax_rag-0.1.0.tar.gz` (1.5 MB)
- `twine check`: PASSED
- Clean environment test: PASSED
- All public APIs importable

## Prerequisites

### 1. Create TestPyPI Account

1. Visit https://test.pypi.org/account/register/
1. Fill in your details and verify email
1. Complete registration

### 2. Generate API Token

1. Log in to TestPyPI
1. Go to Account Settings → API tokens
1. Click "Add API token"
1. Token name: `qe-tax-rag-upload`
1. Scope: "Entire account" (or specific to project after first upload)
1. Click "Add token"
1. **IMPORTANT**: Copy the token immediately (starts with `pypi-`)
1. Store securely (you won't see it again)

### 3. Verify Build Tools Installed

```bash
# Should already be installed from build phase
uv pip list | grep -E "(twine|hatchling)"
# Expected output:
# hatchling   1.27.0
# twine       6.2.0
```

## Upload Process

### Step 1: Navigate to Project Directory

```bash
cd /Users/manonjacquin/Documents_local/POCs/qe-tax-rag
```

### Step 2: Verify Built Packages Exist

```bash
ls -lh dist/
# Should show:
# qe_tax_rag-0.1.0-py3-none-any.whl (36 KB)
# qe_tax_rag-0.1.0.tar.gz (1.5 MB)
```

### Step 3: Upload to TestPyPI

```bash
uv run twine upload --repository testpypi dist/*
```

**Authentication Prompts**:

- Username: `__token__`
- Password: `pypi-...` (your API token from Prerequisites step 2)

**Expected Output**:

```
Uploading distributions to https://test.pypi.org/legacy/
Uploading qe_tax_rag-0.1.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 37.2/37.2 kB • 00:00 • ?
Uploading qe_tax_rag-0.1.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.5/1.5 MB • 00:01 • ?

View at:
https://test.pypi.org/project/qe-tax-rag/0.1.0/
```

### Step 4: Verify Upload on TestPyPI

1. Visit https://test.pypi.org/project/qe-tax-rag/
1. Check that version 0.1.0 is listed
1. Verify README renders correctly
1. Check metadata (classifiers, Python versions, license)
1. Verify badges display (some may not work on TestPyPI)

## Verification Testing

### Test Installation from TestPyPI

```bash
# Create fresh test environment
cd ..
uv venv testpypi_verify
source testpypi_verify/bin/activate

# Install from TestPyPI
# Note: --extra-index-url needed because dependencies are on PyPI, not TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            qe-tax-rag

# Verify installation
python -c "import qe_tax_rag as qe; print(f'✅ Version: {qe.__version__}')"
# Expected: ✅ Version: 0.1.0

# Test public API imports
python -c "from qe_tax_rag import init, search, get_version; print('✅ All APIs importable')"
# Expected: ✅ All APIs importable

# Cleanup
deactivate
cd qe-tax-rag
rm -rf ../testpypi_verify
```

### Test Basic Functionality (Optional)

**Note**: This requires the database to be available. For now, just test imports.

```python
import qe_tax_rag as qe

# This will fail without database uploaded to GitHub Releases
# qe.init()  # Skip for TestPyPI verification

# Verify type hints work
from qe_tax_rag import SearchResult
import typing
hints = typing.get_type_hints(SearchResult)
print(f"✅ Type hints available: {len(hints)} fields")
```

## Success Criteria

Upload is successful if:

- [ ] Package visible at https://test.pypi.org/project/qe-tax-rag/0.1.0/
- [ ] README renders correctly with legal disclaimer at top
- [ ] All metadata correct (Python 3.11+, Beta status, MIT license)
- [ ] `pip install` from TestPyPI succeeds
- [ ] Version 0.1.0 imports correctly
- [ ] All public APIs importable
- [ ] Type hints available (py.typed working)

## Troubleshooting

### "403 Forbidden" Error

- **Cause**: Invalid API token or insufficient permissions
- **Fix**: Regenerate API token, ensure "Entire account" scope

### "400 Bad Request: File already exists"

- **Cause**: Version 0.1.0 already uploaded (can't overwrite)
- **Fix**: Bump version to 0.1.1 in `__init__.py`, rebuild, re-upload

### Dependencies Fail to Install

- **Cause**: Some dependencies not on TestPyPI
- **Fix**: Use `--extra-index-url https://pypi.org/simple/` (already in command above)

### Import Error After Install

- **Cause**: Package structure issue or missing dependencies
- **Fix**: Check `unzip -l dist/*.whl` for correct structure, verify dependencies in
  pyproject.toml

## Next Steps After TestPyPI Success

1. **Tag the Release**:

   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0 - First beta release"
   git push origin v0.1.0
   ```

1. **Prepare for Production PyPI**:

   - Review TestPyPI feedback
   - Fix any issues found during verification
   - Create production PyPI account and token
   - Upload to production PyPI (see RELEASING.md)

1. **GitHub Release**:

   - Create GitHub Release from v0.1.0 tag
   - Attach wheel and sdist as assets
   - Copy CHANGELOG content to release notes

1. **Database Upload** (TICKET 12):

   - Upload database artifact to GitHub Releases
   - Update `db_download_url` in settings
   - Test end-to-end `qe.init()` + `qe.search()`

## Support

If you encounter issues:

1. Check RELEASING.md troubleshooting section
1. Verify package structure: `unzip -l dist/*.whl`
1. Test in clean environment before uploading
1. Review TestPyPI documentation: https://test.pypi.org/help/

## Reference

- TestPyPI: https://test.pypi.org/
- PyPI: https://pypi.org/
- Twine docs: https://twine.readthedocs.io/
- Full release guide: [RELEASING.md](RELEASING.md)
