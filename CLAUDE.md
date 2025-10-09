# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in
this repository.

## Project Overview

**QuickExpense RAG** is a Python library providing semantic search over Canadian Revenue
Agency (CRA) business expense rules. The library combines keyword search (SQLite FTS5)
and semantic search (sqlite-vec with BGE embeddings) using Reciprocal Rank Fusion (RRF)
for hybrid search.

**Critical**: This project is NOT tax advice software. All user-facing APIs and outputs
MUST include prominent legal disclaimers stating the content is informational only and
users must consult qualified tax professionals.

## Architecture Pattern

This project uses **src-layout** structure following Arkalos principles:

- `src/quickexpense_rag/` - Runtime library (distributed via PyPI, user-facing)
- Data is distributed separately via GitHub Releases, not bundled in the Python package
- Clear separation between runtime code and development/test infrastructure

## Key Architectural Decisions

### Hybrid Search Implementation

Search combines three techniques in sequence:

1. **Metadata filtering** - SQL WHERE clause filters by
   province/business_type/expense_type
1. **FTS5 keyword search** - Exact term matching on filtered candidates
1. **Vector semantic search** - BGE-small-en-v1.5 embeddings with cosine similarity
1. **RRF fusion** - Reciprocal Rank Fusion merges rankings: `score = 1/(k + rank)`

### Data Distribution Strategy

- **Code**: Distributed via PyPI (`pip install quickexpense-rag`)
- **Database**: Downloaded from GitHub Releases on first use (via `qe.init()`)
- **Versioning**: Schema version + data version stored in database metadata table
- **Integrity**: SHA256 checksums verified on download, version compatibility checked on
  init

## Database Schema Contract

The schema (defined in `src/quickexpense_rag/data/schema.py`) defines the database
structure:

**Tables**:

- `metadata` - Schema version, data version, build info
- `rules` - Main content table with citation_id (unique), content, metadata (province,
  business_type, expense_type)
- `rules_fts` - FTS5 virtual table for keyword search (auto-synced via triggers)
- `rules_vec` - Vector table for semantic search (384-dim BGE embeddings)

**Key Constraint**: `citation_id` must be unique and follow pattern
`S\d+-F\d+-C\d+-p\d+\.?\d*`

## Development Commands

### Initial Setup

```bash
# Initialize with uv (package manager)
uv init --lib quickexpense-rag
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Quality Checks

```bash
# Format code
uvx ruff format

# Lint code
uvx ruff check

# Type check
uv run mypy src/

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

### Testing

```bash
# Run fast unit tests only
uv run pytest tests/unit -v -m unit

# Run integration tests
uv run pytest tests/integration -v -m integration

# Run specific test file
uv run pytest tests/unit/test_search.py -v

# Skip slow tests
uv run pytest -m "not slow"
```

### Interactive Development

```bash
# Test against fixture database
uv run pytest tests/ --db=tests/fixtures/test_database.db

# Interactive testing
uv run python
>>> import quickexpense_rag as qe
>>> qe.init()
>>> results = qe.search("restaurant meal", province="BC")
```

### Building & Releasing

```bash
# Build package
uv build

# Check wheel contents
unzip -l dist/*.whl | grep "quickexpense_rag/"

# Verify wheel size < 5MB
ls -lh dist/

# Test local install
pip install dist/*.whl

# Upload to TestPyPI
twine check dist/*
twine upload --repository testpypi dist/*
```

## Development Best Practices

### Commit Strategy

- **Small, atomic commits**: Each commit should represent one logical change
- **Pass all checks**: Every commit must pass `ruff`, `mypy`, and all pre-commit hooks
- **Commit frequently**: Don't accumulate large changesets
- **Meaningful messages**: Use conventional commits format (feat:, fix:, docs:,
  refactor:, test:)

### 80/20 Principle

- **Focus on high-value features first**: Deliver core functionality before edge cases
- **Avoid premature optimization**: Get it working, then make it fast
- **Simplicity over cleverness**: Clear code beats clever code
- **YAGNI**: You Aren't Gonna Need It - don't build features speculatively

### Modern Python 3.12+ Standards

- **Type hints everywhere**: Use `str | None` instead of `Optional[str]`
- **Structural pattern matching**: Use `match/case` for complex conditionals
- **Walrus operator**: Use `:=` for assignment expressions where it improves readability
- **f-strings**: Always prefer f-strings over `.format()` or `%` formatting
- **Generics**: Use modern generic syntax `list[str]` instead of `List[str]`
- **dataclasses/Pydantic**: Prefer declarative data models over manual `__init__`

## Documentation Structure (Diataxis Framework)

Follow the [Diataxis framework](https://diataxis.fr/) for documentation:

### Tutorials (Learning-Oriented)

- **Purpose**: Help newcomers take their first steps
- **Location**: `docs/tutorials/`
- **Example**: "Building Your First Expense Search"
- **Characteristics**: Step-by-step, repeatable, beginner-friendly

### How-To Guides (Problem-Oriented)

- **Purpose**: Show how to solve specific problems
- **Location**: `docs/howto/`
- **Example**: "How to Filter by Province and Business Type"
- **Characteristics**: Goal-oriented, practical, assumes basic knowledge

### Reference (Information-Oriented)

- **Purpose**: Describe the machinery (API reference)
- **Location**: `docs/reference/`
- **Example**: API documentation, configuration options
- **Characteristics**: Accurate, complete, up-to-date

### Explanation (Understanding-Oriented)

- **Purpose**: Clarify and illuminate topics
- **Location**: `docs/explanation/`
- **Example**: "Why Hybrid Search with RRF", "Database Schema Design"
- **Characteristics**: Context, background, design decisions

## Important Constraints

### Legal Disclaimers

Every user-facing function, model, and output MUST include prominent disclaimers:

- `SearchResult.disclaimer` computed field (always present)
- `qe.init()` docstring includes legal warning
- `qe.search()` docstring includes "NOT TAX ADVICE" warning
- README.md has prominent disclaimer at top

### Immutability

All Pydantic models use `frozen=True` and `extra='forbid'` to ensure API contracts are
enforced.

### Type Safety

- `strict = True` in mypy.ini
- All functions must have type hints
- No `Any` types without justification

### Embedding Model Lock-in

The BGE-small-en-v1.5 model produces 384-dimensional embeddings. Changing models
requires full database rebuild. The model name is stored in database metadata for
version tracking.

## Testing Strategy

### Fixture Database (tests/fixtures/test_database.db)

A small, hand-crafted database with 10-20 rows for testing, covering:

- Provinces: BC, AB, ON, QC
- Business types: sole_proprietorship, corporation, partnership
- Expense types: meals, travel, vehicle, home_office

This allows development and testing without requiring production data pipeline.

### Test Markers

- `@pytest.mark.unit` - Fast tests (\<100ms each), no I/O
- `@pytest.mark.integration` - Tests with database/network I/O
- `@pytest.mark.slow` - Tests taking >1 second (embeddings, full operations)

## Configuration Management

Settings use `pydantic-settings` with environment variable support:

- Prefix: `QUICKEXPENSE_`
- Example: `QUICKEXPENSE_CACHE_DIR=/custom/path`
- `.env` file supported (use `.env.example` as template)

**Available settings**:

- `cache_dir`: Local cache directory for downloaded databases
- `embedding_model`: BGE model name (default: "BAAI/bge-small-en-v1.5")
- `default_top_k`: Default number of search results (default: 5)
- `db_download_url`: GitHub Releases URL for database

## Version Compatibility

The library checks version compatibility on `qe.init()`:

- **Schema version**: Major.Minor (e.g., "1.0") - breaking schema changes increment
  major
- **Data version**: YYYY.MM (e.g., "2024.12") - new data releases increment month
- **Library version**: Semantic versioning (e.g., "0.1.0")

Incompatible versions raise `DataVersionMismatchError` with clear upgrade instructions.

## Common Pitfalls

1. **Don't bundle database in package** - It's downloaded separately from GitHub
   Releases
1. **Don't skip disclaimers** - Every user-facing output needs legal warnings
1. **Don't break the schema contract** - Tests and runtime depend on consistent schema
1. **Use fixture DB for tests** - Don't require production data for development
1. **Embedding model changes require full rebuild** - Vector dimensions are fixed at 384
1. **Don't over-engineer** - Follow 80/20 principle, build what's needed now

## File Structure Conventions

```
src/
  quickexpense_rag/           # Runtime library (in PyPI package)
    search/                   # Search engine, enums, models
      hybrid.py               # Hybrid search implementation
      models.py               # Pydantic models
      enums.py                # Province, BusinessType, ExpenseType
    data/                     # Data layer
      schema.py               # Database schema definition
      manager.py              # Download, cache, verify
    embeddings/               # Embedding service
      encoder.py              # BGE encoder singleton
    api.py                    # Public API: init(), search(), get_version()
    exceptions.py             # Custom exception hierarchy
    settings.py               # Configuration (pydantic-settings)

tests/
  fixtures/                   # Test data
    test_database.db          # Hand-crafted test DB (committed to git)
  unit/                       # Fast unit tests
  integration/                # Integration tests

docs/                         # Documentation (Diataxis structure)
  tutorials/                  # Learning-oriented guides
  howto/                      # Problem-solving guides
  reference/                  # API documentation
  explanation/                # Understanding-oriented content
```
