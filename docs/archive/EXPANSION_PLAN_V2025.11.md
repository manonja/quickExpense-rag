# Expansion Plan: Process Remaining 13 HTML Files

**Date:** 2025-10-24 **Goal:** Process remaining 13 HTML files using same workflow as
t4002-5 (PR #42-45)

______________________________________________________________________

## Current State

**Completed (PR #46):**

- File: t4002-5.html
- Rules: 63
- Database: data-v2025.10.23 (1.7 MB)
- Workflow: PRE-143 (extract) → PRE-144 (build) → PRE-145 (validate) → Release

**Remaining:**

- Files: 13 HTML files (t4002-1 through t4002-15, excluding 5, 7, 13)
- Estimated rules: ~180-200 additional rules
- Target database: data-v2025.11 (~4-7 MB)

______________________________________________________________________

## Proven Workflow (from t4002-5)

### PRE-143: Extract HTML → YAML

```bash
uv run extract-rules \
  cra_documents/cra_t4002e_rev24_dump/t4002-X.html \
  output/t4002-X/rules.yml \
  --manual-review-file output/t4002-X/manual_review.yml
```

- Dual parser (classic + LLM)
- Adjudicator resolves conflicts
- Lineage tracking (timestamps, source)
- Output: YAML with validated rules

### PRE-144: Build YAML → SQLite

```bash
uv run python scripts/cli.py build \
  --input-file output/t4002-X/rules.yml \
  --output-db output/t4002-X/rules.db \
  --output-manifest output/t4002-X/manifest.json
```

- Generates embeddings (BGE-small-en-v1.5)
- Creates FTS5 index
- Populates vector index
- Preserves lineage in metadata_json

### PRE-144: Validate Search

```bash
uv run python scripts/cli.py search "test query" \
  --db-path output/t4002-X/rules.db --top-k 3
```

- Test queries return results
- Lineage chain visible
- Citation IDs valid

______________________________________________________________________

## Simplified Plan (3 Steps)

### Step 1: Test Sample (Validate Workflow Scales)

Process 2-3 files individually to confirm workflow works for other files:

```bash
# Test diverse files
for file in t4002-1 t4002-8 t4002-12; do
  echo "Processing $file..."

  # Extract
  uv run extract-rules \
    cra_documents/cra_t4002e_rev24_dump/$file.html \
    output/test/$file.yml

  # Build
  uv run python scripts/cli.py build \
    --input-file output/test/$file.yml \
    --output-db output/test/$file.db

  # Quick search test
  uv run python scripts/cli.py search "expense" \
    --db-path output/test/$file.db --top-k 1

  # Count rules
  echo "Rules extracted: $(grep -c '^- rule_number:' output/test/$file.yml)"
done
```

**Success criteria:**

- All 3 files extract without errors
- Rules have valid citation IDs
- Search returns results
- Lineage present

**If this passes:** Proceed to Step 2 **If this fails:** Debug issues before processing
all files

______________________________________________________________________

### Step 2: Process All Files

Use existing pipeline-extraction command (processes all files + combines):

```bash
uv run python scripts/cli.py pipeline-extraction \
  --input-dir cra_documents/cra_t4002e_rev24_dump/ \
  --output-db data/cra_rules_v2.db \
  --keep-intermediate
```

**This command does:**

1. Runs extract-rules on each HTML file
1. Combines all YAML into single ruleset
1. Builds database with embeddings
1. Runs validation checks

**Monitor during execution:**

- Watch console output for first few files
- Check for errors or warnings
- Note total rules extracted

**Expected output:**

- Total rules: >200 (target: 247+)
- Database size: 4-7 MB
- Processing time: 30-45 minutes

______________________________________________________________________

### Step 3: Release

**3.1 Validate Database**

```bash
# Run built-in validator
uv run python scripts/cli.py validate --db-path data/cra_rules_v2.db

# Test sample searches
uv run python scripts/cli.py search "meals" --db-path data/cra_rules_v2.db --top-k 5
uv run python scripts/cli.py search "vehicle" --db-path data/cra_rules_v2.db --top-k 5
uv run python scripts/cli.py search "home office" --db-path data/cra_rules_v2.db --top-k 5

# Check stats
sqlite3 data/cra_rules_v2.db "SELECT COUNT(*) FROM rules;"
sqlite3 data/cra_rules_v2.db "SELECT source_file, COUNT(*) FROM rules GROUP BY source_file;"
```

**3.2 Prepare Release**

```bash
# Checksum
shasum -a 256 data/cra_rules_v2.db > data/cra_rules_v2.db.sha256
cat data/cra_rules_v2.db.sha256

# Get stats for release notes
sqlite3 data/cra_rules_v2.db "SELECT COUNT(*) FROM rules;"
ls -lh data/cra_rules_v2.db
```

**3.3 Update Library Configuration**

Edit `src/qe_tax_rag/settings.py`:

```python
database_version: str = "2025.11"
database_sha256: str = "[checksum from above]"
db_download_url: str = "https://github.com/manonja/quickExpense-rag/releases/download/data-v2025.11/cra_rules.db"
```

**3.4 Create GitHub Release**

1. Go to: https://github.com/manonja/quickExpense-rag/releases
1. Click "Draft a new release"
1. Tag: `data-v2025.11`
1. Title: "CRA Tax Rules Database - v2025.11 (Full T4002 Guide)"
1. Description:
   ```markdown
   Expanded from 63 rules (1 file) to [X] rules (14 files).
   Full CRA T4002 Business and Professional Income Guide coverage.

   - Source: 14 HTML files (t4002-1 through t4002-15)
   - Total rules: [X]
   - Database size: [X MB]
   - SHA256: [checksum]

   Migration: `qe.init(force_update=True)`
   ```
1. Upload: Rename `data/cra_rules_v2.db` → `cra_rules.db` and upload
1. Publish

**3.5 Verify Download**

```bash
# Test download works
curl -L -O https://github.com/manonja/quickExpense-rag/releases/download/data-v2025.11/cra_rules.db
shasum -a 256 cra_rules.db  # Should match settings.py

# Test end-to-end
rm -rf ~/.cache/qe_tax_rag/
uv run python -c "import qe_tax_rag as qe; qe.init(); print(qe.get_version())"
```

**3.6 Update Documentation**

Update these files:

- `README.md` - Update stats: 63→247+ rules, 1→14 files, 1.7MB→XMB
- `CLAUDE.md` - Update project status with new coverage
- `CHANGELOG.md` - Add v2025.11 entry

**3.7 Commit & PR**

```bash
git add \
  src/qe_tax_rag/settings.py \
  README.md \
  CLAUDE.md \
  CHANGELOG.md \
  data/cra_rules_v2.db.sha256

git commit -m "feat: expand database to full T4002 guide (14 files, 247+ rules)

Process all 14 HTML files from CRA T4002 guide, expanding coverage
from 63 to 247+ searchable expense rules.

- Database: data-v2025.11
- Files: t4002-1 through t4002-15 (14 total)
- Size: [X MB]

Release: https://github.com/manonja/quickExpense-rag/releases/tag/data-v2025.11

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push -u origin feat/expand-to-full-t4002-guide
gh pr create --title "Expand database to full T4002 guide (14 files, 247+ rules)"
```

______________________________________________________________________

## Success Criteria

- [ ] Step 1: Sample files (3) process successfully
- [ ] Step 2: All 14 files process successfully
- [ ] Total rules >200 (ideally 247+)
- [ ] Database validates (all checks pass)
- [ ] Search queries return relevant results
- [ ] Database size \<10 MB
- [ ] GitHub release created and downloadable
- [ ] Documentation updated

______________________________________________________________________

## Time Estimate

- Step 1 (test sample): 1-1.5 hours
- Step 2 (full pipeline): 1 hour
- Step 3 (release + docs): 1-1.5 hours
- **Total: 3-4 hours**

______________________________________________________________________

## What We're NOT Doing (80/20 + YAGNI)

- ✗ Per-file validation reports
- ✗ Performance benchmarking (premature optimization)
- ✗ Deep data analysis
- ✗ Separate expansion report document
- ✗ Multi-phase quality gates

We're doing: **Same workflow as t4002-5, scaled to 14 files**
