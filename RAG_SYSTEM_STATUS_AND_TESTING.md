# QE Tax RAG System - User Testing Guide

**Date:** 2025-10-18 **Status:** ✅ **Ready for User Testing**

---

## 🎯 Executive Summary

### Critical Finding: The New Extraction Pipeline is LIVE

The high-quality extraction pipeline is now **fully integrated** with the RAG database. We have a new, primary, end-to-end workflow that converts CRA HTML documents into a high-precision, searchable database without requiring a runtime API key.

**Bottom Line:** You can test the complete, high-quality RAG system **TODAY** using a single, powerful command. The original Gemini-based pipeline is now a legacy option, useful for specific comparisons.

**This guide provides the simplest path to get you from raw CRA documents to successfully running test queries.**

---

## 🚀 How to Test Your RAG System (80/20 Guide)

This is the minimal, fastest workflow to build a database and start searching.

### Step 1: Build the Database (One Command)

The new `pipeline-extraction` command handles everything: HTML extraction, transformation, database indexing, and validation.

```bash
# Run the complete pipeline (one command does everything)
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules.db

# This creates:
# - data/cra_rules.db (SQLite database with FTS5 + vector search)
# - data/manifest.json (metadata)
```

This process uses the new, high-quality extraction system and does **NOT** require a `GEMINI_API_KEY`.

### Step 2: Search the Database

Once the database is built, you can use the library's API to run queries.

```python
import qe_tax_rag as qe

# Initialize (loads the database at data/cra_rules.db by default)
qe.init()

# Search for expense rules
results = qe.search("restaurant meal expense", top_k=5)

# Access results
for r in results:
    print(f"Citation: {r.citation_id} (Score: {r.score:.2f})")
    print(f"Content: {r.content}")
    print(f"Source: {r.source_url}")
    print(f"Disclaimer: {r.disclaimer}")
    print("-" * 20)
```

---

## 🧪 Recommended Test Scenarios

The new pipeline excels at precision. Use these scenarios to validate its quality.

| Query Type      | Example Query                              | What to Look For                                                              |
| :-------------- | :----------------------------------------- | :---------------------------------------------------------------------------- |
| **Keyword**     | `"meals and entertainment"`                | The main rule about the 50% deductibility of meal expenses.                   |
| **Line Item**   | `"Line 8523"`                              | The exact content for rule 8523 should be the top result with a high score.   |
| **Semantic**    | `"Can I deduct my car's gas?"`             | Results related to vehicle expenses, mileage, and fuel.                       |
| **Conceptual**  | `"What are common business expenses?"`    | A variety of results covering different expense types (e.g., travel, supplies). |
| **Filtering**   | `qe.search("vehicle", income_type="fishing")` | Results for vehicle expenses specifically applicable to fishing income.       |
| **Edge Case**   | `"xyzabc123"`                              | Should return 0 results, demonstrating no irrelevant matches.                 |

---

## 📊 System Architecture & Pipelines

We now have two end-to-end pipelines with different strengths.

### Pipeline 1: High-Precision Extraction (✅ Recommended)

This is the **new, primary RAG flow**. It uses a Mixture-of-Experts extraction system for superior accuracy and metadata.

**Flow:**

```
HTML Files
    ↓
[Classic + LLM Parsers with Adjudicator] → ExtractedRule (YAML)
    ↓
[YAML Transformer] → ParsedDocument (JSONL)
    ↓
[IndexBuilder] → SQLite Database (FTS5 + Vector Search)
    ↓
[HybridSearchEngine] → Search Results
```

**Location:** `scripts/cli.py`
**Command:** `pipeline-extraction`

### Pipeline 2: Gemini-based Parsing (⚠️ Legacy)

This is the **original RAG flow**. It's good for generating broad, narrative context but is less precise and requires an API key.

**Flow:**

```
HTML/PDF Files
    ↓
[TextExtractor] → Clean Text Files
    ↓
[GeminiParser] → ParsedDocument (JSONL)
    ↓
[IndexBuilder] → SQLite Database
    ↓
[HybridSearchEngine] → Search Results
```

**Location:** `scripts/cli.py`
**Command:** `pipeline`

### Which Pipeline Should You Use?

| Feature                | Extraction Pipeline (New & Recommended) | Gemini Pipeline (Legacy)                             |
| ---------------------- | --------------------------------------- | ---------------------------------------------------- |
| **Primary Use Case**   | High-precision, line-item queries       | Broad, conceptual queries                            |
| **Chunking Strategy**  | One rule per chunk                      | Large, multi-paragraph chunks                        |
| **Metadata**           | Rich (income type, confidence score)    | Basic (inferred from content)                        |
| **API Key Required**   | ❌ **No**                               | ✅ **Yes** (`GEMINI_API_KEY`)                        |
| **CLI Command**        | `pipeline-extraction`                   | `pipeline`                                           |
| **Recommendation**     | **Default for production & testing**    | Use for search quality comparison or as a fallback.  |

---

## 🛠️ Advanced Workflows (For Debugging)

If you need to inspect the intermediate files produced by the new pipeline, you can run the stages manually.

### Stage 1: Extract HTML to YAML

This runs the extraction and adjudication but stops before transformation.

```bash
uv run extract-rules run \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/cra_rules.yml \
  --manual-review-file output/manual_review.yml
```

### Stage 2: Transform YAML to JSONL

This command (part of the same script) can be used to transform the YAML into the JSONL format required by the database builder.

```bash
# This functionality is now integrated into the `run` command via a flag.
uv run extract-rules run \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/cra_rules.yml \
  --auto-transform \
  --output-jsonl output/chunks.jsonl
```

### Stage 3: Build Database from JSONL

This uses the main CLI to build the database from the intermediate JSONL file.

```bash
uv run python scripts/cli.py build \
  --input-file output/chunks.jsonl \
  --output-db data/cra_rules.db
```

---

## 📋 Current State Summary

| Aspect                      | Status           | Details                                                              |
| --------------------------- | ---------------- | -------------------------------------------------------------------- |
| **Working RAG Search**      | ✅ **YES**       | Use `pipeline-extraction` to build, then `qe.search()` to query.     |
| **High-Quality Extraction** | ✅ **YES**       | The `extract-rules` script produces high-fidelity YAML.              |
| **Integration**             | ✅ **YES**       | The transformer connects the extraction pipeline to the RAG database. |
| **Test RAG Today**          | ✅ **YES**       | Use the `pipeline-extraction` command.                               |
| **Database Schema**         | ✅ **Valid**     | SQLite with FTS5, vector search, and metadata.                       |
| **Search API**              | ✅ **Working**   | `qe.init()` and `qe.search()` are fully functional.                  |

---

## 🔗 Key Files Reference

### New Extraction & RAG Pipeline

- `scripts/cli.py`: Orchestrator for `pipeline-extraction`.
- `src/qe_tax_rag/extraction/ca/orchestrator.py`: Core extraction logic (HTML → YAML).
- `src/qe_tax_rag/extraction/ca/transformer.py`: Core transformation logic (YAML → JSONL).
- `src/qe_tax_rag/data/builder.py`: IndexBuilder (JSONL → SQLite).
- `src/qe_tax_rag/api.py`: Public search API (`init`, `search`).

### Legacy Gemini Pipeline

- `scripts/cli.py`: Orchestrator for the `pipeline` command.
- `scripts/parser/gemini_parser.py`: Gemini-based text-to-JSONL parser.

---

**For detailed step-by-step testing instructions, see `USER_GUIDE.md`.**
