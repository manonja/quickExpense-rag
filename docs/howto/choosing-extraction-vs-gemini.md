# How-To: Choosing Between Extraction and Gemini Pipelines

## Quick Decision Matrix

| Use Case                             | Recommended Pipeline | Why                                         |
| ------------------------------------ | -------------------- | ------------------------------------------- |
| Line-item queries ("Line 8523 meals")| **Extraction**       | Higher precision, structured metadata       |
| Conceptual queries ("What can I deduct?") | **Gemini**      | More context, explanatory content           |
| No Gemini API key available          | **Extraction**       | No runtime API dependency                   |
| Need `income_type` metadata          | **Extraction**       | Structured metadata included                |
| Want maximum recall                  | **Gemini**           | ~1000 chunks vs ~247 (T4002)                |

## Pipeline Comparison

### Extraction Pipeline (✅ Primary & Recommended)

**Status**: Production-ready, fully integrated

**Architecture**: Classic Parser → LLM Parser → Adjudicator → Transformer → Database

**Strengths**:

- ✅ No API key needed (after initial extraction)
- ✅ Structured metadata (income types, confidence scores, extraction sources)
- ✅ Precise LINE-{number} citations (e.g., "LINE-8523")
- ✅ ~247 focused chunks per document (T4002)
- ✅ Extraction provenance tracking (classic/llm/adjudicated)
- ✅ Faster build times (~3-5 minutes vs ~10 minutes)

**Limitations**:

- ⚠️ Less narrative context than Gemini
- ⚠️ Keyword-based expense classification (not ML - future enhancement)

**Best For**:

- **All production use cases** (primary recommendation)
- Line-item specific queries ("Line 8523")
- Systems requiring high precision
- Systems needing audit trails (extraction source tracking)
- Environments without Gemini API access

---

### Gemini Pipeline (⚠️ Legacy Alternative)

**Status**: Functional but deprecated for most use cases

**Architecture**: HTML → Gemini LLM → JSONL → Database

**Strengths**:

- ✅ Rich narrative content and context
- ✅ Better for highly conceptual queries
- ✅ ~1000 chunks per document (T4002)
- ✅ Natural language explanations

**Limitations**:

- ⚠️ Requires `GEMINI_API_KEY` at runtime
- ⚠️ Broader, less precise chunks
- ⚠️ No extraction provenance metadata
- ⚠️ API rate limits and costs
- ⚠️ Slower build times

**Best For**:

- Search quality comparison benchmarking
- Legacy systems already using Gemini pipeline
- Specific use cases requiring maximum narrative context

---

## Usage Commands

### Extraction Pipeline

**Full automated pipeline** (recommended):

```bash
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/extraction_rules.db
```

**Step-by-step** (for debugging):

```bash
# Step 1: Extract HTML → YAML
uv run extract-rules run cra_documents/cra_t4002e_rev24_dump/ \
  output/rules.yml \
  --auto-transform --output-jsonl output/chunks.jsonl

# Step 2: Build database
uv run python scripts/cli.py build \
  --input-file output/chunks.jsonl \
  --output-db data/extraction_rules.db

# Step 3: Validate
uv run python scripts/cli.py validate --db-path data/extraction_rules.db
```

---

### Gemini Pipeline

See existing CLAUDE.md section for Gemini usage (requires `GEMINI_API_KEY`).

---

## Migration Guide

### From Gemini to Extraction

1. Run extraction pipeline to generate new database
1. Compare search results between databases
1. Gradually transition queries to extraction database
1. Monitor for any quality regressions

### From Extraction to Gemini

1. Set `GEMINI_API_KEY` environment variable
1. Run Gemini pipeline to generate new database
1. Test conceptual queries on both databases
1. Transition based on query type requirements

---

## Performance Characteristics

### Extraction Pipeline

- **Build Time**: ~30-120s for T4002 (247 rules)
- **Database Size**: ~10-20MB (T4002)
- **Search Latency**: \<100ms (typical)
- **Memory Usage**: ~200-500MB (during build)

### Gemini Pipeline

- **Build Time**: ~5-10 minutes for T4002 (API rate limits)
- **Database Size**: ~50-100MB (T4002)
- **Search Latency**: \<100ms (typical)
- **Memory Usage**: ~200-500MB (during build)

---

## Recommendation

**✅ Use the Extraction Pipeline for all new development and production systems:**

- More reliable (no API dependency)
- Better structured metadata for filtering
- Faster build times (~3-5 min vs ~10 min)
- Lower costs (no API fees)
- Production-ready and fully integrated

**⚠️ Consider Gemini Pipeline only when:**

- Comparing search quality for benchmarking
- You need maximum narrative context for exploratory research
- You have existing systems dependent on the Gemini pipeline

**Default Choice**: When in doubt, use `pipeline-extraction`.

---

## Questions?

- See `USER_GUIDE.md` for quick start testing guide
- See `RAG_SYSTEM_STATUS_AND_TESTING.md` for system status and architecture
- See `CLAUDE.md` for detailed extraction pipeline documentation
- File issues at GitHub if you encounter problems
