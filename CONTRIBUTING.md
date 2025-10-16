# Contributing to QuickExpense RAG

Thank you for your interest in contributing! This guide covers development workflow, testing, and code quality standards.

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Initial Setup

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/quickexpense-rag.git
cd quickexpense-rag

# Install dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

## Testing

### Test Organization

Tests are organized by speed and purpose:

- **Unit tests** (`@pytest.mark.unit`): Fast tests (<100ms each), no I/O
- **Integration tests** (`@pytest.mark.integration`): Tests with database/network I/O
- **Slow tests** (`@pytest.mark.slow`): Tests taking >1 second (embeddings, full operations)

### Running Tests

#### Fast Unit Tests Only

```bash
# Fastest - unit tests only (~2-5 seconds)
uv run pytest tests/unit -v -m unit
```

#### Integration Tests

```bash
# Integration tests with I/O (~10-20 seconds)
uv run pytest tests/integration -v -m integration
```

#### All Tests Except Slow Performance Tests

```bash
# Default CI mode - fast + integration (~30-40 seconds)
uv run pytest -m "not slow" -v
```

#### Full Test Suite

```bash
# Everything including performance tests (~60-90 seconds)
uv run pytest tests/ -v
```

### Coverage Reporting

#### Quick Coverage Check

```bash
# Terminal report with coverage percentage
uv run pytest --cov=src/quickexpense_rag --cov-report=term
```

#### HTML Coverage Report

```bash
# Generate browsable HTML report in htmlcov/
uv run pytest --cov=src/quickexpense_rag --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

#### Coverage for Specific Module

```bash
# Check coverage for a single module
uv run pytest --cov=src/quickexpense_rag/api --cov-report=term -v

# Check coverage for search module
uv run pytest --cov=src/quickexpense_rag/search --cov-report=term -v
```

#### Enforce Coverage Threshold

```bash
# Fail if coverage below 85%
uv run pytest --cov=src/quickexpense_rag --cov-fail-under=85
```

### Coverage Requirements

The project enforces minimum coverage thresholds to ensure code quality:

| Module | Minimum Coverage | Current Status |
|--------|-----------------|----------------|
| **Overall** | ≥85% | ✅ 94% |
| `api.py` | ≥95% | ✅ 100% |
| `search/hybrid.py` | ≥95% | ✅ 97% |
| `data/manager.py` | ≥90% | ✅ 99% |

**Why these targets?**

- **api.py (≥95%)**: User-facing API - critical for developer experience
- **search/hybrid.py (≥95%)**: Core search algorithm - must be thoroughly tested
- **data/manager.py (≥90%)**: Data download/cache - handles external dependencies
- **Overall (≥85%)**: Ensures comprehensive test suite across all modules

### Test Markers Reference

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only slow tests (performance benchmarks)
pytest -m slow

# Run everything except slow tests (default for CI)
pytest -m "not slow"

# Combine markers (unit OR integration, but not slow)
pytest -m "(unit or integration) and not slow"
```

### Writing Tests

#### Test File Naming

- Unit tests: `tests/unit/test_<module>.py`
- Integration tests: `tests/integration/test_<feature>.py`

#### Test Markers

Always mark your tests appropriately:

```python
import pytest

@pytest.mark.unit
def test_fast_logic():
    """Unit test - no I/O, <100ms."""
    assert add(2, 2) == 4

@pytest.mark.integration
def test_database_query(fixture_db):
    """Integration test - uses database."""
    results = query_database(fixture_db)
    assert len(results) > 0

@pytest.mark.slow
def test_performance_benchmark():
    """Slow test - performance measurement."""
    # Expensive operation
    pass
```

#### Using Fixtures

Common fixtures from `tests/conftest.py`:

```python
def test_with_fixture_db(fixture_db):
    """Use committed test database (read-only)."""
    # fixture_db is Path to tests/fixtures/test_database.db
    pass

def test_with_temp_db(temp_db):
    """Use temporary writable database."""
    # temp_db is Path to fresh temporary database
    # Created per-test, automatically cleaned up
    pass

def test_with_mock_encoder(mock_encoder):
    """Use mocked BGEEncoder for fast tests."""
    # mock_encoder returns zero embeddings with correct shape
    embedding = mock_encoder.embed_query("test")
    assert embedding.shape == (384,)
```

## Code Quality

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```bash
# Run all hooks on all files
uv run pre-commit run --all-files

# Run specific hook
uv run pre-commit run ruff --all-files
uv run pre-commit run mypy --all-files
```

**Hooks include:**

- **ruff**: Linting with auto-fix
- **ruff-format**: Code formatting
- **mypy**: Type checking (strict mode)
- **pyright**: Additional type checking
- **mdformat**: Markdown formatting

### Manual Quality Checks

```bash
# Format code
uvx ruff format

# Lint and auto-fix
uvx ruff check --fix

# Type check
uv run mypy src/

# All quality checks
uv run pre-commit run --all-files
```

## Continuous Integration

### CI Workflow

GitHub Actions runs on every push and PR:

1. **Linting & Formatting** (pre-commit.yml)
   - Ruff linting
   - Ruff formatting
   - Mypy + Pyright type checking
   - Markdown formatting

2. **Tests** (test.yml)
   - Runs on Ubuntu 24.04 and macOS
   - Python 3.12
   - Full test suite with coverage
   - **Coverage threshold enforced**: ≥85% required
   - Uploads coverage artifacts

3. **Lock File Check** (lock-check.yml)
   - Ensures uv.lock is up-to-date

### Making CI Pass

Before pushing:

```bash
# 1. Run pre-commit hooks
uv run pre-commit run --all-files

# 2. Run tests with coverage threshold
uv run pytest -m "not slow" --cov=src/quickexpense_rag --cov-fail-under=85

# 3. Verify everything passes
echo "✅ Ready to push!"
```

## Commit Conventions

Use conventional commit format:

```
<type>: <short summary (50 chars max)>

<detailed description explaining WHY, not WHAT>
- Use bullet points for multiple changes
- Focus on motivation and context

Rationale:
- Explain technical decisions
- Document trade-offs

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `test`: Add or update tests
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `build`: Build system or dependencies
- `ci`: CI/CD changes
- `perf`: Performance improvements
- `style`: Code formatting (no logic changes)
- `chore`: Maintenance tasks

## Project Structure

```
src/quickexpense_rag/       # Runtime library (distributed via PyPI)
  api.py                    # Public API: init(), search(), get_version()
  exceptions.py             # Custom exception hierarchy
  settings.py               # Configuration (pydantic-settings)
  data/                     # Data layer
    schema.py               # Database schema
    manager.py              # Download, cache, verify
    builder.py              # Index builder (indexing pipeline)
    validator.py            # Validation logic
  embeddings/               # Embedding service
    encoder.py              # BGEEncoder singleton
  search/                   # Search engine
    hybrid.py               # Hybrid search implementation
    models.py               # Pydantic models
    enums.py                # Province, BusinessType

tests/                      # Test suite
  conftest.py               # Shared fixtures
  fixtures/                 # Test data
    test_database.db        # Hand-crafted test DB (committed)
  unit/                     # Fast unit tests
  integration/              # Integration tests

scripts/                    # Maintainer tools (not in package)
  cli.py                    # Indexing pipeline CLI
  parser/                   # Document parsing
  preprocessor/             # Text extraction
  indexer/                  # Database building

docs/                       # Documentation
```

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/quickexpense-rag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/quickexpense-rag/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
