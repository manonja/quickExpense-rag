# Testing Plan: Extraction Pipeline Validation (REVISED)

**Date:** 2025-10-21 **Status:** Ready for Implementation **Approach:** Test-Driven
Development with Progressive Validation **Architecture:** HTML → YAML → SQLite (Direct,
No JSONL Transformer)

______________________________________________________________________

## Critical Architecture Changes

### What Changed and Why

**Previous Architecture (INCORRECT)**:

```
HTML → YAML → JSONL → SQLite
       ↓       ↓        ↓
   Pydantic  Manual   Manual
             Transform Schema
```

**Revised Architecture (CORRECT)**:

```
HTML → YAML → SQLite
       ↓      ↓
   Pydantic  Pydantic
   (ExtractedContent → DatabaseChunk)
```

### Key Improvements

1. **Eliminated JSONL Transformer**: Direct YAML→SQLite loading reduces complexity and
   eliminates transformation bugs
1. **Unified Pydantic v2 Data Model**: Single canonical schema ensures type safety
   throughout pipeline
1. **Section-Level Granularity**: Each section = one searchable database chunk (not
   document-level)
1. **Normalized Metadata**: Extraction pipeline populates type-safe fields
   (`expense_types`, `provinces`), not inferred later
1. **Batch Embedding Generation**: Efficient bulk processing during YAML→SQLite loading

______________________________________________________________________

## Unified Pydantic v2 Data Models

### Core Architecture

```python
# src/qe_tax_rag/models.py

from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

# ==============================================================================
# Extraction Models (YAML Serialization/Deserialization)
# ==============================================================================

class Section(BaseModel):
    """
    Represents a single, coherent, searchable section of a document.
    This is the atomic unit for RAG retrieval (one section = one database chunk).
    """
    model_config = ConfigDict(extra='forbid')  # Reject unexpected fields

    section_id: str = Field(
        ...,
        description="Unique ID within document, e.g., '1.1' or 'part-a-item-3'"
    )
    title: str = Field(..., description="Section title")
    content_text: str = Field(..., description="Raw text content of the section")

    # Type-safe metadata for filtering (extracted by parsers, NOT inferred)
    expense_types: List[str] = Field(
        default_factory=list,
        description="Expense categories: ['meals', 'travel', 'vehicle', ...]"
    )
    income_types: List[str] = Field(
        default_factory=list,
        description="Income types: ['business', 'fishing', 'farming']"
    )
    provinces: List[str] = Field(
        default_factory=list,
        description="Applicable provinces: ['BC', 'ON', 'QC', ...]"
    )
    business_types: List[str] = Field(
        default_factory=list,
        description="Business types: ['sole_proprietorship', 'corporation', ...]"
    )

    # General metadata for non-filterable data (parser confidence, etc.)
    misc_metadata: Dict[str, any] = Field(default_factory=dict)


class ExtractedContent(BaseModel):
    """
    The canonical data model for content extracted from a single HTML source.
    This model is serialized to YAML and is the contract between extraction and loading.
    """
    source_document_id: str = Field(
        ...,
        description="Unique ID for source HTML (e.g., filename 't4002-1.html')"
    )
    document_title: str = Field(..., description="Main title of the document")
    publication_date: Optional[datetime] = Field(
        None,
        description="Publication date if available"
    )
    sections: List[Section] = Field(..., description="All extracted sections")
    disclaimer: str = Field(
        ...,
        description="Mandatory legal disclaimer (NOT TAX ADVICE warning)"
    )


# ==============================================================================
# Database Models (SQLite Storage - One Row Per Section)
# ==============================================================================

class DatabaseChunk(BaseModel):
    """
    Represents a single chunk (one Section) stored in the SQLite database.
    Each section becomes one searchable row with its own embedding and citation_id.
    """
    id: UUID = Field(
        default_factory=uuid4,
        description="Primary key for database record"
    )
    citation_id: str = Field(
        ...,
        description="Globally unique ID: '{source_document_id}-{section_id}'"
    )
    source_document_id: str = Field(..., description="Source document identifier")
    document_title: str = Field(..., description="Title of source document")

    # Section content
    section_id: str
    section_title: str
    section_content_text: str

    # Filterable metadata (stored as JSON strings in SQLite)
    expense_types_json: str  # Serialized list
    income_types_json: str
    provinces_json: str
    business_types_json: str

    # Generated during YAML→SQLite loading
    embedding: List[float] = Field(
        ...,
        description="384-dim BGE embedding (title + content concatenated)"
    )
    created_at_utc: datetime = Field(default_factory=datetime.utcnow)
```

### YAML Serialization Format

**Recommended Approach** (Pydantic v2 + PyYAML):

```python
import yaml
from qe_tax_rag.models import ExtractedContent

# Serialize ExtractedContent to YAML
data_dict = extracted_content.model_dump(mode='json')  # JSON-compatible types
yaml_str = yaml.dump(data_dict, sort_keys=False, indent=2)

with open("output.yaml", "w") as f:
    f.write(yaml_str)

# Deserialize YAML to ExtractedContent
with open("output.yaml", "r") as f:
    data = yaml.safe_load(f)

extracted_content = ExtractedContent(**data)  # Pydantic validation
```

**Why `model_dump(mode='json')`?**

- Converts `datetime` → ISO 8601 strings
- Converts `UUID` → string representation
- Ensures YAML is interoperable and human-readable

______________________________________________________________________

## Overview

This revised plan validates the extraction pipeline through 4 progressive tickets:

1. **TICKET 1:** HTML → YAML extraction (four-pronged validation)
1. **TICKET 2:** YAML → SQLite database construction (direct, no JSONL)
1. **TICKET 3:** End-to-end single HTML → complete database
1. **TICKET 4:** Full batch processing (multiple HTML files)

**Principles Applied:** MECE, 80/20, YAGNI, Progressive Validation

______________________________________________________________________

## TICKET 1: HTML → YAML (Four-Pronged Validation)

### Goal

Achieve **100% confidence** that the extraction pipeline (Classic Parser + LLM Parser +
Adjudicator) produces valid, schema-compliant YAML from HTML documents.

### Four-Pronged Testing Strategy

#### Prong 1: Classic Parser (BeautifulSoup) Standalone

**Goal**: Verify `html_str → ExtractedContent` works correctly for BeautifulSoup parser
in isolation.

**Test Module**: `tests/unit/extraction/test_classic_parser.py`

**Fixtures**:

- `valid_complete.html` - Golden case with all expected structures
- `complex_tables.html` - Stress test for table parsing
- `empty_sections.html` - Structure present but no content
- `no_title.html` - Missing metadata fields

**Test Function**:

```python
import pytest
from pathlib import Path
from src.qe_tax_rag.extraction.parsers.classic import ClassicParser
from src.qe_tax_rag.extraction.models import ExtractedContent

@pytest.mark.parametrize("html_fixture,expected_dict", [
    ("valid_complete.html", {...}),
    ("complex_tables.html", {...}),
])
def test_classic_parser_standalone(html_fixture, expected_dict):
    """Test Classic parser produces correct ExtractedContent."""
    html_path = Path(f"tests/fixtures/html/{html_fixture}")
    html_content = html_path.read_text()

    parser = ClassicParser()
    result = parser.parse(html_content)

    # Verify result is valid Pydantic model
    assert isinstance(result, ExtractedContent)

    # Serialize and compare structure
    result_dict = result.model_dump()
    assert result_dict["document_title"] == expected_dict["document_title"]
    assert len(result_dict["sections"]) == expected_dict["section_count"]
```

**Property-Based Test (Hypothesis)**:

```python
from hypothesis import given, strategies as st, settings

@given(html=st.text(min_size=1, max_size=1000))
@settings(max_examples=100)
def test_classic_parser_never_crashes(html):
    """Property: Classic parser never crashes on any HTML-like input."""
    parser = ClassicParser()
    try:
        result = parser.parse(html)
        # If parsing succeeds, result must be valid ExtractedContent
        if result is not None:
            assert isinstance(result, ExtractedContent)
    except ValueError:
        # Parser is allowed to raise ValueError for truly invalid input
        pass
```

#### Prong 2: LLM Parser (Gemini) Standalone

**Goal**: Verify `html_str → ExtractedContent` works for Gemini parser with mocked API
responses.

**Test Module**: `tests/unit/extraction/test_llm_parser.py`

**Fixtures**: Same HTML fixtures as Classic parser

**Mocking Strategy**:

```python
import pytest
from unittest.mock import MagicMock
from src.qe_tax_rag.extraction.parsers.llm import LLMParser

def test_llm_parser_standalone(mocker):
    """Test LLM parser with mocked Gemini API."""
    # Mock the Gemini API client
    mock_client = mocker.patch('src.qe_tax_rag.extraction.parsers.llm.gemini_client')

    # Define predictable mock response
    mock_response = {
        "document_title": "Test Document",
        "sections": [
            {"section_id": "1", "title": "Introduction", "content_text": "..."}
        ]
    }
    mock_client.generate_content.return_value.text = json.dumps(mock_response)

    parser = LLMParser()
    html_content = Path("tests/fixtures/html/valid_complete.html").read_text()
    result = parser.parse(html_content)

    # Verify API was called with correct prompt
    assert mock_client.generate_content.called

    # Verify result is valid ExtractedContent
    assert isinstance(result, ExtractedContent)
    assert result.document_title == "Test Document"
    assert len(result.sections) == 1
```

#### Prong 3: Adjudicator (4 Scenarios)

**Goal**: Test the adjudication logic under controlled conditions with known
disagreements.

**Test Module**: `tests/unit/extraction/test_adjudicator.py`

**Fixture Strategy**: Create Python modules with Pydantic objects defining known
scenarios.

**Fixture Structure**:

```
tests/fixtures/adjudicator/
├── scenario_agreement.py
├── scenario_classic_wrong.py
├── scenario_llm_wrong.py
└── scenario_both_wrong.py
```

**Example Fixture** (`scenario_classic_wrong.py`):

```python
from src.qe_tax_rag.extraction.models import ExtractedContent, Section

# Classic parser MISSED Section 2
classic_result = ExtractedContent(
    source_document_id="test-doc",
    document_title="Test Document",
    sections=[
        Section(section_id="1", title="Intro", content_text="Introduction text"),
        # Section 2 missing!
        Section(section_id="3", title="Conclusion", content_text="Conclusion text"),
    ],
    disclaimer="NOT TAX ADVICE"
)

# LLM parser got it RIGHT
llm_result = ExtractedContent(
    source_document_id="test-doc",
    document_title="Test Document",
    sections=[
        Section(section_id="1", title="Intro", content_text="Introduction text"),
        Section(section_id="2", title="Body", content_text="Body text"),  # Present!
        Section(section_id="3", title="Conclusion", content_text="Conclusion text"),
    ],
    disclaimer="NOT TAX ADVICE"
)

# Expected: Adjudicator should choose LLM's complete result
expected_result = llm_result
```

**Test Function**:

```python
import pytest
from src.qe_tax_rag.extraction.adjudicator import Adjudicator

def test_adjudicator_classic_wrong():
    """Test adjudicator when Classic parser misses a section."""
    from tests.fixtures.adjudicator import scenario_classic_wrong as scenario

    adjudicator = Adjudicator()
    result = adjudicator.merge(scenario.classic_result, scenario.llm_result)

    # Assert adjudicator chose the complete result (LLM)
    assert len(result.sections) == 3
    assert result.sections[1].section_id == "2"  # Missing section restored

    # Verify result matches expected
    assert result.model_dump() == scenario.expected_result.model_dump()
```

**Four Scenarios to Test**:

1. **Agreement**: Both parsers produce identical `ExtractedContent`

   - **Expected**: Adjudicator returns either result (they're the same)

1. **Classic Wrong**: Classic parser missing a section, LLM correct

   - **Expected**: Adjudicator chooses LLM's complete result

1. **LLM Wrong**: LLM hallucinates a fake section, Classic correct

   - **Expected**: Adjudicator filters out hallucinated section

1. **Both Wrong (Merge)**: Classic has Section A, LLM has Section B (both missing the
   other)

   - **Expected**: Adjudicator merges both, returning Sections A + B

#### Prong 4: Full E2E Orchestration

**Goal**: Test the complete HTML→YAML flow with all components integrated.

**Test Module**: `tests/integration/test_extraction_orchestrator.py`

**Fixtures**: 3-5 real CRA HTML documents from `cra_documents/cra_t4002e_rev24_dump/`

**Test Function**:

```python
import pytest
from pathlib import Path
from src.qe_tax_rag.extraction.orchestrator import run_extraction

@pytest.mark.integration
def test_full_extraction_orchestrator():
    """Test full HTML→YAML pipeline with real CRA document."""
    html_path = Path("tests/fixtures/html/cra_t4002_sample.html")
    output_yaml = Path("output/test_orchestrator.yml")

    # Run full extraction (Classic + LLM + Adjudicator)
    run_extraction(html_path, output_yaml)

    # Verify YAML was created
    assert output_yaml.exists()
    assert output_yaml.stat().st_size > 0

    # Deserialize and validate YAML
    import yaml
    with output_yaml.open() as f:
        data = yaml.safe_load(f)

    extracted_content = ExtractedContent(**data)  # Pydantic validation

    # Smoke tests
    assert extracted_content.source_document_id == "cra_t4002_sample.html"
    assert len(extracted_content.sections) > 0
    assert extracted_content.disclaimer.startswith("This information is NOT tax advice")
```

### Acceptance Criteria (TICKET 1)

1. ✅ **Prong 1**: Classic parser tested standalone with 8+ fixtures, property test
   passes 100 examples
1. ✅ **Prong 2**: LLM parser tested standalone with mocked API, 100% deterministic
1. ✅ **Prong 3**: Adjudicator tested with 4 scenarios (agreement, classic wrong, LLM
   wrong, both wrong)
1. ✅ **Prong 4**: Full E2E orchestrator tested with real CRA HTML, produces valid YAML
1. ✅ All YAML output validated against Pydantic `ExtractedContent` model
1. ✅ YAML serialization uses `model_dump(mode='json')` + `yaml.dump()`

### Manual Testing Commands (TICKET 1)

```bash
# ============================================================================
# Prong 1: Test Classic Parser Standalone
# ============================================================================

# Test with valid HTML
cat > output/test_classic.html <<'EOF'
<html>
<head><title>Test Document</title></head>
<body>
  <h1>Introduction</h1>
  <p>This is the introduction section.</p>
  <h2>Section 1.1</h2>
  <p>Meals and entertainment expenses are 50% deductible.</p>
</body>
</html>
EOF

uv run python -c "
from pathlib import Path
from src.qe_tax_rag.extraction.parsers.classic import ClassicParser
import yaml

html = Path('output/test_classic.html').read_text()
parser = ClassicParser()
result = parser.parse(html)

# Serialize to YAML
yaml_str = yaml.dump(result.model_dump(mode='json'), indent=2)
Path('output/classic_result.yml').write_text(yaml_str)
print('✅ Classic parser output saved to output/classic_result.yml')
"

# Verify YAML structure
head -30 output/classic_result.yml

# ============================================================================
# Prong 2: Test LLM Parser Standalone (with mocked API)
# ============================================================================

# Run pytest with mocked Gemini API
uv run pytest tests/unit/extraction/test_llm_parser.py -v

# ============================================================================
# Prong 3: Test Adjudicator
# ============================================================================

uv run pytest tests/unit/extraction/test_adjudicator.py -v

# ============================================================================
# Prong 4: Test Full E2E Orchestration
# ============================================================================

# Extract a single HTML file through full pipeline
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/t4002-1.html \
  output/test_e2e.yml \
  --verbose

# Verify YAML was created and is valid
ls -lh output/test_e2e.yml

# Validate YAML against Pydantic schema
cat > validate_yaml.py <<'EOF'
import yaml
from pathlib import Path
from src.qe_tax_rag.extraction.models import ExtractedContent

yaml_path = Path("output/test_e2e.yml")
with yaml_path.open() as f:
    data = yaml.safe_load(f)

# This will raise ValidationError if invalid
extracted = ExtractedContent(**data)

print(f"✅ YAML is valid!")
print(f"Document: {extracted.document_title}")
print(f"Sections: {len(extracted.sections)}")
print(f"First section: {extracted.sections[0].title}")
EOF

uv run python validate_yaml.py
```

### 80/20 Focus (TICKET 1)

✅ **Test This:**

- YAML structural integrity (Pydantic validation)
- Parser isolation (each component tested independently)
- Adjudication logic correctness (4 scenarios)
- E2E orchestration (full pipeline integration)

❌ **Skip This:**

- LLM accuracy auditing (trust Gemini's capabilities)
- Exhaustive HTML edge cases (focus on representative samples)
- Performance benchmarking (optimization is YAGNI)

### Dependencies

None (foundational ticket)

______________________________________________________________________

## TICKET 2: YAML → SQLite (Direct, No JSONL Transformer)

### Goal

Build a loader that directly deserializes YAML into `ExtractedContent` objects and
stores each `Section` as a searchable database chunk with embeddings.

### Acceptance Criteria

1. ✅ Deserialize YAML → `ExtractedContent` Pydantic objects
1. ✅ Each `Section` → one database row (`DatabaseChunk`)
1. ✅ `citation_id` generation: `f"{source_document_id}-{section_id}"`
1. ✅ Embedding generation: batch process, concatenate `title + "\n\n" + content_text`
1. ✅ FTS5 index functional (MATCH queries work)
1. ✅ Vector search functional (cosine similarity queries work)
1. ✅ Property-based testing: Loader handles any valid `ExtractedContent` object

### Architecture

**Data Flow**:

```
YAML File
   ↓ (yaml.safe_load)
Dictionary
   ↓ (Pydantic validation)
ExtractedContent
   ↓ (iterate sections)
List[Section]
   ↓ (for each section)
DatabaseChunk (with embedding)
   ↓ (bulk insert)
SQLite Database
```

### Embedding Generation Strategy

**What to Embed**: Concatenate section title and content

```python
embedding_text = f"{section.title}\n\n{section.content_text}"
```

**When to Embed**: Batch processing for efficiency

```python
# Collect all sections from all YAML files
all_sections = []
for yaml_file in yaml_files:
    extracted = ExtractedContent(**yaml.safe_load(yaml_file))
    all_sections.extend(extracted.sections)

# Generate embeddings in a single batch
texts = [f"{s.title}\n\n{s.content_text}" for s in all_sections]
embeddings = embedding_model.encode(texts, batch_size=32)

# Create DatabaseChunk objects with embeddings
chunks = [
    DatabaseChunk(
        citation_id=f"{extracted.source_document_id}-{section.section_id}",
        section_title=section.title,
        section_content_text=section.content_text,
        embedding=embedding.tolist(),
        ...
    )
    for section, embedding in zip(all_sections, embeddings)
]
```

### Manual Testing Commands (TICKET 2)

```bash
# ============================================================================
# Test 1: YAML → SQLite Direct Loading
# ============================================================================

# Prerequisite: Create a test YAML file with ExtractedContent structure
cat > output/test_sample.yml <<'EOF'
source_document_id: "test-doc-001"
document_title: "Canadian Tax Rules - Sample"
publication_date: "2024-12-01T00:00:00"
sections:
  - section_id: "1.1"
    title: "Meals and Entertainment"
    content_text: "Meals and entertainment expenses are 50% deductible for business purposes."
    expense_types: ["meals"]
    income_types: ["business"]
    provinces: []
    business_types: []
  - section_id: "1.2"
    title: "Vehicle Expenses"
    content_text: "Vehicle expenses include fuel, maintenance, and insurance."
    expense_types: ["vehicle"]
    income_types: ["business"]
    provinces: []
    business_types: []
disclaimer: "This information is NOT tax advice. Consult a qualified tax professional."
EOF

# Load YAML into SQLite database
uv run python scripts/cli.py load \
  --input-yaml output/test_sample.yml \
  --output-db output/test_direct.db

# Verify database was created
ls -lh output/test_direct.db

# ============================================================================
# Test 2: Inspect Database Schema
# ============================================================================

sqlite3 output/test_direct.db <<'SQL'
.schema

-- Check tables exist
.tables

-- Count chunks (should be 2 sections)
SELECT COUNT(*) FROM chunks;

-- Inspect first chunk
SELECT
  citation_id,
  section_title,
  substr(section_content_text, 1, 50) AS preview,
  expense_types_json
FROM chunks
LIMIT 1;
SQL

# ============================================================================
# Test 3: Verify FTS5 Search
# ============================================================================

sqlite3 output/test_direct.db <<'SQL'
-- Search for "meals"
SELECT citation_id, section_title
FROM chunks
WHERE section_content_text MATCH 'meals';
-- Expected: citation_id = "test-doc-001-1.1"

-- Search for "vehicle"
SELECT citation_id, section_title
FROM chunks
WHERE section_content_text MATCH 'vehicle';
-- Expected: citation_id = "test-doc-001-1.2"
SQL

# ============================================================================
# Test 4: Verify Vector Embeddings
# ============================================================================

sqlite3 output/test_direct.db <<'SQL'
-- Check embedding dimensions (should be 384 for BGE-small-en-v1.5)
SELECT citation_id, length(embedding) / 4 AS embedding_dim
FROM chunks
LIMIT 1;
-- Expected: embedding_dim = 384 (384 floats × 4 bytes each)
SQL

# ============================================================================
# Test 5: Property-Based Testing with Hypothesis
# ============================================================================

# Run property tests (generates varied ExtractedContent objects)
uv run pytest tests/unit/loader/test_yaml_to_sqlite_property.py -v
```

### Automated Test Structure (TICKET 2)

```python
# tests/unit/loader/test_yaml_to_sqlite.py

import pytest
import sqlite3
import yaml
from pathlib import Path
from src.qe_tax_rag.data.loader import load_yaml_to_database
from src.qe_tax_rag.extraction.models import ExtractedContent, Section

@pytest.fixture
def valid_yaml(tmp_path):
    """Create valid YAML fixture with ExtractedContent structure."""
    yaml_path = tmp_path / "test.yml"

    extracted = ExtractedContent(
        source_document_id="test-doc",
        document_title="Test Document",
        sections=[
            Section(
                section_id="1",
                title="Introduction",
                content_text="This is the introduction.",
                expense_types=["meals"]
            ),
            Section(
                section_id="2",
                title="Body",
                content_text="This is the body.",
                expense_types=["travel"]
            ),
        ],
        disclaimer="NOT TAX ADVICE"
    )

    yaml_data = yaml.dump(extracted.model_dump(mode='json'))
    yaml_path.write_text(yaml_data)

    return yaml_path


def test_yaml_to_database_creates_chunks(valid_yaml, tmp_path):
    """Test that YAML sections become database chunks."""
    db_path = tmp_path / "test.db"

    load_yaml_to_database(valid_yaml, db_path)

    # Verify database exists
    assert db_path.exists()

    # Check chunk count
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    count = cursor.fetchone()[0]

    assert count == 2  # Two sections
    conn.close()


def test_citation_id_generation(valid_yaml, tmp_path):
    """Test that citation_id is correctly formatted."""
    db_path = tmp_path / "test.db"

    load_yaml_to_database(valid_yaml, db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT citation_id FROM chunks ORDER BY citation_id")
    citation_ids = [row[0] for row in cursor.fetchall()]

    assert citation_ids == ["test-doc-1", "test-doc-2"]
    conn.close()


def test_fts5_index_functional(valid_yaml, tmp_path):
    """Test that FTS5 search works."""
    db_path = tmp_path / "test.db"

    load_yaml_to_database(valid_yaml, db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT citation_id FROM chunks WHERE section_content_text MATCH 'introduction'")
    results = cursor.fetchall()

    assert len(results) == 1
    assert results[0][0] == "test-doc-1"
    conn.close()
```

### Property-Based Test (Hypothesis)

```python
# tests/unit/loader/test_yaml_to_sqlite_property.py

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import builds, lists, text
from src.qe_tax_rag.extraction.models import ExtractedContent, Section
from src.qe_tax_rag.data.loader import load_yaml_to_database
import yaml

# Strategy for generating valid Section objects
section_strategy = builds(
    Section,
    section_id=st.text(min_size=1, max_size=10),
    title=st.text(min_size=1, max_size=100),
    content_text=st.text(min_size=1, max_size=500),
    expense_types=lists(st.sampled_from(["meals", "travel", "vehicle"]), max_size=3),
    income_types=lists(st.sampled_from(["business", "fishing"]), max_size=2),
)

# Strategy for generating valid ExtractedContent objects
extracted_content_strategy = builds(
    ExtractedContent,
    source_document_id=st.text(min_size=1, max_size=20),
    document_title=st.text(min_size=1, max_size=100),
    sections=lists(section_strategy, min_size=1, max_size=10),
    disclaimer=st.just("NOT TAX ADVICE"),
)


@given(extracted=extracted_content_strategy)
@settings(max_examples=50)
def test_loader_handles_any_valid_extracted_content(extracted, tmp_path):
    """
    Property: Loader correctly handles ANY valid ExtractedContent object.
    Tests structural robustness (empty lists, unicode, optional fields).
    """
    yaml_path = tmp_path / "test.yml"
    db_path = tmp_path / "test.db"

    # Serialize to YAML
    yaml_data = yaml.dump(extracted.model_dump(mode='json'))
    yaml_path.write_text(yaml_data)

    # Load into database (should never crash)
    load_yaml_to_database(yaml_path, db_path)

    # Verify database was created
    assert db_path.exists()

    # Verify chunk count matches section count
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    count = cursor.fetchone()[0]
    assert count == len(extracted.sections)
    conn.close()
```

### 80/20 Focus (TICKET 2)

✅ **Test This:**

- YAML deserialization correctness (Pydantic validation)
- Section-to-chunk mapping (1:1 correspondence)
- Citation ID generation (`{doc_id}-{section_id}`)
- FTS5 index functionality
- Embedding generation and storage
- Structural robustness (property-based testing)

❌ **Skip This:**

- Semantic quality of embeddings (trust BGE model)
- Vector search ranking quality (defer to TICKET 3 E2E)
- Performance optimization (YAGNI)

### Dependencies

TICKET 1 (requires `ExtractedContent` model and valid YAML fixtures)

______________________________________________________________________

## TICKET 3: Single HTML → Database (E2E Integration)

### Goal

Validate the full pipeline integration (HTML → YAML → SQLite) for a single HTML file.

### Acceptance Criteria

1. ✅ Single HTML file processed through full pipeline without errors
1. ✅ Valid SQLite database produced at specified path
1. ✅ Database contains chunks derived from source HTML (section count matches)
1. ✅ Searchable terms from HTML found via FTS5 query
1. ✅ Hybrid search (FTS5 + vector) returns relevant results

### Manual Testing Commands (TICKET 3)

```bash
# ============================================================================
# Test 1: Full Pipeline (HTML → YAML → SQLite)
# ============================================================================

# Step 1: Extract HTML to YAML (TICKET 1)
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/t4002-1.html \
  output/single_e2e.yml \
  --verbose

# Verify YAML created
ls -lh output/single_e2e.yml
head -50 output/single_e2e.yml

# Step 2: Load YAML to SQLite (TICKET 2)
uv run python scripts/cli.py load \
  --input-yaml output/single_e2e.yml \
  --output-db output/single_e2e.db

# Verify database created
ls -lh output/single_e2e.db

# ============================================================================
# Test 2: Validate Database Integrity
# ============================================================================

sqlite3 output/single_e2e.db <<'SQL'
-- Check table structure
.schema chunks

-- Count chunks
SELECT COUNT(*) FROM chunks;

-- Show first 3 chunks
SELECT
  citation_id,
  section_title,
  substr(section_content_text, 1, 60) AS preview
FROM chunks
LIMIT 3;

-- Test FTS search for known term
SELECT citation_id, section_title
FROM chunks
WHERE section_content_text MATCH 'expense OR meal OR deduct'
LIMIT 5;
SQL

# ============================================================================
# Test 3: Test Search via Python API
# ============================================================================

cat > test_e2e_search.py <<'EOF'
"""Test search on single-file database."""
import qe_tax_rag as qe

# Initialize with test database
qe.init(db_path="output/single_e2e.db")

# Test FTS search
print("=== FTS Keyword Search ===")
results = qe.search("business expense", top_k=3, search_mode="keyword")
for i, r in enumerate(results, 1):
    print(f"{i}. {r.citation_id}: {r.content[:80]}...")
    print(f"   Score: {r.score:.3f}\n")

# Test vector semantic search
print("\n=== Vector Semantic Search ===")
results = qe.search("business expense", top_k=3, search_mode="semantic")
for i, r in enumerate(results, 1):
    print(f"{i}. {r.citation_id}: {r.content[:80]}...")
    print(f"   Score: {r.score:.3f}\n")

# Test hybrid search (RRF)
print("\n=== Hybrid Search (RRF) ===")
results = qe.search("business expense", top_k=3, search_mode="hybrid")
for i, r in enumerate(results, 1):
    print(f"{i}. {r.citation_id}: {r.content[:80]}...")
    print(f"   Score: {r.score:.3f}\n")
EOF

uv run python test_e2e_search.py
```

### Automated Test Structure (TICKET 3)

```python
# tests/integration/test_single_file_e2e.py

import pytest
import sqlite3
from pathlib import Path
from src.qe_tax_rag.extraction.orchestrator import run_extraction
from src.qe_tax_rag.data.loader import load_yaml_to_database

@pytest.fixture
def golden_html():
    """Path to known-good real CRA HTML file."""
    return Path("tests/fixtures/html/cra_t4002_sample.html")


@pytest.mark.integration
def test_single_html_to_database_e2e(golden_html, tmp_path):
    """Test full pipeline: HTML → YAML → SQLite."""
    yaml_path = tmp_path / "test.yml"
    db_path = tmp_path / "test.db"

    # Stage 1: HTML → YAML
    run_extraction(golden_html, yaml_path)
    assert yaml_path.exists()
    assert yaml_path.stat().st_size > 0

    # Stage 2: YAML → SQLite
    load_yaml_to_database(yaml_path, db_path)
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
    cursor.execute("SELECT citation_id FROM chunks WHERE section_content_text MATCH 'expense' LIMIT 1")
    results = cursor.fetchall()
    assert len(results) > 0, "FTS search should return results"

    # Test 3: Embeddings exist and have correct dimension
    cursor.execute("SELECT length(embedding) / 4 AS dim FROM chunks LIMIT 1")
    dim = cursor.fetchone()[0]
    assert dim == 384, "Embeddings should be 384-dimensional (BGE-small-en-v1.5)"

    conn.close()
```

### 80/20 Focus (TICKET 3)

✅ **Test This:**

- Pipeline orchestration and integration
- Inter-component handoffs (file I/O)
- Basic database queryability (FTS5 + vector)
- Search API functionality

❌ **Skip This:**

- Re-testing component internals (trust TICKET 1 & 2)
- Exhaustive search quality validation
- Performance optimization

### Dependencies

TICKET 1 (HTML → YAML), TICKET 2 (YAML → SQLite)

______________________________________________________________________

## TICKET 4: Batch HTML → Database (Production CLI)

### Goal

Validate production CLI handles batch processing with error resilience and proper
aggregation.

### Acceptance Criteria

1. ✅ CLI processes directory with multiple HTML files
1. ✅ Single aggregated SQLite database produced
1. ✅ Chunk count in DB matches total sections across all valid HTML files
1. ✅ Mix of valid/invalid HTML handled gracefully (logs errors, continues processing)
1. ✅ Final database queryable with data from all successfully processed documents
1. ✅ Progress reporting and logging functional

### Manual Testing Commands (TICKET 4)

```bash
# ============================================================================
# Test 1: Full Batch Pipeline on Entire Document Set
# ============================================================================

uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db output/full_pipeline.db \
  --verbose

# Expected output:
# ✅ Stage 1/3: Extracting HTML to YAML
#    Processed 20/20 files (247 sections extracted)
# ✅ Stage 2/3: Loading YAML to SQLite
#    Generated 247 embeddings
#    Inserted 247 chunks
# ✅ Stage 3/3: Validating database
#    FTS5 index: OK
#    Vector index: OK
#    Schema validation: OK

# ============================================================================
# Test 2: Inspect Final Database
# ============================================================================

sqlite3 output/full_pipeline.db <<'SQL'
-- Count total chunks
SELECT COUNT(*) FROM chunks;

-- Count unique documents
SELECT COUNT(DISTINCT source_document_id) FROM chunks;

-- Sample random chunks
SELECT
  citation_id,
  section_title,
  substr(section_content_text, 1, 60) AS preview
FROM chunks
ORDER BY RANDOM()
LIMIT 10;

-- Test FTS search coverage
SELECT COUNT(*) FROM chunks WHERE section_content_text MATCH 'meal';
SELECT COUNT(*) FROM chunks WHERE section_content_text MATCH 'vehicle';
SELECT COUNT(*) FROM chunks WHERE section_content_text MATCH 'deduction';
SQL

# ============================================================================
# Test 3: Validate Database Integrity
# ============================================================================

uv run python scripts/cli.py validate --db-path output/full_pipeline.db

# Expected:
# ✅ Schema validation passed
# ✅ FTS5 index functional (247 indexed chunks)
# ✅ Vector embeddings present (247/247 chunks)
# ✅ Citation IDs unique (0 duplicates)
# ✅ No orphaned records

# ============================================================================
# Test 4: Test Search Quality
# ============================================================================

cat > test_full_search.py <<'EOF'
"""Test search quality on full production database."""
import qe_tax_rag as qe

qe.init(db_path="output/full_pipeline.db")

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
        print(f"   Title: {r.title}")
        print(f"   Content: {r.content[:120]}...")
        print(f"   Expense Types: {r.expense_types}")
EOF

uv run python test_full_search.py

# ============================================================================
# Test 5: Error Resilience (Mixed Valid/Invalid HTML)
# ============================================================================

mkdir -p output/test_mixed
cp cra_documents/cra_t4002e_rev24_dump/t4002-1.html output/test_mixed/
cp cra_documents/cra_t4002e_rev24_dump/t4002-2.html output/test_mixed/
echo "<html><incomplete>" > output/test_mixed/invalid.html

uv run python scripts/cli.py pipeline-extraction \
  --input-dir output/test_mixed/ \
  --output-db output/test_mixed.db \
  --verbose

# Expected:
# ⚠️  Warning: Failed to parse invalid.html (skipping)
# ✅ Successfully processed 2/3 files
# ✅ Database created with 2 documents

# Verify database has content despite error
sqlite3 output/test_mixed.db "SELECT COUNT(*) FROM chunks;"
# Expected: > 0 chunks

# ============================================================================
# Test 6: Keep Intermediate Files for Debugging
# ============================================================================

uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db output/full_with_intermediates.db \
  --intermediate-dir output/intermediates/ \
  --keep-intermediate

# Inspect intermediate files
ls -lh output/intermediates/
# Should see:
# - cra_rules.yml (aggregated YAML from all HTML)
# - manual_review.yml (edge cases flagged by adjudicator, if any)
```

### Automated Test Structure (TICKET 4)

```python
# tests/e2e/test_full_pipeline.py

import pytest
import subprocess
import sqlite3
from pathlib import Path

@pytest.fixture
def mixed_html_dir(tmp_path):
    """Create directory with valid and invalid HTML files."""
    html_dir = tmp_path / "html_input"
    html_dir.mkdir()

    # Copy 2 valid HTML files from fixtures
    valid_html_1 = html_dir / "valid1.html"
    valid_html_2 = html_dir / "valid2.html"
    Path("tests/fixtures/html/cra_t4002_sample.html").read_text()
    valid_html_1.write_text(Path("tests/fixtures/html/cra_t4002_sample.html").read_text())
    valid_html_2.write_text(Path("tests/fixtures/html/cra_t4002_sample.html").read_text())

    # Create 1 invalid HTML file
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

    # Verify database has content from valid files
    conn = sqlite3.connect(output_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    count = cursor.fetchone()[0]
    assert count > 0, "Database should have chunks from valid files"
    conn.close()


@pytest.mark.e2e
def test_pipeline_handles_partial_failures(mixed_html_dir, tmp_path):
    """Test that pipeline continues processing despite some failures."""
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
    assert "invalid.html" in result.stderr or "warning" in result.stdout.lower()

    # Database should still be created with valid data
    assert output_db.exists()

    # Verify chunk count > 0
    conn = sqlite3.connect(output_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    count = cursor.fetchone()[0]
    assert count > 0
    conn.close()
```

### 80/20 Focus (TICKET 4)

✅ **Test This:**

- CLI interface and argument parsing
- Batch processing multiple files
- Error resilience (continue on partial failures)
- Aggregated database correctness
- Progress reporting and logging

❌ **Skip This:**

- Per-document content validation (trust TICKET 3)
- Performance optimization (YAGNI for 247 files)
- Edge cases in individual parsers (covered in TICKET 1)

### Dependencies

TICKET 3 (E2E single file pipeline)

______________________________________________________________________

## Comprehensive Fixture Strategy

### Fixture Directory Structure

```
tests/fixtures/
├── html/                          # HTML fixtures for extraction testing
│   ├── synthetic/                 # Hand-crafted edge cases
│   │   ├── valid_complete.html    # Golden case (all structures present)
│   │   ├── malformed.html         # Unclosed tags, invalid nesting
│   │   ├── empty_sections.html    # Structure but no content
│   │   ├── unicode.html           # Accents, currency symbols, multi-byte
│   │   ├── complex_tables.html    # Parser stress test
│   │   ├── no_title.html          # Missing metadata fields
│   │   ├── classic_fails.html     # Forces Classic parser to fail
│   │   └── llm_fails.html         # Forces LLM parser to fail
│   └── real_world/                # Real CRA documents
│       ├── cra_t4002_sample.html  # Representative sample (small)
│       ├── cra_t4002_full.html    # Full document (large)
│       └── cra_t4003_sample.html  # Different document type
├── adjudicator/                   # Python fixtures with Pydantic objects
│   ├── scenario_agreement.py      # Both parsers agree
│   ├── scenario_classic_wrong.py  # Classic missing section
│   ├── scenario_llm_wrong.py      # LLM hallucinates section
│   └── scenario_both_wrong.py     # Both have different errors
└── yaml/                          # YAML fixtures for loader testing
    ├── valid_complete.yml         # Golden ExtractedContent
    ├── empty_sections.yml         # No sections (edge case)
    ├── unicode.yml                # Unicode in content
    └── minimal.yml                # Minimal required fields only
```

### Coverage Matrix

| Fixture                     | Prong 1 (Classic) | Prong 2 (LLM) | Prong 3 (Adj) | Prong 4 (E2E) | TICKET 2 | TICKET 3 | TICKET 4 |
| --------------------------- | ----------------- | ------------- | ------------- | ------------- | -------- | -------- | -------- |
| `valid_complete.html`       | ✅                | ✅            | ✅            | ✅            | -        | ✅       | -        |
| `malformed.html`            | ✅                | ✅            | -             | -             | -        | -        | -        |
| `empty_sections.html`       | ✅                | ✅            | -             | -             | -        | -        | -        |
| `unicode.html`              | ✅                | ✅            | -             | -             | -        | -        | -        |
| `complex_tables.html`       | ✅                | -             | -             | -             | -        | -        | -        |
| `classic_fails.html`        | ✅                | ✅            | ✅            | -             | -        | -        | -        |
| `llm_fails.html`            | ✅                | ✅            | ✅            | -             | -        | -        | -        |
| `cra_t4002_sample.html`     | -                 | -             | -             | ✅            | -        | ✅       | -        |
| `cra_t4002_full.html`       | -                 | -             | -             | ✅            | -        | -        | ✅       |
| `scenario_agreement.py`     | -                 | -             | ✅            | -             | -        | -        | -        |
| `scenario_classic_wrong.py` | -                 | -             | ✅            | -             | -        | -        | -        |
| `scenario_llm_wrong.py`     | -                 | -             | ✅            | -             | -        | -        | -        |
| `scenario_both_wrong.py`    | -                 | -             | ✅            | -             | -        | -        | -        |
| `valid_complete.yml`        | -                 | -             | -             | -             | ✅       | -        | -        |
| `empty_sections.yml`        | -                 | -             | -             | -             | ✅       | -        | -        |
| `unicode.yml`               | -                 | -             | -             | -             | ✅       | -        | -        |

______________________________________________________________________

## Implementation Order

```
┌────────────────────────────────────────────┐
│           TICKET 1                         │
│      HTML → YAML (4 Prongs)                │
│  1a: Classic Parser                        │
│  1b: LLM Parser (mocked)                   │
│  1c: Adjudicator (4 scenarios)             │
│  1d: Full E2E Orchestration                │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│           TICKET 2                         │
│      YAML → SQLite (Direct)                │
│  - Pydantic deserialization                │
│  - Section → DatabaseChunk mapping         │
│  - Batch embedding generation              │
│  - FTS5 + vector index creation            │
│  - Property-based testing (Hypothesis)     │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│           TICKET 3                         │
│    Single HTML → Database (E2E)            │
│  - Chain TICKET 1 + TICKET 2               │
│  - Integration smoke tests                 │
│  - Search API validation                   │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│           TICKET 4                         │
│    Batch HTML → Database (Production)      │
│  - Directory processing                    │
│  - Error resilience                        │
│  - Progress reporting                      │
│  - CLI interface                           │
└────────────────────────────────────────────┘
```

**Suggested Implementation Sequence:**

1. **TICKET 1** (3-4 days) - Four-pronged extraction validation

   - Day 1: Prong 1 (Classic parser) + fixtures
   - Day 2: Prong 2 (LLM parser with mocks) + Prong 3 (Adjudicator)
   - Day 3: Prong 4 (E2E orchestration) + property tests
   - Day 4: Integration and debugging

1. **TICKET 2** (2-3 days) - Direct YAML→SQLite loader

   - Day 1: Pydantic deserialization + section mapping
   - Day 2: Embedding generation + database insertion
   - Day 3: Property-based testing + debugging

1. **TICKET 3** (1-2 days) - Single file E2E integration

   - Day 1: Integration test + search API validation
   - Day 2: Edge case testing + documentation

1. **TICKET 4** (1-2 days) - Production batch CLI

   - Day 1: Batch processing + error handling
   - Day 2: Progress reporting + E2E testing

**Total Estimated Time:** 7-11 days

______________________________________________________________________

## Key Principles Applied

### MECE (Mutually Exclusive, Collectively Exhaustive)

- Each ticket tests a distinct pipeline stage
- No overlap between tickets
- Together, they cover the entire pipeline
- Four prongs in TICKET 1 are mutually exclusive (Classic vs. LLM vs. Adjudicator vs.
  E2E)

### 80/20 (Pareto Principle)

- Focus on structural/integration validation (high value)
- Skip exhaustive content validation (low ROI)
- Prioritize tests that catch real bugs (parser crashes, schema violations)
- Use property-based testing for robustness, not semantic correctness

### YAGNI (You Aren't Gonna Need It)

- No over-engineered test infrastructure
- Use pytest + hypothesis essentials (no custom test frameworks)
- Avoid premature optimization (performance testing deferred)
- Simple fixtures (synthetic + real-world, no complex test data generators)

### Progressive Validation

- Build confidence layer-by-layer (component → integration → E2E)
- Component tests (TICKET 1-2) catch bugs in isolation
- Integration tests (TICKET 3) validate inter-component handoffs
- E2E tests (TICKET 4) validate production workflow
- Catch bugs early in smaller, focused tests

______________________________________________________________________

## Success Criteria

### Definition of Done (All Tickets)

1. ✅ All automated tests pass (`uv run pytest -v`)
1. ✅ Manual testing commands documented and verified
1. ✅ Test coverage >80% for core pipeline logic
1. ✅ CI/CD pipeline includes all tests
1. ✅ Documentation updated with new architecture

### Quality Gates

- **Unit Tests (TICKET 1-2):** \<100ms per test, >90% pass rate
- **Integration Tests (TICKET 3):** \<5s per test, >85% pass rate
- **E2E Tests (TICKET 4):** \<60s per test, 100% pass rate
- **Property Tests (Hypothesis):** 50-100 examples per test, 0 failures

______________________________________________________________________

## Troubleshooting Guide

### Common Issues

**Issue:** Pydantic validation fails on YAML deserialization

```bash
# Debug: Inspect YAML structure
cat output/test.yml | head -50

# Debug: Check Pydantic schema
uv run python -c "
from src.qe_tax_rag.extraction.models import ExtractedContent
import json
print(json.dumps(ExtractedContent.model_json_schema(), indent=2))
"

# Fix: Ensure YAML uses model_dump(mode='json')
```

**Issue:** Embedding generation fails (dimension mismatch)

```bash
# Debug: Check embedding model
uv run python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-small-en-v1.5')
test_embedding = model.encode('test')
print(f'Embedding dimension: {len(test_embedding)}')
"
# Expected: 384

# Fix: Verify model name matches BGE-small-en-v1.5
```

**Issue:** FTS5 search returns no results

```bash
# Debug: Check if FTS index exists
sqlite3 output/test.db "SELECT * FROM sqlite_master WHERE type='table' AND name LIKE '%fts%';"

# Debug: Check chunk content
sqlite3 output/test.db "SELECT citation_id, substr(section_content_text, 1, 60) FROM chunks LIMIT 5;"

# Fix: Rebuild database with correct FTS configuration
```

**Issue:** Adjudicator produces unexpected result

```bash
# Debug: Enable verbose logging
uv run extract-rules extract input.html output.yml --verbose --debug

# Debug: Inspect adjudicator fixture
cat tests/fixtures/adjudicator/scenario_classic_wrong.py

# Fix: Verify expected_result matches adjudicator logic
```

______________________________________________________________________

## Next Steps

1. **Review this revised plan** with the team
1. **Create GitHub issues** for each ticket (4 issues)
1. **Set up test fixtures** (8 synthetic HTML + 3 real-world + 4 adjudicator scenarios)
1. **Create Pydantic models** in `src/qe_tax_rag/models.py`
1. **Implement TICKET 1 (Prong 1)** first (Classic parser tests)
1. **Run manual tests** after each prong/ticket completion
1. **Update CI/CD** to include all new tests
1. **Document findings** and edge cases discovered

______________________________________________________________________

**Happy Testing! 🎉**

For questions or issues, refer to `CLAUDE.md` or consult with the team.
