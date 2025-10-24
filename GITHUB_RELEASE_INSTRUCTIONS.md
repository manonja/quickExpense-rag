# GitHub Release Instructions for data-v2025.10.23

## Checklist

Follow these steps to create the GitHub Release for the CRA rules database:

### Step 1: Navigate to Releases Page

1. Go to: https://github.com/manonja/quickExpense-rag/releases
1. Click: **"Draft a new release"**

### Step 2: Tag Information

- **Tag version**: `data-v2025.10.23`
- **Target**: `develop` branch (or after merging this PR)
- Click: **"Create new tag: data-v2025.10.23 on publish"**

### Step 3: Release Title

```
CRA Tax Rules Database - October 2025
```

### Step 4: Release Description

Copy and paste the following (from `data/RELEASE_NOTES_v2025.10.23.md`):

```markdown
Production SQLite database with CRA business expense rules.

## Database Statistics

- **Total Chunks:** 63 searchable expense rules
- **Schema Version:** 1.0
- **Data Version:** 2025.10.23
- **Embedding Model:** BGE-small-en-v1.5 (384 dimensions)
- **Source Documents:** CRA T4002 Business and Professional Income Guide
- **Source Files:** t4002-5.html
- **Lineage Coverage:** 100% (classic parser + adjudicator)
- **Expense Types:** 16 unique categories
- **Search Indices:** FTS5 full-text + sqlite-vec semantic search

## File Verification

**SHA256 Checksum:**
```

960601b0e7a1b73e59ce8f857b603516382341ba22729da9d90858bbf0f6125b

````

**Verify download:**
```bash
shasum -a 256 cra_rules.db
# Should match: 960601b0e7a1b73e59ce8f857b603516382341ba22729da9d90858bbf0f6125b
````

## Usage

Install the library:

```bash
pip install qe-tax-rag
```

The database will be downloaded automatically on first use:

```python
import qe_tax_rag as qe

# Downloads database from this GitHub Release
qe.init()

# Search expense rules
results = qe.search(
    query="restaurant meals for client meetings",
    province="BC",
    expense_types=["meals"]
)
```

## Quality Validation

This database has been validated through comprehensive testing:

- **Search Success Rate:** 10/10 queries (100% - exceeds 70% threshold)
- **Lineage Traceability:** 100% coverage with source document tracking
- **Integrity Checks:** All database constraints verified
- **Embedding Quality:** All 63 chunks have valid 384-dim vectors

See [PR #44](https://github.com/manonja/quickExpense-rag/pull/44) and
[PR #45](https://github.com/manonja/quickExpense-rag/pull/45) for full validation
reports.

## Distribution Model

- **Code:** Distributed via PyPI (`pip install qe-tax-rag`)
- **Database:** Downloaded from GitHub Releases on first use
- **Versioning:** Schema version + data version stored in database metadata
- **Integrity:** SHA256 checksums verified on download

## Disclaimer

⚠️ **IMPORTANT: NOT FINANCIAL OR TAX ADVICE**

This software is provided for informational purposes only and is not a substitute for
professional financial or tax advice. Always consult with a qualified tax professional
before making financial decisions.

## Support

- Documentation: https://github.com/manonja/quickExpense-rag
- Issues: https://github.com/manonja/quickExpense-rag/issues
- Examples: See `examples/` directory in repository

````

### Step 5: Upload Database File

1. Click **"Attach binaries by dropping them here or selecting them"**
2. Navigate to: `data/cra_rules.db` (1.7 MB)
3. Upload the file
4. Wait for upload to complete (green checkmark appears)

### Step 6: Publish Release

1. **DO NOT** check "Set as a pre-release"
2. **DO NOT** check "Set as the latest release" (this is code, not data)
3. Click: **"Publish release"**

### Step 7: Verify Release

After publishing:

1. Go to: https://github.com/manonja/quickExpense-rag/releases
2. Confirm `data-v2025.10.23` appears in releases list
3. Click on the release
4. Verify download URL works: https://github.com/manonja/quickExpense-rag/releases/download/data-v2025.10.23/cra_rules.db
5. Test download:

   ```bash
   curl -L -O https://github.com/manonja/quickExpense-rag/releases/download/data-v2025.10.23/cra_rules.db
   shasum -a 256 cra_rules.db
   # Should output: 960601b0e7a1b73e59ce8f857b603516382341ba22729da9d90858bbf0f6125b
````

### Step 8: Update Library (if needed)

If the download URL in `src/qe_tax_rag/settings.py` was a placeholder:

1. Verify the actual URL works
1. Update `settings.py` with the correct URL if different
1. Commit the change

## Troubleshooting

### Upload Fails

- Check file size (should be ~1.7 MB)
- Try different browser
- Ensure stable internet connection
- Try uploading from desktop instead of web UI

### Wrong File Uploaded

1. Delete the release (not just draft)
1. Start over from Step 1
1. **Important**: GitHub caches release assets, so the tag must be deleted and recreated

### SHA256 Doesn't Match

This is a critical error - DO NOT publish the release:

1. Recalculate SHA256: `shasum -a 256 data/cra_rules.db`
1. Update `src/qe_tax_rag/settings.py` with correct checksum
1. Verify database file integrity
1. Check if file was corrupted during copy

## After Release

1. Test end-to-end download:

   ```bash
   rm -rf ~/.cache/qe_tax_rag/
   python -c "import qe_tax_rag as qe; qe.init()"
   ```

1. Verify examples work:

   ```bash
   python examples/basic_rag.py
   ```

1. Update Linear ticket PRE-148 with release URL

1. Celebrate! 🎉
