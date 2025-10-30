# QE Tax RAG

[![PyPI version](https://badge.fury.io/py/qe-tax-rag.svg)](https://badge.fury.io/py/qe-tax-rag)
[![Python versions](https://img.shields.io/pypi/pyversions/qe-tax-rag)](https://pypi.org/project/qe-tax-rag)
[![CI/CD Status](https://github.com/manonja/qe-tax-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/manonja/qe-tax-rag/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚠️ IMPORTANT: NOT FINANCIAL OR TAX ADVICE

**This software is provided for informational purposes only and is not a substitute for
professional financial or tax advice.** Always consult with a qualified tax professional
or accountant before making financial decisions. CRA rules are complex, change
frequently, and require professional interpretation. The developers assume no liability
for any actions taken based on the use of this tool.

## What is this?

A Python library for semantic search over Canadian Revenue Agency (CRA) business expense
rules. Built for ML engineers building expense classification agents and developers who
need programmatic access to CRA expense rule information.

## Project Status

**✅ Epic 0 Complete: Make Search Work**

- **Production Database**: 63 CRA expense rules from T4002 guide (t4002-5.html)
- **Search Validated**: 10/10 test queries successful (100% success rate)
- **Lineage Tracking**: 100% coverage with source traceability
- **RAG Examples**: Full integration examples with Gemini, OpenAI, Anthropic
- **Data Scope**: Current database covers single HTML source (future: full T4002 guide)
- **GitHub Release**:
  [data-v2025.10.23](https://github.com/manonja/quickExpense-rag/releases/tag/data-v2025.10.23)

## Key Features

- 🔍 **Hybrid Search**: Combines keyword (FTS5) + semantic search (vector embeddings)
  using BGE-small-en-v1.5
- 🎯 **Smart Filtering**: Filter by province, business type, and expense categories
- 📚 **Authoritative Citations**: Returns CRA source URLs with unique citation IDs for
  verification
- 🔗 **Many-to-Many Expense Types**: Rules can match multiple expense categories
  simultaneously
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
# Note: Current database contains federal rules (no province-specific data)
results = qe.search(
    query="restaurant meals for client meetings",
    expense_types=["meals", "travel"],
    top_k=5
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

**💡 Want to build a tax Q&A chatbot?** See the
[RAG Integration Examples](#rag-integration-examples) section below for complete
examples using OpenAI, Anthropic, or Gemini.

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

1. **Metadata Filtering**: SQL WHERE clause filters by
   province/business_type/expense_type
1. **FTS5 Keyword Search**: Exact term matching on filtered candidates using SQLite's
   full-text search
1. **Vector Semantic Search**: BGE-small-en-v1.5 embeddings (384-dim) with cosine
   similarity via sqlite-vec
1. **RRF Fusion**: Reciprocal Rank Fusion merges keyword and semantic rankings for
   optimal results

### Data Distribution

- **Code**: Distributed via PyPI (`pip install qe-tax-rag`)
- **Database**: Downloaded from
  [GitHub Releases](https://github.com/manonja/quickExpense-rag/releases) on first
  `init()` call (~1.7 MB)
- **Current Release**:
  [data-v2025.10.28](https://github.com/manonja/quickExpense-rag/releases/tag/data-v2025.10.28)
  - **Source**: Full T4002 PDF (pages 1-113) from CRA T4002 Business and Professional
    Income Guide
  - **Coverage**: 662 searchable content items (RULE, DEFINITION, PRINCIPLE, TABLE)
  - **Lineage**: 100% extraction coverage with timestamps and source tracking
  - **Improvements**: Dedicated sections for CCA, farm losses, capital gains
  - **Note**: Future releases will expand to additional CRA documents and HTML chapters
- **Versioning**: Schema version + data version stored in database metadata
- **Integrity**: SHA256 checksums verified automatically on download
- **Updates**: Database versions released independently from code versions

**Current Limitations:**

- Database contains federal CRA rules only (no province or business-type specific
  metadata)
- Filtering by `province` or `business_type` parameters will return 0 results
- Use `expense_types` filtering for categorizing rules

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
- `business_type`: Filter by business type (`"sole_proprietorship"`, `"corporation"`,
  `"partnership"`)
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

## RAG Integration Examples

Build tax Q&A chatbots using Retrieval-Augmented Generation (RAG) with QE Tax RAG as the
knowledge base.

### What's Included

The `examples/` directory contains complete, working examples demonstrating how to
integrate QE Tax RAG with Large Language Models (LLMs):

- **[basic_rag.py](examples/basic_rag.py)** - Standalone Python script showing the
  complete RAG workflow
- **[basic_rag.ipynb](examples/basic_rag.ipynb)** - Jupyter notebook for interactive
  exploration *(coming soon)*
- **[examples/README.md](examples/README.md)** - Detailed setup instructions and
  troubleshooting

### What You'll Learn

The examples demonstrate:

1. **Environment Setup** - Loading API keys and initializing the database
1. **Basic Search** - Querying CRA rules without LLM integration
1. **RAG Pipeline** - Building context and generating AI responses
1. **Output Formatting** - Displaying answers with proper citations
1. **Advanced Patterns** - Multi-turn conversations, caching, error handling

### Quick Example

```python
import qe_tax_rag as qe
import os
from openai import OpenAI  # or anthropic, google-generativeai

# Initialize database
qe.init()

# Search CRA rules
results = qe.search(
    query="Can I deduct restaurant meals for client meetings?",
    province="BC",
    expense_types=["meals"],
    top_k=5
)

# Build context from search results
context = "\n\n".join([
    f"[{i}] {r.content} (Citation: {r.citation_id})"
    for i, r in enumerate(results, 1)
])

# Call LLM with context
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a tax information assistant. Use ONLY the provided CRA excerpts. Include citations. Remind users to consult a tax professional."},
        {"role": "user", "content": f"Question: {query}\n\nCRA Excerpts:\n{context}"}
    ]
)

print(response.choices[0].message.content)
```

### Supported LLM Providers

The examples include code for:

- **OpenAI** (GPT-4, GPT-3.5-turbo)
- **Anthropic** (Claude 3.5 Sonnet, Claude 3 Opus)
- **Google** (Gemini 2.0 Flash, Gemini Pro)

You only need **one** API key to run the examples.

### Getting Started

1. Install optional dependencies:

   ```bash
   pip install -r examples/requirements.txt
   ```

1. Set up your API key in `.env`:

   ```bash
   cp .env.example .env
   # Edit .env and add your API key:
   # OPENAI_API_KEY=sk-...
   # or ANTHROPIC_API_KEY=sk-ant-...
   # or GEMINI_API_KEY=...
   ```

1. Run the example:

   ```bash
   python examples/basic_rag.py
   ```

See [examples/README.md](examples/README.md) for detailed instructions, troubleshooting,
and advanced patterns.

### Important Notes

- **Legal Disclaimers**: All examples include prominent disclaimers reminding users this
  is NOT professional tax advice
- **Citation Tracking**: Examples demonstrate proper citation of CRA sources in LLM
  responses
- **Error Handling**: Includes handling for missing API keys, rate limits, and network
  errors
- **Privacy**: Search queries and CRA data never leave your machine (only LLM queries
  use external APIs)

## Integration with Multi-Agent Systems

QE Tax RAG is designed for seamless integration into production multi-agent workflows,
particularly AutoGen-based systems for expense processing and tax compliance.

### Use Case: quickExpense Integration

The library serves as the knowledge base for the **quickExpense** application's
CRArulesAgent, providing retrieval-grounded compliance analysis:

**Before RAG Integration:**

- CRArulesAgent relies purely on LLM reasoning → risk of hallucinations
- No source citations or audit trail
- Rules limited to LLM's training data cutoff

**After RAG Integration:**

- Every tax decision backed by authoritative CRA rules from the database
- Citations (e.g., `LINE-8523`) link to official CRA publications
- Hybrid approach: Retrieval (factual) + LLM (interpretation)
- Database updates independently from application code

### Integration Guide

For detailed step-by-step instructions on integrating qe-tax-rag into multi-agent
workflows:

**📖 [Integration Guide for quickExpense](docs/INTEGRATION_QUICKEXPENSE.md)**

The guide covers:

- Architecture & data flow diagrams
- 15-step integration checklist with acceptance criteria
- API usage patterns for agent workflows
- Testing strategies (unit, integration, E2E)
- Deployment considerations (Docker, Kubernetes, FastAPI lifespan)
- Performance optimization and caching
- Troubleshooting common integration issues

### Quick Integration Example

```python
# In your AutoGen CRArulesAgent
import qe_tax_rag as qe

class CRArulesAgent:
    def __init__(self):
        qe.init()  # Initialize RAG database
        self.llm = TogetherAI(model="llama-3.1-70b")

    def analyze_expense(self, expense_data: dict) -> dict:
        # Step 1: Retrieve relevant CRA rules
        query = f"{expense_data['category']} {expense_data['vendor']} deduction"
        rules = qe.search(query, expense_types=[expense_data['category']], top_k=5)

        # Step 2: Format context for LLM
        context = "\n\n".join([
            f"[{r.citation_id}] {r.content}\nSource: {r.source_url}"
            for r in rules
        ])

        # Step 3: LLM reasoning with grounded context
        prompt = f"Analyze expense: {expense_data}\n\nCRA Rules:\n{context}"
        response = self.llm.generate(prompt)

        return parse_json(response)  # Returns citations + deductible percentage
```

### Production Deployment

For FastAPI applications, initialize once on startup using lifespan events:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import qe_tax_rag as qe

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize RAG database
    qe.init(path=os.environ.get("QE_TAX_RAG_DB_PATH", "/data/qe_tax_rag"))
    print(f"✅ qe-tax-rag initialized: {qe.get_version()}")
    yield
    # Shutdown cleanup

app = FastAPI(lifespan=lifespan)
```

See the [Integration Guide](docs/INTEGRATION_QUICKEXPENSE.md) for complete deployment
patterns including Docker, Kubernetes, and multi-instance configurations.

## Troubleshooting

### Database Download Issues

**Problem**: "Failed to download database from GitHub Releases"

**Solutions**:

- Check internet connection and GitHub accessibility
- Verify firewall isn't blocking `github.com`
- Try manual download from
  [GitHub Releases](https://github.com/manonja/quickExpense-rag/releases)
- Place downloaded `cra_rules.db` in cache dir: `~/.cache/qe_tax_rag/`

### Version Mismatch

**Problem**: "DataVersionMismatchError: Database version incompatible"

**Solutions**:

- Update library: `pip install --upgrade qe-tax-rag`
- Force database refresh: `qe.init(force_update=True)`
- Check release notes for breaking changes

### SHA256 Verification Failure

**Problem**: "Database SHA256 checksum mismatch"

**Solutions**:

- Delete corrupted cache: `rm -rf ~/.cache/qe_tax_rag/`
- Re-run `qe.init()` to download fresh database
- Report issue if problem persists (possible release corruption)

### Empty Search Results

**Problem**: Query returns no results

**Solutions**:

- Try broader search terms: "meals" instead of "restaurant client dinners"
- Remove filters: Don't specify `province` or `expense_types` if unsure
- Check query spelling and use CRA terminology
- Use semantic search by avoiding overly specific keywords

### LLM API Errors

**Problem**: "Rate limit exceeded" or "Invalid API key" when running RAG examples

**Solutions**:

- **Rate limits**: Wait and retry, or add exponential backoff (see examples)
- **Invalid key**: Verify API key is correct and active
- **Billing**: Ensure API account has credits and billing enabled
- **Try alternative**: Examples support OpenAI, Anthropic, and Gemini

For more troubleshooting, see [examples/README.md](examples/README.md).

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
1. Create a feature branch
1. Run tests and quality checks
1. Submit a pull request

See [CLAUDE.md](CLAUDE.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [sentence-transformers](https://www.sbert.net/) for embeddings
- Powered by [sqlite-vec](https://github.com/asg017/sqlite-vec) for vector search
- Data sourced from
  [Canada Revenue Agency](https://www.canada.ca/en/revenue-agency.html)

______________________________________________________________________

**Remember**: This is informational content only. Always consult a qualified tax
professional for advice specific to your situation.
