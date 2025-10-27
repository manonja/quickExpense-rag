# T4002 Content Type Investigation & Incremental Extraction Plan

**Goal**: Deliver value quickly (83 rules in database) while building understanding for future multi-content-type extraction.

**Status**: Investigation Phase
**Date**: 2025-10-24

## Current Situation

### Available Files (11 HTML files)
- t4002-1.html, t4002-2.html, t4002-4.html, t4002-6.html, t4002-8.html, t4002-9.html
- t4002-10.html, t4002-11.html, t4002-12.html, t4002-14.html, t4002-15.html

### Temporarily Moved
- `t4002-3.html` → `t4002-3.html.CONTEXTUAL_ONLY` (principles/guidance, references rules)
- `t4002-5.html` → `t4002-5.html.ALREADY_PROCESSED` (63 rules in production database)

### Known Extraction Results
From previous pipeline run (failed at database build due to duplicates):
- **t4002-4.html**: 16 rules (farming/fishing income)
- **t4002-6.html**: 4 rules (expenses)
- **All others**: 0 line-numbered rules (intro/CCA chapters)
- **Duplicates found**: LINE-9600, LINE-9604 (blocking database build)

### Problem
Cannot build database due to duplicate `citation_id` constraint violation.

## Chosen Approach: Option A + Documentation

**Deliver value NOW + Build understanding for LATER**

### Phase 1: Fix Duplicates & Extract Rules (NOW)
1. Investigate duplicate LINE-9600, LINE-9604
2. Fix citation_id format: `{source_file}-LINE-{number}` (e.g., `t4002-4-LINE-9600`)
3. Extract 20 rules from t4002-4.html + t4002-6.html
4. Combine with 63 production rules from t4002-5.html
5. Release **data-v2025.11** with ~83 total rules

**Outcome**: Working database with expanded rule coverage (original goal achieved)

### Phase 2: Document Content Types (NOW - in parallel)
1. Manually explore representative HTML files
2. Document patterns for each content type
3. Create examples showing structure
4. Build foundation for future V2 extraction

**Outcome**: Clear understanding of all content types, ready for future work

### Phase 3: V2 Multi-Content Extraction (LATER - separate epic)
Use documentation from Phase 2 to design and implement:
- Unified `content` table with content_type discriminator
- Modular parsers (rules, principles, tables, examples, guidance)
- Pydantic models with discriminated unions
- Schema v2.0 with proper migration

**Outcome**: Full HTML content capture (rules + principles + tables + examples + guidance)

## Phase 1 Tasks: Fix Duplicates & Deliver Rules

### Task 1.1: Investigate Duplicates (15 min)
```bash
# Find which files contain LINE-9600
grep -n "9600" cra_documents/cra_t4002e_rev24_dump/*.html

# Find which files contain LINE-9604
grep -n "9604" cra_documents/cra_t4002e_rev24_dump/*.html
```

**Document findings**:
- Are these true duplicates (identical content in multiple files)?
- Or rule definition vs. rule reference?
- Which file has the canonical definition?

**Create**: `docs/DUPLICATE_ANALYSIS.md`

### Task 1.2: Fix Citation ID Format (1 hour)
**Update**: `src/qe_tax_rag/extraction/ca/models.py`

Change citation_id generation from:
```python
citation_id = f"LINE-{rule_number}"
```

To:
```python
citation_id = f"{source_stem}-LINE-{rule_number}"
# e.g., "t4002-4-LINE-9600"
```

**Special case**: Keep t4002-5.html using old format `LINE-{number}` for backwards compatibility with production database.

**Commit**: "fix: add source file prefix to citation_id to prevent duplicates"

### Task 1.3: Rebuild Database with Fixed Citations (30 min)
```bash
# Use existing intermediate YAML from previous pipeline run
# Location: /var/folders/.../qetax_extract_g5hrn73o/rules.yml

# Update citation_ids in YAML
# Build database from corrected YAML
uv run python scripts/cli.py build \
  --input-file /path/to/corrected_rules.yml \
  --output-db output/new_rules.db

# Verify: Should have 20 rules with no duplicates
sqlite3 output/new_rules.db "SELECT COUNT(*) FROM rules;"
```

**Commit**: "feat: extract 20 rules from t4002-4 and t4002-6 with unique citations"

### Task 1.4: Combine with Production Database (1 hour)
**Option A - SQL Merge**:
```bash
# Export production rules (63 from t4002-5.html)
sqlite3 data/cra_rules.db ".dump rules" > prod_rules.sql

# Import into new database
sqlite3 output/new_rules.db < prod_rules.sql

# Verify total count
sqlite3 output/new_rules.db "SELECT COUNT(*) FROM rules;"
# Expected: 83 rules (63 + 20)
```

**Option B - YAML Merge** (cleaner):
```bash
# Extract production rules to YAML
# Combine YAMLs
# Rebuild database from combined YAML
```

**Commit**: "feat: combine production database (63 rules) with new extractions (20 rules)"

### Task 1.5: Validate & Release (30 min)
```bash
# Validate schema
uv run python scripts/cli.py validate --db-path data/cra_rules_v2.db

# Test searches
uv run python scripts/cli.py search "meals" --db-path data/cra_rules_v2.db
uv run python scripts/cli.py search "vehicle" --db-path data/cra_rules_v2.db
uv run python scripts/cli.py search "farming income" --db-path data/cra_rules_v2.db

# Check lineage
sqlite3 data/cra_rules_v2.db "SELECT citation_id, source_file FROM rules ORDER BY source_file;"
```

**Create GitHub Release**: data-v2025.11
- Database file: `cra_rules_v2.db`
- Size: ~96-100KB (up from 80KB)
- Rules: 83 total (63 from t4002-5 + 16 from t4002-4 + 4 from t4002-6)

**Commit**: "release: data-v2025.11 with 83 CRA expense rules"

## Phase 2 Tasks: Document Content Types

### Task 2.1: Explore RULES File (30 min)
**File**: t4002-4.html (16 rules - farming/fishing income)

Read HTML structure, document:
- How line-numbered rules appear (HTML pattern, anchor IDs)
- Rule title format
- Content structure
- Section/chapter metadata

**Create**: `docs/CONTENT_EXAMPLES.md` (Section: RULES)

**Commit**: "docs: document RULES content type patterns from t4002-4.html"

### Task 2.2: Explore PRINCIPLES File (30 min)
**File**: t4002-3.html.CONTEXTUAL_ONLY

Read HTML structure, document:
- Content that references rules (e.g., "Report at line 9974...")
- How principles differ from rule definitions
- Section structure
- Relationship to rules

**Update**: `docs/CONTENT_EXAMPLES.md` (Section: PRINCIPLES)

**Commit**: "docs: document PRINCIPLES content type patterns from t4002-3.html"

### Task 2.3: Explore TABLES File (30 min)
**Likely file**: t4002-8.html, t4002-10.html, or t4002-11.html (CCA chapters)

Scan for `<table>` elements, document:
- Table types (CCA rates, deduction limits, calculation tables)
- Table structure (headers, rows, columns)
- Caption/title patterns
- Context (what section contains the table)

**Update**: `docs/CONTENT_EXAMPLES.md` (Section: TABLES)

**Commit**: "docs: document TABLES content type patterns from t4002-X.html"

### Task 2.4: Explore EXAMPLES File (30 min)
**File**: t4002-3.html.CONTEXTUAL_ONLY (Patrick's GST example)

Read example sections, document:
- Example structure (likely `<section class="panel">` with "Example" heading)
- Content format (narrative, calculations, forms)
- Rules demonstrated
- How examples link to rules

**Update**: `docs/CONTENT_EXAMPLES.md` (Section: EXAMPLES)

**Commit**: "docs: document EXAMPLES content type patterns from t4002-3.html"

### Task 2.5: Explore GUIDANCE File (30 min)
**File**: t4002-1.html (Chapter 1 - General Information)

Read general content, document:
- Introductory paragraphs
- Definitions (e.g., "What is a business?")
- Procedural instructions
- Cross-references
- What makes it "guidance" vs other types

**Update**: `docs/CONTENT_EXAMPLES.md` (Section: GUIDANCE)

**Commit**: "docs: document GUIDANCE content type patterns from t4002-1.html"

### Task 2.6: Summarize Findings (30 min)
Create comprehensive summary document:

**File**: `docs/CONTENT_TYPE_ARCHITECTURE.md`

Include:
- All 5 content types with clear definitions
- HTML patterns for each type
- Extraction strategies
- Duplicate handling strategies
- Citation ID schemes
- Recommended parser architecture (from Zen consultation)
- Migration path to V2 schema

**Commit**: "docs: comprehensive content type architecture for future V2 extraction"

## Success Criteria

### Phase 1 (Immediate Value)
✅ Database has 83 rules (63 production + 20 new)
✅ No duplicate citation_id errors
✅ All searches working
✅ Lineage traceable to source files
✅ GitHub release created (data-v2025.11)

### Phase 2 (Foundation for Future)
✅ All 5 content types documented with examples
✅ HTML patterns identified
✅ Extraction strategies defined
✅ Architecture document created
✅ Clear roadmap for V2 implementation

## Timeline

**Phase 1**: 3-4 hours (deliver value)
- Task 1.1: 15 min
- Task 1.2: 1 hour
- Task 1.3: 30 min
- Task 1.4: 1 hour
- Task 1.5: 30 min

**Phase 2**: 3 hours (build understanding)
- Task 2.1-2.5: 30 min each (2.5 hours)
- Task 2.6: 30 min

**Total**: 6-7 hours

## Next Steps

1. **Start Task 1.1**: Investigate duplicates (LINE-9600, LINE-9604)
2. **Small commits**: One task = one commit
3. **Build incrementally**: Get database working first, then document
4. **Ask questions**: If anything unclear, pause and clarify before proceeding
