# QE Tax RAG

[![PyPI version](https://badge.fury.io/py/qe-tax-rag.svg)](https://badge.fury.io/py/qe-tax-rag)
[![Python versions](https://img.shields.io/pypi/pyversions/qe-tax-rag)](https://pypi.org/project/qe-tax-rag)
[![CI/CD Status](https://github.com/manonja/qe-tax-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/manonja/qe-tax-rag/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚠️ IMPORTANT: NOT FINANCIAL OR TAX ADVICE

**This software is provided for informational purposes only and is not a substitute for professional financial or tax advice.** Always consult with a qualified tax professional or accountant before making financial decisions. CRA rules are complex, change frequently, and require professional interpretation. The developers assume no liability for any actions taken based on the use of this tool.

## What is this?

A Python library for semantic search over Canadian Revenue Agency (CRA) business expense rules. Built for ML engineers building expense classification agents and developers who need programmatic access to CRA expense rule information.

## Key Features

- 🔍 **Hybrid Search**: Combines keyword (FTS5) + semantic search (vector embeddings) using BGE-small-en-v1.5
- 🎯 **Smart Filtering**: Filter by province, business type, and expense categories
- 📚 **Authoritative Citations**: Returns CRA source URLs with unique citation IDs for verification
- 🔗 **Many-to-Many Expense Types**: Rules can match multiple expense categories simultaneously
- 🔒 **Privacy-First**: No API keys or network calls after initial database download
- 📦 **Lightweight**: Package < 5MB (database downloaded separately from GitHub Releases)
- ⚡ **Fast**: Local SQLite database with FTS5 and vector search (sub-250ms queries)
- 🛡️ **Type-Safe**: Full type hints with mypy/pyright support

## Installation

```bash
pip install qe-tax-rag
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install qe-tax-rag
```

## Quick Start

```python
import qe_tax_rag as qe

# Initialize (downloads database on first run)
qe.init()

# Search for expense rules
results = qe.search(
    query="restaurant expense while traveling for training",
    province="BC",
    business_type="sole_proprietorship",
    expense_types=["meals", "travel"]
)

# Access results
for result in results:
    print(f"Citation: {result.citation_id}")
    print(f"Content: {result.content}")
    print(f"Source: {result.source_url}")
    print(f"Expense Types: {result.expense_types}")
    print(f"⚠️ {result.disclaimer}")
    print("---")
```

### Example Output

```python
Citation: S3-F2-C1-p1.25
Content: A taxpayer's capital cost of a depreciable property...
Source: https://www.canada.ca/en/revenue-agency/services/tax/...
Expense Types: ['vehicle', 'capital_cost_allowance']
⚠️ INFORMATIONAL ONLY - NOT TAX ADVICE
This information is for educational purposes only and does not constitute tax advice...
```

## How It Works

QE Tax RAG uses a multi-stage hybrid search approach:

1. **Metadata Filtering**: SQL WHERE clause filters by province/business_type/expense_type
2. **FTS5 Keyword Search**: Exact term matching on filtered candidates using SQLite's full-text search
3. **Vector Semantic Search**: BGE-small-en-v1.5 embeddings (384-dim) with cosine similarity via sqlite-vec
4. **RRF Fusion**: Reciprocal Rank Fusion merges keyword and semantic rankings for optimal results

### Data Distribution

- **Code**: Distributed via PyPI (`pip install qe-tax-rag`)
- **Database**: Downloaded from GitHub Releases on first `init()` call (~10-50MB)
- **Versioning**: Schema version + data version stored in database metadata
- **Integrity**: SHA256 checksums verified automatically on download

### Architecture

```
User Query
    ↓
[Metadata Filter] → Province/Business/Expense Type
    ↓
[Keyword Search] → FTS5 exact term matching
    ↓
[Semantic Search] → Vector embeddings + cosine similarity
    ↓
[RRF Fusion] → Merge rankings
    ↓
Ranked Results with Citations
```

## API Reference

### `init(force_update: bool = False) -> None`

Initialize the library and download the database if needed.

**Parameters:**
- `force_update`: Force re-download even if cached database exists

**Raises:**
- `NetworkError`: If download fails and no cached database available
- `DataVersionMismatchError`: If database version incompatible with library version

**Example:**
```python
import qe_tax_rag as qe

# First-time initialization (downloads database)
qe.init()

# Force update to latest database
qe.init(force_update=True)
```

### `search(query: str, province: str | None = None, business_type: str | None = None, expense_types: list[str] | None = None, top_k: int = 5) -> list[SearchResult]`

Search CRA expense rules with optional filtering.

**Parameters:**
- `query`: Natural language expense description (min 3 characters)
- `province`: Filter by province (`"BC"`, `"AB"`, `"ON"`, `"QC"`, etc.)
- `business_type`: Filter by business type (`"sole_proprietorship"`, `"corporation"`, `"partnership"`)
- `expense_types`: Filter by expense categories (matches rules with ANY of these types)
- `top_k`: Number of results to return (1-50, default: 5)

**Returns:**
- List of `SearchResult` objects with citations and disclaimers

**Raises:**
- `DatabaseNotInitializedError`: If `init()` not called first
- `ValidationError`: If invalid parameters provided

**Example:**
```python
# Basic search
results = qe.search("home office expenses")

# Filtered search
results = qe.search(
    query="vehicle mileage deduction",
    province="ON",
    business_type="sole_proprietorship",
    expense_types=["vehicle", "travel"],
    top_k=10
)
```

### `get_version() -> dict[str, str]`

Get library and database version information.

**Returns:**
- Dictionary with `library_version`, `data_version`, and `schema_version`

**Example:**
```python
version_info = qe.get_version()
print(version_info)
# {'library_version': '0.1.0', 'data_version': '2025.01', 'schema_version': '1.0'}
```

### Data Models

#### `SearchResult`

```python
class SearchResult:
    content: str                    # Rule text content
    citation_id: str                # Unique citation (e.g., "S3-F2-C1-p1.25")
    source_url: str                 # CRA source URL
    score: float                    # Relevance score (0.0-1.0)
    province: Province | None       # Applicable province
    business_type: BusinessType | None  # Applicable business type
    expense_types: list[str]        # Applicable expense categories
    retrieved_at: datetime          # When data was indexed
    disclaimer: str                 # Legal disclaimer (computed property)
```

#### `Province` Enum

`BC`, `AB`, `SK`, `MB`, `ON`, `QC`, `NB`, `NS`, `PE`, `NL`, `YT`, `NT`, `NU`

#### `BusinessType` Enum

`sole_proprietorship`, `corporation`, `partnership`

## Configuration

QE Tax RAG uses environment variables for configuration:

```bash
# Optional configuration
export QE_TAX_RAG_CACHE_DIR="/custom/cache/path"
export QE_TAX_RAG_EMBEDDING_DEVICE="cuda"  # or "cpu" (default)
export QE_TAX_RAG_DEFAULT_TOP_K=10
```

See [CLAUDE.md](CLAUDE.md) for all configuration options.

## Development

### Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone repository
git clone https://github.com/manonja/qe-tax-rag
cd qe-tax-rag

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Testing

```bash
# Run unit tests
uv run pytest tests/unit -v

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/qe_tax_rag --cov-report=html
```

### Quality Checks

```bash
# Format code
uvx ruff format

# Lint
uvx ruff check

# Type check
uv run mypy src/
uv run pyright
```

## Project Status

✅ **Beta** - v0.1.0 ready for release. All core features implemented:
- Hybrid search (FTS5 + vector)
- Many-to-many expense type support
- Complete test suite (23/23 tests passing)
- Full type safety (mypy + pyright strict mode)

See [plan.md](plan.md) for the full implementation roadmap.

## Roadmap

- [ ] Support for French-language CRA documents
- [ ] Additional provinces and territories coverage
- [ ] Extended expense categories
- [ ] Web API server mode
- [ ] ChatGPT/Claude plugin integration

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Run tests and quality checks
4. Submit a pull request

See [CLAUDE.md](CLAUDE.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [sentence-transformers](https://www.sbert.net/) for embeddings
- Powered by [sqlite-vec](https://github.com/asg017/sqlite-vec) for vector search
- Data sourced from [Canada Revenue Agency](https://www.canada.ca/en/revenue-agency.html)

---

**Remember**: This is informational content only. Always consult a qualified tax professional for advice specific to your situation.
