# QE Tax RAG System - Current Status & Testing Guide

**Date:** 2025-10-17
**Status:** System Architecture Analysis & Testing Plan

---

## 🎯 Executive Summary

### Critical Finding: Two Separate Pipelines

Your QE Tax RAG system currently has **TWO independent pipelines**:

1. **Pipeline 1 (Working RAG)** ✅ - Original Gemini-based pipeline that produces a functional searchable database
2. **Pipeline 2 (New Extraction)** ⚠️ - High-quality HTML-to-YAML extraction (TICKETS 1-6 complete) that is **NOT connected** to the RAG database

**Bottom Line:** You can test the RAG system TODAY using Pipeline 1. The new extraction pipeline produces excellent YAML output but requires a transformer to integrate with the RAG database.

---

## 📊 System Architecture

### Pipeline 1: Working RAG System ✅ (Original Gemini-based)

This is the **ONLY functional end-to-end RAG flow** that exists today.

**Flow:**
```
HTML/PDF Files
    ↓
[TextExtractor] → Clean Text Files
    ↓
[GeminiParser] → ParsedDocument Objects (JSONL)
    ↓
[IndexBuilder] → SQLite Database
    ├─ FTS5 keyword search index
    ├─ Vector embeddings (BGE-small-en-v1.5, 384-dim)
    └─ Metadata tables
    ↓
[HybridSearchEngine] → Search Results with RRF fusion
```

**Location:** `scripts/cli.py`

**Commands:**
- `preprocess` - HTML/PDF → clean text
- `parse` - Text → ParsedDocument (JSONL) via Gemini
- `build` - JSONL → SQLite database with embeddings
- `validate` - Database integrity checks
- `pipeline` - Run all steps in sequence

**User Flow (Working Today):**
```bash
# Step 1: Set up your API key
export GEMINI_API_KEY="your-key-here"

# Step 2: Run the complete pipeline (one command does everything)
uv run python scripts/cli.py pipeline --input-dir cra_documents/cra_t4002e_rev24_dump/

# This creates:
# - data/cra_rules.db (SQLite database with FTS5 + vector search)
# - data/manifest.json (metadata)
```

**Then you can search:**
```python
import qe_tax_rag as qe

# Initialize (loads the database)
qe.init()

# Search for expense rules
results = qe.search("restaurant meal expense", top_k=5)

# Access results
for r in results:
    print(f"Citation: {r.citation_id}")
    print(f"Content: {r.content}")
    print(f"Source: {r.source_url}")
    print(f"Disclaimer: {r.disclaimer}")
```

---

### Pipeline 2: New Extraction System ⚠️ (TICKETS 1-6 Complete, BUT Disconnected)

This is a **high-quality extraction pipeline** using Mixture-of-Experts (MoE) approach with grounded adjudication, but it creates YAML files that are **NOT connected to the RAG database**.

**Flow:**
```
HTML Files
    ↓
[Classic Parser] → ExtractedRule objects (rule-based extraction)
    ↓
[LLM Parser] → ExtractedRule objects (semantic extraction)
    ↓
[Adjudicator] → Resolves conflicts with grounding
    ├─ Perfect matches → Accept classic parser
    ├─ Conflicts → LLM adjudication with HTML evidence
    └─ Orphans → LLM validation
    ↓
[YAML Generator] → cra_rules.yml
    ├─ Resolved rules (high confidence)
    └─ manual_review.yml (edge cases)
```

**Location:** `src/qe_tax_rag/extraction/ca/` and `scripts/extract_rules.py`

**User Flow (Creates YAML, NOT RAG database):**
```bash
# Run the extraction pipeline
uv run extract-rules \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/cra_rules.yml \
  --manual-review-file output/manual_review.yml \
  --verbose

# This creates:
# - output/cra_rules.yml (ExtractedRule objects)
# - output/manual_review.yml (if conflicts exist)
```

**Output Schema (ExtractedRule):**
```yaml
rules:
  - rule_number: 8523
    title: "Meals and entertainment"
    content: "Full text description of the rule..."
    applies_to: ["business", "fishing"]
    source_citation: "Line 8523"
    chapter: "Chapter 3 – Expenses"
    section: "Part 4 – Net income (loss) before adjustments"
    source_file: "t4002-5.html"
    expert_source: "adjudicated"
    anchor_id: "tocch3ln8523"
    confidence_score: 0.95
```

**❌ Problem:** This YAML output is **NOT used by the RAG database**. It's currently a standalone artifact.

---

## 🔍 The Disconnect: Schema Incompatibility

### What Pipeline 2 Produces (ExtractedRule Schema - YAML)

```yaml
rules:
  - rule_number: 8523
    title: "Meals and entertainment"
    content: "..."
    applies_to: ["business", "fishing"]
    chapter: "Chapter 3 – Expenses"
    section: "Part 4 – Net income"
    source_file: "t4002-5.html"
```

**Structure:** Flat list of individual expense rules

### What Pipeline 1 Needs (ParsedDocument Schema - JSONL)

```json
{
  "title": "T4002 Business Expenses Guide",
  "document_id": "t4002-5",
  "metadata": {
    "province": [],
    "business_type": [],
    "expense_type": []
  },
  "sections": [
    {
      "section_title": "Chapter 3 – Expenses",
      "section_level": 1,
      "content": [
        {
          "type": "paragraph",
          "text": "...",
          "citation_id": "S3-F2-C1-p1.25"
        }
      ]
    }
  ]
}
```

**Structure:** Hierarchical document with sections containing various content types

### Missing Component

**There is no transformer connecting these two schemas.**

To integrate the pipelines, you would need:
1. **YAML → JSONL Transformer**
   - Read ExtractedRule objects from YAML
   - Group by source_file
   - Map to ParsedDocument structure
   - Convert citation format
   - Write to JSONL for IndexBuilder

---

## 📋 Current State Summary

| Aspect | Status | Details |
|--------|--------|---------|
| **Working RAG Search** | ✅ **YES** | Use Pipeline 1 (`scripts/cli.py pipeline`) |
| **High-Quality Extraction** | ✅ **YES** | Pipeline 2 complete (`extract-rules`) |
| **Integration** | ❌ **NO** | Pipeline 2 output not consumed by RAG database |
| **Test RAG Today** | ✅ **YES** | Use Pipeline 1 only |
| **Database Schema** | ✅ **Valid** | SQLite with FTS5, vector search, metadata |
| **Search API** | ✅ **Working** | `qe.init()` and `qe.search()` functional |
| **Hybrid Search (RRF)** | ✅ **Implemented** | FTS5 + Vector with Reciprocal Rank Fusion |
| **Legal Disclaimers** | ✅ **Enforced** | Non-suppressible disclaimers on all results |

---

## 🚀 How to Test Your RAG System TODAY

### Option A: Use Existing Test Database (Fastest)

```bash
# The fixture database already exists for testing
uv run pytest tests/integration/test_user_story_2.py -v

# Or test the API directly with fixture DB
uv run python -c "
import qe_tax_rag as qe
qe.init()
results = qe.search('vehicle expenses', top_k=3)
for r in results:
    print(f'{r.citation_id}: {r.content[:100]}...')
"
```

### Option B: Build Fresh Database from HTML (Using Pipeline 1)

```bash
# 1. Set API key for Gemini parser
export GEMINI_API_KEY="your-actual-key"

# 2. Run complete pipeline (preprocess → parse → build → validate)
uv run python scripts/cli.py pipeline \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules.db \
  --data-version 2025.10

# 3. Validate the database
uv run python scripts/cli.py validate --db-path data/cra_rules.db

# 4. Use the RAG search
uv run python -c "
import qe_tax_rag as qe

# Initialize with the new database
qe.init()

# Search for home office deduction
results = qe.search('home office deduction', province='BC', top_k=5)

print(f'Found {len(results)} results\n')
for r in results:
    print(f'Citation: {r.citation_id}')
    print(f'Content: {r.content[:200]}...')
    print(f'Score: {r.score:.3f}')
    print('---')
"
```

---

## 🧪 Comprehensive Testing Plan

### Phase 1: Validate Existing RAG Search

**Goal:** Confirm the RAG system works end-to-end with the existing pipeline

**Steps:**

1. **Build fresh database from HTML**
   ```bash
   export GEMINI_API_KEY="your-key"
   uv run python scripts/cli.py pipeline \
     --input-dir cra_documents/cra_t4002e_rev24_dump/ \
     --output-db data/cra_rules.db \
     --data-version 2025.10
   ```

2. **Validate database integrity**
   ```bash
   uv run python scripts/cli.py validate --db-path data/cra_rules.db
   ```

3. **Run integration tests**
   ```bash
   uv run pytest tests/integration/ -v
   ```

4. **Manual search testing**
   ```bash
   uv run python -c "
   import qe_tax_rag as qe
   qe.init()

   test_queries = [
       'restaurant meal expenses',
       'home office deduction',
       'vehicle mileage',
       'capital cost allowance',
       'advertising expenses'
   ]

   for query in test_queries:
       results = qe.search(query, top_k=3)
       print(f'Query: {query} -> {len(results)} results')
       if results:
           print(f'  Top: {results[0].citation_id}: {results[0].content[:100]}...')
       print()
   "
   ```

**What to verify:**
- ✅ Database builds successfully
- ✅ All validation checks pass
- ✅ Search returns relevant results
- ✅ Citations are valid
- ✅ Disclaimers present on all results
- ✅ Query latency < 250ms

---

### Phase 2: Test Extraction Pipeline Quality

**Goal:** Verify the new extraction pipeline produces high-quality YAML

**Steps:**

1. **Run extraction on all HTML files**
   ```bash
   uv run extract-rules \
     cra_documents/cra_t4002e_rev24_dump/ \
     output/extracted_rules.yml \
     --manual-review-file output/manual_review.yml \
     --verbose
   ```

2. **Examine the output**
   ```bash
   cat output/extracted_rules.yml | head -100
   ```

3. **Check if manual review needed**
   ```bash
   if [ -f output/manual_review.yml ]; then
     echo "Manual review items found:"
     cat output/manual_review.yml
   fi
   ```

**What to verify:**
- ✅ Extraction completes without errors
- ✅ YAML schema is valid (rule_number, title, content, applies_to)
- ✅ Chapter/section fields populated correctly
- ✅ Adjudication statistics reasonable (high % perfect matches)
- ✅ Manual review items are legitimate edge cases

---

### Phase 3: Search Quality Testing

**Goal:** Validate hybrid search (FTS5 + vector) returns accurate results

**Create test file:** `tests/manual/test_search_quality.py`

```python
"""Manual search quality tests for RAG system."""
import qe_tax_rag as qe

qe.init()

# Test 1: Exact keyword match
print("Test 1: Exact keyword match")
results = qe.search("meals and entertainment", top_k=5)
assert len(results) > 0, "Should return results for exact keyword"
assert any("meal" in r.content.lower() for r in results), "Should find 'meal' in results"
print(f"✅ Found {len(results)} results for 'meals and entertainment'")

# Test 2: Semantic search (different words, same meaning)
print("\nTest 2: Semantic search")
results = qe.search("restaurant dining expenses", top_k=5)
assert len(results) > 0, "Should return results for semantic query"
assert any("meal" in r.content.lower() or "entertainment" in r.content.lower() for r in results), \
    "Should find semantically related content"
print(f"✅ Found {len(results)} results for 'restaurant dining expenses'")

# Test 3: Filtering by business type
print("\nTest 3: Filtering by business type")
results = qe.search("vehicle", business_type="sole_proprietorship", top_k=5)
assert len(results) >= 0, "Should handle business type filtering"
if results:
    business_types = [r.business_type for r in results if r.business_type]
    print(f"✅ Found {len(results)} results with business type filtering")

# Test 4: Multiple expense types
print("\nTest 4: Multiple expense types filtering")
results = qe.search("travel costs", expense_types=["travel", "meals"], top_k=5)
assert len(results) >= 0, "Should handle expense type filtering"
print(f"✅ Found {len(results)} results for travel/meals expense types")

# Test 5: Edge cases - nonsense query
print("\nTest 5: Edge case - nonsense query")
results = qe.search("xyzabc123", top_k=5)
print(f"Nonsense query returned {len(results)} results (should be 0 or very low)")

# Test 6: Very long query
print("\nTest 6: Very long query")
long_query = "I need to understand the rules for deducting expenses related to business meals and entertainment including travel and lodging"
results = qe.search(long_query, top_k=5)
assert len(results) > 0, "Should handle long queries"
print(f"✅ Found {len(results)} results for long query")

# Test 7: Check all results have required fields
print("\nTest 7: Result schema validation")
results = qe.search("vehicle", top_k=3)
for r in results:
    assert r.citation_id, "Should have citation_id"
    assert r.content, "Should have content"
    assert r.source_url, "Should have source_url"
    assert r.disclaimer, "Should have disclaimer"
    assert 0.0 <= r.score <= 1.0, "Score should be between 0 and 1"
print(f"✅ All results have required fields")

print("\n" + "="*50)
print("✅ All search quality tests passed!")
print("="*50)
```

**Run:**
```bash
uv run python tests/manual/test_search_quality.py
```

---

### Phase 4: Performance Benchmarking

**Goal:** Measure system performance

**Create benchmark script:** `tests/manual/benchmark.py`

```python
"""Performance benchmarking for RAG search."""
import time
import qe_tax_rag as qe

qe.init()

queries = [
    "meals and entertainment",
    "vehicle expenses",
    "home office",
    "advertising costs",
    "travel expenses",
    "capital cost allowance",
    "professional fees",
    "insurance premiums",
    "bank charges",
    "telephone and utilities"
]

print("Running performance benchmarks...")
print("="*60)

latencies = []
for query in queries:
    start = time.time()
    results = qe.search(query, top_k=5)
    elapsed = (time.time() - start) * 1000  # ms
    latencies.append(elapsed)
    print(f"{query:30s} -> {len(results)} results in {elapsed:.1f}ms")

print("="*60)
print(f"\nPerformance Summary:")
print(f"  Average latency: {sum(latencies)/len(latencies):.1f}ms")
print(f"  Max latency:     {max(latencies):.1f}ms")
print(f"  Min latency:     {min(latencies):.1f}ms")
print(f"  Total queries:   {len(queries)}")

# Check if target met
avg_latency = sum(latencies) / len(latencies)
if avg_latency < 250:
    print(f"\n✅ Target met: Average latency ({avg_latency:.1f}ms) < 250ms")
else:
    print(f"\n⚠️  Target missed: Average latency ({avg_latency:.1f}ms) >= 250ms")
```

**Run:**
```bash
uv run python tests/manual/benchmark.py
```

**Target:** Average latency < 250ms

---

### Phase 5: Citation Accuracy Spot Check

**Goal:** Verify results are grounded in actual CRA content (no hallucinations)

**Manual verification process:**

```bash
# 1. Get a result
uv run python -c "
import qe_tax_rag as qe
qe.init()
results = qe.search('meals', top_k=1)
r = results[0]
print(f'Citation: {r.citation_id}')
print(f'Source URL: {r.source_url}')
print(f'Content Preview: {r.content[:300]}...')
print(f'Expense Types: {r.expense_types}')
print(f'Province: {r.province}')
print(f'Business Type: {r.business_type}')
"

# 2. Manually verify:
# - Does citation_id match a real CRA document section?
# - Does source_url point to valid canada.ca page?
# - Is content accurate (not hallucinated)?
# - Are metadata fields correct?
```

**Spot check at least 5-10 results across different queries**

---

### Phase 6: End-to-End User Workflow

**Goal:** Simulate real-world usage scenario

**Create user simulation:** `tests/manual/user_workflow.py`

```python
"""Simulate end-to-end user workflow."""
import qe_tax_rag as qe

# Step 1: Initialize (downloads database if needed)
print("="*60)
print("QE Tax RAG - End-to-End User Workflow Simulation")
print("="*60)

print("\n[Step 1] Initializing QE Tax RAG...")
qe.init()
print("✅ Initialization complete")

# Step 2: Search for expense guidance
print("\n[Step 2] Searching for 'business travel meal expenses'...")
results = qe.search(
    query="business travel meal expenses",
    province="BC",
    business_type="sole_proprietorship",
    top_k=5
)
print(f"✅ Search complete: Found {len(results)} results")

# Step 3: Display results
print(f"\n[Step 3] Displaying results:\n")
print("="*60)
for i, result in enumerate(results, 1):
    print(f"\n{i}. Citation: {result.citation_id} (Score: {result.score:.3f})")
    print(f"   Content: {result.content[:200]}...")
    print(f"   Source: {result.source_url}")
    print(f"   Expense Types: {result.expense_types}")
    print(f"   ⚠️  {result.disclaimer[:100]}...")
print("="*60)

# Step 4: Check version
print("\n[Step 4] Checking version information...")
version_info = qe.get_version()
print(f"✅ Library Version: {version_info['library_version']}")
print(f"✅ Data Version: {version_info['data_version']}")
print(f"✅ Schema Version: {version_info['schema_version']}")

# Step 5: Test filtering
print("\n[Step 5] Testing advanced filtering...")
results_filtered = qe.search(
    query="vehicle",
    expense_types=["vehicle", "travel"],
    top_k=3
)
print(f"✅ Filtered search: Found {len(results_filtered)} results for vehicle + travel")

print("\n" + "="*60)
print("✅ End-to-End Workflow Complete!")
print("="*60)
```

**Run:**
```bash
uv run python tests/manual/user_workflow.py
```

---

## 🔧 What's NOT Testable Today

**Cannot test without additional integration work:**

- ❌ Using the new extraction pipeline (extract-rules) output in the RAG database
- ❌ Comparing quality: GeminiParser vs. Classic+LLM+Adjudicator parsers
- ❌ End-to-end flow: HTML → extract-rules → RAG database

**Why:** The YAML → JSONL transformer is missing (ExtractedRule → ParsedDocument schema conversion)

---

## 📊 Success Criteria

### Must Pass ✅

1. Database builds from HTML without errors
2. Validation checks all pass (schema, row counts, embeddings)
3. Search returns results for common queries
4. All results have valid citations and disclaimers
5. Average query latency < 250ms
6. No SQL injection vulnerabilities (parameterized queries verified)

### Should Pass 👍

1. Hybrid search (RRF) outperforms keyword-only or vector-only
2. Filtering (province, business_type, expense_types) works correctly
3. Extraction pipeline produces valid YAML with reasonable adjudication stats
4. Manual review items are genuine edge cases (not systematic failures)
5. Search results are semantically relevant (not just keyword matches)

### Nice to Have 💡

1. Support for French-language CRA documents
2. Real-time search result explanations (why this result ranked high)
3. Integration with the new extraction pipeline via transformer
4. Automated regression tests with golden dataset

---

## 🎯 Recommended Testing Order

1. **Phase 1** - Build database and validate **(30 minutes)**
   - Creates fresh database from HTML files
   - Validates schema and integrity

2. **Phase 3** - Search quality tests **(15 minutes)**
   - Tests exact match, semantic search, filtering
   - Validates result schema

3. **Phase 4** - Performance benchmarks **(10 minutes)**
   - Measures query latency
   - Verifies target < 250ms

4. **Phase 6** - End-to-end workflow **(10 minutes)**
   - Simulates real user journey
   - Tests all API functions

5. **Phase 2** - Extraction quality **(20 minutes, optional)**
   - Tests new extraction pipeline
   - Not required for RAG testing but good for quality validation

6. **Phase 5** - Citation spot checks **(15 minutes, manual)**
   - Verify no hallucinations
   - Check source URL validity

**Total estimated time: ~1.5 hours for comprehensive testing**

---

## 📝 Next Steps (Future Integration Work)

If you want to integrate the new extraction pipeline with the RAG database:

### Required: YAML-to-JSONL Transformer

**Location:** `src/qe_tax_rag/extraction/ca/yaml_to_jsonl.py`

**Responsibilities:**
1. Load ExtractedRule objects from YAML
2. Transform to ParsedDocument schema:
   - Map `rule_number` → `citation_id` (format: "L{rule_number}" or similar)
   - Map `title` + `content` → Section with TextChunk
   - Map `applies_to` → Metadata.business_type and/or expense_type
   - Generate province metadata (extract from source or default)
3. Write ParsedDocument objects to JSONL

**Key Mapping Decisions Needed:**
- **Citation ID format:** Current schema expects `S\d+-F\d+-C\d+-p\d+\.?\d*` pattern. Options:
  - Create simpler format like "L8523" for Line 8523
  - Map rule_number to fake section/form/chapter pattern
  - Relax the schema pattern validation

- **Province metadata:** ExtractedRule has no province field. Options:
  - Default to null (applies to all provinces)
  - Infer from source_file or chapter
  - Add province extraction to the extraction pipeline

- **Expense type mapping:** How to map `applies_to` (business/farming/fishing) to `expense_type` list (meals, travel, vehicle, etc.)?
  - Use rule title/content to infer expense categories
  - Create manual mapping table
  - Use LLM-based classification

**CLI Integration:**
Add new command to `scripts/extract_rules.py`:
```bash
uv run extract-rules yaml-to-jsonl INPUT_YAML OUTPUT_JSONL
```

Then the integrated flow would be:
```bash
# Step 1: Extract to YAML
uv run extract-rules HTML_DIR OUTPUT.yml

# Step 2: Transform to JSONL
uv run extract-rules yaml-to-jsonl OUTPUT.yml CHUNKS.jsonl

# Step 3: Build database
uv run python scripts/cli.py build --input-file CHUNKS.jsonl --output-db cra_rules.db
```

---

## 🔗 Key Files Reference

### Pipeline 1 (Working RAG)
- `scripts/cli.py` - Main CLI orchestrator
- `src/qe_tax_rag/data/builder.py` - IndexBuilder (JSONL → SQLite)
- `src/qe_tax_rag/api.py` - Public API (init, search)
- `src/qe_tax_rag/search/hybrid.py` - Hybrid search engine (RRF fusion)
- `scripts/parser/schema.py` - ParsedDocument schema

### Pipeline 2 (New Extraction)
- `scripts/extract_rules.py` - Extraction CLI
- `src/qe_tax_rag/extraction/ca/orchestrator.py` - Extraction orchestrator
- `src/qe_tax_rag/extraction/ca/classic_parser.py` - Rule-based parser
- `src/qe_tax_rag/extraction/ca/llm_parser.py` - LLM-based parser
- `src/qe_tax_rag/extraction/ca/adjudicator.py` - Conflict resolution
- `src/qe_tax_rag/extraction/ca/schema.py` - ExtractedRule schema

### Database Schema
- `src/qe_tax_rag/data/schema.py` - SQLite schema definition
- Tables: metadata, rules, rules_fts (FTS5), rules_vec (sqlite-vec), expense_types, rule_expense_type_links

### Search Models
- `src/qe_tax_rag/search/models.py` - ExpenseQuery, SearchResult, IndexManifest
- `src/qe_tax_rag/search/enums.py` - Province, BusinessType enums

---

## 📚 Additional Resources

- **Project README:** `/README.md`
- **Development Guide:** `/CLAUDE.md`
- **Implementation Plan:** `/html-to-yaml-plan.md`
- **Test Fixtures:** `/tests/fixtures/`
- **Test Database:** `/tests/fixtures/test_database.db`

---

**Generated:** 2025-10-17
**Author:** Claude Code Analysis with Zen MCP
**Version:** 1.0
