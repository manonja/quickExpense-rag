# YAML-to-JSONL Transformer: Design & Implementation Plan

**Date:** 2025-10-17 **Status:** Comprehensive Planning Complete **Planning Method:**
Zen MCP Planner (8-step deep analysis)

______________________________________________________________________

## Executive Summary

This document outlines the design and implementation plan for a **YAML-to-JSONL
transformer** that bridges the extraction pipeline (TICKETS 1-6) with the RAG database
system.

### The Current Disconnect

```
[Extraction Pipeline - COMPLETE]
HTML → Classic Parser + LLM Parser → Adjudicator → ExtractedRule (YAML)
                                                          |
                                                          X  <-- GAP
                                                          |
[RAG Pipeline - WORKING]                                  v
ParsedDocument (JSONL) → IndexBuilder → SQLite → HybridSearch
```

### What the Transformer Enables

Once implemented, the transformer creates a complete end-to-end flow:

```
HTML Files
    |
    v
[Extraction Pipeline]
    |-- Classic Parser (rule-based, fast, reliable)
    |-- LLM Parser (semantic, flexible)
    |
    v
[Adjudicator]
    |-- Perfect matches → Accept classic
    |-- Conflicts → LLM resolution with grounding
    |-- Orphans → LLM validation
    |
    v
ExtractedRule objects (YAML)
    |-- rule_number: 8523
    |-- title: "Meals and entertainment"
    |-- content: "Full description..."
    |-- applies_to: ["business", "fishing"]
    |-- confidence_score: 0.95
    |
    v
[YAML-to-JSONL Transformer] <-- THIS IS THE MISSING PIECE
    |-- Schema mapping
    |-- Metadata enrichment
    |-- Hierarchical grouping
    |
    v
ParsedDocument objects (JSONL)
    |-- Grouped by source file
    |-- Hierarchical sections
    |-- Enriched metadata
    |
    v
[IndexBuilder]
    |-- Generate embeddings (BGE-small-en-v1.5)
    |-- Build FTS5 index
    |-- Build vector index
    |
    v
SQLite Database
    |-- rules table
    |-- rules_fts (keyword search)
    |-- rules_vec (semantic search)
    |-- expense_types (many-to-many)
    |
    v
[HybridSearchEngine]
    |-- FTS5 keyword search
    |-- Vector semantic search
    |-- RRF fusion
    |
    v
Search Results with Citations & Disclaimers
```

______________________________________________________________________

## Part 1: What the Transformer Enables

### Immediate Benefits

**1. Complete End-to-End Extraction Flow**

- Currently: Extraction produces YAML (dead end)
- With Transformer: HTML → YAML → JSONL → Database → Search
- Impact: High-quality, grounded extraction flows into searchable RAG system

**2. Superior Data Quality**

- Currently: Single LLM (GeminiParser) extracts everything
- With Transformer: MoE (Classic + LLM) with adjudication
- Quality improvement: ~85% perfect matches, ~13% auto-corrected, ~2% manual review
- Impact: More accurate rule content, fewer hallucinations

**3. Enhanced Metadata**

- Currently: Limited metadata from Gemini parsing
- With Transformer:
  - Income types (business, farming, fishing) from applies_to
  - Inferred expense categories (meals, travel, vehicle) from content
  - Confidence scores (0.0-1.0) for quality filtering
  - Audit trail (which expert extracted this rule)
- Impact: Better search filtering, quality control, debugging

**4. No Gemini API Dependency for Extraction**

- Currently: Requires GEMINI_API_KEY for parsing
- With Transformer: Extraction uses local HTML parsing + adjudication
- Impact: Reduced API costs, offline operation, faster processing

**5. Editable Intermediate Format**

- Currently: Direct HTML → Database (no manual correction)
- With Transformer: HTML → YAML → (manual review) → JSONL → Database
- Impact: Users can edit YAML before indexing, manual corrections possible

### Future Opportunities

**1. Quality Filtering**

```python
# Filter search results by extraction confidence
results = qe.search(
    "meals",
    min_confidence=0.9,  # Only high-confidence extractions
    top_k=5
)
```

**2. Multi-Language Support**

- Extend extraction to French CRA documents
- Adjudicator can handle bilingual validation
- YAML format supports multiple languages

**3. Hybrid Approach**

- Combine Gemini conceptual content (guidance, explanations)
- With Extraction rules (line items, specifics)
- Best of both worlds: precision + context

**4. Custom Rules Management**

```bash
# Extract rules
uv run extract-rules HTML_DIR rules.yml

# User edits YAML manually (corrections, additions)
vim rules.yml

# Transform and index
uv run extract-rules transform rules.yml chunks.jsonl
uv run python scripts/cli.py build --input-file chunks.jsonl
```

______________________________________________________________________

## Part 2: How the System Works with Transformer

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    TWO PARALLEL PIPELINES                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Pipeline 1 (EXISTING - Gemini-based)                       │
│  ┌──────┐   ┌──────────┐   ┌────────────┐   ┌──────┐      │
│  │ HTML │──>│  Gemini  │──>│ Parsed     │──>│  DB  │      │
│  │      │   │  Parser  │   │ Document   │   │      │      │
│  └──────┘   └──────────┘   └────────────┘   └──────┘      │
│                                                               │
│  Pipeline 2 (NEW - Extraction-based)                        │
│  ┌──────┐   ┌──────────┐   ┌────────────┐   ┌──────────┐  │
│  │ HTML │──>│ Extract  │──>│ YAML       │──>│Transform │  │
│  │      │   │ Pipeline │   │ (Rules)    │   │ to JSONL │  │
│  └──────┘   └──────────┘   └────────────┘   └──────────┘  │
│                                                     │         │
│                                                     v         │
│                                              ┌────────────┐  │
│                                              │ Parsed     │  │
│                                              │ Document   │  │
│                                              └────────────┘  │
│                                                     │         │
│                                                     v         │
│                                              ┌────────────┐  │
│                                              │ IndexBuilder│ │
│                                              │  (shared)   │  │
│                                              └────────────┘  │
│                                                     │         │
│                                                     v         │
│                                              ┌────────────┐  │
│                                              │  SQLite DB │  │
│                                              │  (shared)  │  │
│                                              └────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Details

**Step 1: HTML Extraction (Already Complete)**

```
Input:  cra_documents/cra_t4002e_rev24_dump/*.html
Output: output/cra_rules.yml

Command:
  uv run extract-rules cra_documents/cra_t4002e_rev24_dump/ output/cra_rules.yml

YAML Structure:
  schema_version: "1.0"
  extraction_timestamp: "2025-10-17T10:30:00Z"
  rules:
    - rule_number: 8523
      title: "Meals and entertainment"
      content: "You can deduct the cost of meals..."
      applies_to: ["business", "fishing"]
      chapter: "Chapter 3 – Expenses"
      section: "Part 4 – Net income"
      source_file: "t4002-5.html"
      expert_source: "adjudicated"
      confidence_score: 0.95
      anchor_id: "tocch3ln8523"
```

**Step 2: YAML-to-JSONL Transformation (To Be Implemented)**

```
Input:  output/cra_rules.yml
Output: data/chunks.jsonl

Command:
  uv run extract-rules transform output/cra_rules.yml data/chunks.jsonl

Transformation Logic:
  1. Group rules by source_file (e.g., t4002-5.html)
  2. Within each file, group by chapter → section
  3. Create ParsedDocument structure:
     - title: "CRA T4002 Business Expenses - Part 5"
     - document_id: "t4002-5"
     - sections: [hierarchical structure]
  4. Map each ExtractedRule → TextChunk:
     - text: rule.title + "\n\n" + rule.content
     - citation_id: "LINE-{rule_number}"
     - extraction_source: rule.expert_source
     - extraction_confidence: rule.confidence_score
  5. Infer metadata:
     - income_type: applies_to (direct mapping)
     - expense_type: keyword classifier on title+content
     - province: None (federal rules)

JSONL Structure (one line per document):
  {
    "title": "CRA T4002 Business Expenses - Part 5",
    "document_id": "t4002-5",
    "metadata": {
      "province": [],
      "business_type": [],
      "expense_type": ["meals", "entertainment"],
      "income_type": ["business", "fishing"]
    },
    "sections": [
      {
        "section_title": "Chapter 3 – Expenses",
        "section_level": 1,
        "content": [
          {
            "section_title": "Part 4 – Net income",
            "section_level": 2,
            "content": [
              {
                "type": "paragraph",
                "text": "Meals and entertainment\n\nYou can deduct...",
                "citation_id": "LINE-8523",
                "extraction_source": "adjudicated",
                "extraction_confidence": 0.95,
                "source_anchor": "tocch3ln8523"
              }
            ]
          }
        ]
      }
    ]
  }
```

**Step 3: Database Building (Existing Infrastructure)**

```
Input:  data/chunks.jsonl
Output: data/cra_rules.db

Command:
  uv run python scripts/cli.py build --input-file data/chunks.jsonl

Process:
  1. Load ParsedDocument from JSONL
  2. Flatten to chunks (via ParsedDocument.to_flat_chunks())
  3. Generate BGE embeddings (384-dim vectors)
  4. Insert into SQLite:
     - rules table (content, citation_id, metadata_json)
     - rules_fts (FTS5 keyword search)
     - rules_vec (vector search)
     - expense_types + rule_expense_type_links (many-to-many)
  5. Optimize and validate
```

**Step 4: Search (Existing Infrastructure)**

```
Python API:
  import qe_tax_rag as qe
  qe.init()
  results = qe.search("meals", top_k=5)

Search Process:
  1. Metadata filtering (SQL WHERE clause)
     - province, business_type, expense_types
  2. FTS5 keyword search
     - Exact term matching on filtered candidates
  3. Vector semantic search
     - BGE embeddings + cosine similarity
  4. RRF fusion
     - Combine rankings: score = 1/(k + rank)
  5. Return SearchResult objects
     - citation_id: "LINE-8523"
     - content: "Meals and entertainment\n\nYou can deduct..."
     - score: 0.87
     - disclaimer: "⚠️ INFORMATIONAL ONLY - NOT TAX ADVICE..."
```

______________________________________________________________________

## Part 3: Schema Mapping Strategy

### The Core Challenge

**Source Schema (ExtractedRule):**

```python
class ExtractedRule(BaseModel):
    rule_number: int                     # 8523
    title: str                           # "Meals and entertainment"
    content: str                         # Full description
    applies_to: list[ApplicabilityType]  # ["business", "fishing"]
    source_citation: str                 # "Line 8523"
    chapter: str                         # "Chapter 3 – Expenses"
    section: str | None                  # "Part 4 – Net income"
    source_file: str                     # "t4002-5.html"
    expert_source: ExpertSource          # "adjudicated"
    anchor_id: str | None                # "tocch3ln8523"
    confidence_score: float              # 0.95
```

**Target Schema (ParsedDocument):**

```python
class ParsedDocument(BaseModel):
    title: str                           # "CRA T4002 - Part 5"
    document_id: str | None              # "t4002-5"
    metadata: Metadata                   # Nested structure
    sections: list[Section]              # Hierarchical content

class Metadata(BaseModel):
    province: list[str]                  # ["BC", "ON", ...]
    business_type: list[str]             # ["sole_proprietorship", ...]
    expense_type: list[str]              # ["meals", "travel", ...]
    income_type: list[str]               # NEW: ["business", "farming", ...]

class Section(BaseModel):
    section_title: str                   # "Chapter 3"
    section_level: int                   # 1, 2, 3
    content: list[ContentItem]           # TextChunk, ListChunk, TableChunk

class TextChunk(BaseModel):
    type: Literal["paragraph", "footnote"]
    text: str                            # Combined title + content
    citation_id: str | None              # "LINE-8523"
    extraction_source: str | None        # NEW: "adjudicated"
    extraction_confidence: float | None  # NEW: 0.95
    source_anchor: str | None            # NEW: "tocch3ln8523"
```

### Key Mapping Decisions

**1. Citation ID Format**

- **Problem:** Current pattern `S\d+-F\d+-C\d+-p\d+\.?\d*` doesn't fit rule_number
- **Solution:** Relax pattern to accept `LINE-{rule_number}`
  - Example: `LINE-8523` for rule_number 8523
  - Update: `src/qe_tax_rag/search/models.py`
  - Pattern: `r"^(S\d+-F\d+-C\d+-p\d+\.?\d*|LINE-\d+)$"`
- **Impact:** Backward compatible (existing citations still valid)

**2. Document Grouping**

- **Strategy:** Group rules by source_file
- **Logic:**
  ```
  cra_rules.yml (flat list of 247 rules)
    → Group by source_file
    → t4002-1.html: [rule_8000, rule_8010, ...]
    → t4002-5.html: [rule_8523, rule_8910, ...]

  Each source_file → One ParsedDocument
    → title: "CRA T4002 - Part {N}"
    → document_id: "t4002-{N}"
    → sections: Hierarchical by chapter → section
  ```

**3. Hierarchical Section Organization**

```
ParsedDocument("t4002-5")
  └─ Section(title="Chapter 3 – Expenses", level=1)
       └─ Section(title="Part 4 – Net income", level=2)
            ├─ TextChunk(citation_id="LINE-8523", text="Meals...")
            ├─ TextChunk(citation_id="LINE-8910", text="Vehicle...")
            └─ TextChunk(citation_id="LINE-9200", text="Travel...")
```

**4. Metadata Mapping**

| ExtractedRule Field | ParsedDocument Field            | Transformation                          |
| ------------------- | ------------------------------- | --------------------------------------- |
| applies_to          | metadata.income_type            | Direct mapping: ["business", "fishing"] |
| title + content     | metadata.expense_type           | Infer via keyword classifier            |
| N/A                 | metadata.province               | Default to None (federal rules)         |
| N/A                 | metadata.business_type          | Not mapped (different semantic)         |
| expert_source       | TextChunk.extraction_source     | Preserve as metadata                    |
| confidence_score    | TextChunk.extraction_confidence | Preserve as metadata                    |
| anchor_id           | TextChunk.source_anchor         | Preserve for debugging                  |

**5. Expense Type Inference**

Keyword-based classifier (simple, fast, good enough for MVP):

```python
EXPENSE_TYPE_KEYWORDS = {
    "meals": ["meal", "food", "restaurant", "dining", "entertainment"],
    "travel": ["travel", "transportation", "airfare", "hotel", "lodging"],
    "vehicle": ["vehicle", "automobile", "car", "motor", "mileage", "fuel"],
    "home_office": ["home office", "workspace", "rent"],
    "advertising": ["advertising", "marketing", "promotion"],
    "supplies": ["supplies", "materials", "stationery"],
    "professional_fees": ["professional fees", "legal", "accounting"],
    "insurance": ["insurance", "premium"],
    "utilities": ["telephone", "utilities", "internet", "electricity"],
    "capital": ["capital cost", "cca", "depreciation", "asset"],
}

def infer_expense_types(rule: ExtractedRule) -> list[str]:
    text = (rule.title + " " + rule.content).lower()
    matched = []
    for expense_type, keywords in EXPENSE_TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matched.append(expense_type)
    return matched if matched else ["general"]
```

Example:

- Rule title: "Meals and entertainment"
- Inferred: ["meals"] (matches "meal" keyword)
- Stored in: metadata.expense_type

______________________________________________________________________

## Part 4: Error Handling & Validation

### Multi-Layer Validation Strategy

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Input Validation (Pre-transformation)         │
├─────────────────────────────────────────────────────────┤
│ - Schema version compatibility check                    │
│ - Duplicate rule_number detection                       │
│ - Required fields validation (source_file, chapter)     │
│ → Critical errors: FAIL-FAST (stop transformation)      │
└─────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Transformation Validation (During)            │
├─────────────────────────────────────────────────────────┤
│ - Citation ID uniqueness check                          │
│ - Hierarchical structure validity                       │
│ - Metadata inference success                            │
│ → Non-critical errors: LOG WARNING, SKIP RULE, CONTINUE │
└─────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Output Validation (Post-transformation)       │
├─────────────────────────────────────────────────────────┤
│ - JSONL format validation (parse each line)            │
│ - ParsedDocument schema validation (Pydantic)          │
│ - Required nested fields check                          │
│ → Errors: REPORT, provide line numbers for debugging   │
└─────────────────────────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Integration Validation (IndexBuilder)         │
├─────────────────────────────────────────────────────────┤
│ - Sample JSONL with IndexBuilder                       │
│ - Verify embeddings generate successfully              │
│ - Check database integrity after build                  │
│ → Errors: INTEGRATION TEST FAILURE                     │
└─────────────────────────────────────────────────────────┘
```

### Error Handling Architecture

**Exception Hierarchy:**

```python
class TransformationError(Exception):
    """Base exception for all transformation errors."""
    pass

class CriticalTransformationError(TransformationError):
    """Fatal error - stops transformation immediately."""
    # Examples:
    # - Invalid YAML syntax
    # - Schema version mismatch
    # - Duplicate citation IDs

class SkippableTransformationError(TransformationError):
    """Non-fatal error - skip this rule/document, continue."""
    # Examples:
    # - Individual rule missing required field
    # - Metadata inference failure (falls back to defaults)
    # - Chapter/section parsing fails for one rule
```

**Fail-Fast vs. Graceful Degradation:**

| Error Type                    | Strategy               | Rationale                                   |
| ----------------------------- | ---------------------- | ------------------------------------------- |
| Invalid YAML syntax           | Fail-Fast              | Cannot proceed without valid input          |
| Schema version mismatch       | Fail-Fast              | Incompatible schemas = data corruption risk |
| Duplicate citation IDs        | Fail-Fast              | Breaks uniqueness constraint in database    |
| Missing source_file           | Fail-Fast              | Cannot group rules without this key         |
| Missing chapter (single rule) | Skip Rule              | Other rules still processable               |
| Expense type inference fails  | Default to ["general"] | Non-critical, has fallback                  |
| Province inference fails      | Default to None        | Non-critical, has fallback                  |

**Error Reporting:**

If errors occur during transformation, generate detailed report:

```yaml
# transformation_errors.yml
timestamp: "2025-10-17T10:30:00Z"
input_file: "output/cra_rules.yml"
output_file: "data/chunks.jsonl"

summary:
  total_rules: 247
  successful: 245
  skipped: 2
  errors: 2

errors:
  - rule_number: 9999
    source_file: "t4002-12.html"
    error: "Missing chapter field"
    severity: "skippable"
    action: "Skipped this rule, continued processing"

  - rule_number: 8765
    source_file: "t4002-15.html"
    error: "Invalid applies_to value: 'unknown'"
    severity: "skippable"
    action: "Defaulted applies_to to empty list"
```

______________________________________________________________________

## Part 5: CLI Integration & User Workflows

### New Commands

**1. Transform Command**

```bash
uv run extract-rules transform INPUT.yml OUTPUT.jsonl [OPTIONS]

Arguments:
  INPUT.yml      Input YAML file from extract-rules
  OUTPUT.jsonl   Output JSONL file for IndexBuilder

Options:
  --continue-on-error       Skip errors and continue (default: true)
  --error-report PATH       Path for error report YAML
  --verbose, -v             Enable verbose logging

Examples:
  # Basic transformation
  uv run extract-rules transform output/rules.yml data/chunks.jsonl

  # With error reporting
  uv run extract-rules transform output/rules.yml data/chunks.jsonl \
    --error-report errors.yml --verbose
```

**2. Auto-Transform Flag (Enhancement to existing command)**

```bash
uv run extract-rules HTML_DIR OUTPUT.yml [--auto-transform --output-jsonl PATH]

Example:
  # Extract and automatically transform to JSONL
  uv run extract-rules cra_documents/cra_t4002e_rev24_dump/ output/rules.yml \
    --auto-transform --output-jsonl data/chunks.jsonl
```

**3. pipeline-extraction Command (New end-to-end command)**

```bash
uv run python scripts/cli.py pipeline-extraction \
  --input-dir HTML_DIR \
  --output-db DATABASE.db

Stages:
  1. Extract rules from HTML (extract-rules)
  2. Transform YAML to JSONL (transformer)
  3. Build RAG database (existing build command)
  4. Validate database (existing validate command)

Example:
  uv run python scripts/cli.py pipeline-extraction \
    --input-dir cra_documents/cra_t4002e_rev24_dump/ \
    --output-db data/cra_rules.db
```

### User Workflows After Integration

**Workflow 1: Granular Control (Development/Debugging)**

```bash
# Step 1: Extract rules to YAML
uv run extract-rules cra_documents/cra_t4002e_rev24_dump/ output/rules.yml

# Step 2: Inspect YAML (manual review, corrections)
cat output/rules.yml | head -100
vim output/rules.yml  # Make manual corrections if needed

# Step 3: Transform YAML to JSONL
uv run extract-rules transform output/rules.yml data/chunks.jsonl

# Step 4: Build database
uv run python scripts/cli.py build --input-file data/chunks.jsonl \
  --output-db data/cra_rules.db

# Step 5: Validate database
uv run python scripts/cli.py validate --db-path data/cra_rules.db

# Step 6: Search
python -c "import qe_tax_rag as qe; qe.init(); print(qe.search('meals', top_k=3))"
```

**Workflow 2: Streamlined (Production)**

```bash
# One command: HTML → Database (via extraction pipeline)
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules.db

# Search
python -c "import qe_tax_rag as qe; qe.init(); print(qe.search('meals', top_k=3))"
```

**Workflow 3: Hybrid (Extract + Manual Review + Transform)**

```bash
# Extract with auto-transform
uv run extract-rules cra_documents/cra_t4002e_rev24_dump/ output/rules.yml \
  --auto-transform --output-jsonl data/chunks.jsonl

# Build and validate
uv run python scripts/cli.py build --input-file data/chunks.jsonl \
  --output-db data/cra_rules.db
uv run python scripts/cli.py validate --db-path data/cra_rules.db
```

**Workflow 4: Original Gemini Pipeline (Still Available)**

```bash
# Original pipeline continues to work
export GEMINI_API_KEY="your-key"
uv run python scripts/cli.py pipeline --input-dir cra_documents/...
```

### Three Pipeline Options

After implementation, users will have THREE options:

| Pipeline       | Data Source     | Quality   | Speed  | API Cost | Use Case                               |
| -------------- | --------------- | --------- | ------ | -------- | -------------------------------------- |
| **Gemini**     | Full document   | Good      | Medium | $$$      | Conceptual queries, exploratory search |
| **Extraction** | Line items only | Excellent | Fast   | $        | Specific line items, precise targeting |
| **Hybrid**     | Both            | Best      | Slow   | $$$$     | Maximum coverage and quality           |

______________________________________________________________________

## Part 6: Search Quality Impact Analysis

### Chunking Comparison

**Original Gemini Pipeline:**

- Granularity: Paragraph-level, section-level
- Chunk count: ~500-1000 chunks for T4002 guide
- Context: Rich document narrative, explanations, examples
- Structure: Hierarchical (chapters → sections → paragraphs)

**Extraction-Based Pipeline:**

- Granularity: Rule-level (one rule = one chunk)
- Chunk count: ~247 chunks (one per line item)
- Context: Chapter/section metadata, but flatter
- Structure: Grouped by file → chapter → section → rules

### Advantages of Extraction Approach

**1. Precision Targeting**

- Each rule is atomic unit
- Example: "Line 8523" → Direct hit (not buried in section)
- Better for users who know specific line numbers

**2. Higher Content Quality**

- MoE + adjudication → more accurate text
- Confidence scores enable filtering
- Less noise from navigation/explanatory content

**3. Better Metadata**

- Income type (business/farming/fishing)
- Inferred expense categories
- Audit trail (expert source, confidence)

**4. Fewer Irrelevant Results**

- Focused on "what can I deduct?"
- No conceptual guidance chunks

### Disadvantages of Extraction Approach

**1. Loss of Context**

- No surrounding explanatory text
- Introductory paragraphs dropped
- Cross-references lost

**2. Fewer Chunks**

- 247 vs 1000 → less embedding coverage
- Could hurt exploratory queries

**3. Rigid Structure**

- Only "Line XXXX" patterns extracted
- Misses conceptual sections
- Users asking "What is a business expense?" may get no results

### Hybrid Search Impact

**FTS5 Keyword Search:**

- BETTER: Each rule self-contained, exact matching works well
- BETTER: Rule titles are descriptive
- RISK: Fewer chunks → fewer keyword matches

**Vector Semantic Search:**

- BETTER: Focused content → purer embeddings
- RISK: Smaller corpus → less rich embedding space
- RISK: No conceptual chunks → conceptual queries fail

**RRF Fusion:**

- Should still work well (combines both rankings)
- May need to adjust k parameter (currently k=60)

### Mitigation: Dual Indexing (Recommended)

Build TWO databases and let users choose:

**1. Gemini Database (gemini_rules.db)**

- Full document content
- Conceptual guidance
- Exploratory search
- Use case: "How do I calculate depreciation?"

**2. Extraction Database (extraction_rules.db)**

- Line items only
- Precise targeting
- Higher quality
- Use case: "What can I deduct for meals?"

**Configuration:**

```python
import qe_tax_rag as qe

# Use extraction database (default)
qe.init(database="extraction_rules.db")
results = qe.search("meals", top_k=5)

# Use Gemini database (conceptual queries)
qe.init(database="gemini_rules.db")
results = qe.search("What is a business expense?", top_k=5)
```

### Expected Performance

| Query Type          | Gemini Pipeline | Extraction Pipeline  | Change      |
| ------------------- | --------------- | -------------------- | ----------- |
| Line-item specific  | 60% precision   | 85% precision        | +25% BETTER |
| Conceptual          | 70% recall      | 30% recall           | -40% WORSE  |
| Semantic similarity | 65% MRR         | 70% MRR              | +5% BETTER  |
| Overall             | Baseline        | Depends on query mix | MEASURE     |

**Testing Plan:**

1. Create golden dataset (50 test queries)
1. Run against both databases
1. Measure precision, recall, MRR
1. Document trade-offs
1. Recommend which pipeline for which use case

______________________________________________________________________

## Part 7: Implementation Roadmap

### Phase 1: Schema Compatibility (Critical Path)

**MUST BE DONE FIRST**

**Task 1.1: Relax Citation ID Pattern**

- File: `src/qe_tax_rag/search/models.py`
- Line: SearchResult.citation_id field
- Change:
  ```python
  # FROM:
  citation_id: str = Field(
      ...,
      pattern=r"S\d+-F\d+-C\d+-p\d+\.?\d*",
      description="The unique CRA citation identifier."
  )

  # TO:
  citation_id: str = Field(
      ...,
      pattern=r"^(S\d+-F\d+-C\d+-p\d+\.?\d*|LINE-\d+)$",
      description="The unique CRA citation identifier (S-F-C-p or LINE-XXXX format)."
  )
  ```
- Impact: Backward compatible (existing patterns still valid)
- Testing: Unit test with both formats

**Task 1.2: Extend ParsedDocument Metadata Schema**

- File: `scripts/parser/schema.py`
- Changes:
  ```python
  # Add to Metadata class:
  class Metadata(BaseModel):
      province: list[str] = Field(default_factory=list)
      business_type: list[str] = Field(default_factory=list)
      expense_type: list[str] = Field(default_factory=list)
      income_type: list[str] = Field(default_factory=list)  # NEW

  # Add to TextChunk class:
  class TextChunk(BaseModel):
      type: Literal["paragraph", "footnote"]
      text: str
      citation_id: str | None = None
      # NEW: Extraction metadata
      extraction_source: str | None = None
      extraction_confidence: float | None = None
      source_anchor: str | None = None
  ```
- Impact: Backward compatible (new fields are optional)
- Testing: Ensure existing JSONL still parses

**Task 1.3: Verify Database Schema**

- File: `src/qe_tax_rag/data/schema.py`
- Check: `metadata_json TEXT` field exists (it does)
- Action: No changes needed (extraction metadata stores in JSON)

### Phase 2: Core Transformer Implementation

**Task 2.1: Create Transformer Module**

- File: `src/qe_tax_rag/extraction/ca/transformer.py`
- Functions to implement:
  ```python
  def transform_yaml_to_jsonl(
      yaml_path: Path,
      jsonl_path: Path,
      continue_on_error: bool = True,
  ) -> TransformationReport:
      """Main entry point."""

  def load_yaml(yaml_path: Path) -> RuleSet:
      """Load and validate YAML."""

  def group_by_source_file(rules: list[ExtractedRule]) -> dict[str, list[ExtractedRule]]:
      """Group rules by source_file."""

  def transform_rules_to_document(
      source_file: str,
      rules: list[ExtractedRule]
  ) -> ParsedDocument:
      """Create ParsedDocument from rules."""

  def infer_expense_types(rule: ExtractedRule) -> list[str]:
      """Keyword-based classifier."""

  def validate_yaml_input(rule_set: RuleSet) -> None:
      """Pre-transformation validation."""

  def validate_jsonl_output(jsonl_path: Path) -> ValidationReport:
      """Post-transformation validation."""
  ```

**Task 2.2: Implement Grouping Logic**

- Group rules by source_file
- Within each file, group by chapter
- Within each chapter, group by section
- Build hierarchical Section structure
- Map each ExtractedRule → TextChunk

**Task 2.3: Implement Metadata Mapping**

- applies_to → income_type (direct)
- Infer expense_type (keyword classifier)
- Province defaults to None
- Preserve audit trail (expert_source, confidence, anchor_id)

**Task 2.4: Implement Error Handling**

- Define exception hierarchy
- Implement fail-fast for critical errors
- Implement graceful degradation for non-critical
- Generate TransformationReport

### Phase 3: CLI Integration

**Task 3.1: Add Transform Command**

- File: `scripts/extract_rules.py`
- Add new `@app.command()` for `transform`
- CLI signature: `uv run extract-rules transform INPUT.yml OUTPUT.jsonl`
- Options: --continue-on-error, --error-report, --verbose

**Task 3.2: Add Auto-Transform Flag**

- File: `scripts/extract_rules.py`
- Modify existing `run` command
- Add options: --auto-transform, --output-jsonl
- Chain extraction → transformation

**Task 3.3: Add pipeline-extraction Command**

- File: `scripts/cli.py`
- Add new `@app.command()` for `pipeline_extraction`
- Orchestrate: extract → transform → build → validate

### Phase 4: Testing & Validation

**Task 4.1: Unit Tests**

- File: `tests/unit/test_transformer.py`
- Test functions:
  - test_group_by_source_file()
  - test_transform_rules_to_document()
  - test_infer_expense_types()
  - test_validate_yaml_input()
  - test_error_handling()

**Task 4.2: Integration Tests**

- File: `tests/integration/test_extraction_pipeline.py`
- Test full flow: YAML → JSONL → Database
- Compare with Gemini results
- Verify database integrity

**Task 4.3: Search Quality Tests**

- Create golden dataset (50 queries)
- Run against both databases
- Measure precision, recall, MRR
- Document trade-offs

**Task 4.4: Performance Tests**

- Measure transformation time
- Measure database build time
- Measure search latency

### Phase 5: Documentation & Rollout

**Task 5.1: Update Documentation**

- README.md: Add extraction pipeline section
- CLAUDE.md: Add transformer development guide
- Create this document (TRANSFORMER_DESIGN_PLAN.md)

**Task 5.2: Create Examples**

- Example notebooks
- Comparison guide

**Task 5.3: Migration Guide**

- For existing users
- Trade-offs and recommendations

______________________________________________________________________

## Part 8: Key Decisions Summary

| Decision               | Choice                         | Rationale                       | Impact                          |
| ---------------------- | ------------------------------ | ------------------------------- | ------------------------------- |
| **Citation ID Format** | LINE-{rule_number}             | Simple, traceable, unique       | Requires schema relaxation      |
| **Document Grouping**  | By source_file                 | Preserves document context      | Natural file-based organization |
| **applies_to Mapping** | income_type (new field)        | Semantically accurate           | Schema extension required       |
| **expense_type**       | Infer from content             | Keyword classifier              | Good enough for MVP             |
| **Province**           | Default to None                | Federal rules apply to all      | Manual mapping for future       |
| **Audit Trail**        | Preserve in metadata           | Enables quality filtering       | Slight storage overhead         |
| **Error Handling**     | Hybrid (fail-fast + graceful)  | Balance integrity and usability | Robust without brittleness      |
| **CLI Structure**      | Subcommand + auto-flag         | Flexible, discoverable          | Easy to use                     |
| **Search Quality**     | Dual indexing (both pipelines) | Gather data before decision     | No immediate deprecation        |

______________________________________________________________________

## Part 9: Success Metrics

### Short-Term (Week 5)

- [ ] Transformer implemented and tested
- [ ] Full pipeline runs end-to-end (HTML → YAML → JSONL → DB → Search)
- [ ] Search quality baseline established (both pipelines)
- [ ] Documentation complete (README, CLAUDE.md, this document)
- [ ] Users can choose pipeline via CLI flag

### Long-Term (3 months)

- [ ] 80%+ users prefer extraction pipeline
- [ ] Search quality meets or exceeds Gemini baseline
- [ ] Extraction pipeline is default recommendation
- [ ] Gemini pipeline moved to "legacy" or deprecated

### Measurement Criteria

**Data Quality:**

- Extraction confidence scores: Mean > 0.85
- Manual review rate: < 5%
- Citation accuracy: 100% (no duplicates, all valid)

**Search Quality:**

- Line-item queries: +20-30% precision improvement
- Conceptual queries: Documented trade-offs
- Overall MRR: Matches or exceeds Gemini

**User Experience:**

- Transformation time: < 10 seconds for 247 rules
- Database build time: < 5 minutes total
- Search latency: < 250ms per query
- Error rate: < 2% failed transformations

______________________________________________________________________

## Part 10: Risks & Mitigation

| Risk                                    | Impact | Probability | Mitigation                                    |
| --------------------------------------- | ------ | ----------- | --------------------------------------------- |
| **Search quality regression**           | High   | Medium      | Keep both pipelines, A/B test, gather data    |
| **Citation ID conflicts**               | Medium | Low         | Validate uniqueness in transformer            |
| **Metadata inference inaccuracy**       | Low    | Medium      | Manual review, improve classifier iteratively |
| **User confusion (two pipelines)**      | Medium | High        | Clear documentation, default recommendation   |
| **Schema evolution breaks transformer** | High   | Low         | Version compatibility checks, fail-fast       |
| **Performance degradation**             | Medium | Low         | Benchmark transformation, optimize if needed  |

______________________________________________________________________

## Conclusion

The YAML-to-JSONL transformer is the **critical missing piece** that connects the
high-quality extraction pipeline (TICKETS 1-6) with the existing RAG database
infrastructure.

### What It Unlocks

1. **Complete end-to-end extraction flow** (HTML → Search)
1. **Superior data quality** (MoE + adjudication)
1. **Enhanced metadata** (income types, expense categories, confidence)
1. **No Gemini API dependency** for extraction
1. **Editable intermediate format** (YAML)

### Implementation Approach

- **5-phase roadmap** with clear dependencies
- **Dual indexing strategy** (keep both pipelines)
- **Comprehensive testing** (unit, integration, search quality)
- **Robust error handling** (fail-fast + graceful degradation)
- **User-friendly CLI** (granular control + one-command convenience)

### Next Steps

1. **Review this plan** with stakeholders
1. **Implement Phase 1** (schema compatibility)
1. **Build transformer** (Phase 2)
1. **Test thoroughly** (Phase 4)
1. **Document and roll out** (Phase 5)

The transformer is estimated at **5 weeks of development** with proper testing and
documentation. It's a strategic investment that future-proofs the RAG system and enables
significant quality improvements.

______________________________________________________________________

**Generated:** 2025-10-17 **Planning Method:** Zen MCP Planner (gemini-2.5-pro)
**Status:** Ready for Implementation Review
