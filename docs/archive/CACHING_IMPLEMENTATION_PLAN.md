# Smart Caching & Stepwise Testing Plan

**Date**: 2025-10-18
**Status**: Ready for Implementation
**Estimated Time**: ~75 minutes
**Expected Cost Savings**: 90%+ on subsequent pipeline runs

---

## Executive Summary

This plan implements a **content-addressable caching layer** for the LLM parser to prevent burning API credits during development. It follows the **80/20 principle**: simple, battle-tested `diskcache` library with SHA256 content hashing, plus a **stepwise testing strategy** (1 file → 3 files → full corpus) to validate incrementally without wasting credits.

**Critical Discovery**: Your background extraction job is currently failing with `404 models/gemini-1.5-flash is not found`. We need to fix the model name mismatch first.

---

## Problem Statement

### Current State (Anti-Pattern)
- LLM parser calls Gemini API for **every HTML file** on **every run**
- No caching = re-processing already-seen files after failures
- Development iteration = burning credits unnecessarily
- **Analogous to**: `SELECT * FROM LARGE_TABLE` in production DB

### Target State (Solution)
- Cache Gemini responses using content-addressable keys
- Cache HIT = instant response, zero API cost
- Cache MISS = new/changed files only trigger API calls
- Progressive testing: validate with 1 file before processing all 13

---

## Critical Issues Identified

### Issue 1: Model Name 404 Error

**Error from background job**:
```
NotFound: 404 models/gemini-1.5-flash is not found for API version v1beta
```

**Root Cause**: Mismatch between configured model and actual API call
- `settings.py` shows: `llm_model_name: str = "gemini-2.0-flash-exp"`
- API error indicates: Code is using `gemini-1.5-flash`

**Resolution**: Find and fix the hardcoded or overridden model name

---

## Implementation Plan

### Phase 1: Fix Model Name Bug (5 minutes)

**Action Items**:
1. Kill the failing background extraction job (Bash f1509b)
2. Search codebase for any hardcoded `gemini-1.5-flash` references
3. Verify `settings.py` is correctly loaded and not overridden
4. Test with a single file to confirm API connectivity

**Validation**:
```bash
# Should succeed without 404 errors
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/t4002-2.html \
  output/model_test.yml \
  --verbose
```

---

### Phase 2: Implement Smart Caching (30 minutes)

Following Zen's generated implementation plan from `zen_generated.code`.

#### Step 2.1: Add Dependency

```bash
uv add diskcache
```

**Why `diskcache`?**
- Mature, pure-Python library
- SQLite-backed, thread-safe, persistent storage
- Dictionary-like interface (simple to use)
- Handles file locking, serialization, eviction policies
- Better than custom JSON/pickle/SQLite implementation

#### Step 2.2: Create Cache Module

**File**: `src/qe_tax_rag/extraction/ca/cache.py`

```python
"""Persistent, content-addressable cache for LLM API responses."""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from diskcache import Cache

logger = logging.getLogger(__name__)


class LLMResponseCache:
    """
    A content-addressable cache for LLM responses.

    Uses diskcache to store raw text responses from an LLM, keyed by a hash
    of the inputs that generated the response (prompt, model name, and content).
    This avoids expensive, duplicate API calls during development and testing.
    """

    def __init__(self, cache_dir: str | Path):
        """
        Initializes the cache in the specified directory.

        Args:
            cache_dir: The directory where cache data will be stored.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(str(self.cache_dir))
        logger.info(f"LLM response cache initialized at: {self.cache_dir}")

    def _generate_key(
        self, prompt: str, model_name: str, content: str
    ) -> str:
        """
        Generates a deterministic SHA256 hash from the inputs.

        Args:
            prompt: The LLM prompt text.
            model_name: The name of the LLM model.
            content: The source content being sent to the LLM.

        Returns:
            A SHA256 hex digest to use as a cache key.
        """
        hasher = hashlib.sha256()
        hasher.update(prompt.encode("utf-8"))
        hasher.update(model_name.encode("utf-8"))
        hasher.update(content.encode("utf-8"))
        return hasher.hexdigest()

    def get(
        self, prompt: str, model_name: str, content: str
    ) -> Optional[str]:
        """
        Retrieves a cached response if one exists.

        Args:
            prompt: The LLM prompt text.
            model_name: The name of the LLM model.
            content: The source content.

        Returns:
            The cached response text, or None if not found.
        """
        key = self._generate_key(prompt, model_name, content)
        cached_value = self._cache.get(key)
        if cached_value:
            logger.debug(f"Cache HIT for key: {key[:10]}...")
            return str(cached_value)
        logger.debug(f"Cache MISS for key: {key[:10]}...")
        return None

    def set(
        self, prompt: str, model_name: str, content: str, response_text: str
    ) -> None:
        """
        Stores an LLM response in the cache.

        Args:
            prompt: The LLM prompt text.
            model_name: The name of the LLM model.
            content: The source content.
            response_text: The raw text of the LLM response to cache.
        """
        key = self._generate_key(prompt, model_name, content)
        self._cache.set(key, response_text)
        logger.debug(f"Cache SET for key: {key[:10]}...")

    def close(self) -> None:
        """Closes the cache connection."""
        self._cache.close()
```

**Key Design Decisions**:
- **Content-addressable**: Cache key = SHA256(prompt + model + content)
- **Auto-invalidation**: HTML changes → different hash → cache miss
- **Raw response caching**: Store JSON string, not parsed Pydantic objects
- **Decoupled from schema**: Cache survives `ExtractedRule` model changes

#### Step 2.3: Update Settings

**File**: `src/qe_tax_rag/extraction/ca/settings.py`

Add optional `cache_dir` field:

```python
"""Configuration settings for the Canadian HTML-to-YAML extraction pipeline."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the data extraction pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QE_TAX_RAG_EXTRACTION_",
        extra="ignore",
    )

    # Gemini API Configuration
    gemini_api_key: str = Field(
        default="",
        description="Gemini API key for HTML-to-YAML extraction (required for operation).",
    )
    llm_model_name: str = "gemini-2.0-flash-exp"
    adjudicator_model_name: str = "gemini-2.0-flash-exp"

    # Caching Configuration
    cache_dir: str | None = Field(
        default=None,
        description="Directory to store cached LLM responses. If not set, caching is disabled.",
    )


# Singleton instance
settings = Settings()
```

**Configuration Options**:
- CLI flag: `--cache-dir .llm_cache/` (explicit, recommended)
- Environment variable: `QE_TAX_RAG_EXTRACTION_CACHE_DIR=/path/to/cache`
- Default: `None` (caching disabled)

#### Step 2.4: Update LLM Parser

**File**: `src/qe_tax_rag/extraction/ca/llm_parser.py`

Key changes:
1. Import `LLMResponseCache`
2. Add `cache_dir` parameter to `parse()` function
3. Check cache before API call
4. Store successful responses

```python
"""LLM-based parser for CRA tax documents using Gemini API."""

import json
import logging
import random
import time
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from bs4 import BeautifulSoup
from google.api_core import exceptions as google_exceptions

from qe_tax_rag.extraction.ca.cache import LLMResponseCache
from qe_tax_rag.extraction.ca.exceptions import ParserError
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
)
from qe_tax_rag.extraction.ca.settings import settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """..."""  # Existing prompt unchanged


def parse(
    html_path: str, cache_dir: Optional[str | Path] = None
) -> list[ExtractedRule]:
    """
    Parse HTML file using text-based LLM to extract line-numbered expense rules.

    Args:
        html_path: Absolute path to the local HTML file.
        cache_dir: Directory to cache LLM responses. If None, caching is disabled.

    Returns:
        List of ExtractedRule objects with expert_source set to LLM.

    Raises:
        ParserError: If file cannot be read or API call fails permanently.
    """
    # Initialize cache if a directory is provided
    cache = LLMResponseCache(cache_dir) if cache_dir else None

    # Read HTML file
    try:
        html_content = Path(html_path).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        msg = f"HTML file not found: {html_path}"
        logger.error(msg)
        raise ParserError(msg) from e
    except OSError as e:
        msg = f"Failed to read HTML file: {html_path}"
        logger.error(msg, exc_info=True)
        raise ParserError(msg) from e

    # Extract <main> content using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    main_tag = soup.find("main")
    if not main_tag:
        msg = f"No <main> tag found in {html_path}"
        logger.warning(msg)
        main_content_text = soup.get_text()
    else:
        main_content_text = main_tag.get_text()

    # Check cache first
    response_text = None
    if cache:
        response_text = cache.get(
            prompt=EXTRACTION_PROMPT,
            model_name=settings.llm_model_name,
            content=main_content_text,
        )

    if response_text:
        logger.info(f"Cache HIT for {html_path}. Skipping API call.")
    else:
        logger.info(f"Cache MISS for {html_path}. Calling Gemini API.")

        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.llm_model_name)

        # Token safety check
        try:
            token_count = model.count_tokens(main_content_text)
            if token_count.total_tokens > 1_000_000:
                logger.warning(
                    f"Content of {html_path} exceeds token limit: "
                    f"{token_count.total_tokens} tokens (max: 1M). "
                    "Extraction may fail or be incomplete."
                )
        except Exception as e:
            logger.debug(f"Token counting failed for {html_path}: {e}")

        # Call LLM with retry logic
        retries = 4
        backoff_factor = 5
        last_exception = None

        for attempt in range(retries):
            try:
                response = model.generate_content(
                    [EXTRACTION_PROMPT, main_content_text],
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json"
                    ),
                )
                response_text = response.text
                break  # Success - exit retry loop
            except (
                google_exceptions.ResourceExhausted,
                google_exceptions.ServiceUnavailable,
                google_exceptions.InternalServerError,
            ) as e:
                last_exception = e
                if attempt + 1 == retries:
                    msg = f"API call failed permanently for {html_path} after {retries} attempts"
                    logger.error(msg, exc_info=True)
                    raise ParserError(msg) from e

                wait_time = (backoff_factor ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"API error for {html_path}, attempt {attempt + 1}/{retries}. "
                    f"Retrying in {wait_time:.2f} seconds... Error: {e}"
                )
                time.sleep(wait_time)
        else:
            msg = f"API call failed for {html_path}"
            logger.error(msg, exc_info=True)
            raise ParserError(msg) from last_exception

        # Store the successful response in the cache
        if cache and response_text:
            cache.set(
                prompt=EXTRACTION_PROMPT,
                model_name=settings.llm_model_name,
                content=main_content_text,
                response_text=response_text,
            )

    # Parse JSON response (existing code unchanged)
    try:
        data = json.loads(response_text or "{}")
        rules_data = data.get("rules", [])
    except json.JSONDecodeError as e:
        msg = f"Failed to parse JSON response for {html_path} (malformed/truncated JSON)"
        logger.warning(
            f"{msg}. Gemini may have truncated the response for large files. "
            "Returning empty list to allow fallback to Classic Parser results. "
            f"Error: {e}"
        )
        return []

    # Convert to ExtractedRule objects (existing code unchanged)
    rules = []
    source_file = Path(html_path).name

    for rule_dict in rules_data:
        try:
            applies_to_str = rule_dict.get("applies_to", [])
            applies_to_enum = [ApplicabilityType(s) for s in applies_to_str]

            rule = ExtractedRule(
                rule_number=rule_dict["rule_number"],
                title=rule_dict["title"],
                content=rule_dict["content"],
                applies_to=applies_to_enum,
                source_citation=rule_dict["source_citation"],
                chapter=rule_dict["chapter"],
                section=rule_dict.get("section"),
                source_file=source_file,
                expert_source=ExpertSource.LLM,
                anchor_id=rule_dict.get("anchor_id"),
                confidence_score=0.8,
            )
            rules.append(rule)
        except (KeyError, ValueError) as e:
            msg = f"Failed to validate rule data in {html_path}"
            logger.error(f"{msg}. Invalid data: {rule_dict}", exc_info=True)
            raise ParserError(msg) from e

    logger.info(f"LLM parser extracted {len(rules)} rules from {html_path}")
    return rules
```

**Log Messages Added**:
- `Cache HIT for {html_path}. Skipping API call.`
- `Cache MISS for {html_path}. Calling Gemini API.`

#### Step 2.5: Update Orchestrator

**File**: `src/qe_tax_rag/extraction/ca/orchestrator.py`

Add `cache_dir` parameter and wire through to parser:

```python
def run_extraction(
    input_path: Path,
    output_yaml: Path,
    manual_review_yaml: Path,
    dry_run: bool = False,
    cache_dir: Optional[Path] = None,  # NEW
) -> dict[str, Any]:
    """
    Execute the HTML-to-YAML extraction pipeline.

    Args:
        input_path: Path to HTML file or directory of HTML files
        output_yaml: Path for output YAML file
        manual_review_yaml: Path for manual review YAML file
        dry_run: If True, skip YAML file generation
        cache_dir: Optional directory for caching LLM responses

    Returns:
        Dictionary with extraction statistics
    """
    logger.info(f"Starting extraction pipeline for {input_path}")

    # ... existing code ...

    for html_file in html_files:
        try:
            html_content = html_file.read_text(encoding="utf-8")

            # Parse with both parsers
            classic_rules = classic_parse(str(html_file))
            llm_rules = llm_parse(str(html_file), cache_dir=cache_dir)  # UPDATED

            # ... rest of existing code ...
```

#### Step 2.6: Update CLI

**File**: `scripts/extract_rules.py`

Add `--cache-dir` option to the `run` and `extract` commands:

```python
@app.command()
def run(
    input_path: Annotated[Path, ...],
    output_yaml: Annotated[Path, ...],
    manual_review_yaml: Annotated[Path, ...] = Path("manual_review.yml"),
    verbose: Annotated[bool, ...] = False,
    auto_transform: Annotated[bool, ...] = False,
    output_jsonl: Annotated[Path | None, ...] = None,
    cache_dir: Annotated[  # NEW
        Path | None,
        typer.Option(
            "--cache-dir",
            help="Directory to cache LLM responses (improves performance and reduces API costs).",
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Extract structured rules from CRA HTML documents into YAML format."""

    # ... existing code ...

    stats, transformation_report = _run_extraction_pipeline(
        html_files=html_files,
        output_yaml=output_yaml,
        manual_review_yaml=manual_review_yaml,
        output_jsonl=output_jsonl if auto_transform else None,
        verbose=verbose,
        cache_dir=cache_dir,  # NEW
    )
```

Update `_run_extraction_pipeline` helper:

```python
def _run_extraction_pipeline(
    html_files: list[Path],
    output_yaml: Path,
    manual_review_yaml: Path,
    output_jsonl: Path | None,
    verbose: bool = False,
    cache_dir: Path | None = None,  # NEW
) -> tuple[dict, "TransformationReport | None"]:
    """Adapter for core extraction pipeline."""

    # ... existing code ...

    result = run_extraction(
        input_path=input_dir,
        output_yaml=output_yaml,
        manual_review_yaml=manual_review_yaml,
        cache_dir=cache_dir,  # NEW
    )

    # ... rest of existing code ...
```

---

### Phase 3: Stepwise Testing Strategy (20 minutes)

Progressive validation to catch issues early without burning credits.

#### Test 1: Single File - Cache MISS (First Run)

**Objective**: Validate basic caching setup, API connectivity

```bash
# Pick a file with rules (avoid intro pages like t4002-1.html)
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/t4002-2.html \
  output/test_single.yml \
  --cache-dir .llm_cache/ \
  --verbose
```

**Expected Output**:
```
INFO - LLM response cache initialized at: .llm_cache/
INFO - Cache MISS for cra_documents/.../t4002-2.html. Calling Gemini API.
INFO - LLM parser extracted 15 rules from t4002-2.html
```

**Verification**:
- ✅ `.llm_cache/` directory created
- ✅ Cache contains SQLite files (`cache.db`, etc.)
- ✅ No 404 model errors
- ✅ `output/test_single.yml` contains extracted rules

#### Test 2: Single File - Cache HIT (Second Run)

**Objective**: Verify cache retrieval works

```bash
# Re-run exact same command
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/t4002-2.html \
  output/test_single.yml \
  --cache-dir .llm_cache/ \
  --verbose
```

**Expected Output**:
```
INFO - LLM response cache initialized at: .llm_cache/
INFO - Cache HIT for cra_documents/.../t4002-2.html. Skipping API call.
INFO - LLM parser extracted 15 rules from t4002-2.html
```

**Verification**:
- ✅ No API call made (check logs for "Calling Gemini API" - should be absent)
- ✅ Execution time < 5 seconds (vs ~30s for API call)
- ✅ Output identical to Test 1

#### Test 3: Cache Invalidation (HTML Content Change)

**Objective**: Verify content-addressable caching works

```bash
# Modify t4002-2.html (add a space at end of file)
echo " " >> cra_documents/cra_t4002e_rev24_dump/t4002-2.html

# Re-run
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/t4002-2.html \
  output/test_single.yml \
  --cache-dir .llm_cache/ \
  --verbose

# Restore original file
git checkout cra_documents/cra_t4002e_rev24_dump/t4002-2.html
```

**Expected Output**:
```
INFO - Cache MISS for cra_documents/.../t4002-2.html. Calling Gemini API.
```

**Verification**:
- ✅ Cache MISS triggered (content hash changed)
- ✅ New cache entry created
- ✅ Original file restored via git

#### Test 4: Small Batch (3 Files)

**Objective**: Validate cache efficiency with multiple files

```bash
# Create test subset
mkdir -p test_subset
cp cra_documents/cra_t4002e_rev24_dump/t4002-{2,3,4}.html test_subset/

# Run extraction
uv run extract-rules extract \
  test_subset/ \
  output/test_batch.yml \
  --cache-dir .llm_cache/ \
  --verbose
```

**Expected Output**:
```
INFO - Discovered 3 HTML files
INFO - Cache HIT for test_subset/t4002-2.html. Skipping API call.
INFO - Cache MISS for test_subset/t4002-3.html. Calling Gemini API.
INFO - Cache MISS for test_subset/t4002-4.html. Calling Gemini API.
```

**Verification**:
- ✅ 1 cache HIT (t4002-2 from Test 1)
- ✅ 2 cache MISSes (new files)
- ✅ Total API calls: 2 (not 3)

**Cleanup**:
```bash
rm -rf test_subset/
```

#### Test 5: Full Corpus (All 13 Files)

**Objective**: Validate production usage with cache

```bash
# First run (with cache from previous tests)
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/cra_rules.yml \
  --manual-review-file output/manual_review.yml \
  --cache-dir .llm_cache/ \
  --verbose
```

**Expected Output**:
```
INFO - Discovered 13 HTML files
INFO - Cache HIT for ... (files from previous tests)
INFO - Cache MISS for ... (remaining files)
Total API calls: ~10 (not 13)
```

**Second Run** (complete cache):
```bash
# Re-run to verify full cache coverage
uv run extract-rules extract \
  cra_documents/cra_t4002e_rev24_dump/ \
  output/cra_rules.yml \
  --manual-review-file output/manual_review.yml \
  --cache-dir .llm_cache/ \
  --verbose
```

**Expected Output**:
```
INFO - Discovered 13 HTML files
[13x] INFO - Cache HIT for ...
Total execution time: < 30 seconds (vs ~5 minutes without cache)
Total API calls: 0
```

**Verification**:
- ✅ All 13 files cached
- ✅ Zero API calls on second run
- ✅ Near-instant execution
- ✅ Output files identical

---

### Phase 4: Documentation & Cleanup (10 minutes)

#### Update CLAUDE.md

Add caching section to developer guide:

```markdown
## LLM Response Caching

The extraction pipeline supports opt-in caching of LLM responses to reduce API costs during development.

### Usage

```bash
# Enable caching with --cache-dir flag
uv run extract-rules extract \
  input/ \
  output/rules.yml \
  --cache-dir .llm_cache/
```

### How It Works

- **Content-addressable**: Cache key = SHA256(prompt + model + HTML content)
- **Auto-invalidation**: HTML changes automatically invalidate cache
- **Persistent**: Cache survives across runs (SQLite-backed)
- **Thread-safe**: Uses `diskcache` library for safe concurrent access

### Cache Management

```bash
# Check cache size
du -sh .llm_cache/

# Clear cache
rm -rf .llm_cache/

# Disable caching (omit --cache-dir flag)
uv run extract-rules extract input/ output.yml
```

### Expected Performance

- **First run**: Normal API latency (~30s per file)
- **Cached runs**: Near-instant (\<1s per file)
- **Cost savings**: 90%+ on subsequent runs
```

#### Add .llm_cache/ to .gitignore

```bash
echo ".llm_cache/" >> .gitignore
```

#### Delete zen_generated.code

```bash
rm zen_generated.code
```

---

## Testing Checklist

- [ ] Phase 1: Fix model name bug (404 error resolved)
- [ ] Phase 2.1: `diskcache` dependency added
- [ ] Phase 2.2: `cache.py` module created with `LLMResponseCache` class
- [ ] Phase 2.3: `settings.py` updated with `cache_dir` field
- [ ] Phase 2.4: `llm_parser.py` updated with cache logic
- [ ] Phase 2.5: `orchestrator.py` wired to pass cache_dir
- [ ] Phase 2.6: CLI `--cache-dir` flag added
- [ ] Phase 3.1: Single file cache MISS test passed
- [ ] Phase 3.2: Single file cache HIT test passed
- [ ] Phase 3.3: Cache invalidation test passed
- [ ] Phase 3.4: Small batch (3 files) test passed
- [ ] Phase 3.5: Full corpus (13 files) test passed
- [ ] Phase 4: Documentation updated, cleanup complete

---

## Key Benefits

| Metric | Without Cache | With Cache (2nd run) |
|--------|---------------|----------------------|
| Execution Time | ~5 minutes | ~30 seconds |
| API Calls | 13 (all files) | 0 (all cached) |
| API Cost | $X | $0 |
| Development Iterations | Expensive | Free |

---

## Trade-offs & Design Decisions

### Why Cache Raw JSON Instead of Parsed Objects?

**Decision**: Cache `response.text` (raw JSON string), not `ExtractedRule` objects

**Rationale**:
- Parsing (`json.loads()` + Pydantic validation) is cheap (~1ms)
- API call is expensive (~30s + $cost)
- Caching raw JSON decouples cache from schema changes
- If `ExtractedRule` model changes, cache remains valid

### Why SHA256 Content Hashing?

**Decision**: Cache key includes HTML content hash, not just filename

**Rationale**:
- Files can be edited/updated during development
- Filename alone would serve stale cached data
- Content hash auto-invalidates on any HTML change
- Prevents subtle bugs from outdated cached responses

### Why `diskcache` Over Custom Implementation?

**Decision**: Use battle-tested `diskcache` library

**Rationale**:
- Thread-safe, handles file locking automatically
- Persistent SQLite backend (survives crashes)
- Eviction policies, TTL support (if needed later)
- ~100 lines of code avoided vs custom implementation
- Follows 80/20 principle: simple, reliable, minimal complexity

---

## Optional Enhancements (Future Work)

### Cache Introspection Commands

Add CLI commands for cache management:

```bash
# Show cache statistics
uv run extract-rules cache-info --cache-dir .llm_cache/

# Output:
# Cache Directory: .llm_cache/
# Total Entries: 13
# Disk Size: 2.3 MB
# Hit Rate: 85.7% (12/14 requests)

# Clear cache
uv run extract-rules cache-clear --cache-dir .llm_cache/
```

### TTL-Based Expiration

Add time-based expiration for production use:

```python
# In cache.py
self._cache.set(key, response_text, expire=86400)  # 24-hour TTL
```

### Cache Warming

Pre-populate cache for CI/CD:

```bash
# Warm cache before tests
uv run extract-rules cache-warm \
  cra_documents/ \
  --cache-dir .llm_cache/
```

---

## Success Criteria

✅ All 13 HTML files process successfully with caching enabled
✅ Second run completes in <30 seconds (vs ~5 minutes)
✅ Zero API calls on cached runs
✅ Cache HIT/MISS logged clearly for debugging
✅ HTML content changes trigger cache invalidation
✅ Documentation updated with usage examples
✅ No regression in extraction quality (same output as non-cached)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Cache corruption | `diskcache` uses SQLite transactions, ACID guarantees |
| Stale cached data | Content-addressable keys auto-invalidate on changes |
| Disk space exhaustion | Monitor cache size, add eviction policies if needed |
| False cache hits | SHA256 collision probability negligible (2^-256) |
| Breaking schema changes | Cache stores raw JSON, decoupled from Pydantic models |

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Fix model bug | 5 min | None |
| Phase 2: Implement caching | 30 min | Phase 1 complete |
| Phase 3: Stepwise testing | 20 min | Phase 2 complete |
| Phase 4: Documentation | 10 min | Phase 3 complete |
| **Total** | **~75 min** | Sequential execution |

---

## Contact & Support

For questions or issues:
- GitHub Issues: https://github.com/anthropics/claude-code/issues
- Documentation: `CLAUDE.md`, `USER_GUIDE.md`
- Zen MCP: Use `chat with zen` for architectural guidance

---

**Next Steps**: Start with Phase 1 (fix model bug), then proceed sequentially through the phases. Use the testing checklist to track progress.
