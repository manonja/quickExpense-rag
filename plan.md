# Production-Ready Implementation Plan: CRA RAG Library

## 🚀 Quick Start: What's Changed

This plan has been **optimized for 80/20 productivity** - delivering maximum value with
minimum time:

### Key Optimizations

1. ⭐ **NEW Ticket 1.5**: CI/CD quality gates moved to Day 1 (was Ticket 12)
1. ⭐ **NEW Ticket 4.5**: Fixture database enables parallel development
1. ⚡ **Parallel Workstreams**: Runtime API and data pipeline work simultaneously
1. 🎯 **40% faster**: 6-7 days total (was 10-12 days)
1. 🎉 **60% faster to demo**: Working search in 2-3 days (was 5-7 days)

### What You Get

- **Day 1**: Project setup + CI quality gates enforcing code standards
- **Day 2-3**: Working `qer.search()` function (Workstream A complete)
- **Day 4-5**: Production data pipeline (Workstream B complete)
- **Day 6-7**: E2E testing, packaging, release automation

### For Teams

- **Solo dev**: Follow Workstream A → B sequentially for fastest feedback
- **2-person team**: One on runtime (A), one on pipeline (B) - true parallelism
- **3+ team**: Split Phase 2 definitions, then allocate to workstreams

______________________________________________________________________

## Architecture Summary

- **Structure**: Arkalos pattern (app/ runtime, scripts/ internal tools)
- **Search**: SQLite + FTS5 (keywords) + sqlite-vec (semantic) + RRF fusion
- **Distribution**: Code via PyPI, data via GitHub Releases
- **Legal**: Mandatory disclaimers on all APIs
- **Tech Stack**: Python 3.11+, uv, Pydantic v2, sentence-transformers, sqlite-vec,
  Gemini Flash

## ⚡ Parallel Development Strategy

**Critical Path Optimization**: This plan enables two independent workstreams that work
in parallel:

- **Workstream A (Runtime Library)**: Delivers a working `search()` API in 2-3 days
  using fixture data
- **Workstream B (Indexing Pipeline)**: Builds production data ingestion (can start
  after core definitions)

**Key Enabler**: **Ticket 4.5** creates a fixture database that unblocks the runtime
team to work independently of the data pipeline team. Quality gates (CI/CD linting,
formatting, type checking) are established on Day 1 via **Ticket 1.5**.

**Result**: Working demo in 2-3 days (vs 5-7 days), parallel team productivity, faster
feedback loops.

______________________________________________________________________

## ✨ Key Architecture Decisions

### Parsing Strategy: Gemini Flash over Custom HTML/PDF Parser

**Decision**: Use Gemini Flash 2.0 for document parsing instead of automated web
scraping + brittle regex/BeautifulSoup parsing.

**Rationale**:

1. **Less Brittle**: LLM understands semantic structure vs regex patterns that break
   with website changes
1. **No Scraping Maintenance**: Maintainer manually downloads CRA docs - eliminates web
   scraping breakage
1. **Better Semantics**: LLM extracts citations, metadata, and chunks with understanding
   of legal document structure
1. **Cost-Effective**: ~$1.59 for all 50 documents (negligible compared to maintenance
   cost)
1. **Validated Output**: Multi-layer validation (Pydantic + regex + content grounding)
   catches hallucinations
1. **Flexible**: Works with HTML or PDF without format-specific parsing code

**Workflow**:

1. Maintainer manually downloads CRA HTML/PDF → `data/raw/`
1. Pre-processor extracts clean text → `data/preprocessed/`
1. Gemini Flash parses text → structured JSON chunks → `data/processed/chunks.jsonl`
1. Index builder creates embeddings → SQLite database
1. Validation pipeline ensures quality

**Trade-offs**:

- ✅ Eliminates parser brittleness (biggest maintenance pain)
- ✅ Better semantic understanding
- ✅ Simpler codebase (prompt engineering vs complex parsing logic)
- ⚠️ Requires Gemini API key during indexing (not runtime)
- ⚠️ Potential for LLM hallucinations (mitigated by validation)
- ⚠️ Small cost per rebuild (~$1.59 for 50 docs)

______________________________________________________________________

## TICKET 1: Project Foundation & Build System

**Scope**: Initialize project structure, dependency management, linting, type checking,
pre-commit hooks

### Acceptance Criteria

- [ ] Project initialized with `uv init --lib quickexpense-rag`
- [ ] `pyproject.toml` configured:
  ```toml
  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [project]
  name = "quickexpense-rag"
  version = "0.1.0"
  requires-python = ">=3.11"
  dependencies = [
      "pydantic>=2.0",
      "pydantic-settings>=2.0",
      "sentence-transformers>=2.2",
      "sqlite-vec>=0.1",
      "httpx>=0.25",
      "tqdm>=4.66",
      "google-generativeai>=0.3",
      "pdfplumber>=0.10",
  ]

  [project.optional-dependencies]
  dev = [
      "pytest>=7.4",
      "pytest-cov>=4.1",
      "pytest-asyncio>=0.21",
      "ruff>=0.1",
      "mypy>=1.7",
      "pre-commit>=3.5",
  ]
  ```
- [ ] Directory structure created:
  ```
  app/
    rag/
      search/
      data/
      embeddings/
    api.py
    exceptions.py
  scripts/
  config/
  data/
  tests/
    unit/
    integration/
    fixtures/
  docs/
  ```
- [ ] `ruff.toml` configured:
  ```toml
  line-length = 100
  target-version = "py311"
  select = ["E", "F", "I", "N", "UP", "RUF", "B", "SIM", "C90"]
  ignore = ["E501"]  # Let formatter handle line length

  [per-file-ignores]
  "tests/*" = ["S101"]  # Allow assert in tests
  ```
- [ ] `mypy.ini` configured:
  ```ini
  [mypy]
  python_version = 3.11
  strict = True
  warn_return_any = True
  warn_unused_configs = True
  disallow_untyped_defs = True
  ```
- [ ] `.pre-commit-config.yaml` with hooks:
  - ruff-format (code formatting)
  - ruff (linting)
  - mypy (type checking)
- [ ] Verification commands pass:
  ```bash
  uv sync
  uv run pre-commit run --all-files
  uv run mypy app/
  ```

**Dependency**: None **Enables**: All other tickets

______________________________________________________________________

## TICKET 1.5: CI/CD Quality Gates ⭐ NEW

**Scope**: Establish automated quality gates on Day 1 (linting, formatting, type
checking, testing)

### Acceptance Criteria

- [ ] `.github/workflows/ci.yml` created with core quality jobs:
  ```yaml
  name: CI
  on: [push, pull_request]
  jobs:
    lint:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - run: uvx ruff check
        - run: uvx ruff format --check

    typecheck:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - run: uv run mypy app/

    test:
      runs-on: ${{ matrix.os }}
      strategy:
        matrix:
          os: [ubuntu-latest, windows-latest, macos-latest]
          python: ["3.11", "3.12", "3.13"]
      steps:
        - uses: actions/checkout@v4
        - run: uv sync
        - run: uv run pytest tests/ -v -m "not slow"
  ```
- [ ] GitHub branch protection rules configured (optional but recommended):
  - Require CI passing before merge
  - Require 1 approval for PRs
- [ ] Local pre-commit hooks verified working:
  ```bash
  uv run pre-commit run --all-files
  ```
- [ ] All jobs pass on initial test PR
- [ ] Documentation: Add "Development" section to README with:
  - How to run tests locally
  - How to run linting/formatting
  - How to bypass hooks if needed (--no-verify)

**Dependency**: TICKET 1 **Enables**: Quality gates for all subsequent development
**Rationale**: Moving CI setup to Day 1 prevents tech debt accumulation and ensures code
quality from the start. The release automation workflows (build-database.yml,
release.yml) remain in TICKET 12 as they're only needed for publishing artifacts.

______________________________________________________________________

## TICKET 2: Database Schema & Versioning

**Scope**: Define canonical database schema, versioning strategy, migration plan

### Acceptance Criteria

- [ ] `app/rag/data/schema.py` defines complete schema:
  ```python
  SCHEMA_VERSION = "1.0"

  CREATE_TABLES_SQL = """
  -- Metadata table for versioning
  CREATE TABLE IF NOT EXISTS metadata (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
  );

  -- Main content table
  CREATE TABLE IF NOT EXISTS rules (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      content TEXT NOT NULL,
      citation_id TEXT UNIQUE NOT NULL,
      source_url TEXT NOT NULL,
      source_hash TEXT NOT NULL,  -- SHA256 of source document
      province TEXT,
      business_type TEXT,
      expense_type TEXT,
      metadata_json TEXT,
      retrieved_at TEXT NOT NULL,  -- ISO 8601
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  -- FTS5 virtual table for keyword search
  CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
      content,
      content='rules',
      content_rowid='id',
      tokenize='porter unicode61'
  );

  -- Triggers to keep FTS in sync
  CREATE TRIGGER IF NOT EXISTS rules_ai AFTER INSERT ON rules BEGIN
      INSERT INTO rules_fts(rowid, content) VALUES (new.id, new.content);
  END;

  CREATE TRIGGER IF NOT EXISTS rules_ad AFTER DELETE ON rules BEGIN
      DELETE FROM rules_fts WHERE rowid = old.id;
  END;

  CREATE TRIGGER IF NOT EXISTS rules_au AFTER UPDATE ON rules BEGIN
      UPDATE rules_fts SET content = new.content WHERE rowid = new.id;
  END;

  -- Vector table for semantic search
  CREATE VIRTUAL TABLE IF NOT EXISTS rules_vec USING vec0(
      id INTEGER PRIMARY KEY,
      embedding FLOAT[384]
  );

  -- Indexes for metadata filtering
  CREATE INDEX IF NOT EXISTS idx_province ON rules(province);
  CREATE INDEX IF NOT EXISTS idx_business_type ON rules(business_type);
  CREATE INDEX IF NOT EXISTS idx_expense_type ON rules(expense_type);
  CREATE INDEX IF NOT EXISTS idx_citation ON rules(citation_id);
  """
  ```
- [ ] Versioning strategy documented:
  - Schema version stored in `metadata` table:
    `INSERT INTO metadata VALUES ('schema_version', '1.0')`
  - Data version stored in `metadata` table:
    `INSERT INTO metadata VALUES ('data_version', '2024.12')`
  - Library checks compatibility on init:
    `assert db_version.startswith(LIB_VERSION_MAJOR)`
- [ ] `app/rag/data/migrations.py` created (empty for v1, future-proofing)
- [ ] Unit test verifies:
  - Schema SQL executes without errors
  - All tables and indexes created
  - Metadata table populated correctly
  - Foreign key constraints enforced

**Dependency**: TICKET 1 **Enables**: TICKET 5, TICKET 9A-C (indexing pipeline)

______________________________________________________________________

## TICKET 3: Configuration & Exception Hierarchy

**Scope**: User-configurable settings, custom exceptions, logging setup

### Acceptance Criteria

- [ ] `config/settings.py` using pydantic-settings:
  ```python
  from pydantic_settings import BaseSettings, SettingsConfigDict

  class Settings(BaseSettings):
      model_config = SettingsConfigDict(
          env_file=".env",
          env_prefix="QUICKEXPENSE_",
          case_sensitive=False
      )

      # Data settings
      cache_dir: Path = Path.home() / ".cache" / "quickexpense_rag"
      db_download_url: str = "https://github.com/.../releases/download/..."
      db_filename: str = "cra_rules.db"

      # Embedding settings
      embedding_model: str = "BAAI/bge-small-en-v1.5"
      embedding_device: str = "cpu"
      embedding_batch_size: int = 32

      # Search settings
      default_top_k: int = 5
      rrf_k: int = 60  # RRF constant

      # Network settings
      request_timeout: int = 30
      download_retries: int = 3

      # Logging
      log_level: str = "INFO"

      # Gemini settings (for indexing pipeline only, not runtime)
      gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
      gemini_model: str = "gemini-2.5-flash"
      gemini_temperature: float = 0.0

  settings = Settings()
  ```
- [ ] `app/exceptions.py` with custom exception hierarchy:
  ```python
  class QuickExpenseError(Exception):
      """Base exception for all library errors."""

  class DatabaseNotInitializedError(QuickExpenseError):
      """Database not found. Call init() first."""

  class DataVersionMismatchError(QuickExpenseError):
      """Database version incompatible with library version."""

  class ChecksumMismatchError(QuickExpenseError):
      """Downloaded database failed integrity check."""

  class NetworkError(QuickExpenseError):
      """Network operation failed."""

  class ParsingError(QuickExpenseError):
      """Document parsing failed."""

  class EmbeddingError(QuickExpenseError):
      """Embedding generation failed."""
  ```
- [ ] Logging configured in `app/__init__.py`:
  ```python
  import logging
  logging.getLogger("quickexpense_rag").addHandler(logging.NullHandler())
  ```
- [ ] `.env.example` created with all settings documented
- [ ] Unit tests verify:
  - Settings load from environment variables
  - Settings load from .env file
  - Default values applied correctly
  - All exceptions are catchable and have clear messages

**Dependency**: TICKET 1 **Enables**: All subsequent tickets (all use config and
exceptions)

______________________________________________________________________

## TICKET 4: Pydantic Models with Legal Safeguards

**Scope**: Type-safe data models for all API boundaries

### Acceptance Criteria

- [ ] `app/rag/search/enums.py`:
  ```python
  from enum import Enum

  class Province(str, Enum):
      BC = "BC"
      AB = "AB"
      ON = "ON"
      QC = "QC"
      # ... all provinces

  class BusinessType(str, Enum):
      SOLE_PROPRIETORSHIP = "sole_proprietorship"
      CORPORATION = "corporation"
      PARTNERSHIP = "partnership"

  class ExpenseType(str, Enum):
      MEALS = "meals"
      TRAVEL = "travel"
      VEHICLE = "vehicle"
      HOME_OFFICE = "home_office"
      # ... all expense types
  ```
- [ ] `app/rag/search/models.py`:
  ```python
  from pydantic import BaseModel, Field, computed_field, ConfigDict
  from datetime import datetime

  class ExpenseQuery(BaseModel):
      model_config = ConfigDict(frozen=True, extra='forbid')

      query: str = Field(..., min_length=3, description="Search query")
      province: Province | None = None
      business_type: BusinessType | None = None
      expense_type: ExpenseType | None = None
      top_k: int = Field(5, ge=1, le=50)

  class SearchResult(BaseModel):
      model_config = ConfigDict(frozen=True)

      content: str
      citation_id: str
      source_url: str
      score: float = Field(..., ge=0.0, le=1.0)
      province: Province | None
      business_type: BusinessType | None
      expense_type: ExpenseType | None
      retrieved_at: datetime

      @computed_field
      @property
      def disclaimer(self) -> str:
          return (
              "⚠️ INFORMATIONAL ONLY - NOT TAX ADVICE\n"
              "This information is for educational purposes only and does not "
              "constitute tax advice. CRA rules are complex and change frequently. "
              "Always consult a qualified tax professional or accountant. "
              "The data may be incomplete, outdated, or incorrectly interpreted."
          )

  class IndexManifest(BaseModel):
      version: str  # YYYY.MM format
      schema_version: str
      source_files: list[dict[str, str]]  # [{path, hash}]
      embedding_model: str
      chunk_count: int
      created_at: datetime
      sha256: str  # Hash of the database file
  ```
- [ ] Unit tests verify:
  - Invalid enum values raise ValidationError
  - Query with empty string raises ValidationError
  - top_k out of range raises ValidationError
  - SearchResult JSON includes disclaimer
  - All models are immutable (frozen=True)
  - `mypy` passes on all model files

**Dependency**: TICKET 1, TICKET 3 **Enables**: TICKET 5, TICKET 6, TICKET 9A-C

______________________________________________________________________

## TICKET 4.5: Fixture Database for Parallel Development ⭐ NEW

**Scope**: Create a small, version-controlled SQLite database with hand-crafted test
data to unblock runtime library development

### Acceptance Criteria

- [ ] `tests/fixtures/test_database.db` created with schema from TICKET 2:
  - 10-20 hand-crafted rows representing diverse CRA rules
  - Pre-computed embeddings (384-dim vectors) for each row
  - Coverage across provinces (BC, AB, ON, QC)
  - Coverage across business types (sole_prop, corp, partnership)
  - Coverage across expense types (meals, travel, vehicle, home_office)
- [ ] `tests/fixtures/create_fixture_db.py` script:
  ```python
  def create_fixture_database(output_path: Path):
      """Create test database with hand-crafted data."""
      # 1. Initialize schema
      # 2. Insert 10-20 realistic test rows
      # 3. Generate embeddings using BGEEncoder
      # 4. Populate all three tables (rules, rules_fts, rules_vec)
      # 5. Insert metadata (schema_version, data_version)
  ```
- [ ] Sample test data examples:
  ```python
  {
      "content": "Meals and entertainment expenses for business travel are 50% deductible...",
      "citation_id": "S3-F2-C1-p1.25",
      "source_url": "https://canada.ca/...",
      "province": "BC",
      "business_type": "sole_proprietorship",
      "expense_type": "meals"
  }
  ```
- [ ] Database committed to git (tests/fixtures/test_database.db)
- [ ] Unit test verifies fixture DB:
  - Has expected row count (10-20)
  - All embeddings present and correct dimensions
  - FTS5 index searchable
  - Vector search works
  - Metadata table populated
- [ ] Documentation in `tests/fixtures/README.md`:
  - Purpose: Enable runtime library development before indexing pipeline is complete
  - How to regenerate if schema changes
  - Known limitations (small dataset, hand-crafted)

**Dependency**: TICKET 2 (Schema), TICKET 3 (Config) **Enables**: TICKET 5, 6, 7, 8
(entire runtime library can now be developed and tested independently) **Rationale**:
This is the critical enabler for parallel development. The fixture database allows the
runtime team (Workstream A) to build and test the search API while the indexing team
(Workstream B) works on the production data pipeline. Both teams target the same schema
contract but work independently.

______________________________________________________________________

## TICKET 4.6: Database Schema for Many-to-Many Expense Types ⭐ NEW

**Scope**: Extend database schema to support multiple expense types per rule

### Acceptance Criteria

- [ ] `src/quickexpense_rag/data/schema.py` - **CRITICAL: Remove old column first to
  avoid duplicate data**:
  - **DELETE line 38**: `expense_type TEXT,` from `rules` table definition
  - **DELETE line 77**:
    `CREATE INDEX IF NOT EXISTS idx_expense_type ON rules(expense_type);`
- [ ] `src/quickexpense_rag/data/schema.py` - Add new tables to CREATE_TABLES_SQL:
  ```python
  -- Controlled vocabulary for expense types
  CREATE TABLE IF NOT EXISTS expense_types (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE NOT NULL
  );

  -- Many-to-many junction table
  CREATE TABLE IF NOT EXISTS rule_expense_type_links (
      rule_id INTEGER NOT NULL,
      expense_type_id INTEGER NOT NULL,
      PRIMARY KEY (rule_id, expense_type_id),
      FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE,
      FOREIGN KEY (expense_type_id) REFERENCES expense_types(id) ON DELETE CASCADE
  );

  -- Indexes for efficient joins
  CREATE INDEX IF NOT EXISTS idx_link_rule ON rule_expense_type_links(rule_id);
  CREATE INDEX IF NOT EXISTS idx_link_type ON rule_expense_type_links(expense_type_id);
  ```
- [ ] Populate `expense_types` table with canonical list:
  ```sql
  INSERT INTO expense_types (name) VALUES
      ('meals'), ('travel'), ('vehicle'), ('home_office'),
      ('advertising'), ('supplies'), ('professional_fees'), ...;
  ```
- [ ] Unit tests verify:
  - All three tables created successfully
  - Foreign key constraints enforced (cannot link to non-existent rule or type)
  - Cascade deletes work (deleting rule removes links)
  - Duplicate expense type names rejected (UNIQUE constraint)
  - Junction table indexes exist and improve query performance
- [ ] Schema version remains "1.0" (pre-release breaking change)

**Dependency**: TICKET 2 (Base Schema) **Enables**: TICKET 4.7 (Models), TICKET 7
(Search), TICKET 9B-C (Indexing) **Rationale**: CRA rules frequently apply to multiple
expense categories. A many-to-many relationship provides accurate domain modeling,
maintains fast indexed queries, and enforces data integrity through foreign keys.

______________________________________________________________________

## TICKET 4.7: Pydantic Models for Multi-Type Expenses ⭐ NEW

**Scope**: Update data models to handle multiple expense types per rule

### Acceptance Criteria

- [ ] `app/rag/search/models.py` updated:
  ```python
  class ExpenseQuery(BaseModel):
      model_config = ConfigDict(frozen=True, extra='forbid')

      query: str = Field(..., min_length=3, description="Search query")
      province: Province | None = None
      business_type: BusinessType | None = None
      expense_types: list[str] | None = Field(  # Changed from expense_type
          None,
          description="Filter by expense types (matches rules with ANY of these types)"
      )
      top_k: int = Field(5, ge=1, le=50)

  class SearchResult(BaseModel):
      model_config = ConfigDict(frozen=True)

      content: str
      citation_id: str
      source_url: str
      score: float = Field(..., ge=0.0, le=1.0)
      province: Province | None
      business_type: BusinessType | None
      expense_types: list[str]  # Changed from expense_type: ExpenseType | None
      retrieved_at: datetime

      @computed_field
      @property
      def disclaimer(self) -> str:
          return (
              "⚠️ INFORMATIONAL ONLY - NOT TAX ADVICE\n"
              "This information is for educational purposes only and does not "
              "constitute tax advice. CRA rules are complex and change frequently. "
              "Always consult a qualified tax professional or accountant. "
              "The data may be incomplete, outdated, or incorrectly interpreted."
          )
  ```
- [ ] `app/rag/search/enums.py` - Keep `ExpenseType` enum for reference:
  ```python
  class ExpenseType(str, Enum):
      """Reference enum for common expense types. Not enforced in database."""
      MEALS = "meals"
      TRAVEL = "travel"
      VEHICLE = "vehicle"
      HOME_OFFICE = "home_office"
      ADVERTISING = "advertising"
      SUPPLIES = "supplies"
      PROFESSIONAL_FEES = "professional_fees"
      # ... add comprehensive list
  ```
- [ ] Update validation logic:
  - `expense_types` can be empty list (no filtering)
  - `expense_types` can be None (no filtering)
  - Each string in list validated against canonical `expense_types` table at query time
  - Clear error message if invalid type provided
- [ ] Unit tests verify:
  - `ExpenseQuery` with `expense_types=["meals", "travel"]` validates
  - `ExpenseQuery` with empty list validates
  - `SearchResult.expense_types` returns list (never None)
  - Invalid type in list raises ValidationError
  - Frozen models prevent mutation
  - `mypy` passes on all model files

**Dependency**: TICKET 4 (Base Models), TICKET 4.6 (Schema) **Enables**: TICKET 8
(Public API signature change) **Rationale**: Models must reflect the many-to-many
relationship in the database schema. Using `list[str]` provides flexibility while
maintaining type safety.

______________________________________________________________________

## TICKET 5: Embedding Service

**Scope**: Text-to-vector encoding with BGE model, singleton pattern, batch processing

### Acceptance Criteria

- [ ] `app/rag/embeddings/encoder.py`:
  ```python
  from sentence_transformers import SentenceTransformer
  import numpy as np

  class BGEEncoder:
      _instance = None
      _model = None

      def __new__(cls):
          if cls._instance is None:
              cls._instance = super().__new__(cls)
          return cls._instance

      def __init__(self):
          if self._model is None:
              self._model = SentenceTransformer(
                  settings.embedding_model,
                  device=settings.embedding_device
              )

      def embed_documents(self, texts: list[str]) -> np.ndarray:
          """Embed documents for indexing."""
          if not texts:
              raise ValueError("texts cannot be empty")
          return self._model.encode(
              texts,
              batch_size=settings.embedding_batch_size,
              normalize_embeddings=True,
              show_progress_bar=False
          )

      def embed_query(self, query: str) -> np.ndarray:
          """Embed query with instruction prefix."""
          if not query.strip():
              raise ValueError("query cannot be empty")

          instruction = "Represent this sentence for searching relevant passages: "
          return self._model.encode(
              instruction + query,
              normalize_embeddings=True,
              show_progress_bar=False
          )
  ```
- [ ] Unit tests verify:
  - Singleton pattern: multiple instantiations return same object
  - Empty input raises ValueError
  - Output shape: (n_texts, 384) for bge-small
  - Vectors are L2-normalized (norm ≈ 1.0)
  - Similar texts have cosine similarity > 0.7
  - Query has instruction prefix applied
  - Batch encoding matches sequential encoding
- [ ] Performance test: 100 texts embedded in < 2 seconds on CPU

**Dependency**: TICKET 1, TICKET 3 **Enables**: TICKET 7 (Hybrid Search), TICKET 9C
(Index Builder)

______________________________________________________________________

## TICKET 6: Data Manager (Download, Cache, Verify)

**Scope**: Download database from GitHub, verify integrity, manage cache, handle offline
mode

### Acceptance Criteria

- [ ] `app/rag/data/manager.py`:
  ```python
  class DataManager:
      def get_database_path(self) -> Path:
          """Get path to cached database, download if missing."""

      def download_database(self, force: bool = False) -> Path:
          """Download database from GitHub Releases."""
          # - Show progress bar with tqdm
          # - Atomic write (temp file → rename)
          # - Retry on network errors (exponential backoff)
          # - Verify SHA256 checksum

      def verify_integrity(self, db_path: Path) -> bool:
          """Verify database SHA256 against manifest."""

      def check_version_compatibility(self, db_path: Path) -> None:
          """Check schema and data versions, raise if incompatible."""

      def get_metadata(self, db_path: Path) -> dict:
          """Read metadata table from database."""
  ```
- [ ] **Given** clean environment, **when** `get_database_path()` called, **then**
  database downloaded to cache directory
- [ ] **Given** downloaded database, **when** opened, **then** SHA256 verified against
  manifest
- [ ] **Given** cached database, **when** `download_database(force=True)` called,
  **then** new version downloaded and old replaced
- [ ] **Given** DB version 1.x and library expects 2.x, **when** accessed, **then**
  `DataVersionMismatchError` raised
- [ ] **Given** no network and cached DB exists, **when** `get_database_path()` called,
  **then** returns cached path (offline mode)
- [ ] **Given** no network and no cached DB, **when** `get_database_path()` called,
  **then** `NetworkError` raised with clear message
- [ ] **Given** corrupted download, **when** checksum verified, **then**
  `ChecksumMismatchError` raised and file deleted
- [ ] Network retries: 3 attempts with exponential backoff (1s, 2s, 4s)
- [ ] Unit tests with mocked httpx:
  - Successful download flow
  - Network failure retry logic
  - Integrity verification catches bad data
  - Version mismatch detection
- [ ] Integration test: Download 10KB test database from mock server

**Dependency**: TICKET 1, TICKET 2, TICKET 3 **Enables**: TICKET 8 (Public API)

______________________________________________________________________

## TICKET 7: Hybrid Search Engine (FTS5 + Vector + RRF)

**Scope**: Core search logic combining keyword and semantic search with metadata
filtering

### Acceptance Criteria

- [ ] `app/rag/search/hybrid.py`:
  ```python
  class HybridSearchEngine:
      def __init__(self, db_path: Path, encoder: BGEEncoder):
          self.conn = sqlite3.connect(db_path)
          self.encoder = encoder

      def search(self, query: ExpenseQuery) -> list[SearchResult]:
          """Execute hybrid search."""
          # 1. Build metadata filter JOIN and WHERE clauses
          # 2. FTS5 keyword search on filtered candidates
          # 3. Vector search on filtered candidates
          # 4. RRF fusion
          # 5. Hydrate and return results (with GROUP BY to deduplicate)

      def _metadata_filter(self, query: ExpenseQuery) -> tuple[str, str]:
          """Build SQL JOIN and WHERE clauses from filters.

          Returns:
              (join_clause, where_clause) for expense_types many-to-many filtering
          """
          # For expense_types, build:
          # JOIN: "JOIN rule_expense_type_links link ON r.id = link.rule_id
          #        JOIN expense_types et ON link.expense_type_id = et.id"
          # WHERE: "et.name IN (?, ?, ...)"

      def _keyword_search(self, query_text: str, join_sql: str, where_sql: str, k: int) -> list[tuple]:
          """FTS5 search returning (id, score).

          Query includes JOIN for expense types and GROUP BY r.id to deduplicate.
          """

      def _vector_search(self, query_vec: np.ndarray, join_sql: str, where_sql: str, k: int) -> list[tuple]:
          """Vector search returning (id, distance).

          Query includes JOIN for expense types and GROUP BY r.id to deduplicate.
          """

      def _rrf_fusion(self, fts_results: list, vec_results: list) -> list[tuple]:
          """Reciprocal Rank Fusion: score = 1/(k + rank)."""
  ```
- [ ] RRF fusion algorithm:
  ```python
  def reciprocal_rank_fusion(
      fts_results: list[tuple[int, float]],  # (id, score)
      vec_results: list[tuple[int, float]],  # (id, distance)
      k: int = 60
  ) -> list[tuple[int, float]]:
      scores = {}
      for rank, (id, _) in enumerate(fts_results):
          scores[id] = scores.get(id, 0) + 1 / (k + rank + 1)
      for rank, (id, _) in enumerate(vec_results):
          scores[id] = scores.get(id, 0) + 1 / (k + rank + 1)
      return sorted(scores.items(), key=lambda x: x[1], reverse=True)
  ```
- [ ] **Given** query with province=BC, **when** search executed, **then** only BC
  results returned
- [ ] **Given** query with expense_types=["meals", "travel"], **when** search executed,
  **then** rules tagged with EITHER "meals" OR "travel" returned
- [ ] **Given** rule tagged with ["meals", "travel"], **when** searching for
  expense_types=["meals"], **then** rule is included in results
- [ ] **Given** query "T2125 form", **when** keyword search run, **then** exact term
  match returned
- [ ] **Given** query "restaurant meal", **when** vector search run, **then**
  semantically similar "dining expense" returned
- [ ] **Given** keyword results [A, B] and vector results [B, C], **when** RRF applied,
  **then** B ranked first (appears in both)
- [ ] **Given** no keyword matches but semantic matches exist, **when** search executed,
  **then** vector results returned
- [ ] **Given** filters matching zero rows, **when** search executed, **then** empty
  list returned gracefully
- [ ] **Given** 100MB database, **when** 100 searches executed, **then** p99 latency \<
  250ms
- [ ] Unit tests with test database:
  - Metadata filtering isolates provinces
  - Expense type filtering with JOIN: matches ANY of provided types
  - GROUP BY deduplicates rules matching multiple types
  - FTS5 finds exact keywords
  - Vector search finds semantic matches
  - RRF correctly merges rankings
  - Edge cases: no results, single result, 100+ results
- [ ] Integration test: Real query on fixture database

**Dependency**: TICKET 2, TICKET 3, TICKET 4, TICKET 4.6, TICKET 4.7, TICKET 5
**Enables**: TICKET 8 (Public API)

______________________________________________________________________

## TICKET 8: Public API

**Scope**: User-facing functions with legal disclaimers, initialization, search
interface

### Acceptance Criteria

- [ ] `app/api.py`:
  ```python
  def init(force_update: bool = False) -> None:
      """
      Initialize library and download database if needed.

      ⚠️ LEGAL DISCLAIMER:
      This library provides informational content only and does not
      constitute professional tax advice. Always consult a qualified
      tax professional or accountant. CRA rules are complex and change
      frequently. The data may be incomplete or outdated.

      Args:
          force_update: Force re-download even if cached DB exists

      Raises:
          NetworkError: If download fails and no cached DB available
          DataVersionMismatchError: If DB version incompatible
      """

  def search(
      query: str,
      province: str | None = None,
      business_type: str | None = None,
      expense_types: list[str] | None = None,
      top_k: int = 5
  ) -> list[SearchResult]:
      """
      Search CRA expense rules.

      ⚠️ NOT TAX ADVICE - Informational purposes only.

      Args:
          query: Natural language expense description
          province: Filter by province (e.g., "BC", "ON")
          business_type: Filter by business type
          expense_types: Filter by expense categories (matches rules with ANY of these types)
          top_k: Number of results to return (1-50)

      Returns:
          List of SearchResult objects with citations and disclaimers

      Raises:
          DatabaseNotInitializedError: If init() not called
          ValidationError: If invalid parameters provided
      """

  def get_version() -> dict[str, str]:
      """Get library and database versions."""
      return {
          "library_version": __version__,
          "data_version": data_manager.get_metadata()["data_version"],
          "schema_version": data_manager.get_metadata()["schema_version"]
      }
  ```
- [ ] `app/__init__.py`:
  ```python
  from .api import init, search, get_version
  from .rag.search.models import SearchResult, ExpenseQuery
  from .exceptions import *

  __version__ = "0.1.0"
  __all__ = ["init", "search", "get_version", "SearchResult", "ExpenseQuery"]
  ```
- [ ] **Given** library imported, **when** `search()` called without `init()`, **then**
  `DatabaseNotInitializedError` raised with message "Call init() first"
- [ ] **Given** `init()` called, **when** `search(query="restaurant in BC")` executed,
  **then** returns list of SearchResult objects
- [ ] **Given** invalid province "ZZ", **when** `search()` called, **then**
  ValidationError raised
- [ ] **Given** top_k=100 (out of range), **when** `search()` called, **then**
  ValidationError raised
- [ ] **Given** expense_types=["unknown_type"], **when** `search()` called, **then**
  ValidationError raised
- [ ] All function docstrings include legal disclaimer
- [ ] Unit tests verify:
  - Init without network and no cache raises NetworkError
  - Search returns correctly typed results with expense_types as list
  - All exceptions have clear, actionable messages
  - get_version() returns correct dict structure
- [ ] Integration test (User Story 1):
  ```python
  import quickexpense_rag as qer
  qer.init()
  results = qer.search(
      query="restaurant expense while traveling for training",
      province="BC",
      business_type="sole_proprietorship",
      expense_types=["meals", "travel"]
  )
  assert len(results) > 0
  assert results[0].disclaimer.startswith("⚠️")
  assert results[0].citation_id is not None
  assert results[0].source_url.startswith("https://")
  assert isinstance(results[0].expense_types, list)
  assert len(results[0].expense_types) > 0
  ```

**Dependency**: TICKET 3, TICKET 4, TICKET 4.6, TICKET 4.7, TICKET 6, TICKET 7
**Enables**: User Story 1 (ML engineer API)

______________________________________________________________________

## TICKET 9A: Document Pre-processor

**Scope**: Convert manually downloaded HTML/PDF files to clean text for LLM parsing

### Acceptance Criteria

- [ ] **Manual Download Process** documented in `docs/maintainer_guide.md`:

  - Target URLs:
    - Main index:
      https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios.html
    - Focus on Series 1 (Individuals), Series 3 (Business), Series 4 (Enterprises)
    - Filter for expense-related folios only
  - Save to `data/raw/` with descriptive names (e.g., `S3-F2-C1.html`, `S3-F2-C1.pdf`)
  - Create `data/raw/manifest.json` with download metadata:
    ```json
    [
      {
        "filename": "S3-F2-C1.html",
        "source_url": "https://...",
        "downloaded_at": "2024-12-15T10:00:00Z",
        "sha256": "abc123..."
      }
    ]
    ```

- [ ] `scripts/preprocessor/text_extractor.py`:

  ```python
  class TextExtractor:
      def extract_from_html(self, html_path: Path) -> str:
          """Extract clean text from HTML using BeautifulSoup."""
          # - Find main content area (avoid headers/footers)
          # - Use get_text(separator='\n', strip=True)
          # - Return plain text preserving structure

      def extract_from_pdf(self, pdf_path: Path) -> str:
          """Extract clean text from PDF using pdfplumber."""
          # - Preserve reading order
          # - Handle multi-column layouts
          # - Join pages with newlines
          # - Return plain text

      def preprocess_file(self, input_path: Path, output_path: Path) -> None:
          """Convert HTML or PDF to clean text file."""
  ```

- [ ] Output structure:

  ```
  data/preprocessed/
    S1-F1-C1.txt
    S3-F2-C1.txt
    S4-F3-C2.txt
  ```

- [ ] Unit tests:

  - HTML extraction removes markup but preserves structure
  - PDF extraction handles multi-page documents
  - Both formats produce clean, parseable text
  - File detection (HTML vs PDF) works correctly

- [ ] Integration test: Preprocess 1 real HTML and 1 real PDF file

**Dependency**: TICKET 1, TICKET 3 **Enables**: TICKET 9B (Gemini Parser)

______________________________________________________________________

## TICKET 9B: Gemini Flash Parser

**Scope**: Use Gemini Flash to parse documents into structured chunks with citations

### Acceptance Criteria

- [ ] `scripts/parser/schema.py` - Pydantic models for parsed output:

  ```python
  from typing import List, Literal, Optional, Union
  from pydantic import BaseModel, Field

  class Metadata(BaseModel):
      province: List[str] = Field(default_factory=list)
      business_type: List[str] = Field(default_factory=list)
      expense_type: List[str] = Field(default_factory=list)

  class TextChunk(BaseModel):
      type: Literal["paragraph", "footnote"]
      text: str
      citation_id: Optional[str] = None

  class ListItem(BaseModel):
      type: Literal["list_item"]
      text: str
      citation_id: Optional[str] = None
      sub_items: List["ListItem"] = Field(default_factory=list)

  class ListChunk(BaseModel):
      type: Literal["list"]
      items: List[ListItem]

  class TableChunk(BaseModel):
      type: Literal["table"]
      data: List[List[str]]
      citation_id: Optional[str] = None

  ContentItem = Union[TextChunk, ListChunk, TableChunk]

  class Section(BaseModel):
      section_title: str
      section_level: int
      content: List[ContentItem]

  class ParsedDocument(BaseModel):
      title: str
      document_id: Optional[str] = None  # e.g., "S3-F2-C1"
      metadata: Metadata
      sections: List[Section]
  ```

- [ ] `scripts/parser/gemini_parser.py`:

  ```python
  class GeminiParser:
      def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
          """Initialize Gemini client."""

      def parse_document(self, text: str, source_filename: str) -> ParsedDocument:
          """Parse clean text using Gemini Flash with structured output."""
          # - Build detailed system prompt with role-playing
          # - Include JSON schema in prompt
          # - Add few-shot examples
          # - Request structured JSON output
          # - Parse response with ParsedDocument.model_validate_json()

      def _build_prompt(self, text: str, document_id: str) -> str:
          """Construct parsing prompt with instructions."""
          # System prompt includes:
          # - Role: "Expert CRA legal document analyst"
          # - Task: Parse into structured JSON
          # - Citation extraction patterns (S#-F#-C#-p#.#)
          # - Metadata extraction heuristics
          # - Few-shot examples
          # - JSON schema definition

      def flatten_to_chunks(self, parsed: ParsedDocument) -> list[dict]:
          """Convert hierarchical ParsedDocument to flat chunk list."""
          # - Iterate sections and content items
          # - Preserve context (section titles) in chunk metadata
          # - Output format compatible with TICKET 9C
  ```

- [ ] Prompt engineering:

  - **Role**: "You are an expert CRA legal and tax document analyst"
  - **Instructions**:
    - Extract verbatim text (no summarization)
    - Identify document ID and metadata
    - Extract citation IDs matching pattern: `S\d+-F\d+-C\d+-p\d+\.?\d*`
    - **Extract ALL applicable expense types** from canonical list (not just one)
    - Include canonical expense type list in prompt: \["meals", "travel", "vehicle",
      "home_office", "advertising", "supplies", "professional_fees", ...\]
    - Return expense types as JSON array of strings
    - Preserve hierarchical structure
    - Handle nested lists, tables, footnotes
  - **Few-shot examples**: Include 2-3 examples showing multiple expense types per chunk
  - **JSON schema**: Full schema embedded in prompt

- [ ] Validation layer (`scripts/parser/validator.py`):

  ```python
  class ParserValidator:
      def validate_parsed_document(self, parsed: ParsedDocument, source_text: str) -> dict:
          """Run validation checks, return report."""
          # 1. Schema validation (already done by Pydantic)
          # 2. Citation format validation (regex)
          # 3. Content grounding (chunk text in source text)
          # 4. Structural sanity (section levels, no empty sections)
          # 5. Expense type validation (against canonical list from expense_types table)
          # 6. Statistics (chunk count, citation coverage, expense type distribution)
          # 7. Log unknown expense types for manual review (don't fail build)
  ```

- [ ] Output: `data/processed/chunks.jsonl`

  ```json
  {
    "content": "A taxpayer's capital cost...",
    "citation_id": "S3-F2-C1-p1.25",
    "source_url": "https://...",
    "metadata": {
      "province": ["BC"],
      "business_type": ["sole_proprietorship"],
      "expense_type": ["vehicle"],
      "section_title": "Capital Cost of Depreciable Property",
      "document_id": "S3-F2-C1"
    }
  }
  ```

- [ ] Configuration in `config/settings.py`:

  ```python
  # Add to Settings class
  gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
  gemini_model: str = "gemini-2.5-flash"
  gemini_temperature: float = 0.0  # Deterministic
  ```

- [ ] Unit tests:

  - Pydantic schema validation catches malformed JSON
  - Citation regex validation works
  - Content grounding detects hallucinations
  - Prompt construction includes all required elements

- [ ] Integration test with real document:

  - Parse 1 preprocessed CRA document
  - Validate all chunks have unique citation_ids
  - Verify metadata extracted correctly
  - Check cost: ~$0.03 per document

- [ ] Error handling:

  - Retry on API errors (3 attempts with backoff)
  - Log warnings for failed validations
  - Continue pipeline on non-critical errors
  - Store validation report for manual review

- [ ] Cost tracking:

  - Log tokens used per document
  - Estimated cost: ~$1.59 for 50 documents
  - Budget alert if cost exceeds threshold

**Dependency**: TICKET 2, TICKET 4, TICKET 9A **Enables**: TICKET 9C (Index Builder)

______________________________________________________________________

## TICKET 9C: Index Builder

**Scope**: Convert Gemini-parsed chunks to embeddings, populate SQLite database,
generate manifest

### Acceptance Criteria

- [ ] `scripts/indexer/build_index.py`:
  ```python
  class IndexBuilder:
      def build_index(
          self,
          chunks_path: Path,
          output_db: Path,
          manifest_path: Path
      ) -> IndexManifest:
          """Build searchable database from Gemini-parsed chunks."""
          # 1. Load chunks from JSONL (Gemini parser output)
          # 2. Initialize database with schema (from TICKET 4.6)
          # 3. Populate expense_types table with canonical list
          # 4. Generate embeddings (batch process with progress bar)
          # 5. Insert into rules table (without expense_type column)
          # 6. Insert into rule_expense_type_links for each expense type per rule
          # 7. Insert into rules_fts and rules_vec tables
          # 8. Verify integrity (no missing embeddings, all links have valid FKs)
          # 9. Compute database SHA256
          # 10. Write manifest JSON
  ```
- [ ] Features:
  - Populate expense_types table before processing chunks
  - For each chunk, insert rule then create links in rule_expense_type_links
  - Batch embedding generation (32 chunks at a time)
  - Progress bar for long operations
  - Transaction safety (rollback on error)
  - Duplicate detection (by citation_id)
  - Integrity checks: all chunks have embeddings, FTS index populated, all expense type
    links valid
- [ ] Output:
  - `data/cra_rules_v2024.12.db` (versioned by year-month)
  - `data/manifest.json`:
    ```json
    {
      "version": "2024.12",
      "schema_version": "1.0",
      "source_files": [...],
      "embedding_model": "BAAI/bge-small-en-v1.5",
      "chunk_count": 1234,
      "created_at": "2024-12-15T10:30:00Z",
      "sha256": "abc123..."
    }
    ```
- [ ] **Given** 1000 chunks, **when** index built, **then** completes in \<5 minutes
- [ ] **Given** duplicate citation_id, **when** inserted, **then** error raised with
  citation shown
- [ ] **Given** embedding generation fails for one chunk, **when** building, **then**
  error logged and build continues (or fails, based on flag)
- [ ] Unit tests with 10 test chunks:
  - Database created with correct schema (including expense_types and
    rule_expense_type_links)
  - expense_types table populated with canonical list
  - All tables populated (rules, rules_fts, rules_vec, rule_expense_type_links)
  - Chunk with multiple expense types creates multiple links
  - FTS triggers work (update rules → FTS updated)
  - Vector embeddings stored correctly
  - Foreign key constraints enforced (invalid expense type rejected)
  - Manifest JSON valid and complete
- [ ] Integration test: Full build from 50 chunks
  - Verify chunk count matches
  - Test search query returns results
  - Test rule with multiple expense types found by searching for any one type
  - Manifest SHA256 matches actual database file

**Dependency**: TICKET 2, TICKET 4, TICKET 4.6, TICKET 5, TICKET 9B **Enables**: User
Story 2 (auditable indexing)

______________________________________________________________________

## TICKET 9D: Maintainer CLI

**Scope**: Command-line interface to orchestrate preprocessing, parsing, building,
validation

### Acceptance Criteria

- [ ] `scripts/cli.py` using typer:
  ```python
  app = typer.Typer()

  @app.command()
  def preprocess(
      input_dir: Path = "data/raw",
      output_dir: Path = "data/preprocessed"
  ):
      """Convert HTML/PDF files to clean text."""
      # - Process all files in input_dir
      # - Auto-detect HTML vs PDF
      # - Save .txt files to output_dir

  @app.command()
  def parse(
      input_dir: Path = "data/preprocessed",
      output_path: Path = "data/processed/chunks.jsonl"
  ):
      """Parse text files to chunks using Gemini Flash."""
      # - Requires GEMINI_API_KEY environment variable
      # - Process all .txt files in input_dir
      # - Show progress bar
      # - Log token usage and estimated cost

  @app.command()
  def build(
      chunks_path: Path = "data/processed/chunks.jsonl",
      output_db: Path = "data/cra_rules.db",
      manifest_path: Path = "data/manifest.json"
  ):
      """Build searchable database."""

  @app.command()
  def validate(db_path: Path = "data/cra_rules.db"):
      """Run quality checks on database."""

  @app.command()
  def pipeline(output_db: Path = "data/cra_rules.db"):
      """Run full pipeline: preprocess → parse → build → validate."""
  ```
- [ ] `scripts/validator.py`:
  ```python
  class IndexValidator:
      def validate(self, db_path: Path) -> dict:
          """Run all validation checks, return report."""
          # - All chunks have valid citation_ids (format check)
          # - No duplicate citations
          # - All embeddings present and correct dimensions
          # - FTS index searchable
          # - Sample searches return sensible results
          # - Statistics: chunk count, coverage by province/expense_type
  ```
- [ ] Usage:
  ```bash
  # Step 1: Manually download CRA documents to data/raw/ (see docs/maintainer_guide.md)

  # Step 2: Preprocess
  uv run python scripts/cli.py preprocess --input-dir data/raw --output-dir data/preprocessed

  # Step 3: Parse with Gemini
  export GEMINI_API_KEY=your_key_here
  uv run python scripts/cli.py parse --input-dir data/preprocessed --output data/processed/chunks.jsonl

  # Step 4: Build database
  uv run python scripts/cli.py build --output-db data/cra_rules_v2024.12.db

  # Step 5: Validate
  uv run python scripts/cli.py validate --db-path data/cra_rules_v2024.12.db

  # Or run steps 2-5 together (requires manual download first)
  uv run python scripts/cli.py pipeline
  ```
- [ ] Error handling:
  - Clear error messages for each stage
  - Failed step doesn't erase previous work
  - Option to continue on non-critical errors (--force flag)
- [ ] Integration test: Run pipeline on 3 test HTML files
- [ ] Documentation: `scripts/README.md` with maintainer guide

**Dependency**: TICKET 9A, TICKET 9B, TICKET 9C **Enables**: User Story 2 (maintainer
workflow)

______________________________________________________________________

## TICKET 10: Test Infrastructure & E2E Suite

**Scope**: Pytest configuration, fixtures, comprehensive test coverage

### Acceptance Criteria

- [ ] `pyproject.toml` pytest config:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  python_files = ["test_*.py"]
  python_classes = ["Test*"]
  python_functions = ["test_*"]
  markers = [
      "unit: Fast unit tests (<100ms each)",
      "integration: Integration tests with I/O",
      "slow: Tests taking >1 second",
  ]
  addopts = "--strict-markers --tb=short"
  ```
- [ ] `tests/conftest.py` with fixtures:
  ```python
  @pytest.fixture
  def temp_db(tmp_path) -> Path:
      """Create temporary test database."""

  @pytest.fixture
  def sample_chunks() -> list[Chunk]:
      """Load sample chunks from fixtures."""

  @pytest.fixture
  def mock_encoder() -> BGEEncoder:
      """Mock encoder for fast tests."""
  ```
- [ ] Test fixtures (`tests/fixtures/`):
  - `sample_folios/` - 3 real CRA HTML excerpts
  - `sample_chunks.jsonl` - 50 pre-parsed chunks
  - `test_database.db` - Pre-built 10KB database
  - `expected_results.json` - Known search results for test queries
- [ ] Unit tests (>95% coverage for core modules):
  - `tests/unit/test_models.py`
  - `tests/unit/test_embeddings.py`
  - `tests/unit/test_data_manager.py`
  - `tests/unit/test_search.py`
- [ ] Integration tests:
  - `tests/integration/test_search_scenarios.py`:
    - BC sole prop restaurant meal (test expense_types=["meals"])
    - Vehicle expense with mileage (test expense_types=["vehicle", "travel"])
    - Home office deduction (test expense_types=["home_office"])
    - Multi-type query (expense_types=["meals", "travel"]) matches rules with ANY type
    - Rule with multiple types appears in search for any single type
  - `tests/integration/test_full_pipeline.py`:
    - Scrape → parse → build → search
    - Verify chunks with multiple expense types create correct junction table entries
- [ ] Performance tests:
  - Search latency < 250ms (p99)
  - Embedding 100 texts < 2s
  - Database init < 1s
- [ ] Commands:
  ```bash
  uv run pytest tests/unit -v -m unit
  uv run pytest tests/integration -v -m integration
  uv run pytest --cov=app --cov-report=html --cov-report=term
  uv run pytest -m "not slow"  # Fast tests only
  ```
- [ ] Coverage requirements in CI:
  - Overall: ≥85%
  - app/api.py: ≥95%
  - app/rag/search/hybrid.py: ≥95%
  - app/rag/data/manager.py: ≥90%

**Dependency**: All previous tickets **Enables**: Quality assurance before release

______________________________________________________________________

## TICKET 11: PyPI Packaging

**Scope**: Package configuration, README, license, build artifacts

### Acceptance Criteria

- [ ] `pyproject.toml` project metadata:
  ```toml
  [project]
  name = "quickexpense-rag"
  version = "0.1.0"
  description = "Semantic search over CRA business expense rules"
  readme = "README.md"
  license = {text = "MIT"}
  authors = [{name = "...", email = "..."}]
  requires-python = ">=3.11"
  keywords = ["cra", "rag", "tax", "canada", "semantic-search"]
  classifiers = [
      "Development Status :: 4 - Beta",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: MIT License",
      "Programming Language :: Python :: 3.11",
      "Programming Language :: Python :: 3.12",
      "Programming Language :: Python :: 3.13",
  ]

  [project.urls]
  Homepage = "https://github.com/.../quickexpense-rag"
  Documentation = "https://github.com/.../quickexpense-rag/docs"
  Repository = "https://github.com/.../quickexpense-rag"
  Changelog = "https://github.com/.../quickexpense-rag/CHANGELOG.md"

  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [tool.hatchling.build.targets.wheel]
  packages = ["app"]
  exclude = ["tests", "scripts", "data"]
  ```
- [ ] `README.md` structure:
  ```markdown
  # QuickExpense RAG

  [![PyPI](badge)] [![Python](badge)] [![License](badge)] [![CI](badge)]

  ## ⚠️ LEGAL DISCLAIMER
  **THIS IS NOT TAX ADVICE.** This library provides informational content
  only and does not constitute professional tax advice. CRA rules are
  complex, change frequently, and require professional interpretation.
  Always consult a qualified tax professional or accountant.

  ## What is this?
  A Python library for semantic search over Canadian Revenue Agency (CRA)
  business expense rules. Built for ML engineers building expense
  classification agents.

  ## Installation
  pip install quickexpense-rag

  ## Quick Start
  [User Story 1 example code]

  ## How It Works
  - Hybrid search: keywords (FTS5) + semantics (vector)
  - Database downloaded separately (not in package)
  - Returns CRA citations with source URLs

  ## Features
  - 🔍 Semantic + keyword search
  - 🎯 Filter by province, business type, expense category
  - 📚 Returns authoritative CRA citations
  - 🔒 No API keys or network calls after setup
  - 📦 Lightweight package (<5MB)

  ## Documentation
  [Link to docs]

  ## License
  MIT
  ```
- [ ] `LICENSE` file (MIT)
- [ ] `CHANGELOG.md`:
  ```markdown
  # Changelog
  All notable changes to this project will be documented in this file.

  The format is based on [Keep a Changelog](https://keepachangelog.com/).

  ## [0.1.0] - 2024-12-XX
  ### Added
  - Initial release
  - Hybrid search (FTS5 + vector)
  - Support for BC, AB, ON, QC provinces
  - Coverage of business expense folios
  ```
- [ ] `py.typed` marker file for type hints
- [ ] Build and test:
  ```bash
  uv build
  ls dist/  # Should show .whl and .tar.gz
  unzip -l dist/*.whl | grep "app/"  # Verify only app/ included
  pip install dist/*.whl
  python -c "import quickexpense_rag; print(quickexpense_rag.__version__)"
  ```
- [ ] Verify wheel size < 5MB
- [ ] TestPyPI upload:
  ```bash
  twine check dist/*
  twine upload --repository testpypi dist/*
  pip install --index-url https://test.pypi.org/simple/ quickexpense-rag
  ```

**Dependency**: All implementation tickets **Enables**: User Story 3 (PyPI publishing)

______________________________________________________________________

## TICKET 12: Release Automation

**Scope**: GitHub Actions for PyPI releases and database artifact publishing

**Note**: CI quality gates (linting, formatting, type checking, testing) are now in
TICKET 1.5 and should already be in place.

### Acceptance Criteria

- [ ] `.github/workflows/release.yml`:
  ```yaml
  name: Release
  on:
    push:
      tags: ['v*']
  jobs:
    build:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - run: uv build
        - run: twine check dist/*

    publish:
      needs: build
      runs-on: ubuntu-latest
      permissions:
        id-token: write
      steps:
        - uses: pypa/gh-action-pypi-publish@release/v1

    github-release:
      needs: publish
      runs-on: ubuntu-latest
      steps:
        - uses: actions/create-release@v1
          with:
            tag_name: ${{ github.ref }}
            body_path: CHANGELOG.md
  ```
- [ ] `.github/workflows/build-database.yml`:
  ```yaml
  name: Build Database
  on:
    workflow_dispatch:  # Manual trigger only (requires manual download step)
  jobs:
    build:
      runs-on: ubuntu-latest
      env:
        GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      steps:
        - uses: actions/checkout@v4
        - name: Check for raw data
          run: |
            if [ ! -d "data/raw" ] || [ -z "$(ls -A data/raw)" ]; then
              echo "Error: data/raw/ is empty. Manually download CRA documents first."
              exit 1
            fi
        - run: uv run python scripts/cli.py pipeline
        - run: uv run python scripts/cli.py validate
        - name: Display cost report
          run: cat logs/parsing_cost.json
        - uses: actions/upload-artifact@v3
          with:
            name: database
            path: data/*.db

    release:
      needs: build
      runs-on: ubuntu-latest
      steps:
        - uses: softprops/action-gh-release@v1
          with:
            tag_name: data-${{ github.run_number }}
            files: data/cra_rules*.db
  ```
- [ ] Note: No canary tests needed (no automated scraping to break)
- [ ] Test release to TestPyPI from release workflow
- [ ] Test database build workflow manually with sample data
- [ ] Documentation: `docs/maintainer_guide.md` with release process

**Dependency**: TICKET 11 (Packaging), TICKET 9D (Maintainer CLI for database builds)
**Enables**: Automated releases to PyPI and GitHub Releases **Note**: CI quality gates
from TICKET 1.5 are prerequisites and should already be passing

______________________________________________________________________

## Dependency Graph

```
Phase 1: Foundation (Day 1)
├─ TICKET 1 (Project Setup)
├─ TICKET 1.5 (CI Quality Gates) ← 1
│
Phase 2: Core Definitions (Days 1-2, Parallel)
├─ TICKET 2 (Schema & Versioning) ← 1
├─ TICKET 3 (Config & Exceptions) ← 1
├─ TICKET 4 (Pydantic Models) ← 1, 3
├─ TICKET 4.5 (Fixture Database) ⭐ ← 2, 3
├─ TICKET 4.6 (Many-to-Many Schema) ⭐ NEW ← 2
├─ TICKET 4.7 (Multi-Type Models) ⭐ NEW ← 4, 4.6
│
┌─────────────────────────────────────────────────────────────────────┐
│ PARALLEL WORKSTREAMS (Days 2-5)                                     │
│                                                                      │
│ Workstream A: Runtime Library        Workstream B: Indexing Pipeline│
│ (User-facing search API)             (Data ingestion)               │
│                                                                      │
│ TICKET 5 (Embeddings) ← 1, 3         TICKET 9A (Preprocessor) ← 1, 3│
│     ↓                                     ↓                          │
│ TICKET 7 (Hybrid Search)             TICKET 9B (Gemini Parser)      │
│     ← 2,3,4,4.5,4.6,4.7,5                 ← 2, 4, 4.6, 9A           │
│     ↓                                     ↓                          │
│ TICKET 6 (Data Manager - Simple) ← 2,3   TICKET 9C (Index Builder)  │
│     ↓                                         ← 2, 4, 4.6, 5, 9B    │
│ TICKET 8 (Public API)                    ↓                          │
│     ← 3,4,4.6,4.7,6,7                TICKET 9D (Maintainer CLI)      │
│     ↓                                     ← 9A, 9B, 9C               │
│ 🎉 MILESTONE: Working demo!                                          │
└─────────────────────────────────────────────────────────────────────┘
                         ↓
Phase 4: Integration & Release (Days 6-7)
├─ TICKET 6 (Complete Data Manager - add download/cache) ← 8, 9D
├─ TICKET 10 (E2E Testing) ← ALL
├─ TICKET 11 (Packaging) ← ALL
├─ TICKET 12 (Release Automation) ← 11, 9D
```

**Key Changes**:

- ⭐ **Ticket 4.5** (Fixture Database) unblocks Workstream A to develop independently
- ⭐ **Ticket 4.6 & 4.7** (Many-to-Many Expense Types) enable accurate domain modeling
- ⭐ **Ticket 1.5** (CI Gates) moved to Day 1 for immediate quality enforcement
- **Parallel Development**: Runtime (A) and Pipeline (B) work simultaneously after Phase
  2
- **Fast Feedback**: Working demo achievable in 2-3 days (after Ticket 8)

## User Story Coverage

### ✅ User Story 1: ML Engineer API

**Covered by**: TICKET 8 (Public API), TICKET 4 (Models), TICKET 4.6 (Schema), TICKET
4.7 (Models), TICKET 7 (Search)

```python
import quickexpense_rag as qer
qer.init()
results = qer.search(
    query="restaurant expense while traveling for training",
    province="BC",
    business_type="sole_proprietorship",
    expense_types=["meals", "travel"]
)
# Returns SearchResult objects with citations, disclaimers, and expense_types as list
assert isinstance(results[0].expense_types, list)
```

### ✅ User Story 2: Maintainer Indexing

**Covered by**: TICKET 9A-D (Preprocessor, Gemini Parser, Builder, CLI)

```bash
# Step 1: Manual download to data/raw/
# Step 2-5: Automated pipeline
export GEMINI_API_KEY=your_key_here
uv run python scripts/cli.py pipeline --output-db data/cra_rules_v2024.12.db
# Produces: database + manifest.json with full provenance
# Cost: ~$1.59 for 50 documents
```

### ✅ User Story 3: PyPI Publishing

**Covered by**: TICKET 11 (Packaging), TICKET 12 (CI/CD)

```bash
git tag v0.1.0
git push --tags
# GitHub Actions builds and publishes to PyPI automatically
```

## Production Risk Mitigation

### 🔥 Critical Risks

1. **Gemini API Availability**: Network or API outages during indexing

   - **Mitigation**: Retry logic with exponential backoff, cache parsed results, offline
     fallback to manual parsing

1. **LLM Hallucination**: Gemini might generate incorrect citations or content

   - **Mitigation**: Multi-layer validation (Pydantic schema + regex + content
     grounding), manual spot-checking, validation reports

1. **Parsing Cost**: Re-parsing all documents on schema changes

   - **Mitigation**: Cost is negligible (~$1.59 for 50 docs), version parsed outputs,
     incremental re-parsing

1. **Data Integrity**: Malicious database injection

   - **Mitigation**: SHA256 checksum verification, signed manifests, validation pipeline

1. **sqlite-vec Installation**: C extension compilation failures

   - **Mitigation**: Pre-compiled wheels via cibuildwheel, clear fallback docs

1. **Version Mismatch**: Old library + new database (or vice versa)

   - **Mitigation**: Semantic versioning checks in DataManager

1. **Legal Liability**: Users misuse as tax advice

   - **Mitigation**: Prominent disclaimers everywhere, citation provenance

### ✅ Risks Eliminated

- **Scraper Brittleness**: No automated scraping - maintainer manually downloads
  documents
- **HTML/PDF Structure Changes**: LLM parsing is more robust than regex/BeautifulSoup

## Timeline Estimate

### Original Sequential Plan

- **Phase 1 (Foundation)**: 1 day
- **Phase 2 (Definitions)**: 1-2 days (parallel)
- **Phase 3 (Runtime Library)**: 3-4 days (sequential)
- **Phase 4 (Indexing Pipeline)**: 3-4 days (sequential after Phase 3)
- **Phase 5 (Quality & Release)**: 2 days
- **Total: 10-12 days** (2-2.5 weeks)

### ⚡ Optimized Parallel Plan

- **Phase 1 (Foundation + CI Gates)**: 1 day
  - TICKET 1: Project Setup
  - TICKET 1.5: CI Quality Gates
- **Phase 2 (Core Definitions)**: 1 day (parallel work)
  - TICKET 2, 3, 4, 4.5 (can be split among team members)
- **Phase 3 (Parallel Workstreams)**: 3-4 days
  - Workstream A (Runtime): TICKET 5 → 7 → 6 → 8
  - Workstream B (Pipeline): TICKET 9A → 9B → 9C → 9D
  - **🎉 Milestone: Working demo after day 2-3** (Ticket 8 complete)
- **Phase 4 (Integration & Release)**: 1-2 days
  - TICKET 6 (complete), 10, 11, 12

**Total: 6-7 days** (1-1.5 weeks)

### Productivity Gains

- **40% faster** (7 days vs 12 days)
- **Working demo in 2-3 days** vs 5-7 days (60% faster to first demo)
- **Enables 2-person team**: One on runtime, one on pipeline
- **Earlier quality gates**: CI from day 1 prevents rework

______________________________________________________________________

## Next Steps

### Recommended Execution Order

**Day 1: Foundation**

1. TICKET 1: Initialize project, dependencies, directory structure
1. TICKET 1.5: Setup CI/CD quality gates (linting, formatting, type checking)
1. Verify: `uv run pre-commit run --all-files` passes

**Day 1-2: Core Definitions** (can be parallelized among team)

1. TICKET 2: Define database schema
1. TICKET 3: Setup configuration and exceptions
1. TICKET 4: Create Pydantic models
1. TICKET 4.5: Create fixture database (10-20 hand-crafted rows)
1. Verify: Fixture database passes schema validation

**Days 2-5: Split into Two Parallel Workstreams**

**Workstream A (Runtime Team)**:

1. TICKET 5: Embedding service
1. TICKET 7: Hybrid search engine (test against fixture DB)
1. TICKET 6: Data manager (simple version pointing to fixture)
1. TICKET 8: Public API
1. **🎉 Milestone: Demo `qer.search()` working!**

**Workstream B (Pipeline Team)**:

1. TICKET 9A: Document preprocessor
1. TICKET 9B: Gemini parser
1. TICKET 9C: Index builder
1. TICKET 9D: Maintainer CLI

**Days 6-7: Integration & Release**

1. TICKET 6: Complete data manager (download/cache logic)
1. TICKET 10: E2E testing with real database
1. TICKET 11: PyPI packaging
1. TICKET 12: Release automation
1. Deploy to TestPyPI for validation
1. Launch v0.1.0 to PyPI

### Team Composition Recommendations

- **Solo Developer**: Follow Workstream A first for fastest demo, then Workstream B
- **2-Person Team**: One on Workstream A, one on Workstream B
- **3+ Person Team**: Split Phase 2 work, then allocate to workstreams
