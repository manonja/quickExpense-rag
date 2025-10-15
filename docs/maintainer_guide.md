# Maintainer Guide: Document Preprocessing Workflow

This guide documents the manual download and preprocessing workflow for CRA (Canadian Revenue Agency) tax documents. The preprocessing pipeline (TICKET 9A) converts raw HTML/PDF files into clean text for downstream LLM parsing (TICKET 9B: Gemini Flash).

---

## Overview

**Why manual downloads?** Automated web scraping is brittle and breaks frequently when CRA updates their website. Manual downloads by the maintainer eliminate this maintenance burden while keeping costs negligible (~$1.59 for 50 documents with Gemini Flash).

**Workflow Summary**:

1. Maintainer manually downloads CRA HTML/PDF files → `data/raw/`
2. Preprocessing script extracts clean text → `data/preprocessed/`
3. Gemini Flash parses text into structured chunks → `data/processed/chunks.jsonl` (TICKET 9B)
4. Index builder creates searchable database → `data/cra_rules.db` (TICKET 9C)

---

## Step 1: Manual Document Download

### 1.1 Target URLs

**Primary Source**: [CRA Income Tax Folios](https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios.html)

**Focus Areas**:

- **Series 1**: Individuals (personal expenses, home office)
- **Series 3**: Business (business expenses, deductions)
- **Series 4**: Enterprises (corporate expenses, capital cost allowance)

**Filter Criteria**: Focus on expense-related folios only. Look for keywords:

- "expense", "deduction", "allowance"
- "meals", "travel", "vehicle", "home office"
- "capital cost", "depreciation"

### 1.2 Downloading Documents

For each relevant folio:

1. **Navigate to the folio page** (e.g., S3-F2-C1: Capital Cost of Depreciable Property)
2. **Download the HTML version**:
   - Right-click → "Save Page As..." → Save as `S3-F2-C1.html`
   - Use the folio ID (e.g., S3-F2-C1) as the filename
3. **Download the PDF version** (if available):
   - Click "Download PDF" link → Save as `S3-F2-C1.pdf`
4. **Save to `data/raw/`** directory

**Naming Convention**:

- Use the CRA folio ID from the URL
- Examples: `S3-F2-C1.html`, `S4-F8-C3.pdf`, `S1-F1-C1.html`
- Pattern: `S{series}-F{folio}-C{chapter}.{extension}`

**Example URLs**:

```
Series 3, Folio 2, Chapter 1 (Capital Cost):
https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios-index/series-3-property-investments-savings-plans/folio-2-capital-cost-allowance/income-tax-folio-s3-f2-c1-capital-cost-depreciable-property.html

Series 3, Folio 4, Chapter 1 (Business Expenses):
https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios-index/series-3-property-investments-savings-plans/folio-4-general-discussion-capital-cost-allowance/income-tax-folio-s3-f4-c1-general-discussion-capital-cost-allowance.html
```

### 1.3 Document Selection

**How many documents?** Aim for ~50-100 folios covering major expense categories:

- ✅ Meals and entertainment
- ✅ Travel and lodging
- ✅ Vehicle expenses
- ✅ Home office deductions
- ✅ Professional fees
- ✅ Advertising and promotion
- ✅ Capital cost allowance (CCA)
- ✅ Business use of personal property

**Quality over quantity**: Prefer comprehensive, authoritative folios over all available documents.

---

## Step 2: Preprocessing Workflow

### 2.1 Directory Structure

After downloading, your directory should look like:

```
data/
  raw/
    S1-F1-C1.html
    S3-F2-C1.html
    S3-F2-C1.pdf
    S4-F8-C3.html
    ...
  preprocessed/        # Will be created by preprocessing script
  processed/           # Will be created by Gemini parser (TICKET 9B)
```

### 2.2 Running the Preprocessing Script

**Prerequisites**:

```bash
# Install indexing dependencies
uv sync --extra indexing

# Verify dependencies installed
uv run python -c "import bs4, pdfplumber; print('Dependencies OK')"
```

**Run Preprocessing**:

```bash
# Process all HTML/PDF files in data/raw/
uv run python scripts/cli.py preprocess \
  --input-dir data/raw \
  --output-dir data/preprocessed
```

**Expected Output**:

```
data/preprocessed/
  S1-F1-C1.txt
  S3-F2-C1.txt
  S4-F8-C3.txt
  ...
```

**Manifest Generation**: The preprocessing script automatically creates `data/raw/manifest.json` with metadata for each document:

```json
[
  {
    "filename": "S3-F2-C1.html",
    "source_url": "https://www.canada.ca/...",
    "downloaded_at": "2024-12-15T10:00:00Z",
    "sha256": "abc123..."
  }
]
```

### 2.3 Validation

**Verify Preprocessing Success**:

```bash
# Check that all input files were processed
ls -1 data/raw/*.html data/raw/*.pdf | wc -l
ls -1 data/preprocessed/*.txt | wc -l
# Should be equal (or close if some files failed)

# Inspect a sample output file
head -n 50 data/preprocessed/S3-F2-C1.txt
```

**Quality Checks**:

1. **Text is clean**: No HTML tags, no JavaScript, no CSS
2. **Structure preserved**: Headings, paragraphs, lists are readable
3. **No excessive whitespace**: Max 2 consecutive newlines
4. **Encoding correct**: Special characters (é, à, etc.) display properly

**Common Issues**:

- **Empty output file**: PDF might be scanned images (no text layer)
- **Garbled text**: Encoding issue - verify UTF-8
- **Missing sections**: HTML structure unusual - check logs for warnings

---

## Step 3: SHA256 Hash Computation

**Purpose**: SHA256 hashes ensure data integrity and track source document changes.

**Automated**: The preprocessing script (`preprocess_file()`) automatically computes SHA256 hashes during processing and stores them in `data/raw/manifest.json`.

**Manual Verification** (optional):

```bash
# Compute SHA256 hash of a file
shasum -a 256 data/raw/S3-F2-C1.html

# Compare against manifest.json
jq '.[] | select(.filename == "S3-F2-C1.html") | .sha256' data/raw/manifest.json
```

---

## Step 4: Manifest Schema

**File**: `data/raw/manifest.json`

**Schema**:

```json
{
  "documents": [
    {
      "filename": "S3-F2-C1.html",
      "source_url": "https://www.canada.ca/...",
      "downloaded_at": "2024-12-15T10:00:00Z",
      "sha256": "abc123def456..."
    }
  ],
  "created_at": "2024-12-15T12:00:00Z"
}
```

**Field Descriptions**:

- `filename`: Original filename (e.g., `S3-F2-C1.html`)
- `source_url`: Full CRA URL where document was downloaded
- `downloaded_at`: ISO 8601 timestamp (UTC) when file was downloaded
- `sha256`: SHA256 hash (64 hex characters) of the original file
- `created_at`: Manifest creation timestamp (UTC)

**Validation**: The manifest is validated using Pydantic models (`scripts/preprocessor/models.py`):

- Filename must end with `.html` or `.pdf`
- SHA256 must be exactly 64 hexadecimal characters
- Timestamps must be valid ISO 8601 format

---

## Step 5: Next Steps (TICKET 9B: Gemini Parser)

After preprocessing completes, the next step is **TICKET 9B: Gemini Flash Parser**:

1. **Input**: Clean text files in `data/preprocessed/`
2. **Process**: Gemini Flash parses text into structured chunks with citations
3. **Output**: `data/processed/chunks.jsonl` with metadata
4. **Cost**: ~$1.59 for 50 documents (negligible)

See `docs/TICKET-9B-plan.md` (future) for Gemini parsing workflow.

---

## Troubleshooting

### Problem: Preprocessing script fails with "No such file or directory"

**Solution**: Ensure `data/raw/` directory exists and contains HTML/PDF files.

```bash
mkdir -p data/raw
ls data/raw/
```

### Problem: Empty `.txt` files in `data/preprocessed/`

**Possible Causes**:

1. **Scanned PDF**: PDF contains images, not text. Solution: Use OCR or skip file.
2. **Unusual HTML structure**: No `<main>`, `<article>`, or `<body>` tags. Check logs for warnings.
3. **Encoding issue**: File not UTF-8. Re-download or convert encoding.

**Debug**:

```bash
# Check file size
ls -lh data/raw/problem-file.html

# Check raw content
head -n 20 data/raw/problem-file.html

# Run preprocessing with verbose logging
uv run python scripts/cli.py preprocess --verbose
```

### Problem: SHA256 mismatch

**Cause**: File changed after manifest was created (e.g., re-downloaded).

**Solution**: Re-run preprocessing to regenerate manifest with updated hashes.

---

## Maintenance Schedule

**When to update documents?**

- **Quarterly**: CRA updates folios 2-4 times per year
- **Monitor**: CRA announcements, tax year changes, budget updates
- **Incremental**: Download only new/updated folios, not full re-download

**Update Workflow**:

1. Check CRA website for updated folios
2. Download new/updated documents to `data/raw/`
3. Re-run preprocessing script
4. Re-run Gemini parser (TICKET 9B)
5. Rebuild database (TICKET 9C)
6. Publish new release (TICKET 12)

**Cost per update**: ~$0.03 per document with Gemini Flash (negligible).

---

## Best Practices

### ✅ Do

- Use consistent naming convention (folio IDs)
- Save both HTML and PDF when available (HTML preferred for parsing)
- Run preprocessing immediately after downloading (verify quality)
- Keep `data/raw/manifest.json` version-controlled
- Document any manual fixes or special cases in comments

### ❌ Don't

- Don't automate scraping (violates 80/20 principle, adds brittleness)
- Don't modify downloaded files manually (breaks SHA256 verification)
- Don't skip manifest creation (needed for provenance tracking)
- Don't commit large binary files to git (use `.gitignore`)

---

## File Sizes & Storage

**Typical Sizes**:

- HTML file: 50-200 KB
- PDF file: 100-500 KB
- Preprocessed .txt: 20-100 KB
- Total for 50 documents: ~10-20 MB (raw + preprocessed)

**Git Storage**:

- Add `data/raw/*.html` and `data/raw/*.pdf` to `.gitignore`
- Commit `data/raw/manifest.json` (small, important for provenance)
- Keep `data/preprocessed/` in `.gitignore` (regenerable)

---

## Contact & Support

**Questions?** See `CLAUDE.md` for project guidelines and architecture decisions.

**Issues?** Check logs in `.log/` directory (if enabled) or run with `--verbose` flag.

**Updates to this guide?** Maintainers should update this document when workflow changes.

---

**Last Updated**: 2025-10-15
**Related Tickets**: TICKET 9A (Preprocessing), TICKET 9B (Gemini Parser), TICKET 9C (Index Builder)
