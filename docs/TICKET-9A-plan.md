# TICKET 9A: Document Pre-processor - Implementation Plan

## Overview

Implement a document preprocessing pipeline to convert manually downloaded CRA HTML/PDF files into clean text for downstream LLM parsing (Gemini Flash in TICKET 9B).

**Approach**: 80/20 principle - focus on core functionality, avoid over-engineering, pragmatic error handling.

---

## Phase 1: Directory Structure & Dependencies ⏱️ 15 min

### 1.1 Create directory structure

```
data/
  raw/          # Manual downloads (HTML/PDF)
  preprocessed/ # Clean text output
scripts/
  preprocessor/
    __init__.py
    text_extractor.py
    models.py      # Pydantic models for manifest
tests/
  unit/
    test_text_extractor.py
  integration/
    test_preprocessor_integration.py
  fixtures/
    preprocessor/
      sample.html   # Small CRA HTML sample
      sample.pdf    # Small CRA PDF sample
docs/
  maintainer_guide.md
```

### 1.2 Add dependencies

Already present in pyproject.toml under `[project.optional-dependencies.indexing]`:

- ✅ `pdfplumber>=0.10`
- Need to add: `beautifulsoup4>=4.12` and `lxml>=5.0` (for robust HTML parsing)

**Decision**: Add BeautifulSoup4 + lxml to `indexing` optional dependencies (not runtime dependencies).

---

## Phase 2: Pydantic Models for Manifest ⏱️ 20 min

### 2.1 Create `scripts/preprocessor/models.py`

```python
"""Pydantic models for document preprocessing manifest."""
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

class DownloadMetadata(BaseModel):
    """Metadata for a single downloaded document."""
    filename: str = Field(..., description="File name (e.g., S3-F2-C1.html)")
    source_url: str = Field(..., description="Original CRA URL")
    downloaded_at: datetime = Field(..., description="Download timestamp")
    sha256: str = Field(..., pattern=r"^[a-f0-9]{64}$", description="SHA256 hash")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Ensure filename matches expected pattern."""
        if not v.endswith((".html", ".pdf")):
            raise ValueError("Filename must end with .html or .pdf")
        return v

class PreprocessManifest(BaseModel):
    """Manifest of all downloaded documents."""
    documents: list[DownloadMetadata]
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Rationale**: Type-safe manifest validation, SHA256 pattern validation, extensible for future metadata.

---

## Phase 3: Core Text Extraction ⏱️ 2 hours

### 3.1 Create `scripts/preprocessor/text_extractor.py`

**Key Architectural Decisions:**

#### **HTML Parsing Strategy** (80/20 approach)

- **Use CSS selector heuristics** to find main content: `<main>`, `<article>`, `div.content`, `div#content`
- **Fallback**: If selectors fail, extract from `<body>` and filter headers/footers heuristically
- **Avoid**: Complex ML-based content extraction (YAGNI)

#### **PDF Multi-Column Handling**

- **Use pdfplumber's default layout** (works for 80% of cases)
- **Don't** implement complex multi-column detection algorithms initially
- **Accept**: Some text order issues as acceptable trade-off (LLM can handle minor disorder)

#### **Error Handling**

- **Log warnings** for extraction issues but **continue processing**
- **Fail fast** only for missing files or unreadable formats
- **Partial content** is better than no content

#### **Text Cleaning** (minimal preprocessing)

- Normalize whitespace (multiple newlines → max 2)
- Strip leading/trailing whitespace
- Preserve Unicode (no aggressive normalization)
- **Don't**: Remove special characters, lowercase, stemming (LLM handles this)

### 3.2 Implementation Outline

```python
"""Text extraction from HTML and PDF files."""
import hashlib
from pathlib import Path
from typing import Literal
import logging

from bs4 import BeautifulSoup
import pdfplumber

logger = logging.getLogger(__name__)

class TextExtractor:
    """Extract clean text from HTML and PDF documents."""

    def extract_from_html(self, html_path: Path) -> str:
        """Extract clean text from HTML using BeautifulSoup.

        Strategy:
        1. Try to find main content area using CSS selectors
        2. Fallback to <body> if selectors fail
        3. Remove script/style tags
        4. Extract text preserving structure

        Args:
            html_path: Path to HTML file

        Returns:
            Clean text with preserved structure

        Raises:
            FileNotFoundError: If file doesn't exist
            ParsingError: If HTML is unparseable
        """
        # Implementation here

    def extract_from_pdf(self, pdf_path: Path) -> str:
        """Extract clean text from PDF using pdfplumber.

        Strategy:
        1. Iterate pages in order
        2. Use pdfplumber's default layout extraction
        3. Join pages with newlines
        4. Accept minor ordering issues in multi-column layouts

        Args:
            pdf_path: Path to PDF file

        Returns:
            Clean text preserving reading order

        Raises:
            FileNotFoundError: If file doesn't exist
            ParsingError: If PDF is unparseable
        """
        # Implementation here

    def preprocess_file(
        self,
        input_path: Path,
        output_path: Path,
        *,
        compute_hash: bool = True
    ) -> str | None:
        """Auto-detect format and convert to clean text.

        Args:
            input_path: Path to HTML or PDF file
            output_path: Path for output .txt file
            compute_hash: Whether to compute SHA256 hash

        Returns:
            SHA256 hash if compute_hash=True, else None

        Raises:
            ValueError: If file format not supported
            ParsingError: If extraction fails
        """
        # Auto-detect, extract, save, optionally hash

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        # Standard SHA256 implementation

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize whitespace (max 2 consecutive newlines)."""
        # Regex-based normalization
```

**Key Points**:

- Modern Python 3.12 type hints (`str | None`)
- Keyword-only argument for `compute_hash` (clarity)
- Static method for SHA256 (reusable, no state needed)
- Comprehensive docstrings with Args/Returns/Raises

---

## Phase 4: Maintainer Documentation ⏱️ 30 min

### 4.1 Create `docs/maintainer_guide.md`

**Content Structure**:

1. **Manual Download Process** (step-by-step)
   - Target URL: https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios.html
   - Filter criteria (Series 1, 3, 4; expense-related only)
   - Naming convention (S3-F2-C1.html, S3-F2-C1.pdf)
   - Save to `data/raw/`

2. **Manifest Creation**
   - Manual vs automated manifest generation
   - JSON schema with example
   - SHA256 computation: `shasum -a 256 file.html`

3. **Preprocessing Workflow**
   - Command: `uv run python scripts/cli.py preprocess`
   - Expected output in `data/preprocessed/`
   - Validation steps

**80/20 Decision**: Document manual process only; don't build automated scraper (per plan.md rationale).

---

## Phase 5: Testing Strategy ⏱️ 2 hours

### 5.1 Unit Tests (`tests/unit/test_text_extractor.py`)

**Test Coverage** (aiming for 80/20):

```python
import pytest
from scripts.preprocessor.text_extractor import TextExtractor

class TestHTMLExtraction:
    """Test HTML text extraction."""

    def test_extract_from_html_with_main_tag(self):
        """HTML with <main> tag extracts correctly."""

    def test_extract_from_html_with_article_tag(self):
        """HTML with <article> tag extracts correctly."""

    def test_extract_from_html_removes_scripts(self):
        """Script and style tags are removed."""

    def test_extract_from_html_preserves_structure(self):
        """Paragraph breaks are preserved."""

    def test_extract_from_html_missing_file_raises(self):
        """Missing file raises FileNotFoundError."""

class TestPDFExtraction:
    """Test PDF text extraction."""

    def test_extract_from_pdf_single_page(self):
        """Single-page PDF extracts correctly."""

    def test_extract_from_pdf_multi_page(self):
        """Multi-page PDF joins pages with newlines."""

    def test_extract_from_pdf_missing_file_raises(self):
        """Missing file raises FileNotFoundError."""

class TestPreprocessFile:
    """Test end-to-end preprocessing."""

    def test_preprocess_html_file(self, tmp_path):
        """HTML file preprocessed to .txt."""

    def test_preprocess_pdf_file(self, tmp_path):
        """PDF file preprocessed to .txt."""

    def test_preprocess_computes_sha256(self, tmp_path):
        """SHA256 hash computed when requested."""

    def test_preprocess_unsupported_format_raises(self, tmp_path):
        """Unsupported format raises ValueError."""
```

**80/20**: Focus on happy paths + critical error cases. Skip edge cases like corrupted PDFs (handle in integration tests).

### 5.2 Integration Test (`tests/integration/test_preprocessor_integration.py`)

```python
class TestPreprocessorIntegration:
    """Integration test with real CRA document samples."""

    def test_preprocess_real_html_document(self):
        """Preprocess sample CRA HTML document."""
        # Use tests/fixtures/preprocessor/sample.html
        # Verify output is clean, parseable text
        # Verify structure preserved

    def test_preprocess_real_pdf_document(self):
        """Preprocess sample CRA PDF document."""
        # Use tests/fixtures/preprocessor/sample.pdf
        # Verify multi-page handling
        # Accept minor text ordering issues
```

**80/20**: Test with 1 real HTML + 1 real PDF (download small samples from CRA site).

### 5.3 Test Fixtures

**Create minimal test fixtures**:

- `tests/fixtures/preprocessor/sample.html` - Small CRA HTML excerpt (1-2 sections)
- `tests/fixtures/preprocessor/sample.pdf` - Small CRA PDF (1-2 pages)

**Source**: Download actual CRA documents, trim to minimal size (reduce repo bloat).

---

## Phase 6: SHA256 Hash Strategy ⏱️ 15 min

**Decision**: Compute SHA256 **during preprocessing** (not during manual download documentation).

**Rationale**:

- Maintainer documents download process manually
- Preprocessing script auto-computes hashes
- Hashes written to `data/raw/manifest.json` by preprocessing CLI
- Single source of truth

**Workflow**:

1. Maintainer downloads files to `data/raw/`
2. Preprocessing script reads `data/raw/`, computes hashes, creates manifest
3. Manifest stored at `data/raw/manifest.json`

---

## Phase 7: CLI Integration (Preview for TICKET 9D) ⏱️ 30 min

**Note**: Full CLI implementation is TICKET 9D, but scaffold basic command here.

### 7.1 Create `scripts/cli.py` (minimal version)

```python
"""Maintainer CLI for preprocessing pipeline."""
import typer
from pathlib import Path

app = typer.Typer()

@app.command()
def preprocess(
    input_dir: Path = Path("data/raw"),
    output_dir: Path = Path("data/preprocessed")
):
    """Convert HTML/PDF files to clean text.

    Processes all HTML and PDF files in input_dir,
    writes clean text to output_dir, and creates manifest.
    """
    # Scaffold implementation for TICKET 9A
    # Full implementation in TICKET 9D
```

**80/20**: Minimal CLI to manually test preprocessing. Full features in TICKET 9D.

---

## TDD Implementation Workflow

### Cycle 1: Project Setup

1. **Test**: N/A (setup phase)
2. **Code**: Create directory structure, add dependencies
3. **Commit**: "build(deps): add BeautifulSoup4 and lxml for HTML parsing"

### Cycle 2: Pydantic Models

1. **Test**: Write tests for `DownloadMetadata` and `PreprocessManifest` validation
2. **Code**: Implement models with validators
3. **Commit**: "feat(preprocessor): add Pydantic models for manifest validation"

### Cycle 3: SHA256 Utility

1. **Test**: Write test for `compute_sha256()` static method
2. **Code**: Implement SHA256 computation
3. **Commit**: "feat(preprocessor): add SHA256 hash computation utility"

### Cycle 4: HTML Extraction

1. **Test**: Write all HTML extraction tests (main tag, article tag, script removal, etc.)
2. **Code**: Implement `extract_from_html()` to pass tests
3. **Commit**: "feat(preprocessor): implement HTML text extraction with BeautifulSoup"

### Cycle 5: PDF Extraction

1. **Test**: Write all PDF extraction tests (single page, multi-page, etc.)
2. **Code**: Implement `extract_from_pdf()` to pass tests
3. **Commit**: "feat(preprocessor): implement PDF text extraction with pdfplumber"

### Cycle 6: Preprocessing Pipeline

1. **Test**: Write tests for `preprocess_file()` (auto-detection, format routing, etc.)
2. **Code**: Implement `preprocess_file()` orchestration
3. **Commit**: "feat(preprocessor): implement unified preprocessing pipeline"

### Cycle 7: Integration Tests

1. **Test**: Download real CRA samples, write integration tests
2. **Code**: Fix any issues found during integration testing
3. **Commit**: "test(preprocessor): add integration tests with real CRA documents"

### Cycle 8: Documentation

1. **Test**: N/A (documentation phase)
2. **Code**: Write `docs/maintainer_guide.md`
3. **Commit**: "docs(maintainer): add preprocessing workflow guide"

### Cycle 9: CLI Scaffold

1. **Test**: Manual testing of CLI command
2. **Code**: Implement minimal `scripts/cli.py`
3. **Commit**: "feat(cli): add preprocess command scaffold for TICKET 9A"

---

## Implementation Checklist

### Phase 1: Setup (15 min)

- [ ] Create directory structure (`data/raw/`, `data/preprocessed/`, `scripts/preprocessor/`)
- [ ] Add `beautifulsoup4>=4.12` and `lxml>=5.0` to `pyproject.toml` under `indexing`
- [ ] Run `uv sync --extra indexing` to install dependencies
- [ ] **Commit**: "build(deps): add BeautifulSoup4 and lxml for HTML parsing"

### Phase 2: Models (20 min)

- [ ] Write tests for `DownloadMetadata` validation (filename, SHA256 pattern)
- [ ] Write tests for `PreprocessManifest` structure
- [ ] Create `scripts/preprocessor/models.py` with Pydantic models
- [ ] Verify tests pass
- [ ] **Commit**: "feat(preprocessor): add Pydantic models for manifest validation"

### Phase 3: Text Extraction (2 hours)

#### 3.1 SHA256 Utility

- [ ] Write test for `compute_sha256()` static method
- [ ] Implement `compute_sha256()` in `TextExtractor`
- [ ] Verify test passes
- [ ] **Commit**: "feat(preprocessor): add SHA256 hash computation utility"

#### 3.2 HTML Extraction

- [ ] Write test: `test_extract_from_html_with_main_tag()`
- [ ] Write test: `test_extract_from_html_with_article_tag()`
- [ ] Write test: `test_extract_from_html_removes_scripts()`
- [ ] Write test: `test_extract_from_html_preserves_structure()`
- [ ] Write test: `test_extract_from_html_missing_file_raises()`
- [ ] Implement `extract_from_html()` to pass all tests
- [ ] Verify all tests pass
- [ ] **Commit**: "feat(preprocessor): implement HTML text extraction with BeautifulSoup"

#### 3.3 PDF Extraction

- [ ] Write test: `test_extract_from_pdf_single_page()`
- [ ] Write test: `test_extract_from_pdf_multi_page()`
- [ ] Write test: `test_extract_from_pdf_missing_file_raises()`
- [ ] Implement `extract_from_pdf()` to pass all tests
- [ ] Verify all tests pass
- [ ] **Commit**: "feat(preprocessor): implement PDF text extraction with pdfplumber"

#### 3.4 Preprocessing Pipeline

- [ ] Write test: `test_preprocess_html_file()`
- [ ] Write test: `test_preprocess_pdf_file()`
- [ ] Write test: `test_preprocess_computes_sha256()`
- [ ] Write test: `test_preprocess_unsupported_format_raises()`
- [ ] Implement `preprocess_file()` to pass all tests
- [ ] Implement `_normalize_whitespace()` helper
- [ ] Verify all tests pass
- [ ] **Commit**: "feat(preprocessor): implement unified preprocessing pipeline"

### Phase 4: Documentation (30 min)

- [ ] Create `docs/maintainer_guide.md` with manual download process
- [ ] Document CRA target URLs and filtering criteria
- [ ] Document naming conventions and manifest schema
- [ ] Add example workflow and validation steps
- [ ] **Commit**: "docs(maintainer): add preprocessing workflow guide"

### Phase 5: Integration Testing (1 hour)

- [ ] Download small CRA HTML sample → `tests/fixtures/preprocessor/sample.html`
- [ ] Download small CRA PDF sample → `tests/fixtures/preprocessor/sample.pdf`
- [ ] Write integration test: `test_preprocess_real_html_document()`
- [ ] Write integration test: `test_preprocess_real_pdf_document()`
- [ ] Fix any issues found during integration testing
- [ ] Verify integration tests pass
- [ ] **Commit**: "test(preprocessor): add integration tests with real CRA documents"

### Phase 6: CLI Scaffold (30 min)

- [ ] Create `scripts/cli.py` with `preprocess` command (minimal implementation)
- [ ] Add `typer>=0.9` to `indexing` dependencies
- [ ] Manual testing: preprocess sample HTML and PDF files
- [ ] **Commit**: "feat(cli): add preprocess command scaffold for TICKET 9A"

### Final Validation (30 min)

- [ ] Run all tests: `uv run pytest tests/ -v -m "not slow"`
- [ ] Run pre-commit hooks: `uv run pre-commit run --all-files`
- [ ] Manual end-to-end test: Download real CRA document → preprocess → verify output
- [ ] Verify test coverage ≥85% for `text_extractor.py`: `uv run pytest --cov=scripts/preprocessor --cov-report=term`
- [ ] Update `plan.md` to mark TICKET 9A as complete
- [ ] **Commit**: "docs(plan): mark TICKET 9A as complete"

---

## Total Time Estimate

- **Core implementation**: ~4 hours
- **Testing**: ~2 hours
- **Documentation**: ~30 min
- **Buffer for debugging**: ~1.5 hours
- **Total**: ~8 hours (1 full day)

---

## Key Trade-offs & Decisions

| Decision                  | Approach                         | Rationale                                   |
| ------------------------- | -------------------------------- | ------------------------------------------- |
| HTML content extraction   | CSS selector heuristics          | 80/20 - works for CRA docs, avoid complex ML|
| PDF multi-column          | Accept pdfplumber default        | Simple, LLM can handle minor disorder       |
| Error handling            | Log warnings, continue           | Partial content better than failure         |
| Text cleaning             | Minimal normalization            | LLM handles the rest                        |
| SHA256 computation        | During preprocessing             | Single source of truth                      |
| Manifest creation         | Automated during preprocessing   | Reduce manual errors                        |
| Dependencies              | Optional `indexing` group        | Don't bloat runtime package                 |

---

## Success Criteria

✅ All acceptance criteria from plan.md met:

1. Manual download process documented
2. `TextExtractor` class with 3 methods implemented
3. Output structure `data/preprocessed/*.txt` created
4. Unit tests pass (HTML/PDF extraction, format detection)
5. Integration test passes (1 HTML + 1 PDF real document)

✅ Quality gates:

- All tests pass
- Pre-commit hooks pass (ruff, mypy, pyright)
- Test coverage ≥85%
- Documentation complete

✅ Ready for TICKET 9B (Gemini Parser) - clean text output available
