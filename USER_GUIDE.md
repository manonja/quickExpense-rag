# QE Tax RAG - User Guide

**Quick Start Guide for Testing Your RAG System**

**Date:** 2025-10-18 | **Status:** Ready for Testing ✅

---

## 🎯 What You'll Learn

This guide shows you how to:

1. Build a searchable database from CRA documents (1 command, ~5 minutes)
2. Run queries against your database using Python
3. Test with real scenarios to validate the system

**No API key required** for the extraction pipeline!

---

## 🚀 Quick Start (80/20 Path)

### Prerequisites

```bash
# Ensure you have uv installed and dependencies synced
uv sync

# Verify you have CRA HTML documents
ls cra_documents/cra_t4002e_rev24_dump/*.html
```

### Step 1: Build Your Database

Run the complete pipeline with a single command:

```bash
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules.db
```

**What this does:**

- **Stage 1/3:** Extracts rules from HTML using high-quality parsers (Classic + LLM with adjudication)
- **Stage 2/3:** Transforms YAML → JSONL → SQLite database with FTS5 + vector embeddings
- **Stage 3/3:** Validates database integrity

**Expected output:**

```
✅ Stage 1/3: Extracting and transforming rules
   Extracted 247 rules to YAML
   Transformed 247/247 rules to JSONL

✅ Stage 2/3: Building searchable database
   Database built: data/cra_rules.db
   Database size: 15.23 MB

✅ Stage 3/3: Validating database
   Validation passed

🎉 Pipeline complete!
```

**Time:** ~3-5 minutes for T4002 (247 rules)

### Step 2: Search Your Database

Create a test script `test_search.py`:

```python
"""Test script for QE Tax RAG search."""
import qe_tax_rag as qe

# Initialize the library (loads data/cra_rules.db by default)
qe.init()

# Run a simple search
results = qe.search("restaurant meal expense", top_k=5)

# Display results
print(f"Found {len(results)} results:\n")
for i, r in enumerate(results, 1):
    print(f"{i}. Citation: {r.citation_id} (Score: {r.score:.2f})")
    print(f"   Content: {r.content[:200]}...")
    print(f"   Source: {r.source_url}")
    print(f"   Expense Types: {r.expense_types}")
    print(f"   Income Types: {r.income_type}")
    print(f"   ⚠️  {r.disclaimer[:80]}...")
    print()
```

Run it:

```bash
uv run python test_search.py
```

**Expected output:**

```
Found 5 results:

1. Citation: LINE-8523 (Score: 0.92)
   Content: Meals and entertainment You can deduct 50% of food, beverage, and entertainment expenses...
   Source: file:///Users/.../t4002-5.html
   Expense Types: ['meals']
   Income Types: ['business', 'fishing']
   ⚠️  This information is NOT tax advice. Consult a qualified tax professional...
```

---

## 🧪 Test Scenarios

Validate your system with these queries:

### 1. Keyword Match (High Precision)

```python
results = qe.search("meals and entertainment", top_k=3)
# Expected: LINE-8523 as top result with high score (>0.85)
```

### 2. Line Item Query (Exact Match)

```python
results = qe.search("Line 8523", top_k=3)
# Expected: LINE-8523 as the only result with score ~1.0
```

### 3. Semantic Search (Understanding Intent)

```python
results = qe.search("Can I deduct my car's gas?", top_k=5)
# Expected: Vehicle expense rules (fuel, mileage, CCA)
```

### 4. Conceptual Query (Broad Coverage)

```python
results = qe.search("What are common business expenses?", top_k=10)
# Expected: Diverse results (meals, travel, vehicle, advertising, etc.)
```

### 5. Filtering by Income Type

```python
results = qe.search("vehicle", income_type="fishing", top_k=3)
# Expected: Only rules applicable to fishing income
```

### 6. Edge Case (No Matches)

```python
results = qe.search("xyzabc123", top_k=5)
# Expected: 0 results (or very low relevance scores <0.1)
```

---

## 🔧 Advanced Usage

### Keep Intermediate Files for Debugging

```bash
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules.db \
  --intermediate-dir output/ \
  --keep-intermediate
```

This preserves:

- `output/rules.yml` - Extracted rules (YAML)
- `output/chunks.jsonl` - Transformed chunks (JSONL)
- `output/manual_review.yml` - Edge cases requiring review (if any)

### Manual Stage-by-Stage Execution

For debugging or inspection:

```bash
# Stage 1: Extract HTML → YAML
uv run extract-rules run \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/rules.yml \
  --manual-review-file output/manual_review.yml

# Stage 2: Transform YAML → JSONL
uv run extract-rules run \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/rules.yml \
  --auto-transform \
  --output-jsonl output/chunks.jsonl

# Stage 3: Build database from JSONL
uv run python scripts/cli.py build \
  --input-file output/chunks.jsonl \
  --output-db data/cra_rules.db

# Stage 4: Validate
uv run python scripts/cli.py validate \
  --db-path data/cra_rules.db
```

### Alternative: Gemini Pipeline (Legacy)

If you want to compare with the original Gemini-based pipeline:

```bash
# Requires GEMINI_API_KEY
export GEMINI_API_KEY="your-key-here"

uv run python scripts/cli.py pipeline \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules_gemini.db
```

**Use cases for Gemini pipeline:**

- Comparing search quality on conceptual queries
- Generating narrative context for documentation
- Fallback if extraction pipeline has issues

**Recommendation:** Use extraction pipeline (`pipeline-extraction`) as default.

---

## 🎓 Understanding Search Results

### Result Fields

```python
SearchResult(
    citation_id="LINE-8523",           # Unique identifier
    content="Meals and entertainment...", # Rule text
    source_url="file:///.../t4002-5.html", # Original source
    score=0.92,                        # Relevance (0.0-1.0)
    province=None,                     # Province filter (if applicable)
    business_type=None,                # Business type filter
    expense_types=["meals"],           # Expense categories
    income_type=["business", "fishing"], # Income types
    retrieved_at="2025-10-18T...",     # Timestamp
    disclaimer="This information is NOT tax advice..." # Legal warning
)
```

### Score Interpretation

- **0.9-1.0:** Exact or near-exact match
- **0.7-0.9:** Strong relevance
- **0.5-0.7:** Moderate relevance
- **<0.5:** Weak relevance (may not be useful)

### Hybrid Search (RRF)

The system combines two techniques:

1. **FTS5 Keyword Search:** Exact term matching
2. **Vector Semantic Search:** Meaning-based matching (BGE embeddings)
3. **Reciprocal Rank Fusion (RRF):** Merges both rankings

This gives you the best of both worlds: precision and semantic understanding.

---

## 🐛 Troubleshooting

### "No HTML files found"

```
Error: No HTML files found in cra_documents/cra_t4002e_rev24_dump/
```

**Fix:** Verify the directory path and ensure `.html` files exist:

```bash
ls cra_documents/cra_t4002e_rev24_dump/*.html | head -5
```

### "Database not found"

```
Error: Database not found: data/cra_rules.db
```

**Fix:** Run `pipeline-extraction` first to build the database.

### "GEMINI_API_KEY not set" (for Gemini pipeline only)

```
Error: GEMINI_API_KEY environment variable not set
```

**Fix:** This error only applies to the legacy `pipeline` command. The new `pipeline-extraction` command **does not require** an API key.

### Low relevance scores (all results <0.5)

**Possible causes:**

- Query is too vague or generic
- Database doesn't contain relevant content
- Typos in query

**Fix:** Try more specific queries with keywords from the CRA documents.

### No results returned

**Possible causes:**

- Query is completely unrelated to tax rules
- Database is empty or corrupted

**Fix:**

1. Validate database: `uv run python scripts/cli.py validate --db-path data/cra_rules.db`
2. Check row counts in validation output
3. Rebuild database if necessary

---

## 📊 Performance Expectations

### Pipeline Execution Time

- **T4002 (247 rules):** ~3-5 minutes
- **Larger document sets:** ~10-15 minutes (500-1000 rules)

### Search Latency

- **Target:** <250ms per query
- **Typical:** 50-150ms on modern hardware
- **With filtering:** May add 10-50ms

### Database Size

- **T4002:** ~15 MB
- **Includes:** Rules text + FTS5 index + 384-dim vector embeddings

---

## 🔗 Next Steps

1. **Run the Quick Start** - Build your database and test basic queries
2. **Try Test Scenarios** - Validate keyword, semantic, and filtering queries
3. **Explore Advanced Usage** - Inspect intermediate files, compare pipelines
4. **Read Architecture Docs** - See `RAG_SYSTEM_STATUS_AND_TESTING.md` for details
5. **Contribute** - See `CONTRIBUTING.md` for development guidelines

---

## 📚 Additional Resources

- **Developer Guide:** `CLAUDE.md`
- **System Status:** `RAG_SYSTEM_STATUS_AND_TESTING.md`
- **Pipeline Comparison:** `docs/howto/choosing-extraction-vs-gemini.md`
- **API Reference:** See `src/qe_tax_rag/api.py` docstrings

---

**Happy Testing! 🎉**

If you encounter issues, check `RAG_SYSTEM_STATUS_AND_TESTING.md` or open an issue on GitHub.
