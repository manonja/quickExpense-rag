# Pipeline Testing & Validation Plan: HTML → YAML → SQLite

**Date:** 2025-10-22 **Status:** Ready for Implementation **Context:**
Post-normalization testing plan (transformer layer eliminated)

______________________________________________________________________

## Executive Summary

This plan breaks down the extraction pipeline testing into 5 progressive, MECE (Mutually
Exclusive, Collectively Exhaustive) tickets. Each ticket builds confidence
incrementally, from unit tests to full database provisioning.

**Critical Focus: RAG Quality Validation** This plan validates both the **process**
(pipeline runs correctly) AND the **product** (search retrieves relevant results).
Quality checks are integrated throughout all tickets to catch issues early:

- **Tickets 1-3**: Validate content integrity and metadata accuracy
- **Ticket 4**: Basic search quality (first real RAG testing)
- **Ticket 5**: Comprehensive RAG validation (Recall@5 >90%, semantic similarity, RRF
  ranking, filtering)

**Pipeline Architecture (Post-Normalization):**

```
HTML → Classic+LLM Parser → ExtractedRule (YAML) → DatabaseChunk → SQLite (FTS5 + Vector)
```

**Key Principles:**

- **80/20 Focus**: Test high-value paths first, avoid over-engineering
- **YAGNI**: Only test what's needed now, not speculative features
- **MECE**: No overlap between tickets, complete coverage
- **Type Safety**: Use Hypothesis for property-based testing with Pydantic models

______________________________________________________________________

## Dependency Graph

```
TICKET 3 (parallel) ─┐
                     ├─→ TICKET 1 ─→ TICKET 2 ─→ TICKET 4 ─→ TICKET 5
                     │
                     └──────────────────────────────────────────┘
```

**Critical Path:** T1 → T2 → T4 → T5 (16 hours) **Parallel Work:** T3 can be done
anytime (3 hours) **Total Effort:** 24 hours (3 developer-days)

______________________________________________________________________

## TICKET 1: Test Single HTML → YAML Extraction

### Goal

Validate that the extraction pipeline (Classic Parser + LLM Parser + Adjudicator)
produces correct, well-formed YAML output from HTML input.

### Scope

- **In Scope**: HTML parsing, rule extraction, adjudication logic, YAML serialization
- **Out of Scope**: Database insertion, expense classification, embedding generation

### Acceptance Criteria

#### AC1: Valid YAML Output

- Given a fixture HTML file, the extraction process runs without unhandled exceptions
- Output is a single YAML file that deserializes into a valid `RuleSet` Pydantic model
- YAML structure matches schema version 1.0

#### AC2: Citation ID Integrity

- Every `ExtractedRule` has a non-empty `citation_id` field
- Citation ID matches `LINE-{number}` format (e.g., `LINE-8523`)
- No duplicate `citation_id` values within a single `RuleSet`

#### AC3: Adjudicator Logic

- Adjudicator correctly merges outputs from Classic and LLM parsers
- Conflict resolution follows confidence score rules (highest confidence wins)
- All adjudicated rules have `expert_source` field set to appropriate value

#### AC4: Error Handling

- Malformed HTML produces error log and empty `RuleSet` (not crash)
- Empty HTML produces valid empty `RuleSet` with zero rules
- Missing required HTML elements (e.g., no line numbers) logs warnings

#### AC5: Property-Based Testing

- Hypothesis strategies for `ExtractedRule` and `RuleSet` validate model constraints
- YAML serialization/deserialization roundtrip preserves all fields
- Generated test cases cover edge cases (special characters, Unicode, long text)

#### AC6: Content Integrity (RAG Quality)

- Extracted YAML preserves key phrases essential for retrieval
- Given `simple_rule.html` fixture (about "Meals and entertainment"), the extracted
  `content` field must contain semantic keywords: `"deduct 50%"`,
  `"food, beverages, or entertainment"`
- Test fails if core semantic meaning is lost during extraction or adjudication
- Create "golden" YAML fixtures with known-good extractions for regression testing
- This ensures downstream search can find documents based on realistic user queries

### Implementation Tasks

1. **Add Hypothesis dependency**

   - Add `"hypothesis>=6.0"` to `pyproject.toml` dev dependencies
   - Configure Hypothesis profiles (default: 100 examples, CI: 500 examples)

1. **Create test fixtures**

   - Add 3-5 curated HTML files to `tests/fixtures/extraction/ca/`:
     - `simple_rule.html` - Single rule, minimal structure
     - `complex_rule.html` - Multiple rules, nested sections
     - `edge_case.html` - Special characters, missing anchors
     - `malformed.html` - Invalid HTML structure
     - `empty.html` - Empty document

1. **Create Hypothesis strategies**

   - File: `tests/unit/extraction/ca/test_hypothesis_strategies.py`
   - Strategy for `ExtractedRule` (valid rule_number, non-empty content)
   - Strategy for `RuleSet` (valid schema_version, list of rules)

1. **Mock Gemini API client**

   - File: `tests/conftest.py`
   - Fixture: `mock_gemini_client` returns canned responses
   - Include success, failure, and malformed response cases

1. **Unit tests**

   - File: `tests/unit/extraction/ca/test_extraction_e2e.py`
   - Test classic parser isolation
   - Test LLM parser with mocked API
   - Test adjudicator with controlled inputs
   - Test YAML roundtrip with Hypothesis

1. **Create curated YAML fixtures**

   - Save 3-5 representative YAML outputs to `tests/fixtures/extraction/ca/`
   - Use for regression testing in downstream tickets

1. **Add content integrity tests (AC6)**

   - File: `tests/unit/extraction/ca/test_content_integrity.py`
   - Test that `simple_rule.html` extraction contains expected keywords
   - Assert: `assert "deduct 50%" in extracted_rule.content`
   - Assert:
     `assert "food, beverages, or entertainment" in extracted_rule.content.lower()`
   - Create golden YAML fixtures with documented expected content

### Manual Testing Instructions

```bash
# Step 1: Extract a single HTML file to YAML
uv run extract-rules run \
  tests/fixtures/extraction/ca/simple_rule.html \
  output/test_single.yml

# Step 2: Verify YAML structure
cat output/test_single.yml

# Expected output:
# rules:
#   - rule_number: 8523
#     title: "Meals and entertainment"
#     content: "You can deduct 50%..."
#     citation_id: "LINE-8523"
#     ...
# schema_version: "1.0"
# extraction_timestamp: "2025-10-22T..."

# Step 3: Validate YAML deserializes correctly
uv run python -c "
from pathlib import Path
import yaml
from qe_tax_rag.extraction.ca.schema import RuleSet

with open('output/test_single.yml') as f:
    data = yaml.safe_load(f)

ruleset = RuleSet.model_validate(data)
print(f'✅ Valid RuleSet with {len(ruleset.rules)} rules')
print(f'✅ Schema version: {ruleset.schema_version}')
for rule in ruleset.rules:
    print(f'✅ Rule {rule.citation_id}: {rule.title}')
"

# Step 4: Test edge case (malformed HTML)
uv run extract-rules run \
  tests/fixtures/extraction/ca/malformed.html \
  output/test_malformed.yml

# Expected: Error logged, empty RuleSet created (not crash)

# Step 5: Run automated tests
uv run pytest tests/unit/extraction/ca/test_extraction_e2e.py -v
```

### Test Strategy

- **Type**: Unit tests (`@pytest.mark.unit`)
- **Fixtures**: 5 HTML files (common + edge cases)
- **Mocks**: Gemini API client
- **Hypothesis**: Model validation and roundtrip testing

### Estimated Effort

**6 hours**

______________________________________________________________________

## TICKET 2: Test YAML → SQLite Conversion

### Goal

Validate that `RuleSet.to_database_chunks()` correctly transforms YAML rules into
database-ready chunks and inserts them into SQLite.

### Scope

- **In Scope**: YAML deserialization, `DatabaseChunk` transformation, SQLite insertion,
  metadata preservation
- **Out of Scope**: HTML parsing, expense classification logic (mocked), embedding
  generation (mocked)

### Acceptance Criteria

#### AC1: YAML Deserialization

- `RuleSet.from_yaml()` successfully loads curated YAML fixtures
- All `ExtractedRule` objects pass Pydantic validation
- Schema version mismatch raises clear error

#### AC2: DatabaseChunk Transformation

- `to_database_chunks()` generates valid `DatabaseChunk` objects
- All chunks pass Pydantic validation (strict mode)
- Citation ID format preserved: `LINE-{number}`

#### AC3: Database Insertion

- Each `DatabaseChunk` successfully inserts into clean in-memory SQLite database
- No `UNIQUE` constraint violations on `citation_id`
- All required columns populated (no NULL in NOT NULL fields)

#### AC4: Metadata Preservation

- `income_type` preserved from `applies_to` field
- `extraction_source` preserved from `expert_source`
- `extraction_confidence` preserved from `confidence_score`
- `source_anchor` preserved from `anchor_id`
- `section_title` mapped from `chapter` field

#### AC5: Expense Type Inference

- `expense_types` field populated via `ExpenseTypeClassifier`
- Classifier output correctly stored as list of strings
- Empty classifier result stores `["general"]` as default

#### AC6: Property-Based Testing

- Hypothesis generates wide variety of `RuleSet` structures
- `to_database_chunks()` handles all generated inputs without errors
- Database constraints enforced (e.g., citation_id uniqueness)

#### AC7: Chunk Content Fidelity (RAG Quality)

- Transformation from `ExtractedRule` → `DatabaseChunk` must be deterministic and
  complete
- `DatabaseChunk.content` field must be predictable combination of `ExtractedRule.title`
  and `ExtractedRule.content`
- Unit test verifies no silent data loss (e.g., critical title dropped before
  embedding/FTS indexing)
- Test expense_type classification accuracy on known cases:
  - "restaurant meal expenses" → `["meals"]`
  - "vehicle fuel and maintenance" → `["vehicle", "maintenance"]`
- Create 5-10 curated ground truth examples with expected expense_types

### Implementation Tasks

1. **Create in-memory database fixture**

   - File: `tests/conftest.py`
   - Fixture: `in_memory_db` yields fresh SQLite connection per test
   - Initialize schema using `src/qe_tax_rag/data/schema.py`

1. **Create SourceFile fixtures**

   - Fixture: `source_files_mapping` returns dict of filename → SourceFile
   - Include common filenames from test data

1. **Integration tests**

   - File: `tests/integration/test_yaml_to_db.py`
   - Test YAML → RuleSet deserialization
   - Test RuleSet → DatabaseChunk transformation
   - Test DatabaseChunk → SQLite insertion
   - Verify data integrity with SQL queries

1. **Hypothesis tests**

   - Use `RuleSet` strategy from Ticket 1
   - Generate random RuleSets and test transformation
   - Verify no crashes, all constraints satisfied

1. **SQL integrity checks**

   - Query database after insertion
   - Verify row counts match expected
   - Check metadata JSON fields are valid
   - Confirm no NULL citation_ids

1. **Add chunk content fidelity tests (AC7)**

   - File: `tests/unit/test_database_chunk.py`
   - Test: verify `DatabaseChunk.content = f"{title}\n\n{content}"` or similar
     deterministic format
   - Create ground truth fixture: `tests/fixtures/expense_type_ground_truth.yml`
   - Structure: `{rule_content: str, expected_types: list[str]}`
   - Test 5-10 known cases for expense_type classification accuracy

### Manual Testing Instructions

```bash
# Step 1: Convert YAML to database chunks (Python REPL)
uv run python

>>> from pathlib import Path
>>> import yaml
>>> from qe_tax_rag.extraction.ca.schema import RuleSet
>>> from qe_tax_rag.search.models import SourceFile
>>>
>>> # Load YAML fixture
>>> with open('tests/fixtures/extraction/ca/sample_rules.yml') as f:
...     data = yaml.safe_load(f)
>>>
>>> ruleset = RuleSet.model_validate(data)
>>> print(f"Loaded {len(ruleset.rules)} rules")
>>>
>>> # Create source file mapping
>>> source_files = {
...     "t4002-24e": SourceFile(
...         path="t4002-24e.html",
...         url="https://www.canada.ca/t4002-24e.html",
...         hash="abc123"
...     )
... }
>>>
>>> # Convert to DatabaseChunks
>>> chunks = ruleset.to_database_chunks(source_files=source_files)
>>> print(f"Generated {len(chunks)} database chunks")
>>>
>>> # Inspect first chunk
>>> chunk = chunks[0]
>>> print(f"Citation ID: {chunk.citation_id}")
>>> print(f"Content: {chunk.content[:100]}...")
>>> print(f"Expense Types: {chunk.expense_types}")
>>> print(f"Metadata: {chunk.metadata}")

# Step 2: Test database insertion
uv run python

>>> import sqlite3
>>> from qe_tax_rag.data.builder import IndexBuilder
>>> from qe_tax_rag.embeddings.encoder import EmbeddingService
>>>
>>> # Create in-memory database
>>> conn = sqlite3.connect(":memory:")
>>>
>>> # Initialize schema
>>> from qe_tax_rag.data.schema import SCHEMA_SQL
>>> conn.executescript(SCHEMA_SQL)
>>>
>>> # Insert chunks (simplified - actual uses IndexBuilder)
>>> for chunk in chunks:
...     conn.execute(
...         "INSERT INTO rules (citation_id, content, source_url, source_hash, expense_types, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
...         (chunk.citation_id, chunk.content, chunk.source_url, chunk.source_hash,
...          ','.join(chunk.expense_types), chunk.metadata.model_dump_json())
...     )
>>>
>>> # Verify insertion
>>> cursor = conn.execute("SELECT COUNT(*) FROM rules")
>>> print(f"✅ Inserted {cursor.fetchone()[0]} rows")
>>>
>>> # Check for NULL citation_ids
>>> cursor = conn.execute("SELECT COUNT(*) FROM rules WHERE citation_id IS NULL OR citation_id = ''")
>>> count = cursor.fetchone()[0]
>>> print(f"✅ NULL citation_ids: {count} (should be 0)")

# Step 3: Run automated tests
uv run pytest tests/integration/test_yaml_to_db.py -v

# Step 4: Test with Hypothesis (property-based)
uv run pytest tests/integration/test_yaml_to_db.py::test_hypothesis_yaml_to_db -v --hypothesis-show-statistics
```

### Test Strategy

- **Type**: Integration tests (`@pytest.mark.integration`)
- **Fixtures**: Curated YAML files from Ticket 1, in-memory SQLite, SourceFile mapping
- **Hypothesis**: RuleSet strategy for transformation robustness
- **Focus**: Transformation logic and database schema correctness

### Estimated Effort

**5 hours**

______________________________________________________________________

## TICKET 3: Test ExpenseTypeClassifier with Hypothesis

### Goal

Validate keyword-based expense type inference using property-based testing to ensure
robustness across diverse inputs.

### Scope

- **In Scope**: Keyword matching, expense type mapping, edge case handling
- **Out of Scope**: ML-based classification, semantic analysis, database integration

### Acceptance Criteria

#### AC1: Known Keyword Mapping

- Classifier returns correct expense type for unambiguous keywords
- Top 15 expense types correctly mapped:
  - "meals" (meal, food, restaurant, entertainment)
  - "travel" (travel, transportation, airfare, hotel)
  - "vehicle" (vehicle, automobile, car, fuel, mileage)
  - "home_office" (home office, workspace, rent)
  - "advertising" (advertising, marketing)
  - "supplies" (supplies, materials)
  - "professional_fees" (legal, accounting)
  - "utilities" (telephone, internet, electricity)
  - "insurance" (insurance, premium)
  - "capital" (capital cost, cca, depreciation)
  - "maintenance" (maintenance, repair)
  - "salaries" (salaries, wages, employee)
  - "office_equipment" (furniture, computer)
  - "interest" (interest, loan, financing)
  - "bad_debts" (bad debts, uncollectible)

#### AC2: Default Fallback

- Text with no relevant keywords returns `["general"]`
- Empty string returns `["general"]`
- Whitespace-only string returns `["general"]`

#### AC3: Multiple Keywords

- Text with multiple keywords returns all matching expense types
- Results are deterministic (same input → same output)
- No duplicate expense types in output list

#### AC4: Edge Case Robustness

- Handles special characters (Unicode, punctuation)
- Case-insensitive matching (MEAL, Meal, meal all match)
- Word boundary matching (`"meal"` matches, `"oatmeal"` does not)
- Very long text (10,000+ characters) processes without error

#### AC5: Property-Based Testing

- Hypothesis generates diverse text inputs
- No crashes or unhandled exceptions
- Output always returns non-empty list
- All returned values are valid expense type strings

#### AC6: Classification Accuracy Metrics (RAG Quality)

- Calculate precision/recall on curated test set (reuse ground truth from Ticket 2)
- Track classification accuracy: should be >85% for top 15 expense keywords
- Report confusion matrix for misclassifications (which keywords are often missed or
  wrongly matched)
- This ensures expense_type metadata is accurate for downstream filtering in search

### Implementation Tasks

1. **Unit tests with known keywords**

   - File: `tests/unit/extraction/ca/test_expense_classifier.py`
   - Test each of the 15 expense types with canonical keywords
   - Test case sensitivity
   - Test word boundaries

1. **Edge case tests**

   - Test empty string → `["general"]`
   - Test whitespace → `["general"]`
   - Test special characters (Unicode em-dash, etc.)
   - Test very long text (performance check)

1. **Multiple keyword tests**

   - Test "vehicle fuel maintenance" → `["vehicle", "maintenance"]`
   - Test determinism (same input, multiple runs)
   - Test no duplicates

1. **Hypothesis tests**

   - Strategy: `strategies.text()` for random text
   - Strategy: `strategies.sampled_from()` for known keywords
   - Property: Output is always non-empty list
   - Property: All items in output are valid expense type strings

1. **Add accuracy metrics tests (AC6)**

   - File: `tests/unit/extraction/ca/test_classifier_accuracy.py`
   - Load ground truth from `tests/fixtures/expense_type_ground_truth.yml`
   - Calculate precision, recall, accuracy for each expense type
   - Generate confusion matrix report
   - Assert overall accuracy >85%

### Manual Testing Instructions

```bash
# Step 1: Test known keyword mappings (Python REPL)
uv run python

>>> from qe_tax_rag.extraction.ca.schema import ExpenseTypeClassifier, ExtractedRule, ApplicabilityType, ExpertSource
>>>
>>> classifier = ExpenseTypeClassifier()
>>>
>>> # Test meals
>>> rule = ExtractedRule(
...     rule_number=1,
...     title="Meals",
...     content="You can deduct 50% of meal and entertainment expenses.",
...     applies_to=[ApplicabilityType.BUSINESS],
...     source_citation="Line 1",
...     chapter="Ch1",
...     source_file="test.html",
...     expert_source=ExpertSource.CLASSIC,
...     confidence_score=1.0
... )
>>> result = classifier.infer_expense_types(rule)
>>> print(f"Meals: {result}")  # Expected: ['meals']
>>>
>>> # Test vehicle
>>> rule2 = ExtractedRule(
...     rule_number=2,
...     title="Vehicle",
...     content="Deduct vehicle expenses including fuel and maintenance.",
...     applies_to=[ApplicabilityType.BUSINESS],
...     source_citation="Line 2",
...     chapter="Ch1",
...     source_file="test.html",
...     expert_source=ExpertSource.CLASSIC,
...     confidence_score=1.0
... )
>>> result2 = classifier.infer_expense_types(rule2)
>>> print(f"Vehicle: {result2}")  # Expected: ['vehicle', 'maintenance']
>>>
>>> # Test no keywords (default)
>>> rule3 = ExtractedRule(
...     rule_number=3,
...     title="Unknown",
...     content="Some unrelated text.",
...     applies_to=[ApplicabilityType.BUSINESS],
...     source_citation="Line 3",
...     chapter="Ch1",
...     source_file="test.html",
...     expert_source=ExpertSource.CLASSIC,
...     confidence_score=1.0
... )
>>> result3 = classifier.infer_expense_types(rule3)
>>> print(f"Unknown: {result3}")  # Expected: ['general']

# Step 2: Test edge cases
>>> # Empty content
>>> rule_empty = ExtractedRule(
...     rule_number=4,
...     title="",
...     content="",
...     applies_to=[ApplicabilityType.BUSINESS],
...     source_citation="Line 4",
...     chapter="Ch1",
...     source_file="test.html",
...     expert_source=ExpertSource.CLASSIC,
...     confidence_score=1.0
... )
>>> result_empty = classifier.infer_expense_types(rule_empty)
>>> print(f"Empty: {result_empty}")  # Expected: ['general']
>>>
>>> # Special characters
>>> rule_special = ExtractedRule(
...     rule_number=5,
...     title="Meals & Entertainment",
...     content="Food, beverages — 50% deductible.",
...     applies_to=[ApplicabilityType.BUSINESS],
...     source_citation="Line 5",
...     chapter="Ch1",
...     source_file="test.html",
...     expert_source=ExpertSource.CLASSIC,
...     confidence_score=1.0
... )
>>> result_special = classifier.infer_expense_types(rule_special)
>>> print(f"Special chars: {result_special}")  # Expected: ['meals']

# Step 3: Run automated tests
uv run pytest tests/unit/extraction/ca/test_expense_classifier.py -v

# Step 4: Run Hypothesis tests with statistics
uv run pytest tests/unit/extraction/ca/test_expense_classifier.py::test_hypothesis_classifier -v --hypothesis-show-statistics
```

### Test Strategy

- **Type**: Unit tests (`@pytest.mark.unit`)
- **Fixtures**: None (classifier is stateless)
- **Hypothesis**: Text generation + keyword sampling
- **Focus**: Top 15 expense keywords, edge cases

### Estimated Effort

**3 hours**

______________________________________________________________________

## TICKET 4: Test Single HTML → Complete Database Pipeline

### Goal

End-to-end integration test validating the full pipeline from HTML input to searchable
SQLite database.

### Scope

- **In Scope**: Full pipeline orchestration, FTS5 indexing, vector embeddings (mocked),
  search functionality
- **Out of Scope**: Production embedding generation (use mocked), full dataset
  processing

### Acceptance Criteria

#### AC1: E2E Pipeline Success

- `pipeline-extraction` command runs successfully for single HTML file
- No unhandled exceptions during extraction, transformation, or indexing
- Command completes within 30 seconds for single file

#### AC2: Database Creation

- SQLite database created at specified path
- Database file size > 0 bytes
- Database contains expected row count (matches input chunks)

#### AC3: FTS5 Search Functionality

- FTS5 virtual table (`rules_fts`) exists and is populated
- Keyword search returns correct records
- Example: searching "meals" returns rule about meal expenses
- Search result has correct `citation_id` and `content`

#### AC4: Vector Embeddings

- Vector table (`rules_vec`) exists and is populated
- Embedding dimension is 384 (BGE-small-en-v1.5)
- No NULL embeddings in database
- Mocked embeddings acceptable (fixed array for testing)

#### AC5: Data Integrity

- All `citation_id` values follow `LINE-{number}` format
- No NULL or empty `citation_id` values
- Metadata JSON is valid and parseable
- `expense_types` column populated for all rows

#### AC6: Component Integration

- Classic parser → LLM parser → Adjudicator chain works
- YAML serialization → DatabaseChunk transformation works
- DatabaseChunk → SQLite insertion works
- All components from Tickets 1-3 integrate correctly

#### AC7: Basic Search Quality Validation (First Real RAG Testing)

- 3-5 search queries against single-file database with expected results
- Example: If HTML is about meals, query "restaurant expense" should return the meals
  document
- Verify top result is semantically relevant (not just that results exist)
- Top result's `citation_id` should match expected document
- Example test cases:
  - Query: "food expenses" → Expected: meals document as top result
  - Query: "deductible percentage for client dinners" → Expected: meals document in top
    3

#### AC8: Negative Search Test (Precision Validation)

- Query for completely irrelevant term (e.g., "capital gains on stocks" when DB only has
  expense rules)
- Assert: either zero results returned OR top result has very low confidence score
  (\<0.3)
- This guards against system confidently returning irrelevant documents
- Ensures search has reasonable precision, not just recall

### Implementation Tasks

1. **Create E2E test file**

   - File: `tests/integration/test_html_to_db_e2e.py`
   - Use single canonical HTML fixture
   - Mock Gemini API client
   - Mock embedding service

1. **Mock embedding service (refined for AC7)**

   - File: `tests/conftest.py`
   - Fixture: `mock_embedding_service`
   - Instead of single fixed vector, return different vectors based on content:
     - If input contains "meals" or "food" or "restaurant": return
       `VECTOR_A = [0.1, 0.1, 0.1, ...]` (384-dim)
     - If input contains "vehicle" or "mileage": return
       `VECTOR_B = [0.9, 0.9, 0.9, ...]` (384-dim)
     - Otherwise: return `VECTOR_DEFAULT = [0.5, 0.5, 0.5, ...]` (384-dim)
   - This validates that vector similarity search actually works (not just that it runs)
   - Fast (no actual model loading)

1. **Test database creation**

   - Run `pipeline-extraction` via subprocess or direct function call
   - Verify database file exists
   - Check file size is reasonable

1. **Test FTS5 search**

   - Connect to generated database
   - Execute FTS5 query: `SELECT * FROM rules_fts WHERE rules_fts MATCH 'meals'`
   - Verify results are correct

1. **Test vector table**

   - Query `rules_vec` table
   - Verify row count matches `rules` table
   - Check embedding dimensions

1. **Integration verification**

   - Run all integrity checks from Tickets 1-3
   - Verify end-to-end data consistency

1. **Add search quality tests (AC7)**

   - File: `tests/integration/test_search_quality_e2e.py`
   - Define 3-5 test cases:
     `{query: str, expected_citation_id: str, expected_rank: int}`
   - Test: run `qe.search(query, top_k=5)` and assert expected doc is at expected rank
   - Example:
     `{"query": "food expenses", "expected_citation_id": "LINE-8523", "expected_rank": 1}`

1. **Add negative search test (AC8)**

   - Add to `tests/integration/test_search_quality_e2e.py`
   - Test: query for out-of-domain term
   - Assert: `len(results) == 0` OR `results[0].score < 0.3`

### Manual Testing Instructions

```bash
# Step 1: Prepare test environment
mkdir -p output/test_e2e

# Step 2: Run full pipeline on single HTML file
uv run python scripts/cli.py pipeline-extraction \
  --input-dir tests/fixtures/extraction/ca/ \
  --output-db output/test_e2e/single_file.db \
  --keep-intermediate

# Expected output:
# ✅ Stage 1/2: Extracting rules from HTML
#    Extracted N rules to YAML
# ✅ Stage 2/2: Building searchable database
#    Database built: output/test_e2e/single_file.db
# ✅ Stage 3/2: Validating database
#    Validation passed
# 🎉 Pipeline complete!

# Step 3: Verify database exists
ls -lh output/test_e2e/single_file.db
# Expected: File exists, size > 0 KB

# Step 4: Check database schema
uv run python -c "
import sqlite3
conn = sqlite3.connect('output/test_e2e/single_file.db')
cursor = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
tables = [row[0] for row in cursor.fetchall()]
print(f'✅ Tables: {tables}')
# Expected: ['metadata', 'rules', 'rules_fts', 'rules_vec']
"

# Step 5: Test FTS5 search
uv run python -c "
import sqlite3
conn = sqlite3.connect('output/test_e2e/single_file.db')

# FTS5 keyword search
cursor = conn.execute(\"SELECT citation_id, content FROM rules WHERE rowid IN (SELECT rowid FROM rules_fts WHERE rules_fts MATCH 'meals')\")
results = cursor.fetchall()

print(f'✅ FTS5 search results: {len(results)}')
for citation_id, content in results:
    print(f'  - {citation_id}: {content[:80]}...')
"

# Step 6: Verify vector embeddings
uv run python -c "
import sqlite3
conn = sqlite3.connect('output/test_e2e/single_file.db')

# Check vector table
cursor = conn.execute('SELECT COUNT(*) FROM rules_vec')
vec_count = cursor.fetchone()[0]
print(f'✅ Vector embeddings: {vec_count} rows')

# Check embedding dimension
cursor = conn.execute('SELECT embedding FROM rules_vec LIMIT 1')
embedding = cursor.fetchone()[0]
# Parse blob (float32 array)
import struct
dim = len(embedding) // 4  # 4 bytes per float32
print(f'✅ Embedding dimension: {dim} (expected: 384)')
"

# Step 7: Verify citation IDs
uv run python -c "
import sqlite3
conn = sqlite3.connect('output/test_e2e/single_file.db')

# Check for NULL citation_ids
cursor = conn.execute(\"SELECT COUNT(*) FROM rules WHERE citation_id IS NULL OR citation_id = ''\")
null_count = cursor.fetchone()[0]
print(f'✅ NULL citation_ids: {null_count} (should be 0)')

# Check citation_id format
cursor = conn.execute('SELECT citation_id FROM rules LIMIT 5')
citation_ids = [row[0] for row in cursor.fetchall()]
print(f'✅ Sample citation_ids: {citation_ids}')
# Expected: ['LINE-8523', 'LINE-8521', ...]
"

# Step 8: Run automated E2E tests
uv run pytest tests/integration/test_html_to_db_e2e.py -v

# Step 9: Clean up
rm -rf output/test_e2e
```

### Test Strategy

- **Type**: E2E integration test (`@pytest.mark.integration`, `@pytest.mark.slow`)
- **Fixtures**: One canonical HTML file, mocked Gemini API, mocked embeddings, in-memory
  SQLite
- **Focus**: Component wiring, FTS5 + vector integration, data integrity

### Estimated Effort

**6 hours**

______________________________________________________________________

## TICKET 5: Run Full Database Provisioning Script

### Goal

Process the entire T4002 document set (247 rules) and validate the production database.

### Scope

- **In Scope**: Full dataset processing, performance benchmarking, production database
  validation
- **Out of Scope**: Unit testing (already covered), code changes (this is validation
  only)

### Acceptance Criteria

#### AC1: Pipeline Completion

- `pipeline-extraction` processes all 247 HTML documents without unhandled exceptions
- Pipeline completes within performance budget (\<15 minutes)
- All stages (extraction, build, validation) succeed

#### AC2: Database Creation

- SQLite database created at `data/cra_rules.db`
- Database file size is reasonable (expected: 15-25 MB)
- Database integrity verified with `PRAGMA integrity_check`

#### AC3: Row Count Validation

- `SELECT COUNT(*) FROM rules` returns plausible count (200-300 rows)
- `SELECT COUNT(*) FROM rules_fts` matches `rules` count
- `SELECT COUNT(*) FROM rules_vec` matches `rules` count

#### AC4: Citation ID Integrity

- `SELECT COUNT(*) FROM rules WHERE citation_id IS NULL OR citation_id = ''` returns 0
- All citation_ids follow `LINE-{number}` format
- No duplicate citation_ids

#### AC5: FTS5 Functionality

- FTS5 virtual table exists and is queryable
- Sample searches return expected results:
  - "meals" → meal expense rules
  - "vehicle" → vehicle expense rules
  - "Line 8523" → exact rule for line 8523

#### AC6: Vector Embeddings

- All rows have non-NULL embeddings
- Embedding dimensions are 384 for all rows
- Vector search returns results (even with mocked embeddings)

#### AC7: Metadata Integrity

- All `metadata_json` fields are valid JSON
- Income types, expense types, sources are populated
- No missing required metadata fields

#### AC8: Resource Cleanup

- Intermediate YAML files are deleted after successful run
- No orphaned temp directories
- Only final database and manifest remain

#### AC9: Ground Truth Evaluation (Comprehensive RAG Quality)

- Create curated evaluation set: `tests/evaluation/ground_truth.yml`
- Contains 15-20 representative queries with expected `citation_id`s
- Query types include:
  - **Keyword-heavy**: "Line 8523 meals and entertainment"
  - **Semantic/Natural Language**: "how much can I claim for feeding clients?"
  - **Jargon-based**: "CCA for Class 10 vehicles"
  - **Ambiguous**: "travel expenses" (could match multiple rules)
  - **Out-of-domain (negative)**: "capital gains on stocks" (should return zero or low
    confidence)

#### AC10: Search Relevance Testing (Recall@5)

- Automated test runs every query from ground truth set
- For each query, assert at least one `expected_id` appears in top 5 results
- Track overall success rate: must exceed 90%
- This validates the RAG system retrieves relevant documents for real user queries

#### AC11: Semantic Similarity Validation

- For 3-5 key concepts (meals, vehicle, home office), create 2-3 paraphrased queries
- Assert that each paraphrase retrieves the same top `citation_id`
- Example paraphrases for meals:
  - "deducting food expenses for business"
  - "can I write off restaurant bills from client meetings?"
  - "what is the rule for entertainment and meals?"
- All should return same top document (e.g., `LINE-8523`)

#### AC12: RRF Ranking Effectiveness

- Create 2-3 test cases where keyword or vector search alone is insufficient
- Test Case 1 (Vector-dominant): "what can I claim for assets that lose value?" should
  rank CCA rule higher with hybrid than FTS5 alone
- Test Case 2 (FTS-dominant): Query with specific jargon like `"T2200"` should find
  exact document via FTS5, and hybrid should preserve this top ranking
- Compare FTS-only vs vector-only vs hybrid search results
- Assert hybrid search improves or maintains ranking quality

#### AC13: Metadata Filtering Accuracy

- Using a query that returns multiple results (e.g., "business expenses"), apply filters
- Test Case 1: Filter by `expense_types=["vehicle"]` → all results contain "vehicle" in
  their `expense_types`
- Test Case 2: Filter by `income_type="business"` → all results apply to businesses
- Test Case 3: Filter combination: `expense_types=["vehicle"]` AND
  `income_type="business"` → all results satisfy BOTH conditions
- Test Case 4: Filter that should return no results still returns zero results

### Implementation Tasks

1. **Create validation script**

   - File: `scripts/validate_database.py`
   - Standalone script (not pytest)
   - Runs all integrity checks from ACs
   - Returns exit code 0 on success, 1 on failure

1. **Performance benchmarking**

   - Time each pipeline stage
   - Measure database size
   - Log row counts and stats
   - Save benchmark results to `output/benchmark_results.json`

1. **Manual validation checklist**

   - Document in `docs/howto/validating-database.md`
   - Step-by-step CLI commands
   - Expected outputs for each check

1. **Production database**

   - Run full pipeline on T4002 dataset
   - Save to `data/cra_rules.db`
   - Commit benchmark results to git

1. **Create ground truth evaluation set (AC9)**

   - File: `tests/evaluation/ground_truth.yml`
   - Manually research and populate 15-20 queries with expected citation_ids
   - Include diverse query types (keyword, semantic, jargon, ambiguous, negative)
   - Document rationale for each query/expected result pair

1. **Create RAG quality test suite (AC10-13)**

   - File: `tests/quality/test_rag_relevance.py`
   - Mark with custom marker: `@pytest.mark.rag_quality`
   - Requires production database from this ticket as fixture
   - Test recall@5 (AC10): iterate ground truth, assert expected doc in top 5
   - Test semantic similarity (AC11): paraphrased queries return same top result
   - Test RRF ranking (AC12): compare FTS-only, vector-only, hybrid rankings
   - Test metadata filtering (AC13): validate single filters, combinations, negative
     cases

### Manual Testing Instructions

```bash
# ============================================================
# STEP 1: Run Full Pipeline (Production Database)
# ============================================================

# Clear any existing database
rm -f data/cra_rules.db

# Run full pipeline
time uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules.db

# Expected output:
# ✅ Stage 1/2: Extracting rules from HTML
#    Found 247 HTML files to process
#    Extracted XXX rules to YAML
#
# ✅ Stage 2/2: Building searchable database
#    Database built: data/cra_rules.db
#    Database size: XX.XX MB
#
# ✅ Stage 3/2: Validating database
#    Validation passed
#
# 🎉 Pipeline complete!
#
# real    Xm XX.XXXs  (should be < 15 minutes)

# ============================================================
# STEP 2: Basic Database Checks
# ============================================================

# Check database file exists and size
ls -lh data/cra_rules.db
# Expected: File exists, size 15-25 MB

# Check SQLite integrity
sqlite3 data/cra_rules.db "PRAGMA integrity_check;"
# Expected: ok

# ============================================================
# STEP 3: Row Count Validation
# ============================================================

uv run python -c "
import sqlite3
conn = sqlite3.connect('data/cra_rules.db')

# Count rows in each table
tables = ['rules', 'rules_fts', 'rules_vec', 'metadata']
for table in tables:
    if table == 'metadata':
        continue  # metadata is key-value, different structure
    try:
        cursor = conn.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'✅ {table}: {count} rows')
    except Exception as e:
        print(f'❌ {table}: Error - {e}')

# Expected:
# ✅ rules: 200-300 rows (depends on extraction)
# ✅ rules_fts: same as rules
# ✅ rules_vec: same as rules
"

# ============================================================
# STEP 4: Citation ID Integrity
# ============================================================

uv run python -c "
import sqlite3
conn = sqlite3.connect('data/cra_rules.db')

# Check for NULL or empty citation_ids
cursor = conn.execute(
    \"SELECT COUNT(*) FROM rules WHERE citation_id IS NULL OR citation_id = ''\"
)
null_count = cursor.fetchone()[0]
print(f'NULL/empty citation_ids: {null_count}')
assert null_count == 0, '❌ Found NULL or empty citation_ids!'
print('✅ All citation_ids are valid')

# Check citation_id format
cursor = conn.execute('SELECT citation_id FROM rules LIMIT 10')
sample_ids = [row[0] for row in cursor.fetchall()]
print(f'✅ Sample citation_ids: {sample_ids}')
# Expected: ['LINE-8523', 'LINE-8521', 'LINE-8540', ...]

# Check for duplicates
cursor = conn.execute(
    'SELECT citation_id, COUNT(*) FROM rules GROUP BY citation_id HAVING COUNT(*) > 1'
)
duplicates = cursor.fetchall()
if duplicates:
    print(f'❌ Duplicate citation_ids: {duplicates}')
else:
    print('✅ No duplicate citation_ids')
"

# ============================================================
# STEP 5: FTS5 Search Validation
# ============================================================

uv run python -c "
import sqlite3
conn = sqlite3.connect('data/cra_rules.db')

# Test FTS5 search for 'meals'
cursor = conn.execute(
    \"\"\"
    SELECT citation_id, content
    FROM rules
    WHERE rowid IN (
        SELECT rowid FROM rules_fts WHERE rules_fts MATCH 'meals'
    )
    LIMIT 5
    \"\"\"
)
results = cursor.fetchall()
print(f'✅ FTS5 search \"meals\": {len(results)} results')
for citation_id, content in results:
    print(f'  - {citation_id}: {content[:80]}...')

# Test FTS5 search for 'vehicle'
cursor = conn.execute(
    \"\"\"
    SELECT citation_id, content
    FROM rules
    WHERE rowid IN (
        SELECT rowid FROM rules_fts WHERE rules_fts MATCH 'vehicle'
    )
    LIMIT 5
    \"\"\"
)
results = cursor.fetchall()
print(f'✅ FTS5 search \"vehicle\": {len(results)} results')

# Test exact line number search
cursor = conn.execute(
    \"\"\"
    SELECT citation_id, content
    FROM rules
    WHERE rowid IN (
        SELECT rowid FROM rules_fts WHERE rules_fts MATCH 'Line 8523'
    )
    LIMIT 1
    \"\"\"
)
result = cursor.fetchone()
if result:
    print(f'✅ Exact search \"Line 8523\": {result[0]}')
else:
    print('⚠️  No result for \"Line 8523\" (may be expected)')
"

# ============================================================
# STEP 6: Vector Embeddings Validation
# ============================================================

uv run python -c "
import sqlite3
import struct
conn = sqlite3.connect('data/cra_rules.db')

# Check for NULL embeddings
cursor = conn.execute('SELECT COUNT(*) FROM rules_vec WHERE embedding IS NULL')
null_count = cursor.fetchone()[0]
print(f'NULL embeddings: {null_count}')
assert null_count == 0, '❌ Found NULL embeddings!'
print('✅ All embeddings are non-NULL')

# Check embedding dimensions
cursor = conn.execute('SELECT embedding FROM rules_vec LIMIT 1')
embedding_blob = cursor.fetchone()[0]
# Parse float32 array
dim = len(embedding_blob) // 4  # 4 bytes per float32
print(f'✅ Embedding dimension: {dim} (expected: 384)')
assert dim == 384, f'❌ Wrong dimension: {dim}'
"

# ============================================================
# STEP 7: Metadata Validation
# ============================================================

uv run python -c "
import sqlite3
import json
conn = sqlite3.connect('data/cra_rules.db')

# Check metadata_json is valid JSON
cursor = conn.execute('SELECT citation_id, metadata_json FROM rules LIMIT 10')
for citation_id, metadata_json in cursor.fetchall():
    try:
        metadata = json.loads(metadata_json)
        print(f'✅ {citation_id}: Valid JSON metadata')
        # Check required fields
        required_fields = ['income_type', 'extraction_source']
        for field in required_fields:
            if field not in metadata:
                print(f'  ⚠️  Missing field: {field}')
    except json.JSONDecodeError as e:
        print(f'❌ {citation_id}: Invalid JSON - {e}')

print('✅ Metadata validation complete')
"

# ============================================================
# STEP 8: Run Validation Script
# ============================================================

uv run python scripts/validate_database.py --db-path data/cra_rules.db

# Expected output:
# ✅ Database integrity check passed
# ✅ Row counts: rules=247, fts=247, vec=247
# ✅ Citation ID integrity passed
# ✅ FTS5 search functional
# ✅ Vector embeddings valid
# ✅ Metadata validation passed
# 🎉 All validation checks passed!

# ============================================================
# STEP 9: Performance Benchmarks
# ============================================================

# View benchmark results (if saved)
cat output/benchmark_results.json

# Expected structure:
# {
#   "pipeline_duration_seconds": 600.5,
#   "extraction_duration_seconds": 400.2,
#   "build_duration_seconds": 180.1,
#   "validation_duration_seconds": 20.2,
#   "database_size_mb": 18.5,
#   "total_rules": 247,
#   "rules_per_second": 0.41
# }

# ============================================================
# STEP 10: Test Search API (End-User Experience)
# ============================================================

uv run python -c "
import qe_tax_rag as qe

# Initialize (loads data/cra_rules.db)
qe.init()

# Run search
results = qe.search('restaurant meal expense', top_k=5)

print(f'Found {len(results)} results:')
for i, r in enumerate(results, 1):
    print(f'{i}. {r.citation_id} (Score: {r.score:.2f})')
    print(f'   Content: {r.content[:100]}...')
    print(f'   Expense Types: {r.expense_types}')
    print()
"

# Expected: 5 results, top result is about meals with high score (>0.7)
```

### Validation Script Structure

Create `scripts/validate_database.py`:

```python
#!/usr/bin/env python3
"""Validate database integrity after pipeline run."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def validate_database(db_path: Path) -> dict[str, bool]:
    """Run all validation checks and return results."""
    results = {}
    conn = sqlite3.connect(str(db_path))

    # 1. Database integrity
    cursor = conn.execute("PRAGMA integrity_check")
    results["integrity"] = cursor.fetchone()[0] == "ok"

    # 2. Row counts
    cursor = conn.execute("SELECT COUNT(*) FROM rules")
    rules_count = cursor.fetchone()[0]
    results["row_count"] = rules_count > 0

    # 3. Citation ID integrity
    cursor = conn.execute(
        "SELECT COUNT(*) FROM rules WHERE citation_id IS NULL OR citation_id = ''"
    )
    results["citation_id"] = cursor.fetchone()[0] == 0

    # 4. FTS5 search
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM rules WHERE rowid IN "
            "(SELECT rowid FROM rules_fts WHERE rules_fts MATCH 'meals')"
        )
        results["fts5"] = cursor.fetchone()[0] > 0
    except Exception:
        results["fts5"] = False

    # 5. Vector embeddings
    cursor = conn.execute("SELECT COUNT(*) FROM rules_vec WHERE embedding IS NULL")
    results["vectors"] = cursor.fetchone()[0] == 0

    # 6. Metadata JSON
    cursor = conn.execute("SELECT metadata_json FROM rules LIMIT 10")
    valid_json = True
    for (metadata_json,) in cursor.fetchall():
        try:
            json.loads(metadata_json)
        except json.JSONDecodeError:
            valid_json = False
            break
    results["metadata"] = valid_json

    conn.close()
    return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate database integrity")
    parser.add_argument("--db-path", type=Path, required=True)
    args = parser.parse_args()

    if not args.db_path.exists():
        print(f"❌ Database not found: {args.db_path}")
        return 1

    print(f"Validating database: {args.db_path}")
    results = validate_database(args.db_path)

    # Print results
    all_passed = True
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All validation checks passed!")
        return 0
    else:
        print("\n❌ Some validation checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### Test Strategy

- **Type**: System/Manual Test (not pytest)
- **Execution**: Full `pipeline-extraction` on production dataset
- **Validation**: Standalone integrity check script
- **Services**: Real or mocked (mocked recommended for speed)

### Estimated Effort

**4 hours** (includes run time + validation script creation)

______________________________________________________________________

## Appendix A: Hypothesis Configuration

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "pytest-asyncio>=0.21",
    "hypothesis>=6.0",  # Add this line
    "ruff>=0.1",
    "mypy>=1.7",
    "pre-commit>=3.5",
    "pyfakefs>=5.0",
    "types-PyYAML>=6.0",
]
```

Create `.hypothesis/profiles.ini`:

```ini
[default]
max_examples = 100
derandomize = false

[ci]
max_examples = 500
derandomize = false

[quick]
max_examples = 10
derandomize = true
```

______________________________________________________________________

## Appendix B: Common Issues & Troubleshooting

### Issue: "No module named 'hypothesis'"

**Solution**: Run `uv sync` to install dev dependencies

### Issue: "UNIQUE constraint failed: rules.citation_id"

**Solution**: Check for duplicate `rule_number` in extraction output. Verify adjudicator
is deduplicating correctly.

### Issue: "FTS5 search returns 0 results"

**Solution**: Verify FTS5 table is populated: `SELECT COUNT(*) FROM rules_fts`. Check if
triggers are firing.

### Issue: "Embedding dimension is 0"

**Solution**: Check that embedding service is properly mocked/initialized. Verify blob
serialization.

### Issue: "Pipeline takes > 15 minutes"

**Solution**: Profile with `time` command. Check if LLM API is being called (should be
mocked for tests). Verify embedding generation is efficient.

______________________________________________________________________

## Appendix C: Success Metrics

After completing all 5 tickets, you should have:

### Pipeline Quality Metrics

1. **95%+ test coverage** on extraction pipeline code
1. **Zero failing tests** in CI/CD
1. **Production database** (`data/cra_rules.db`) validated and ready
1. **Performance benchmarks** documented
1. **Reusable validation script** for future releases

### RAG Quality Metrics (NEW)

6. **Content integrity validated** - Extracted rules preserve semantic keywords (Ticket
   1 AC6)
1. **Metadata accuracy >85%** - Expense type classification accuracy on curated test set
   (Ticket 3 AC6)
1. **Search relevance >90%** - Recall@5 on ground truth evaluation set (Ticket 5 AC10)
1. **Semantic consistency** - Paraphrased queries return same top result (Ticket 5 AC11)
1. **Hybrid search effectiveness** - RRF ranking validated against FTS-only and
   vector-only (Ticket 5 AC12)
1. **Filtering accuracy 100%** - Metadata filters return only matching documents (Ticket
   5 AC13)

### Overall Confidence

12. **Confidence** that the RAG system works end-to-end AND retrieves relevant results
    for real user queries

______________________________________________________________________

## Next Steps After Ticket 5

1. Commit production database to git (or upload to GitHub Releases)
1. Update `USER_GUIDE.md` with new testing instructions
1. Create release notes documenting pipeline improvements
1. Set up CI/CD to run all tests on every commit
1. Monitor production usage and iterate based on feedback

______________________________________________________________________

**Document Version:** 1.0 **Last Updated:** 2025-10-22 **Authors:** QE Tax RAG Team +
Zen MCP Consultation
