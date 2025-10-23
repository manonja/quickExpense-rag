# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in
this repository.

## Project Overview

**QE Tax RAG** is a Python library providing semantic search over Canadian Revenue
Agency (CRA) business expense rules. The library combines keyword search (SQLite FTS5)
and semantic search (sqlite-vec with BGE embeddings) using Reciprocal Rank Fusion (RRF)
for hybrid search.

**Critical**: This project is NOT tax advice software. All user-facing APIs and outputs
MUST include prominent legal disclaimers stating the content is informational only and
users must consult qualified tax professionals.

## Architecture Pattern

This project uses **src-layout** structure following Arkalos principles:

- `src/qe_tax_rag/` - Runtime library (distributed via PyPI, user-facing)
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

- **Code**: Distributed via PyPI (`pip install qe-tax-rag`)
- **Database**: Downloaded from GitHub Releases on first use (via `qe.init()`)
- **Versioning**: Schema version + data version stored in database metadata table
- **Integrity**: SHA256 checksums verified on download, version compatibility checked on
  init

## Database Schema Contract

The schema (defined in `src/qe_tax_rag/data/schema.py`) defines the database structure:

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
uv init --lib qe-tax-rag
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
>>> import qe_tax_rag as qe
>>> qe.init()
>>> results = qe.search("restaurant meal", province="BC")
```

### Building & Releasing

```bash
# Build package
uv build

# Check wheel contents
unzip -l dist/*.whl | grep "qe_tax_rag/"

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

- **Pass all checks**: Every commit must pass all pre-commit hooks:

  - `ruff` (linting with auto-fix)
  - `ruff-format` (code formatting)
  - `mypy` (type checking - strict mode)
  - `pyright` (type checking - strict mode with selective third-party disables)
  - `mdformat` (markdown formatting with GFM, tables, frontmatter)
  - Standard hooks (trailing whitespace, EOF, YAML, large files, merge conflicts)

- **Dual type checking**: Both mypy and pyright run on every commit; they catch
  different classes of type errors

- **Commit frequently**: Don't accumulate large changesets

- **Meaningful messages**: Use conventional commits format with detailed body:

  ```
  <type>: <short summary (50 chars)>

  <detailed description explaining WHY, not WHAT>
  - Use bullet points for multiple changes
  - Focus on motivation and context
  - Reference ticket numbers if applicable

  Rationale:
  - Explain technical decisions made
  - Document trade-offs considered

  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

  **Types**: feat (feature), fix (bug fix), docs (documentation), refactor, test, build
  (build system/dependencies), ci (CI/CD), perf (performance), style (formatting), chore
  (maintenance)

**Example**:

```
build: add pyright and mdformat to pre-commit hooks

Enhance code quality gates with dual type checking and markdown linting:

- Add pyright (strict mode) alongside mypy for comprehensive type safety
- Add mdformat for consistent markdown formatting (GFM, tables, frontmatter)
- Tighten pyright configuration for better bug detection

Rationale:
- Dual type checkers catch different classes of type issues
- mdformat avoids Node.js dependency (vs markdownlint-cli2)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 80/20 Principle

- **Focus on high-value features first**: Deliver core functionality before edge cases
- **Avoid premature optimization**: Get it working, then make it fast
- **Simplicity over cleverness**: Clear code beats clever code
- **YAGNI**: You Aren't Gonna Need It - don't build features speculatively

### Autonomous Decision-Making Guidelines

**Make decisions autonomously when**:

- Technical trade-offs are clear and align with project principles (80/20, YAGNI,
  simplicity)
- Decision is reversible (tooling, formatting, configuration)
- Choice follows established patterns in the project
- Solution solves immediate blocker without architectural impact
- Multiple approaches exist but one clearly matches project philosophy

**Ask user before deciding when**:

- Architectural changes affect public APIs or core abstractions
- Trade-offs involve competing priorities (speed vs maintainability, simplicity vs
  features)
- Multiple valid approaches exist with different philosophies
- Decision affects project scope, timeline, or dependencies
- User's intent is ambiguous or could be interpreted multiple ways

**Tool Selection Philosophy**:

- **Prefer Python ecosystem**: Choose Python-based tools (mdformat, uvx) over tools
  requiring Node.js, Ruby, or other language runtimes to minimize dependency complexity
- **Prefer built-in/bundled tools**: Use tools already in the ecosystem (uvx, uv run)
  over additional package managers
- **Prefer mature, widely-adopted tools**: Choose tools with active maintenance and
  large communities
- **Consistency matters**: Match existing project patterns (uv for packages, ruff for
  linting, pydantic for models)

**Examples from this project**:

- ✅ Chose mdformat (Python) over markdownlint-cli2 (Node.js) - follows ecosystem
  preference
- ✅ Tightened pyright config based on Zen feedback - clear improvement, reversible
- ✅ Used uvx over npm for tool execution - matches project's uv-based tooling

### Modern Python 3.12+ Standards

- **Type hints everywhere**: Use `str | None` instead of `Optional[str]`
- **Structural pattern matching**: Use `match/case` for complex conditionals
- **Walrus operator**: Use `:=` for assignment expressions where it improves readability
- **f-strings**: Always prefer f-strings over `.format()` or `%` formatting
- **Generics**: Use modern generic syntax `list[str]` instead of `List[str]`
- **dataclasses/Pydantic**: Prefer declarative data models over manual `__init__`

## Code Review Workflow with Zen MCP

### When to Use Zen Tools

Zen MCP tools are powerful for systematic code analysis but should **only be used when
the user requests it**. Do not use Zen tools proactively.

**Available Zen tools**:

- `mcp__zen__codereview` - Comprehensive code review with expert validation
- `mcp__zen__precommit` - Git changes validation before commits
- `mcp__zen__chat` - Collaborative thinking for architectural decisions
- `mcp__zen__debug` - Systematic debugging and root cause analysis
- `mcp__zen__thinkdeep` - Multi-stage investigation for complex problems

### Handling Zen Recommendations

When user requests Zen review and you receive recommendations:

**Implement autonomously when**:

- Changes are clearly improvements (tighter type checking, better configs)
- No architectural trade-offs involved
- Changes align with project standards in CLAUDE.md

**Ask user first when**:

- Recommendations require architectural changes
- Trade-offs between different approaches exist
- Recommendations conflict with explicit project requirements

### Model Selection for Zen

- Use `gemini-2.5-pro` or `gpt-5-pro` for code review (high-stakes analysis)
- Check available models with `mcp__zen__listmodels` if needed

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

### Citation ID Integrity

**CRITICAL**: `citation_id` must NEVER be `None` or empty string (`""`).

- **Database constraint**: `citation_id TEXT UNIQUE NOT NULL` (schema.py:43)
- **Data quality**: Missing citation_id indicates a fundamental extraction/parsing error
- **Error handling**: Code MUST raise `ValueError` for missing citation_id, never use fallback to empty string
- **Formats**: `LINE-{number}` (extraction pipeline) or `S#-F#-C#-p#` (legacy Gemini parser)

**Why no fallbacks**: Empty string would violate database UNIQUE constraint on subsequent inserts, causing silent data corruption. Fail-fast on missing citation_id ensures data integrity.

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

**Purpose**: Enables development and testing without requiring production data pipeline
or network access. The fixture database is version-controlled and committed alongside
code.

**Usage**:

```bash
# Tests automatically use fixture database
uv run pytest tests/unit -v

# Specify fixture explicitly if needed
uv run pytest tests/ --db=tests/fixtures/test_database.db
```

### Test Markers

- `@pytest.mark.unit` - Fast tests (\<100ms each), no I/O
- `@pytest.mark.integration` - Tests with database/network I/O
- `@pytest.mark.slow` - Tests taking >1 second (embeddings, full operations)

## Configuration Management

Settings use `pydantic-settings` with environment variable support:

- Prefix: `QE_TAX_RAG_`
- Example: `QE_TAX_RAG_CACHE_DIR=/custom/path`
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
1. **Don't introduce unnecessary dependencies** - Prefer Python-based tools; avoid
   Node.js, Ruby, or other language ecosystems unless essential for functionality
1. **Don't weaken type checking without justification** - Both mypy and pyright should
   remain strict; only disable specific third-party library checks with documented
   rationale

## File Structure Conventions

```
src/
  qe_tax_rag/           # Runtime library (in PyPI package)
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

## Extraction Pipeline (HTML to Database)

The extraction pipeline transforms raw CRA HTML documents into a searchable database through a
multi-stage process with quality validation at each step.

### Pipeline Architecture

The extraction workflow uses a **Mixture-of-Experts** approach with dual parsers:

1. **Classic Parser** (BeautifulSoup): Fast, deterministic extraction via DOM traversal
1. **LLM Parser** (Gemini): Semantic understanding and context-aware extraction
1. **Adjudicator**: Grounded self-correction layer that resolves conflicts between parsers
1. **Builder**: Converts YAML directly to SQLite via DatabaseChunk model, generates embeddings
1. **Validator**: Smoke tests to verify database integrity

### Direct YAML-to-Database Conversion

The extraction pipeline uses a streamlined approach that eliminates intermediate transformations:

1. **ExtractedRule** (YAML) → **DatabaseChunk** (Pydantic model) → **SQLite** (FTS5 + vector)
2. No JSONL intermediate format - direct conversion via `RuleSet.to_database_chunks()`
3. Type-safe with strict Pydantic validation throughout

#### Key Features

- **Citation Format**: `LINE-{number}` (e.g., `LINE-8523`)
- **Metadata Preservation**: Includes `income_type`, extraction source, confidence, and anchor
- **Expense Classification**: Keyword-based classifier infers expense types from content
- **Supported Types**: meals, travel, vehicle, home_office, advertising, supplies, professional_fees, utilities, insurance, capital, maintenance, salaries, office_equipment, interest, bad_debts
- **Type Safety**: Pydantic models (`DatabaseChunk`, `ChunkMetadata`) replace dict-based schemas

### Usage Options

**Option 1: Full automated pipeline** (recommended)

```bash
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules.db
```

This command automatically:
1. Extracts rules from HTML → YAML
2. Converts YAML directly to SQLite (via DatabaseChunk)
3. Validates database integrity

**Option 2: Pipeline with intermediate files kept** (for debugging)

```bash
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/ \
  --output-db data/rules.db \
  --intermediate-dir output/ \
  --keep-intermediate
```

**Option 3: Manual step-by-step** (for development/testing)

```bash
# Step 1: Extract HTML → YAML
uv run extract-rules \
  cra_documents/cra_t4002e_rev24_dump/t4002-4.html \
  output/rules.yml

# Step 2: Build database directly from YAML (manifest auto-generated)
uv run python scripts/cli.py build \
  --input-file output/rules.yml \
  --output-db data/rules.db

# Step 3: Validate database integrity
uv run python scripts/cli.py validate --db-path data/rules.db
```

**Note on manifests**: The `build` command no longer requires a manifest file. When
omitted, source file metadata is automatically extracted from the YAML/JSONL input:
- For YAML: Reads `source_file` field from each `ExtractedRule`
- For JSONL: Reads `source_filename` from each `ParsedDocument`
- Creates `SourceFile` entries with placeholder URLs and empty hashes

This simplifies manual workflows while preserving backward compatibility with existing
manifests. If you have a custom manifest, use `--manifest-file path/to/manifest.json`.

### Error Handling

The pipeline uses **fail-fast** error handling with stage-specific messages:

- **Stage 1/2 (Extraction)**: HTML parsing, adjudication, YAML generation
- **Stage 2/2 (Build)**: YAML→DatabaseChunk conversion, embedding generation, database construction
- **Stage 3/2 (Validation)**: Schema verification, row counts, embedding dimensions, search tests

If a stage fails:

- Error message identifies the specific stage: `❌ Stage X/2 (Name) failed: <error>`
- Pipeline stops immediately (no cascading failures)
- Intermediate files are preserved for debugging
- Logs include full stack traces for troubleshooting

### Intermediate File Management

The pipeline uses smart cleanup:

- **Temp directory created**: Automatic cleanup on success (unless `--keep-intermediate`)
- **Custom intermediate dir**: Never deleted automatically
- **Pipeline failure**: Always preserves intermediate files for debugging
- **Success with `--keep-intermediate`**: Shows path to preserved files

### Development Tips

1. **Start with manual step-by-step** to understand each stage
1. **Use `--keep-intermediate`** when developing or debugging
1. **Check intermediate YAML** for data quality before building database
1. **Run validation** after building to catch schema/data inconsistencies
1. **Test with small HTML sets** first (1-5 files) before full processing
- Code should never have bare exceptions or exceptions that don't actually serve a purpose beside logging. We want the raw exception and stack trace to help us debug.