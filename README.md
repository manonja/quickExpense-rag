# QuickExpense RAG

Semantic search over Canadian Revenue Agency (CRA) business expense rules.

## ⚠️ LEGAL DISCLAIMER

**THIS IS NOT TAX ADVICE.** This library provides informational content only and does not constitute professional tax advice. CRA rules are complex, change frequently, and require professional interpretation. Always consult a qualified tax professional or accountant.

## What is this?

A Python library for semantic search over Canadian Revenue Agency (CRA) business expense rules. Built for ML engineers building expense classification agents.

## Features

- 🔍 Hybrid search: keywords (FTS5) + semantics (vector)
- 🎯 Filter by province, business type, expense category
- 📚 Returns authoritative CRA citations with source URLs
- 🔒 No API keys or network calls after setup
- 📦 Lightweight package (<5MB)

## Installation

```bash
pip install quickexpense-rag
```

## Quick Start

```python
import quickexpense_rag as qer

# Initialize (downloads database on first run)
qer.init()

# Search with filters
results = qer.search(
    query="restaurant expense while traveling for training",
    province="BC",
    business_type="sole_proprietorship"
)

# Results include citations and disclaimers
for result in results:
    print(f"Citation: {result.citation_id}")
    print(f"Content: {result.content}")
    print(f"Source: {result.source_url}")
    print(f"Score: {result.score}")
    print(result.disclaimer)
```

## Development

### Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/manonja/quickExpense-rag.git
cd quickExpense-rag
uv sync
uv run pre-commit install
```

### Commands

```bash
# Run tests
uv run pytest tests/unit -v -m unit

# Lint
uvx ruff check src/

# Format
uvx ruff format src/

# Type check
uv run mypy src/

# All checks (pre-commit)
uv run pre-commit run --all-files
```

## Project Status

🚧 **Alpha** - TICKET 1 (Foundation) complete. Search functionality coming in TICKET 7-8.

See [plan.md](plan.md) for the full implementation roadmap.

## License

MIT

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed development guidance and architecture.
