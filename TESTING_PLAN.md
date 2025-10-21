# Testing Plan: Extraction Pipeline Validation

**Date:** 2025-10-21
**Status:** Ready for Implementation
**Approach:** Test-Driven Development with Progressive Validation

---

## Overview

This plan validates the extraction pipeline through 5 progressive tickets:

1. **TICKET 1:** HTML → YAML extraction (single file)
2. **TICKET 2:** JSONL → SQLite database construction
3. **TICKET 3:** YAML → JSONL transformation (property-based testing)
4. **TICKET 4:** End-to-end single HTML → complete database
5. **TICKET 5:** Full batch processing (multiple HTML files)

**Principles Applied:** MECE, 80/20, YAGNI, Progressive Validation

---

## TICKET 1: Validate HTML-to-YAML Extraction for Single Document

### Goal

Verify that the extraction pipeline (Classic Parser + LLM Parser + Adjudicator) produces valid, schema-compliant YAML from a single HTML document.

### Acceptance Criteria

1. ✅ Given a sample HTML file, extraction produces a non-empty YAML file
2. ✅ The YAML can be deserialized into its Pydantic model without `ValidationError`
3. ✅ Deserialized object contains key values matching the source HTML (e.g., title, section headers)
4. ✅ Malformed/empty HTML raises documented `ExtractionError`

### Manual Testing Commands

```bash
# Test 1: Extract a single HTML file to YAML
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/t4002-1.html \
  output/test_single.yml \
  --verbose

# Verify YAML was created
ls -lh output/test_single.yml

# Inspect YAML structure
head -50 output/test_single.yml

# Test 2: Validate YAML against Pydantic schema (create test script)
cat > test_yaml_validation.py <<'EOF'
"""Validate extracted YAML against Pydantic schema."""
import yaml
from pathlib import Path
from src.qe_tax_rag.extraction.models import ExtractedDocument

yaml_path = Path("output/test_single.yml")
with yaml_path.open() as f:
    data = yaml.safe_load(f)

# This will raise ValidationError if schema is invalid
doc = ExtractedDocument(**data)
print(f"✅ YAML is valid! Document has {len(doc.rules)} rules")
print(f"Document metadata: {doc.metadata}")
EOF

uv run python test_yaml_validation.py

# Test 3: Extract with malformed HTML (should fail gracefully)
echo "<html><incomplete>" > output/malformed.html
uv run extract-rules extract \
  output/malformed.html \
  output/should_fail.yml \
  --verbose
# Expected: Error message, no YAML file created
```

### Automated Test Structure

```python
# tests/unit/extraction/test_html_to_yaml.py

import pytest
from pathlib import Path
from src.qe_tax_rag.extraction.models import ExtractedDocument
from src.qe_tax_rag.extraction.orchestrator import extract_html_to_yaml

@pytest.fixture
def golden_html(tmp_path):
    """Provide path to known-good HTML file."""
    return Path("tests/fixtures/extraction/t4002-sample.html")

@pytest.fixture
def malformed_html(tmp_path):
    """Create malformed HTML for error testing."""
    malformed = tmp_path / "malformed.html"
    malformed.write_text("<html><incomplete>")
    return malformed

def test_extraction_produces_valid_yaml(golden_html, tmp_path):
    """Test that extraction produces valid YAML."""
    output_yaml = tmp_path / "output.yml"

    # Run extraction
    extract_html_to_yaml(golden_html, output_yaml)

    # Verify YAML exists and is non-empty
    assert output_yaml.exists()
    assert output_yaml.stat().st_size > 0

    # Verify YAML is valid Pydantic model
    import yaml
    with output_yaml.open() as f:
        data = yaml.safe_load(f)

    doc = ExtractedDocument(**data)  # Raises ValidationError if invalid
    assert len(doc.rules) > 0

def test_extraction_handles_malformed_html(malformed_html, tmp_path):
    """Test that malformed HTML raises ExtractionError."""
    output_yaml = tmp_path / "output.yml"

    with pytest.raises(ExtractionError):
        extract_html_to_yaml(malformed_html, output_yaml)
```

### 80/20 Focus

✅ **Test This:**
- YAML structural integrity
- Pydantic schema compliance
- Spot-check key fields (title, section count)

❌ **Skip This:**
- Exhaustive field-by-field validation
- LLM accuracy auditing
- Performance benchmarking

### Dependencies

None (foundational ticket)

---

## TICKET 2: Validate JSONL-to-SQLite Database Construction

### Goal

Ensure the database builder correctly ingests JSONL into SQLite with proper schema, indexes, and FTS5 functionality.

### Acceptance Criteria

1. ✅ Given JSONL with N records, builder creates SQLite with expected schema
2. ✅ Main `chunks` table contains exactly N rows
3. ✅ FTS5 index is functional (MATCH query returns correct records)
4. ✅ Empty JSONL creates valid empty database
5. ✅ Malformed JSONL line raises `DBBuilderError`

### Manual Testing Commands

```bash
# Prerequisite: Create a sample JSONL file
cat > output/test_chunks.jsonl <<'EOF'
{"citation_id": "LINE-1", "content": "Meals and entertainment expenses are 50% deductible", "source_url": "file:///test.html", "expense_types": ["meals"], "income_type": ["business"]}
{"citation_id": "LINE-2", "content": "Vehicle expenses include fuel and maintenance", "source_url": "file:///test.html", "expense_types": ["vehicle"], "income_type": ["business"]}
{"citation_id": "LINE-3", "content": "Home office deduction requires dedicated workspace", "source_url": "file:///test.html", "expense_types": ["home_office"], "income_type": ["business"]}
EOF

# Test 1: Build database from JSONL
uv run python scripts/cli.py build \
  --input-file output/test_chunks.jsonl \
  --output-db output/test_from_jsonl.db

# Verify database was created
ls -lh output/test_from_jsonl.db

# Test 2: Inspect database schema
sqlite3 output/test_from_jsonl.db <<'SQL'
.schema
.tables
SELECT COUNT(*) FROM chunks;
SELECT citation_id, substr(content, 1, 50) FROM chunks LIMIT 3;
SQL

# Test 3: Verify FTS5 search works
sqlite3 output/test_from_jsonl.db <<'SQL'
SELECT citation_id, content
FROM chunks
WHERE content MATCH 'meals';
SQL
# Expected: LINE-1 returned

# Test 4: Test with empty JSONL
touch output/empty.jsonl
uv run python scripts/cli.py build \
  --input-file output/empty.jsonl \
  --output-db output/empty.db
# Expected: Valid database with 0 rows

# Test 5: Test with malformed JSONL
cat > output/malformed.jsonl <<'EOF'
{"citation_id": "LINE-1", "content": "Valid line"}
{this is not valid json}
EOF

uv run python scripts/cli.py build \
  --input-file output/malformed.jsonl \
  --output-db output/should_fail.db
# Expected: Error message about invalid JSON
```

### Automated Test Structure

```python
# tests/unit/data/test_jsonl_to_sqlite.py

import pytest
import sqlite3
from pathlib import Path
from src.qe_tax_rag.data.builder import build_database_from_jsonl

@pytest.fixture
def golden_jsonl(tmp_path):
    """Create valid JSONL fixture."""
    jsonl = tmp_path / "golden.jsonl"
    jsonl.write_text(
        '{"citation_id": "LINE-1", "content": "Test content", "expense_types": ["meals"]}\n'
        '{"citation_id": "LINE-2", "content": "Another test", "expense_types": ["travel"]}\n'
    )
    return jsonl

def test_database_builder_creates_valid_schema(golden_jsonl, tmp_path):
    """Test that builder creates correct database schema."""
    db_path = tmp_path / "test.db"

    build_database_from_jsonl(golden_jsonl, db_path)

    # Verify database exists
    assert db_path.exists()

    # Check schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Verify tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "chunks" in tables
    assert "chunks_fts" in tables

    conn.close()

def test_database_contains_correct_row_count(golden_jsonl, tmp_path):
    """Test that all JSONL records are inserted."""
    db_path = tmp_path / "test.db"

    build_database_from_jsonl(golden_jsonl, db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    count = cursor.fetchone()[0]

    assert count == 2  # Two lines in golden_jsonl
    conn.close()

def test_fts5_search_functional(golden_jsonl, tmp_path):
    """Test that FTS5 index works."""
    db_path = tmp_path / "test.db"

    build_database_from_jsonl(golden_jsonl, db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT citation_id FROM chunks WHERE content MATCH 'Test'")
    results = cursor.fetchall()

    assert len(results) > 0
    assert results[0][0] == "LINE-1"
    conn.close()
```

### 80/20 Focus

✅ **Test This:**
- Schema creation (tables, columns, indexes)
- Row count accuracy
- FTS5 indexing functionality
- Error handling for malformed input

❌ **Skip This:**
- Deep vector search similarity testing (just verify blob dimension)
- Performance benchmarking
- Edge cases in embedding generation

### Dependencies

Ticket 3 (for reliable JSONL fixtures; can use hand-crafted JSONL to unblock)

---

## TICKET 3: Property-Based Validation of YAML-to-JSONL Transformation

### Goal

Use Hypothesis (property-based testing) to validate that the transformer robustly handles all valid input shapes.

### Acceptance Criteria

1. ✅ Transformer converts any valid Pydantic instance to valid JSONL
2. ✅ Correctly handles optional fields (present/absent)
3. ✅ Correctly handles lists of varying lengths (0, 1, many items)
4. ✅ Source Pydantic data correctly represented in output JSONL

### Manual Testing Commands

```bash
# Test 1: Transform existing YAML to JSONL
uv run extract-rules transform \
  output/test_single.yml \
  output/test_transformed.jsonl

# Verify JSONL was created
ls -lh output/test_transformed.jsonl

# Inspect JSONL structure (each line should be valid JSON)
head -5 output/test_transformed.jsonl

# Test 2: Validate each line is valid JSON
cat > validate_jsonl.py <<'EOF'
"""Validate that each JSONL line is valid JSON."""
import json
from pathlib import Path

jsonl_path = Path("output/test_transformed.jsonl")
line_count = 0
with jsonl_path.open() as f:
    for i, line in enumerate(f, 1):
        try:
            obj = json.loads(line)
            line_count += 1
            if i <= 3:  # Print first 3
                print(f"Line {i}: {obj.get('citation_id', 'N/A')}")
        except json.JSONDecodeError as e:
            print(f"❌ Line {i} is invalid JSON: {e}")

print(f"\n✅ All {line_count} lines are valid JSON")
EOF

uv run python validate_jsonl.py

# Test 3: Transform with edge cases (create test YAML)
cat > output/edge_cases.yml <<'EOF'
metadata:
  document_title: "Test Document"
  schema_version: "1.0"
rules:
  - rule_number: 1
    content: "Rule with minimal fields"
  - rule_number: 2
    content: "Rule with optional fields"
    expense_types: []  # Empty list
  - rule_number: 3
    content: "Rule with unicode: café, naïve, 日本語"
    expense_types: ["meals", "travel", "vehicle"]  # Many items
EOF

uv run extract-rules transform \
  output/edge_cases.yml \
  output/edge_cases.jsonl

uv run python validate_jsonl.py  # Should handle all edge cases
```

### Automated Test Structure

```python
# tests/unit/transformer/test_yaml_to_jsonl_property.py

import pytest
import json
from hypothesis import given, strategies as st
from hypothesis_pydantic import from_model
from src.qe_tax_rag.extraction.models import ExtractedDocument, ExtractedRule
from src.qe_tax_rag.transformer.converter import transform_yaml_to_jsonl

# Strategy for generating valid ExtractedRule instances
rule_strategy = from_model(
    ExtractedRule,
    rule_number=st.integers(min_value=1, max_value=10000),
    content=st.text(min_size=1, max_size=500),
    expense_types=st.lists(st.sampled_from(["meals", "travel", "vehicle"]), max_size=5),
)

@given(rule=rule_strategy)
def test_transformer_handles_any_valid_rule(rule, tmp_path):
    """Property test: transformer handles any valid ExtractedRule."""
    # Create minimal document with generated rule
    doc = ExtractedDocument(
        metadata={"schema_version": "1.0"},
        rules=[rule]
    )

    yaml_path = tmp_path / "test.yml"
    jsonl_path = tmp_path / "test.jsonl"

    # Write YAML
    import yaml
    with yaml_path.open('w') as f:
        yaml.dump(doc.model_dump(), f)

    # Transform
    transform_yaml_to_jsonl(yaml_path, jsonl_path)

    # Verify JSONL is valid
    with jsonl_path.open() as f:
        lines = f.readlines()

    assert len(lines) == 1  # One rule

    # Parse JSON
    obj = json.loads(lines[0])

    # Verify data correspondence
    assert obj["citation_id"] == f"LINE-{rule.rule_number}"
    assert obj["content"] == rule.content
    assert set(obj.get("expense_types", [])) == set(rule.expense_types or [])

def test_transformer_handles_optional_fields(tmp_path):
    """Test transformer with optional fields present/absent."""
    doc = ExtractedDocument(
        metadata={"schema_version": "1.0"},
        rules=[
            ExtractedRule(rule_number=1, content="Minimal"),
            ExtractedRule(
                rule_number=2,
                content="Full",
                expense_types=["meals"],
                confidence=0.95
            ),
        ]
    )

    yaml_path = tmp_path / "test.yml"
    jsonl_path = tmp_path / "test.jsonl"

    import yaml
    with yaml_path.open('w') as f:
        yaml.dump(doc.model_dump(), f)

    transform_yaml_to_jsonl(yaml_path, jsonl_path)

    with jsonl_path.open() as f:
        lines = f.readlines()

    assert len(lines) == 2

    # Both lines should be valid JSON
    obj1 = json.loads(lines[0])
    obj2 = json.loads(lines[1])

    # Optional fields should be handled correctly
    assert "expense_types" not in obj1 or obj1["expense_types"] == []
    assert obj2["expense_types"] == ["meals"]
```

### 80/20 Focus

✅ **Test This:**
- Structural robustness (optionality, collections, unicode)
- Valid JSON output for any valid input
- Data correspondence (input → output mapping)

❌ **Skip This:**
- Semantic meaning of generated data
- Performance testing
- Content validation (Hypothesis will generate nonsense text, which is fine)

### Dependencies

Ticket 1 (requires finalized Pydantic models)

---

## TICKET 4: End-to-End Pipeline for Single HTML Document

### Goal

Validate the full pipeline integration (HTML → YAML → JSONL → SQLite) for a single HTML file.

### Acceptance Criteria

1. ✅ Single HTML processes through full pipeline without errors
2. ✅ Valid SQLite database produced at specified path
3. ✅ Database contains records derived from source HTML
4. ✅ Searchable term from HTML found via FTS query

### Manual Testing Commands

```bash
# Test 1: Run full pipeline on single HTML file
# Step 1a: Extract HTML to YAML
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/t4002-1.html \
  output/single_e2e.yml \
  --verbose

# Step 1b: Transform YAML to JSONL
uv run extract-rules transform \
  output/single_e2e.yml \
  output/single_e2e.jsonl

# Step 1c: Build database from JSONL
uv run python scripts/cli.py build \
  --input-file output/single_e2e.jsonl \
  --output-db output/single_e2e.db

# Verify database was created
ls -lh output/single_e2e.db

# Test 2: Smoke test queries
sqlite3 output/single_e2e.db <<'SQL'
-- Check table structure
.schema chunks

-- Count chunks
SELECT COUNT(*) FROM chunks;

-- Show first 3 chunks
SELECT citation_id, substr(content, 1, 60) || '...' AS preview
FROM chunks
LIMIT 3;

-- Test FTS search for known term (adjust based on your HTML content)
SELECT citation_id, substr(content, 1, 80) AS preview
FROM chunks
WHERE content MATCH 'expense OR meal OR deduct'
LIMIT 5;
SQL

# Test 3: Validate database integrity
uv run python scripts/cli.py validate \
  --db-path output/single_e2e.db

# Test 4: Test search via Python API
cat > test_e2e_search.py <<'EOF'
"""Test search on single-file database."""
import qe_tax_rag as qe

# Initialize with our test database
qe.init(db_path="output/single_e2e.db")

# Search for a term likely in the document
results = qe.search("business expense", top_k=5)

print(f"Found {len(results)} results:\n")
for i, r in enumerate(results, 1):
    print(f"{i}. {r.citation_id}: {r.content[:80]}...")
    print(f"   Score: {r.score:.3f}\n")
EOF

uv run python test_e2e_search.py
```

### Automated Test Structure

```python
# tests/integration/test_single_file_e2e.py

import pytest
import sqlite3
from pathlib import Path
from src.qe_tax_rag.extraction.orchestrator import run_extraction_pipeline

@pytest.fixture
def golden_html():
    """Path to known-good HTML file."""
    return Path("tests/fixtures/extraction/t4002-sample.html")

@pytest.mark.integration
def test_single_html_to_database_e2e(golden_html, tmp_path):
    """Test full pipeline: HTML → YAML → JSONL → SQLite."""
    db_path = tmp_path / "test.db"

    # Run full pipeline
    run_extraction_pipeline(
        input_html=golden_html,
        output_db=db_path,
        keep_intermediate=False
    )

    # Verify database exists
    assert db_path.exists()
    assert db_path.stat().st_size > 0

    # Smoke tests
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Test 1: Database has chunks
    cursor.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cursor.fetchone()[0]
    assert chunk_count > 0, "Database should contain chunks"

    # Test 2: FTS search works
    cursor.execute("SELECT citation_id FROM chunks WHERE content MATCH 'expense' LIMIT 1")
    results = cursor.fetchall()
    assert len(results) > 0, "FTS search should return results"

    conn.close()
```

### 80/20 Focus

✅ **Test This:**
- Pipeline orchestration and integration
- Inter-component handoffs (file I/O)
- Basic database queryability

❌ **Skip This:**
- Re-testing component internals (trust Tickets 1-3)
- Exhaustive search quality validation
- Performance optimization

### Dependencies

Tickets 1, 2, 3

---

## TICKET 5: Full-Scale Database Provisioning from Multiple HTML Documents

### Goal

Validate production CLI handles batch processing with error resilience and proper aggregation.

### Acceptance Criteria

1. ✅ `pipeline-extraction` CLI runs successfully on directory with multiple HTMLs
2. ✅ Single aggregated SQLite database produced
3. ✅ Document count in DB matches valid input HTML count
4. ✅ Mix of valid/invalid HTMLs handled gracefully (logs errors, processes valid ones)
5. ✅ Final database queryable with data from all successfully processed documents

### Manual Testing Commands

```bash
# Test 1: Full pipeline on entire document set
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db output/full_pipeline.db \
  --verbose

# Expected output:
# ✅ Stage 1/3: Extracting and transforming rules
#    Extracted 247 rules to YAML
#    Transformed 247/247 rules to JSONL
# ✅ Stage 2/3: Building searchable database
#    Database built: output/full_pipeline.db
# ✅ Stage 3/3: Validating database
#    Validation passed

# Test 2: Inspect final database
sqlite3 output/full_pipeline.db <<'SQL'
-- Count total chunks
SELECT COUNT(*) FROM chunks;

-- Count unique documents (if document tracking exists)
SELECT COUNT(DISTINCT source_url) FROM chunks;

-- Sample data from database
SELECT citation_id, substr(content, 1, 60) || '...' AS preview
FROM chunks
ORDER BY RANDOM()
LIMIT 10;

-- Test FTS search
SELECT COUNT(*) FROM chunks WHERE content MATCH 'meal';
SELECT COUNT(*) FROM chunks WHERE content MATCH 'vehicle';
SELECT COUNT(*) FROM chunks WHERE content MATCH 'deduction';
SQL

# Test 3: Validate database
uv run python scripts/cli.py validate \
  --db-path output/full_pipeline.db

# Test 4: Test search quality
cat > test_full_search.py <<'EOF'
"""Test search quality on full database."""
import qe_tax_rag as qe

qe.init(db_path="output/full_pipeline.db")

# Test different query types
queries = [
    "meals and entertainment",
    "vehicle expenses",
    "home office deduction",
    "Can I deduct my car's gas?",
]

for query in queries:
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")

    results = qe.search(query, top_k=3)

    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r.citation_id} (Score: {r.score:.3f})")
        print(f"   {r.content[:120]}...")
EOF

uv run python test_full_search.py

# Test 5: Test with mixed valid/invalid HTML files
mkdir -p output/test_mixed
cp cra_documents/cra_t4002e_rev24_dump/t4002-1.html output/test_mixed/
cp cra_documents/cra_t4002e_rev24_dump/t4002-2.html output/test_mixed/
echo "<html><incomplete>" > output/test_mixed/invalid.html

uv run python scripts/cli.py pipeline-extraction \
  --input-dir output/test_mixed/ \
  --output-db output/test_mixed.db \
  --verbose

# Expected: 2 valid files processed, 1 error logged, database created

# Test 6: Keep intermediate files for inspection
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db output/full_with_intermediates.db \
  --intermediate-dir output/intermediates/ \
  --keep-intermediate

# Inspect intermediate files
ls -lh output/intermediates/
# Should see: rules.yml, chunks.jsonl, manual_review.yml (if any)
```

### Automated Test Structure

```python
# tests/e2e/test_full_pipeline.py

import pytest
import subprocess
from pathlib import Path

@pytest.fixture
def mixed_html_dir(tmp_path):
    """Create directory with valid and invalid HTML files."""
    html_dir = tmp_path / "html_input"
    html_dir.mkdir()

    # Copy valid HTML files
    valid_html_1 = html_dir / "valid1.html"
    valid_html_2 = html_dir / "valid2.html"
    # ... copy from fixtures ...

    # Create invalid HTML
    invalid_html = html_dir / "invalid.html"
    invalid_html.write_text("<html><incomplete>")

    return html_dir

@pytest.mark.e2e
def test_full_pipeline_cli(mixed_html_dir, tmp_path):
    """Test production CLI on multiple HTML files."""
    output_db = tmp_path / "final.db"

    # Run CLI command
    result = subprocess.run(
        [
            "uv", "run", "python", "scripts/cli.py", "pipeline-extraction",
            "--input-dir", str(mixed_html_dir),
            "--output-db", str(output_db),
        ],
        capture_output=True,
        text=True,
    )

    # Verify success (even with some invalid files)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Verify database created
    assert output_db.exists()

    # Verify database has content
    import sqlite3
    conn = sqlite3.connect(output_db)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM chunks")
    count = cursor.fetchone()[0]
    assert count > 0, "Database should have chunks from valid files"

    conn.close()

@pytest.mark.e2e
def test_pipeline_handles_partial_failures(mixed_html_dir, tmp_path):
    """Test that pipeline processes valid files even when some fail."""
    output_db = tmp_path / "final.db"

    result = subprocess.run(
        [
            "uv", "run", "python", "scripts/cli.py", "pipeline-extraction",
            "--input-dir", str(mixed_html_dir),
            "--output-db", str(output_db),
            "--verbose",
        ],
        capture_output=True,
        text=True,
    )

    # Check that errors were logged but didn't stop processing
    assert "invalid.html" in result.stderr or "error" in result.stdout.lower()

    # Database should still be created with valid data
    assert output_db.exists()
```

### 80/20 Focus

✅ **Test This:**
- CLI interface and argument parsing
- Batch processing multiple files
- Error resilience (continue on partial failures)
- Aggregated database correctness

❌ **Skip This:**
- Per-document content validation (trust Ticket 4)
- Performance optimization
- Edge cases in individual parsers

### Dependencies

Ticket 4

---

## Implementation Order

```
┌──────────────┐
│   TICKET 1   │  Foundation: HTML → YAML validation
│ (HTML→YAML)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   TICKET 3   │────▶│   TICKET 2   │  Can run in parallel
│ (YAML→JSONL) │     │(JSONL→SQLite)│
└──────┬───────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                ▼
       ┌──────────────┐
       │   TICKET 4   │  Integration: Single file E2E
       │  (E2E Single)│
       └──────┬───────┘
              ▼
       ┌──────────────┐
       │   TICKET 5   │  Production: Full batch processing
       │  (E2E Batch) │
       └──────────────┘
```

**Suggested Implementation Sequence:**

1. **TICKET 1** (1-2 days) - Foundation for YAML validation
2. **TICKET 3** (1-2 days) - Defines transformer contract (parallel with Ticket 2)
3. **TICKET 2** (1-2 days) - Database builder validation (parallel with Ticket 3)
4. **TICKET 4** (1 day) - Single-file integration test
5. **TICKET 5** (1 day) - Full production CLI test

**Total Estimated Time:** 5-7 days

---

## Key Principles Applied

### MECE (Mutually Exclusive, Collectively Exhaustive)

- Each ticket tests a distinct pipeline stage
- No overlap between tickets
- Together, they cover the entire pipeline

### 80/20 (Pareto Principle)

- Focus on structural/integration validation
- Skip exhaustive content validation
- Prioritize high-value tests that catch real bugs

### YAGNI (You Aren't Gonna Need It)

- No over-engineered test infrastructure
- Use pytest + hypothesis essentials
- Avoid premature optimization

### Progressive Validation

- Build confidence layer-by-layer
- Component tests before integration tests
- Integration tests before E2E tests
- Catch bugs early in smaller, focused tests

---

## Success Criteria

### Definition of Done (All Tickets)

1. ✅ All automated tests pass (`uv run pytest -v`)
2. ✅ Manual testing commands documented and verified
3. ✅ Test coverage >80% for core pipeline logic
4. ✅ CI/CD pipeline includes all tests
5. ✅ Documentation updated with testing approach

### Quality Gates

- **Unit Tests:** <100ms per test, >90% pass rate
- **Integration Tests:** <5s per test, >85% pass rate
- **E2E Tests:** <60s per test, 100% pass rate
- **Property Tests:** 100 examples per test, 0 failures

---

## Troubleshooting Guide

### Common Issues

**Issue:** YAML validation fails with `ValidationError`

```bash
# Debug: Inspect YAML structure
cat output/test_single.yml | head -50

# Fix: Check Pydantic model matches extraction output
uv run python -c "from src.qe_tax_rag.extraction.models import ExtractedDocument; print(ExtractedDocument.model_json_schema())"
```

**Issue:** JSONL transformation produces empty output

```bash
# Debug: Check YAML input
cat output/test_single.yml | grep -A5 "rules:"

# Debug: Run transformer with verbose logging
uv run extract-rules transform output/test_single.yml output/debug.jsonl --verbose
```

**Issue:** Database builder fails on malformed JSONL

```bash
# Debug: Validate each JSONL line
cat output/test_chunks.jsonl | while read line; do echo "$line" | python -m json.tool > /dev/null || echo "Invalid: $line"; done

# Fix: Ensure transformer produces valid JSON
uv run python validate_jsonl.py
```

**Issue:** FTS5 search returns no results

```bash
# Debug: Check if FTS index exists
sqlite3 output/test.db "SELECT * FROM sqlite_master WHERE type='table' AND name LIKE '%fts%';"

# Debug: Check chunk content
sqlite3 output/test.db "SELECT citation_id, substr(content, 1, 60) FROM chunks LIMIT 5;"

# Fix: Rebuild database with correct FTS configuration
```

---

## Next Steps

1. **Review this plan** with the team
2. **Create GitHub issues** for each ticket
3. **Set up test fixtures** (golden HTML, YAML, JSONL)
4. **Implement TICKET 1** first
5. **Run manual tests** after each ticket completion
6. **Update CI/CD** to include new tests
7. **Document findings** and edge cases discovered

---

**Happy Testing! 🎉**

For questions or issues, refer to `CLAUDE.md` or open a GitHub issue.
