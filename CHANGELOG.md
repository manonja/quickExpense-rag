# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-10-24

### Added

#### Epic 0 Completion: Make Search Work

- **Production Database Release** - Published `data-v2025.10.23` to GitHub Releases
  - 63 searchable CRA expense rules from single source file (t4002-5.html)
  - 100% lineage coverage with extraction timestamps and source tracking
  - SHA256 checksum verification: `960601b0e7a1b73e59ce8f857b603516382341ba22729da9d90858bbf0f6125b`
  - Database auto-downloads on first `qe.init()` call

- **Search Validation** - Validated hybrid search functionality
  - 10/10 test queries successful (100% success rate)
  - FTS5 keyword search + BGE-small-en-v1.5 vector embeddings
  - Reciprocal Rank Fusion (RRF) ranking validated
  - Sub-250ms query performance maintained

- **RAG Integration Examples** - Complete examples for building tax Q&A chatbots
  - `examples/basic_rag.py` - Full RAG pipeline with Gemini, OpenAI, or Anthropic
  - `examples/README.md` - Setup guide and troubleshooting
  - 6-section tutorial: environment, database init, search, RAG pipeline, output, advanced patterns

- **Lineage Metadata** - Minimal lineage tracking implemented
  - Every chunk has `lineage_chain` showing transformation path (e.g., "t4002-5.html | classic_parser -> adjudicator")
  - Extraction timestamps and source file tracking
  - Expert source attribution (classic vs adjudicated)
  - Supports debugging and quality assessment

### Fixed

- **get_version() Returns Actual Metadata** - Fixed hardcoded "not_initialized" values
  - Now queries database metadata table for real `data_version` and `schema_version`
  - Returns "not_initialized" only when called before `qe.init()`
  - Examples now display correct version info

- **Province Filter Removed from Examples** - Fixed 0-results issue in `basic_rag.py`
  - Current database contains federal CRA rules (no province-specific metadata)
  - Removed `province="BC"` filter that was excluding all results
  - Updated query text to reflect federal scope

### Changed

- **Data Source** - Current database built from single HTML file
  - Source: `t4002-5.html` from CRA T4002 Business and Professional Income Guide
  - Coverage: 63 expense rules (subset of full guide)
  - Future epics will expand to full T4002 coverage (247+ rules)

- **Metadata Limitations** - Documented what metadata is NOT present
  - No `province` or `business_type` fields (federal rules apply Canada-wide)
  - Filtering by province returns 0 results
  - Examples updated to reflect this limitation

### Documentation

- Added GitHub Release instructions for data distribution
- Created comprehensive RAG integration guide
- Updated `.env.example` with API key configuration for RAG examples
- Added release notes for data-v2025.10.23

### Quality Metrics (Epic 0)

- ✅ Working hybrid search (FTS5 + vector) for basic queries
- ✅ Every result has lineage_chain (100% coverage)
- ✅ Can trace results to source files via lineage
- ✅ Zero critical errors in search/retrieval
- ✅ 10/10 test queries return relevant results (100% vs 70% threshold)
- ✅ 100% chunks have valid citation_id and lineage
- ✅ CLI search command enables interactive exploration

## [0.2.0] - 2025-10-16

### Changed

- **BREAKING**: Package renamed from `quickexpense-rag` to `qe-tax-rag`
- **BREAKING**: Python module renamed from `quickexpense_rag` to `qe_tax_rag`
- **BREAKING**: Environment variable prefix changed from `QUICKEXPENSE_RAG_` to
  `QE_TAX_RAG_`
- **BREAKING**: Base exception class renamed from `QuickExpenseError` to `QeTaxRagError`
- GitHub repository URL updated to `https://github.com/manonja/qe-tax-rag`
- Default cache directory changed from `~/.cache/quickexpense_rag` to
  `~/.cache/qe_tax_rag`

### Migration Guide

Update your code as follows:

```python
# Before (v0.1.0)
import quickexpense_rag as qe
from quickexpense_rag import QuickExpenseError

# After (v0.2.0)
import qe_tax_rag as qe
from qe_tax_rag import QeTaxRagError
```

Update environment variables:

```bash
# Before
export QUICKEXPENSE_RAG_CACHE_DIR="/custom/path"

# After
export QE_TAX_RAG_CACHE_DIR="/custom/path"
```

## [0.1.0] - 2025-01-15

### Added

#### Core Search Functionality

- Hybrid search combining FTS5 keyword search and vector semantic search
- BGE-small-en-v1.5 embeddings (384-dimensional vectors) for semantic similarity
- Reciprocal Rank Fusion (RRF) algorithm for ranking results from both search methods
- SQLite database with FTS5 full-text search and sqlite-vec for vector operations
- Sub-250ms query performance on typical searches

#### Filtering and Metadata

- Many-to-many relationship for expense types (rules can match multiple categories)
- Metadata filtering by province (BC, AB, ON, QC, SK, MB, NB, NS, PE, NL, YT, NT, NU)
- Metadata filtering by business type (sole_proprietorship, corporation, partnership)
- Metadata filtering by expense types (meals, travel, vehicle, home_office, advertising,
  supplies, professional_fees, utilities, insurance, rent, office, equipment, telephone,
  internet, memberships, subscriptions, entertainment, gifts, donations, repairs,
  maintenance, licenses, permits, fees, interest, bank_charges, bad_debts, salaries,
  wages, benefits, training, education, legal, accounting, consulting, marketing,
  shipping, delivery, taxes, other)
- SQL JOIN-based filtering for efficient many-to-many expense type queries

#### Data Management

- Automatic database download from GitHub Releases on first initialization
- SHA256 checksum verification for database integrity
- Version compatibility checking (schema version + data version)
- Offline mode support (uses cached database when network unavailable)
- Database schema versioning with migration support (version 1.0)
- Singleton pattern for embedding model (prevents redundant model loading)

#### API and Type Safety

- Clean public API: `init()`, `search()`, `get_version()`
- Legal disclaimers on all user-facing APIs and SearchResult objects
- Pydantic v2 models with frozen=True for immutability
- Full type hints with py.typed marker for PEP 561 compliance
- Strict type checking (mypy + pyright in strict mode)
- Modern Python 3.11+ type syntax (`str | None`, `list[str]`)

#### Parsing and Indexing (Scripts)

- Gemini Flash 2.0 LLM-based document parser for structured extraction
- Pre-processor for HTML and PDF → clean text conversion
- Many-to-many expense type extraction (rules tagged with all applicable types)
- Multi-layer validation (Pydantic schema + regex + content grounding)
- Hierarchical document structure preservation (sections, lists, tables, footnotes)
- Citation ID extraction with pattern matching (S#-F#-C#-p#.#)
- Flattening hierarchical ParsedDocument to flat chunks for ingestion
- Index builder with batch embedding generation and progress tracking
- Maintainer CLI (typer) for preprocessing, parsing, building, validation workflows
- Cost tracking for Gemini API usage (~$1.59 for 50 documents)

#### Testing and Quality

- Comprehensive test suite with 23/23 tests passing
- Unit tests (>95% coverage for core modules)
- Integration tests (search scenarios, full pipeline)
- Performance tests (latency, embedding speed, database init)
- Fixture database (10-20 hand-crafted rows) for development and testing
- pytest markers (unit, integration, slow) for selective test execution
- CI/CD with GitHub Actions (lint, format, type check, test)
- Pre-commit hooks (ruff, ruff-format, mypy, pyright, mdformat)
- Dual type checking (mypy + pyright strict) for comprehensive coverage

#### Documentation

- Comprehensive README with legal disclaimers and API reference
- CLAUDE.md with development guidelines and architecture patterns
- Detailed docstrings for all public functions and classes
- Example code demonstrating all features
- Configuration via environment variables (pydantic-settings)

### Documentation

- README with installation and quick start guide
- Legal disclaimers emphasizing this is NOT tax advice
- API reference for init(), search(), get_version()
- Data model documentation (SearchResult, Province, BusinessType enums)
- How It Works section explaining hybrid search architecture
- Configuration options via environment variables
- Development setup instructions
- Testing and quality check commands

### Infrastructure

- Python 3.11+ support (3.11, 3.12, 3.13)
- uv package manager for dependency management
- hatchling build system with src-layout
- Dynamic versioning from __init__.py
- Lightweight package (\<5MB wheel, database downloaded separately)
- Type-safe with mypy and pyright strict mode

[0.1.0]: https://github.com/manonja/quickExpense-rag/releases/tag/v0.1.0
[0.2.0]: https://github.com/manonja/quickExpense-rag/releases/tag/v0.2.0
