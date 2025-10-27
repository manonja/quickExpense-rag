# PDF Coverage Validation Plan (REVISED - YAML-Based)

**Date:** 2025-10-27 (Revised after Zen MCP consultation)
**Goal:** Quick filter to identify which PDF pages are NOT covered in existing YAML extractions

## Context

After consulting with Zen MCP, the original plan (Ghostscript + overlapping page-pairs) was identified as over-engineered for the stated goal of a "quick filter/check". This revision adopts a simpler, faster approach.

## Key Changes from Original Plan

### ❌ Rejected Approaches
- **Ghostscript subprocess** - 112 subprocess calls = slow (several minutes)
- **Overlapping page-pairs** - 2x processing overhead, ambiguous results
- **HTML corpus building** - Wrong comparison target (want to compare against extracted YAML, not raw HTML)

### ✅ New Approach: YAML Corpus + Single-Pass pdfplumber
- **Speed:** One pdfplumber pass in single Python process (orders of magnitude faster)
- **Accuracy:** Compare against already-extracted YAML (ground truth of what's been processed)
- **Simplicity:** Direct page-level scores (no pair ambiguity)
- **Uses existing tools:** pdfplumber already installed in project

## Strategic Rationale (from Zen MCP)

**Why use YAML corpus instead of HTML?**
- Compares against **ground truth** of already-extracted content
- Directly answers: "Do I already have this in my structured data?"
- If PDF page matches YAML corpus, re-running extraction is redundant
- More aligned with ultimate goal: avoid processing already-covered content

**Available YAML files:**
- `output/t4002-4/rules.yml` - 16 rules
- `output/t4002-6/rules.yml` - 2 rules
- `output/t4002-6/principles.yml` - 30 principles
- `output/t4002-10/tables.yml` - 2 tables (127 rows)

## Implementation Plan

### Phase 1: YAML Corpus Building

**Goal:** Build in-memory text corpus from all extracted YAML files

**Steps:**
1. Discover all YAML files in `output/` directory (rules.yml, principles.yml, tables.yml)
2. Load each YAML file and extract text content
3. For rules/principles: Extract `title` + `content` fields
4. For tables: Serialize table_data using order-independent representation
5. Apply aggressive text normalization
6. Concatenate into single reference corpus string

**Table Serialization (Critical for pdfplumber compatibility):**
```python
def serialize_table_row(row: dict[str, str]) -> str:
    """Convert table row to order-independent string.

    Example:
        Input:  {"Class No.": "10", "Depreciable property": "Chain-saws"}
        Output: "Class No.: 10 Depreciable property: Chain-saws"

    Why: pdfplumber may extract columns in different order than YAML.
    Sorting ensures consistent representation for fuzzy matching.
    """
    parts = [f"{k}: {v}" for k, v in row.items()]
    return " ".join(sorted(parts))
```

**Text Normalization:**
```python
def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching."""
    text = text.lower()
    text = text.replace("&nbsp;", " ").replace("&mdash;", "-")
    text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
    return text.strip()
```

### Phase 2: PDF Page Extraction (Single Pass)

**Goal:** Extract text from all PDF pages in one pass using pdfplumber

**Steps:**
1. Open PDF with pdfplumber
2. Iterate through all pages (1 to 113)
3. Extract text from each page using `.extract_text()`
4. Remove common header/footer patterns (optional)
5. Apply same text normalization as YAML corpus
6. Store in dictionary: `{page_num: normalized_text}`

**Implementation:**
```python
import pdfplumber

def extract_pdf_pages(pdf_path: str) -> dict[int, str]:
    """Extract text from all PDF pages in single pass."""
    pdf_pages = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            # Optional: Remove headers/footers
            text = remove_header_footer_patterns(text)
            pdf_pages[page_num] = normalize_text(text)

    return pdf_pages
```

### Phase 3: Fuzzy Matching & Classification

**Goal:** Compare each PDF page against YAML corpus and classify

**Steps:**
1. For each PDF page, calculate fuzzy match score against YAML corpus
2. Use `thefuzz.fuzz.token_set_ratio()` for order-independent matching
3. Classify pages based on score and text length:
   - Score >90% → "already_covered" (discard)
   - Text length <50 chars → "blank" (discard)
   - Otherwise → "needs_extraction" (keep)
4. Generate actionable JSON reports

**Implementation:**
```python
from thefuzz import fuzz

def classify_pages(pdf_pages: dict[int, str], yaml_corpus: str, threshold: int = 90) -> tuple[list, list]:
    """Classify pages as keep or discard."""
    keep_pages = []
    discard_pages = []

    for page_num, page_text in pdf_pages.items():
        score = fuzz.token_set_ratio(page_text, yaml_corpus)

        if score > threshold:
            discard_pages.append({
                "page": page_num,
                "reason": "already_covered",
                "confidence": score,
                "justification": f"High similarity ({score}%) to existing YAML content"
            })
        elif len(page_text) < 50:
            discard_pages.append({
                "page": page_num,
                "reason": "blank",
                "text_length": len(page_text),
                "justification": "Page contains minimal text"
            })
        else:
            keep_pages.append({
                "page": page_num,
                "score": score,
                "reason": "needs_extraction",
                "justification": f"Low similarity ({score}%) - likely new content"
            })

    return keep_pages, discard_pages
```

### Phase 4: Reporting

**Goal:** Generate actionable reports for extraction pipeline

**Output Files:**
1. `output/pdf_coverage/keep_pages.json` - Pages requiring extraction
2. `output/pdf_coverage/discard_pages.json` - Pages to skip (with justification)
3. `output/pdf_coverage/summary.md` - Human-readable summary

**Example keep_pages.json:**
```json
{
  "pdf_source": "cra_documents/T4002-Business-Expenses-Guide.pdf",
  "yaml_sources": ["output/t4002-4/rules.yml", "output/t4002-6/rules.yml", ...],
  "total_pages": 15,
  "pages": [
    {
      "page": 3,
      "score": 45,
      "reason": "needs_extraction",
      "justification": "Low similarity (45%) - likely new content"
    },
    {
      "page": 7,
      "score": 62,
      "reason": "needs_extraction",
      "justification": "Low similarity (62%) - likely new content"
    }
  ]
}
```

**Example discard_pages.json:**
```json
{
  "pdf_source": "cra_documents/T4002-Business-Expenses-Guide.pdf",
  "total_pages": 98,
  "pages": [
    {
      "page": 1,
      "reason": "already_covered",
      "confidence": 95,
      "justification": "High similarity (95%) to existing YAML content"
    },
    {
      "page": 2,
      "reason": "blank",
      "text_length": 12,
      "justification": "Page contains minimal text"
    }
  ]
}
```

## Script Structure

```
scripts/pdf_coverage/
  __init__.py

  # Core modules
  models.py          # Pydantic models (PageScore, CoverageReport)
  yaml_corpus.py     # Load YAML files, build text corpus
  normalizer.py      # Text normalization utilities
  pdf_extractor.py   # pdfplumber single-pass extraction
  matcher.py         # Fuzzy matching logic
  classifier.py      # Page classification logic
  report_generator.py # Generate JSON and markdown reports

  # CLI
  cli.py             # Typer CLI entry point
```

## Dependencies

**Already installed:**
- `pdfplumber` - PDF text extraction
- `pyyaml` - YAML parsing

**To add:**
```bash
uv add thefuzz          # Fuzzy string matching
uv add python-Levenshtein  # Speed up fuzzy matching
uv add typer            # CLI framework (if not already installed)
uv add rich             # CLI formatting (if not already installed)
```

## CLI Interface

```bash
# Run coverage check
uv run python scripts/pdf_coverage/cli.py check \
  --pdf cra_documents/T4002-Business-Expenses-Guide.pdf \
  --yaml-dir output/ \
  --output-dir output/pdf_coverage/ \
  --threshold 90

# Output:
# ✅ Loaded 4 YAML files (50 rules, 30 principles, 2 tables)
# ✅ Built corpus: 125,000 characters
# ✅ Extracted 113 PDF pages
# ✅ Matched pages: 98 covered, 15 need extraction
#
# Reports:
# - output/pdf_coverage/keep_pages.json (15 pages)
# - output/pdf_coverage/discard_pages.json (98 pages)
# - output/pdf_coverage/summary.md
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| ✅ Use existing YAML files | Compare against ground truth (already-extracted content) |
| ✅ pdfplumber single-pass | Fast, no subprocess overhead, already installed |
| ✅ Page-level scores | Simple, actionable (no pair ambiguity) |
| ✅ Order-independent table serialization | Handles column order differences between PDF and YAML |
| ✅ Aggressive text normalization | Handles formatting differences (whitespace, entities) |
| ✅ 90% similarity threshold | High confidence for "already covered" classification |
| ✅ token_set_ratio matching | Order-independent fuzzy matching (handles word reordering) |

## Known Limitations

1. **Incomplete YAML extraction:** If HTML had content NOT extracted to YAML, it won't be in corpus. PDF pages with this content will be flagged as "needs extraction" even if HTML had it. This is acceptable for a quick filter.

2. **Header/footer noise:** PDF pages contain headers/footers not in YAML corpus. This reduces match scores. Mitigated by optional header/footer removal patterns.

3. **Table formatting:** pdfplumber text extraction of tables is lossy (columns → spaces). Mitigated by order-independent serialization and aggressive normalization.

4. **False positives (keep pages):** Some pages might be flagged as "needs extraction" when they're actually covered but formatted very differently. This is acceptable - better to over-extract than miss content.

5. **False negatives (discard pages):** Less likely, but a page with new content might score high if it contains many references to already-extracted rules. Review keep_pages.json manually before processing.

## Success Criteria

- ✅ Identify pages already covered in YAML (>90% confidence)
- ✅ Identify pages needing extraction (low similarity)
- ✅ Fast execution (<1 minute for 113-page PDF)
- ✅ Actionable output (clear list of page numbers to process)
- ✅ No subprocess overhead (pure Python)

## Timeline Estimate

- YAML corpus builder: 1-2 hours
- pdfplumber integration: 1-2 hours
- Fuzzy matching + classification: 2-3 hours
- CLI + reporting: 1-2 hours
- Testing + validation: 2 hours
- **Total: 7-11 hours** (vs. 12-16 hours original Ghostscript plan)

## Future Enhancements

1. **Semantic similarity:** Use embeddings (BGE) instead of fuzzy matching for better accuracy
2. **Page range extraction:** Instead of individual pages, identify contiguous ranges (e.g., "pages 10-15 need extraction")
3. **Confidence calibration:** Tune threshold based on manual review of results
4. **Incremental updates:** Track which YAML files changed since last run, only re-build corpus if needed
5. **Visual diff:** Generate side-by-side PDF page vs YAML content comparison for manual review

## Revision History

- **2025-10-27 (Original):** Created Ghostscript + overlapping page-pair plan
- **2025-10-27 (First Revision):** Simplified to 2-phase with Ghostscript subprocess
- **2025-10-27 (Second Revision - This Version):**
  - ✅ Switched from Ghostscript to pdfplumber (faster, simpler)
  - ✅ Eliminated overlapping page-pairs (direct page-level comparison)
  - ✅ Changed corpus from HTML to YAML (ground truth comparison)
  - ✅ Added order-independent table serialization
  - ✅ Timeline reduced: 7-11 hours (vs. 12-16 hours)

**Next Steps:**
1. Add dependencies: `uv add thefuzz python-Levenshtein`
2. Create `scripts/pdf_coverage/` package structure
3. Implement YAML corpus builder
4. Implement pdfplumber page extractor
5. Implement fuzzy matcher + classifier
6. Implement CLI and reporting
7. Test on T4002 PDF
