# Maintainer Guide: QuickExpense RAG Indexing Pipeline

This guide explains how to build and maintain the searchable database of Canadian Revenue Agency (CRA) business expense rules.

## Overview

The indexing pipeline transforms raw HTML/PDF documents from the CRA website into a searchable SQLite database with full-text search (FTS5) and semantic vector search capabilities.

**Pipeline stages:**

1. **Preprocess**: HTML/PDF → clean text files
2. **Parse**: Text → structured JSONL (using Gemini Flash)
3. **Build**: JSONL → SQLite database with embeddings
4. **Validate**: Smoke tests for database integrity

## Prerequisites

### System Requirements

- Python 3.12
- uv package manager (recommended) or pip
- ~2GB disk space for data and embeddings
- Internet connection for downloading source documents

### Environment Setup

```bash
# Clone repository
git clone https://github.com/manonja/quickExpense-rag.git
cd quickExpense-rag

# Install dependencies
uv sync --extra indexing

# OR with pip
pip install -e ".[indexing]"
```

### API Keys

The **parse** stage requires a Google Gemini API key:

```bash
# Get free API key from https://ai.google.dev/
export GEMINI_API_KEY="your-key-here"
```

**Cost estimation** (Gemini Flash 1.5):

- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens
- Typical: ~$0.50-$2.00 for full CRA corpus (varies by content)

## Quick Start: Full Pipeline

The easiest way to build the database is using the `pipeline` command:

```bash
# 1. Download CRA HTML/PDF files manually to data/raw/
#    (See "Manual Download" section below)

# 2. Set your Gemini API key
export GEMINI_API_KEY="your-key-here"

# 3. Run the full pipeline
uv run python scripts/cli.py pipeline --input-dir data/raw

# Optional: skip confirmation prompts (for automation)
uv run python scripts/cli.py pipeline --input-dir data/raw --force
```

**What happens:**

- Preprocesses HTML/PDF → text (data/preprocessed/)
- Parses text → JSONL chunks (data/processed/chunks.jsonl)
- Builds database with embeddings (data/cra_rules.db)
- Validates database integrity
- Creates manifest with provenance (data/manifest.json)

**Output:**

```
QuickExpense RAG Full Pipeline
Input: data/raw
Output DB: data/cra_rules.db

Stage 1/4: Preprocessing HTML/PDF files
Found 23 files to preprocess
Preprocessing... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 23/23
✅ Preprocessed 23 files

Stage 2/4: Parsing with Gemini Flash
Found 23 text files to parse
Parsing documents... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 23/23
✅ Parsed 23 files

Stage 3/4: Building searchable database
Embedding chunks: 100%|██████████| 145/145 [00:12<00:00, 11.83batch/s]
✅ Database created: data/cra_rules.db

Stage 4/4: Validating database
✅ Validation passed

Pipeline Complete!
✅ Database: data/cra_rules.db
✅ Manifest: data/manifest.json
📊 Database size: 42.31 MB
```

## Manual Workflow: Individual Commands

For more control, run each stage separately:

### Step 1: Manual Download

**Currently required**: CRA documents must be downloaded manually (automated scraping not implemented).

```bash
# Create raw directory
mkdir -p data/raw

# Download CRA pages manually from:
# https://www.canada.ca/en/revenue-agency/services/tax/businesses.html

# Save as: data/raw/S{series}-F{form}-C{chapter}.html
# Examples:
#   data/raw/S1-F1-C1.html  (Meals and entertainment)
#   data/raw/S2-F1-C1.html  (Vehicle expenses)
#   data/raw/S3-F1-C1.html  (Home office)
```

**File naming convention:**

- `S` = Series number (topic area)
- `F` = Form number (document type)
- `C` = Chapter number (section within form)
- Use `.html` or `.pdf` extension

### Step 2: Preprocess

Convert HTML/PDF to clean text:

```bash
uv run python scripts/cli.py preprocess \
  --input-dir data/raw \
  --output-dir data/preprocessed
```

**What it does:**

- Extracts text from HTML/PDF files
- Removes navigation, headers, footers
- Normalizes whitespace
- Computes SHA256 checksums
- Creates `data/raw/manifest.json` with metadata

**Output:**

- `data/preprocessed/*.txt` - Clean text files
- `data/raw/manifest.json` - Document metadata

### Step 3: Parse

Extract structured information using Gemini Flash:

```bash
export GEMINI_API_KEY="your-key-here"

uv run python scripts/cli.py parse \
  --input-dir data/preprocessed \
  --output-file data/processed/chunks.jsonl
```

**What it does:**

- Sends text to Gemini Flash API
- Extracts: title, sections, metadata (province, business type, expense type)
- Generates unique citation IDs for each paragraph
- Writes JSONL format (one ParsedDocument per line)
- Tracks token usage and cost

**Options:**

- `--force` - Continue on API errors instead of stopping

**Output:**

- `data/processed/chunks.jsonl` - Structured documents
- Token usage and cost estimation printed to console

**Cost tracking example:**

```
Token Usage:
  Prompt tokens: 45,230
  Completion tokens: 12,890
  Total tokens: 58,120

Estimated Cost:
  Input: $0.0034
  Output: $0.0039
  Total: $0.0073
```

### Step 4: Build

Create searchable database with embeddings:

```bash
uv run python scripts/cli.py build \
  --input-file data/processed/chunks.jsonl \
  --manifest-file data/raw/manifest.json \
  --output-db data/cra_rules.db \
  --output-manifest data/manifest.json \
  --data-version 2024.12
```

**What it does:**

- Flattens ParsedDocument sections into individual chunks
- Generates BGE embeddings (384-dim) for each chunk
- Creates SQLite database with:
  - FTS5 index for keyword search
  - Vector index for semantic search
  - Metadata for filtering
- Writes manifest with source file provenance

**Options:**

- `--continue-on-error` - Skip chunks with embedding errors
- `--data-version` - Version string (YYYY.MM format)

**Output:**

- `data/cra_rules.db` - SQLite database (~40-50MB)
- `data/manifest.json` - Build metadata

**Performance:**

- ~10-15 chunks/second for embedding generation
- Total time: ~2-5 minutes for typical corpus

### Step 5: Validate

Run smoke tests on the database:

```bash
uv run python scripts/cli.py validate \
  --db-path data/cra_rules.db
```

**What it checks:**

✅ Schema completeness (all required tables exist)
✅ Row count consistency (rules, rules_fts, rules_vec match)
✅ Embedding dimensions (384 for BGE-small-en-v1.5)
✅ Database statistics (chunks, provinces, expense types)

**Output:**

```
QuickExpense RAG Database Validation
Database: data/cra_rules.db

Running validation checks...

╭─ Validation Summary ─╮
│ ✅ Validation PASSED │
╰──────────────────────╯

┏━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check        ┃ Status ┃ Details                      ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ schema       │   ✅   │                              │
│ row_counts   │   ✅   │                              │
│ embeddings   │   ✅   │                              │
│ search       │   ✅   │                              │
└──────────────┴────────┴──────────────────────────────┘

Database Statistics:
  total_chunks: 145
  provinces: ['AB', 'BC', 'ON', 'QC']
  business_types: ['corporation', 'partnership', 'sole_proprietorship']
  expense_types: ['entertainment', 'home_office', 'meals', 'travel', 'vehicle']

All validation checks passed!
```

**Exit codes:**

- `0` - Validation passed
- `1` - Validation failed or database not found

## Directory Structure

```
quickExpense-rag/
├── data/
│   ├── raw/                    # Original HTML/PDF files (git-ignored)
│   │   ├── S1-F1-C1.html
│   │   ├── S2-F1-C1.html
│   │   └── manifest.json       # Source file metadata
│   ├── preprocessed/           # Clean text files (git-ignored)
│   │   ├── S1-F1-C1.txt
│   │   └── S2-F1-C1.txt
│   ├── processed/              # Structured JSONL (git-ignored)
│   │   └── chunks.jsonl
│   ├── cra_rules.db           # Final database (git-ignored)
│   └── manifest.json          # Build manifest (git-ignored)
├── scripts/
│   ├── cli.py                 # Main CLI tool
│   ├── parser/                # Gemini parser
│   └── preprocessor/          # Text extraction
└── tests/
    └── integration/           # Integration tests
```

## Troubleshooting

### Gemini API Errors

**Problem:** `Error: GEMINI_API_KEY environment variable not set`

**Solution:**

```bash
export GEMINI_API_KEY="your-key-here"
```

**Problem:** `429 Too Many Requests` or rate limit errors

**Solution:**

- Gemini Flash free tier: 15 requests/minute
- Wait 1 minute and retry
- Or upgrade to paid tier for higher limits

**Problem:** `400 Bad Request` or parsing errors

**Solution:**

- Check input text quality (run preprocess first)
- Use `--force` flag to continue past errors
- Review failed files in logs

### Database Build Errors

**Problem:** `sqlite3.OperationalError: no such module: vec0`

**Solution:**

```bash
# Ensure sqlite-vec is installed
uv sync
# OR
pip install sqlite-vec
```

**Problem:** `ValueError: Duplicate citation_id found`

**Solution:**

- Citation IDs must be unique across all chunks
- Check JSONL input for duplicates
- Review parser output

**Problem:** Embedding generation is slow

**Solution:**

- Expected: ~10-15 chunks/second on CPU
- For GPU acceleration: Set `QUICKEXPENSE_RAG_DEVICE=cuda` (requires CUDA)
- Reduce batch size if running out of memory

### Validation Failures

**Problem:** Row count mismatch

**Solution:**

- Rebuild database from scratch
- Check for corruption: `sqlite3 data/cra_rules.db "PRAGMA integrity_check;"`

**Problem:** Embedding dimension mismatch

**Solution:**

- Expected: 384 dimensions for BGE-small-en-v1.5
- Don't change embedding model without full rebuild
- Model name stored in database metadata

## Updating the Database

When CRA updates their documentation:

```bash
# 1. Download new HTML files to data/raw/
# 2. Run full pipeline (overwrites existing database)
uv run python scripts/cli.py pipeline --input-dir data/raw --force

# 3. Increment data version
uv run python scripts/cli.py build \
  --data-version 2025.01 \
  # ... other options
```

**Version scheme:**

- `YYYY.MM` format (e.g., 2024.12, 2025.01)
- Increment month when data updates
- Stored in database metadata and manifest

## Best Practices

### For Production

1. **Version control:**
   - Commit manifest.json to track data provenance
   - Tag releases: `git tag -a v2024.12 -m "CRA data December 2024"`

2. **Backup strategy:**
   - Archive `data/cra_rules.db` with version tag
   - Store `data/manifest.json` alongside database
   - Keep `data/raw/` for reproducibility

3. **Automation:**
   - Use `--force` flag to skip prompts
   - Set environment variables in CI/CD
   - Monitor token costs in logs

4. **Testing:**
   - Run validation after every build
   - Check database size (should be ~40-50MB)
   - Verify chunk count is reasonable

### For Development

1. **Small test corpus:**
   - Use 3-5 HTML files for quick iteration
   - Test full pipeline end-to-end
   - Validation should complete in <10 seconds

2. **Cost management:**
   - Test with small files first
   - Monitor token usage output
   - Use `--force` flag sparingly (stops on errors by default)

3. **Debugging:**
   - Check logs in console output
   - Inspect JSONL intermediate files
   - Use SQLite browser to inspect database

## CLI Reference

### Global Options

All commands support:

- `--help` - Show command help
- `-v, --verbose` - Enable debug logging (preprocess command only)

### Commands

#### `preprocess`

Convert HTML/PDF to clean text.

```bash
uv run python scripts/cli.py preprocess [OPTIONS]
```

**Options:**

- `-i, --input-dir PATH` - Input directory (default: data/raw)
- `-o, --output-dir PATH` - Output directory (default: data/preprocessed)
- `-v, --verbose` - Enable verbose logging

#### `parse`

Parse text using Gemini Flash.

```bash
uv run python scripts/cli.py parse [OPTIONS]
```

**Options:**

- `-i, --input-dir PATH` - Input directory (default: data/preprocessed)
- `-o, --output-file PATH` - Output JSONL file (default: data/processed/chunks.jsonl)
- `-f, --force` - Continue on errors

**Environment:**

- `GEMINI_API_KEY` - Required

#### `build`

Build searchable database.

```bash
uv run python scripts/cli.py build [OPTIONS]
```

**Options:**

- `-i, --input-file PATH` - Input JSONL (default: data/processed/chunks.jsonl)
- `-m, --manifest-file PATH` - Source manifest (default: data/raw/manifest.json)
- `-o, --output-db PATH` - Output database (default: data/cra_rules.db)
- `--output-manifest PATH` - Output manifest (default: data/manifest.json)
- `-v, --data-version TEXT` - Data version (default: 2024.12)
- `--continue-on-error` - Skip chunks with errors

#### `validate`

Validate database integrity.

```bash
uv run python scripts/cli.py validate [OPTIONS]
```

**Options:**

- `-d, --db-path PATH` - Database path (default: data/cra_rules.db)

#### `pipeline`

Run full pipeline.

```bash
uv run python scripts/cli.py pipeline [OPTIONS]
```

**Options:**

- `-i, --input-dir PATH` - Input directory (default: data/raw)
- `--preprocessed-dir PATH` - Preprocessed output (default: data/preprocessed)
- `--processed-dir PATH` - Processed output (default: data/processed)
- `-o, --output-db PATH` - Output database (default: data/cra_rules.db)
- `--output-manifest PATH` - Output manifest (default: data/manifest.json)
- `-v, --data-version TEXT` - Data version (default: 2024.12)
- `-f, --force` - Skip confirmations and continue on errors

**Environment:**

- `GEMINI_API_KEY` - Required for parse stage

## Support

- **Issues**: https://github.com/manonja/quickExpense-rag/issues
- **Documentation**: https://github.com/manonja/quickExpense-rag/docs
- **License**: MIT
