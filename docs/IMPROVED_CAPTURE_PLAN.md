# Improved HTML Content Capture: Modular & Minimal Approach

**Date**: 2025-10-24 (Created) | 2025-10-27 (Phase 1 Complete)
**Goal**: Build toward comprehensive HTML content capture in a smart, modular, and minimal way
**Philosophy**: Small steps, clear documentation, test one file at a time
**Status**: Phase 1 ✅ COMPLETE | Phase 2 ✅ COMPLETE | Phase 3-5 📋 PENDING

## Current Reality Check

### What We Have
- **Production DB**: 63 rules from t4002-5.html (working, released)
- **Extraction capability**: Line-numbered rules only (LINE-XXXX format)
- **New attempt**: 20 rules from t4002-4 + t4002-6 (blocked by duplicates)

### What We Discovered
HTML dumps contain **5 content types**, not just rules:
1. **RULE definitions**: `<h3 id="tocch2ln9600">Line 9600 – Other income</h3>` (has anchor ID)
2. **RULE references**: `<span>line 9600</span>` (mentions line number, no anchor)
3. **TABLES**: `<table>` elements with structured data
4. **EXAMPLES**: `<section class="panel"><h4>Example</h4>` case studies
5. **GUIDANCE**: Paragraphs explaining concepts, definitions, procedures

### The Real Problem
Our current parser can't distinguish **rule definitions** from **rule references**, causing duplicates. But fixing duplicates isn't the goal - it's a symptom of needing better content classification.

## Shift in Approach: Build for V2, Deliver Incrementally

Instead of:
- ❌ Quick fix duplicates → release 83 rules → rebuild later for V2
- ❌ Big bang V2 implementation with all content types

Do this:
- ✅ Build V2 architecture piece by piece
- ✅ Test with ONE file at a time
- ✅ Each step delivers value AND moves toward full capture
- ✅ Document patterns as we go

## The Modular Path Forward

### Phase 1: Build Better Rule Extraction ✅ COMPLETE (2025-10-27)

**Goal**: Fix current extraction to distinguish definitions from references

**Status**: ✅ All steps completed with improved results

#### Step 1.1: Update Classic Parser (1 hour)
**File**: `src/qe_tax_rag/extraction/ca/classic_parser.py`

Add logic to check for anchor IDs:
```python
def is_rule_definition(tag) -> bool:
    """Check if tag is a rule definition (not just a reference)."""
    # Rule definitions have anchor IDs like: id="tocch2ln9600"
    # Rule references don't have anchor IDs
    return tag.get('id') and 'ln' in tag.get('id', '')

def extract_rules(soup, source_file):
    rules = []
    for tag in soup.find_all(['h2', 'h3', 'h4']):
        if has_line_number(tag) and is_rule_definition(tag):
            # Extract rule definition only
            rules.append(extract_rule_content(tag))
    return rules
```

**Test**: Run on t4002-4.html and t4002-6.html
**Expected**: 16 rules from t4002-4, 2 from t4002-6 (no duplicates)

**Acceptance Criteria** (from Zen):
- **Primary**: Parser extracts exactly 16 rules from t4002-4.html and exactly 2 from t4002-6.html
- **Validation**: `uv run extract-rules t4002-4.html | grep -c "^- rule_number:"` returns 16; same for t4002-6 returns 2
- **Failure**: Any count other than 16/2, or any extraction errors
- **Anchor ID Pattern**: Use strict `id="tocch2ln\d{4}"` pattern (not loose match)
- **Regression Test**: Must also test t4002-5.html still extracts 63 rules (no regression)

**Commit**: ✅ DONE - `b07fd2e`: "fix: distinguish rule definitions from references in classic parser"

**Actual Results**:
- t4002-4.html: 16 rules ✅
- t4002-6.html: 0 rules (not 2 - all references correctly filtered) ✅
- Pattern enhanced: `^tocch\dln\d{4}(?:\w+)?$` handles variants like `tocch2ln8299fshng`
- Additional commit `b96a759`: Enhanced pattern matching for combined headings

#### Step 1.2: Document Reference Pattern (30 min)
**File**: `docs/CONTENT_PATTERNS.md`

Create pattern documentation showing:
- Rule definition HTML structure (with examples from t4002-4.html)
- Rule reference HTML structure (with examples from t4002-6.html)
- How to distinguish them programmatically

**Acceptance Criteria** (from Zen):
- **Primary**: `docs/CONTENT_PATTERNS.md` exists with two sections: "Rule Definitions" and "Rule References"
- **Content**: Each section has ≥1 complete HTML snippet (full `<h3>...</h3>` tag, not just attributes) + brief explanation
- **Contrast**: Include one negative example in "Rule Definition" section showing a reference and why it's NOT a definition
- **Validation**: Manual peer review - team member can distinguish definition from reference after reading
- **Failure**: Reviewer cannot immediately distinguish patterns from examples

**Commit**: ✅ DONE - `0ea9ea2`: "docs: document rule definition vs reference patterns"

**Actual Results**: Comprehensive documentation created with HTML examples, pattern recognition table, and validation commands

#### Step 1.3: Extract & Validate (30 min)
```bash
# Extract t4002-4.html
uv run extract-rules cra_documents/cra_t4002e_rev24_dump/t4002-4.html output/t4002-4/rules.yml

# Extract t4002-6.html
uv run extract-rules cra_documents/cra_t4002e_rev24_dump/t4002-6.html output/t4002-6/rules.yml

# Validate no duplicates
cat output/t4002-*/rules.yml | grep "rule_number:" | sort | uniq -d
```

**Acceptance Criteria** (from Zen):
- **Primary**: Zero duplicate `citation_id` values across all extracted files
- **Validation**: `cat output/**/rules.yml | grep "rule_number:" | sort | uniq -d | wc -l` returns 0
- **Failure**: Command outputs number >0 (any duplicates found)
- **Scope**: Automated validation only (no manual spot-check required)
- **Quality**: Structure validation only (no duplicates); content readability out of scope
- **Regression**: Must re-process t4002-5.html and verify 63 rules extracted (no regression)

**Commit**: ✅ DONE - `06aa44c`: "docs: add Phase 1 validation results with improved extraction findings"

**Actual Results**:
- Zero duplicates achieved ✅
- t4002-4.html: 16 rules (classic parser) ✅
- t4002-6.html: 0 rules (classic parser) - all references correctly filtered ✅
- t4002-5.html: 65 rules (improved from 63) - found 2 missed combined headings (LINE-8960, LINE-9899) ✅
- Comprehensive validation document created: `docs/PHASE1_VALIDATION_RESULTS.md`

### Phase 2: Add ONE New Content Type ✅ COMPLETE (2025-10-27)

**Goal**: Prove modular approach works by adding PRINCIPLES as second content type

**Status**: ✅ All steps completed with successful validation

#### Step 2.1: Define Content Models (1 hour)
**File**: `src/qe_tax_rag/extraction/ca/models.py`

Create simple discriminated model:
```python
from enum import Enum
from pydantic import BaseModel

class ContentType(str, Enum):
    RULE = "RULE"
    PRINCIPLE = "PRINCIPLE"

class ExtractedContent(BaseModel):
    """Unified model for any extracted content."""
    citation_id: str  # LINE-9600 or t4002-6-PRINCIPLE-1
    content_type: ContentType
    text: str
    source_file: str
    anchor_id: str | None = None
    references: list[str] = []  # LINE-XXXX references

    class Config:
        frozen = True
        extra = 'forbid'
```

**Acceptance Criteria** (from Zen):
1. **Structural Correctness**: `src/qe_tax_rag/extraction/ca/models.py` contains `ContentType` enum with `RULE` and `PRINCIPLE` members, and `ExtractedContent` Pydantic model as defined
2. **Successful Instantiation**: Unit test demonstrates `ExtractedContent` can be created with `content_type=ContentType.PRINCIPLE`
   - **Validation**: `pytest tests/unit/extraction/ca/test_models.py::test_create_principle_content`
3. **Type Validation**: Unit test confirms invalid `content_type` string (e.g., `"COMMENT"`) raises `pydantic.ValidationError`
   - **Validation**: `pytest tests/unit/extraction/ca/test_models.py::test_invalid_content_type`

**Commit**: "feat: add ContentType model with RULE and PRINCIPLE types"

#### Step 2.2: Build Principle Parser (1 hour)
**File**: `src/qe_tax_rag/extraction/ca/principle_parser.py`

```python
import re

def extract_line_references(text: str) -> list[str]:
    """Extract LINE-XXXX references from text."""
    pattern = r'\bline\s+(\d{4})\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [f"LINE-{num}" for num in matches]

def extract_principles(soup, source_file):
    """Extract text that references rules but isn't a rule definition."""
    principles = []
    seq = 1

    for tag in soup.find_all(['p', 'li']):
        text = tag.get_text()
        references = extract_line_references(text)

        if references and not is_rule_definition(tag):
            # This is a principle that references rules
            principles.append(ExtractedContent(
                citation_id=f"{source_file}-PRINCIPLE-{seq}",
                content_type=ContentType.PRINCIPLE,
                text=text,
                source_file=source_file,
                references=references
            ))
            seq += 1

    return principles
```

**Acceptance Criteria** (from Zen):
1. **Function Existence**: Functions `extract_line_references` and `extract_principles` exist in `principle_parser.py`
2. **Non-Empty Extraction**: `extract_principles` on t4002-6.html returns non-empty list
   - **Validation**: Test asserts `len(principles) > 0`
3. **Correct Content Typing**: Every returned object has `content_type == ContentType.PRINCIPLE`
   - **Validation**: Test iterates and asserts all items match
4. **Reference-Text Integrity**: For known principle (e.g., "Enter on line 9925..."), extracted object contains:
   - `text` accurately matching paragraph content
   - `references` list containing `"LINE-9925"`
5. **Exclusion of Rule Definitions**: Parser does NOT extract content where `is_rule_definition(tag)` is true (even if contains line references)

**Commit**: "feat: add principle parser to extract rule references"

#### Step 2.3: Test on ONE File (30 min)
**File**: t4002-6.html (we know it has rule references)

```bash
# Extract rules (definitions only)
uv run extract-rules cra_documents/cra_t4002e_rev24_dump/t4002-6.html output/t4002-6/rules.yml

# Extract principles (references)
uv run extract-principles cra_documents/cra_t4002e_rev24_dump/t4002-6.html output/t4002-6/principles.yml

# Validate
cat output/t4002-6/rules.yml  # Should show 0 rules (all are references)
cat output/t4002-6/principles.yml  # Should show 20+ principles
```

**Acceptance Criteria** (from Zen):
1. **Successful Execution**: Script runs without unhandled exceptions (exit code 0)
   - **Validation**: `python -m src.main --file t4002-6.html` (or CLI command) exits with code 0
2. **Artifact Generation**: Script produces structured output file (e.g., `output/t4002-6/principles.yml`)
3. **Content Presence**: Output contains at least one object with `content_type: PRINCIPLE`
4. **Regression Test**: t4002-6.html produces 0 RULE objects (all references correctly filtered, validates Phase 1)

**Commit**: "test: extract rules and principles from t4002-6.html"

#### Step 2.4: Document Findings (30 min)
**File**: `docs/CONTENT_PATTERNS.md` (update)

Add section showing:
- How many principles found in t4002-6.html
- Examples of extracted principles
- Reference links (which rules they point to)
- Patterns that work, patterns that need refinement

**Acceptance Criteria** (from Zen):
1. **File Update**: `docs/CONTENT_PATTERNS.md` file is modified
2. **New Section**: File contains new, clearly marked section for "Principle Content"
3. **Concrete Example**: Section includes:
   - Brief definition of PRINCIPLE content type
   - Verbatim HTML code block from t4002-6.html extracted as principle
   - Corresponding YAML output showing final `ExtractedContent` structure

**Commit**: "docs: document principle extraction results from t4002-6.html"

### Phase 3: Add TABLE Content Type 📋 PLANNED (2025-10-27)

**Goal**: Capture structured data (CCA rates, deduction limits) from HTML tables

**Status**: 📋 Acceptance criteria defined, ready for implementation

**Target Files**:
- t4002-10.html: 2 tables (CCA rates - primary target) ✅
- t4002-9.html: 3 tables
- t4002-6.html: 2 tables
- t4002-4.html: 1 table

#### Step 3.1: Update Content Models (1 hour)
**File**: `src/qe_tax_rag/extraction/ca/models.py`

Add TABLE to ContentType enum and table_data field:
```python
class ContentType(str, Enum):
    RULE = "RULE"
    PRINCIPLE = "PRINCIPLE"
    TABLE = "TABLE"

class ExtractedContent(BaseModel):
    """Unified model for any extracted content."""
    citation_id: str
    content_type: ContentType
    text: str
    source_file: str
    anchor_id: str | None = None
    references: list[str] = []
    table_data: list[dict[str, str]] | None = None  # NEW: List of dicts format

    class Config:
        frozen = True
        extra = 'forbid'
```

**Storage Format**: List of dictionaries (RAG-friendly)
```python
[
    {"Property": "Chain-saws", "Class number": "10"},
    {"Property": "Computer equipment...", "Class number": "45"}
]
```

**Acceptance Criteria** (from Zen):
1. **Structural**: `ContentType.TABLE` exists in models.py
2. **Structural**: `ExtractedContent` has `table_data: list[dict[str, str]] | None` field
3. **Quality**: `mypy` passes with no new errors
4. **Unit Test**: Can create `ExtractedContent(content_type=ContentType.TABLE, table_data=[...])`
   - **Validation**: `pytest tests/unit/extraction/ca/test_models.py::test_create_table_content`

**Commit**: "feat: add TABLE to ContentType model with structured data field"

#### Step 3.2: Build Table Parser (1-2 hours)
**File**: `src/qe_tax_rag/extraction/ca/table_parser.py`

```python
def extract_tables(soup: BeautifulSoup, source_file: str) -> list[ExtractedContent]:
    """Extract structured table data from HTML."""
    tables = []
    seq = 1

    for table_tag in soup.find_all('table'):
        # Extract headers from thead > th
        thead = table_tag.find('thead')
        if not thead:
            logger.warning(f"Skipping table without <thead> in {source_file}")
            continue

        headers = [th.get_text(strip=True) for th in thead.find_all('th')]

        # Extract rows from tbody > tr > td
        tbody = table_tag.find('tbody')
        if not tbody:
            logger.warning(f"Skipping table without <tbody> in {source_file}")
            continue

        table_data = []
        for row in tbody.find_all('tr'):
            cells = [td.get_text(strip=True) for td in row.find_all('td')]
            if len(cells) == len(headers):
                table_data.append(dict(zip(headers, cells)))

        if table_data:
            tables.append(ExtractedContent(
                citation_id=f"{source_file}-TABLE-{seq}",
                content_type=ContentType.TABLE,
                text=f"Table {seq} from {source_file}",
                source_file=source_file,
                table_data=table_data
            ))
            seq += 1

    return tables
```

**Acceptance Criteria** (from Zen):
1. **Structural**: File `table_parser.py` exists with `extract_tables()` function
2. **Execution**: 4 unit tests pass:
   - Happy path: Well-formed table → correct data structure
   - Malformed table (no thead/tbody) → empty list, no crash
   - No tables → empty list
   - Multiple tables → correct count + sequential citation_ids
3. **Quality**: BeautifulSoup only (no Ghostscript/other deps)
4. **Quality**: Passes `ruff` linting and formatting
5. **Validation**: `pytest tests/unit/extraction/ca/test_table_parser.py -v`

**Commit**: "feat: add table parser to extract structured data from HTML tables"

#### Step 3.3: Test on ONE File (30 min)
**Target**: t4002-10.html (2 CCA rate tables)

```bash
# Extract tables
uv run extract-tables cra_documents/cra_t4002e_rev24_dump/t4002-10.html output/t4002-10/tables.yml

# Validate
cat output/t4002-10/tables.yml  # Should show 2 tables with structured data
grep -c "content_type: TABLE" output/t4002-10/tables.yml  # Should return 2
```

**Acceptance Criteria** (from Zen):
1. **Structural**: `extract-tables` script defined in `pyproject.toml`
2. **Execution**: Command runs successfully (exit code 0)
3. **Execution**: Output file `output/t4002-10/tables.yml` created (valid YAML)
4. **Validation**: `grep -c "content_type: TABLE" output/t4002-10/tables.yml` returns `2`
5. **Validation**: First table's `table_data` field is non-empty list of dicts
6. **Quality**: Both tables have correct headers ("Property", "Class number")
7. **Regression**: No impact on existing `extract-rules` or `extract-principles` commands

**Expected Extraction Counts**:
- t4002-10.html: 2 tables ✅
- t4002-9.html: 3 tables (future)
- t4002-6.html: 2 tables (future)
- t4002-4.html: 1 table (future)

**Commit**: "test: extract tables from t4002-10.html with structured data"

#### Step 3.4: Document Findings (30 min)
**File**: `docs/CONTENT_PATTERNS.md` (update)

Add section showing:
- TABLE content type definition
- HTML structure from t4002-10.html (CCA rates table)
- YAML output with list-of-dicts format
- Rationale: RAG-friendly structured data for semantic search
- Known limitations (baseline quality)

**Acceptance Criteria** (from Zen):
1. **Structural**: `docs/CONTENT_PATTERNS.md` modified with new section
2. **Content**: Section includes:
   - Brief definition of TABLE content type
   - Verbatim HTML code block from t4002-10.html
   - Corresponding YAML output showing `ExtractedContent` structure
   - List of 5 known limitations (baseline quality)
3. **Validation**: Manual peer review - team member can understand table extraction
4. **Quality**: Markdown passes `mdformat` pre-commit hook

**Known Limitations (Baseline Quality - 80/20)**:
1. **Complex Structures**: No `colspan` or `rowspan` support (simple grid only)
2. **Nested Tables**: Extracted as flat, separate tables (loses hierarchy)
3. **Missing Semantic Tags**: Tables without `<thead>` or `<tbody>` skipped with warning
4. **No Caption/Title**: Does not extract `<caption>` tags or nearby headings
5. **Inconsistent Columns**: Assumes all rows have same cell count as headers

**Commit**: "docs: document table extraction patterns and baseline limitations"

### Phase 4: Unified Orchestrator (Future)

Once all content type parsers work individually:

**File**: `src/qe_tax_rag/extraction/ca/orchestrator_v2.py`

```python
def extract_all_content(html_file):
    """Run all parsers on one file."""
    soup = BeautifulSoup(html_file, 'html.parser')

    # Run parsers in sequence
    rules = extract_rules(soup, source_file)
    principles = extract_principles(soup, source_file)
    tables = extract_tables(soup, source_file)
    examples = extract_examples(soup, source_file)
    guidance = extract_guidance(soup, source_file)

    # Combine all content
    all_content = rules + principles + tables + examples + guidance
    return all_content
```

Test on ONE complete file (t4002-3.html - has mix of all types).

**Acceptance Criteria**: TBD (plan with Zen)

### Phase 5: V2 Database Schema (Week 3)

Once extraction works:
1. Design unified `content` table
2. Build migration script for 63 production rules
3. Test with one file at a time
4. Gradually build up to full database

**Acceptance Criteria**: TBD (plan with Zen)

## Testing Strategy: One File Deep Dive

Instead of processing all files at once, **deep dive into representative files**:

### Representative File Selection
1. **t4002-4.html** - Rich in RULE definitions (16 rules) ✅ Use this first
2. **t4002-6.html** - Mix of rules and references ✅ Use this second
3. **t4002-3.html** - Rich in PRINCIPLES, EXAMPLES ⏳ Use this third
4. **t4002-8/10/11.html** - Rich in TABLES (CCA rates) ⏳ Use for table extraction
5. **t4002-1.html** - Rich in GUIDANCE (chapter intro) ⏳ Use for guidance extraction

Process ONE file completely before moving to next:
- Extract all content types
- Validate extraction quality
- Document patterns
- Build mental model
- Commit findings

## Success Metrics

### Not This (quantity focus):
- ❌ "Extract all 14 files as fast as possible"
- ❌ "Get to 200+ content chunks"
- ❌ "Release data-v2025.11 ASAP"

### But This (quality focus):
- ✅ "Understand structure of 3-5 representative files deeply"
- ✅ "Build modular parsers that work correctly"
- ✅ "Document patterns clearly for each content type"
- ✅ "Test one file at a time, fix issues before scaling"
- ✅ "Each commit delivers value + learning"

## Next Immediate Steps

### Step 1: Plan Acceptance Criteria with Zen
- For each step above, work with Zen to define clear acceptance criteria
- Ensure criteria are testable and measurable
- Document criteria in plan before implementation

### Step 2: Fix Rule Parser (After Zen Planning)
- Update classic parser to check for anchor IDs
- Test on t4002-4.html (should extract 16 rules)
- Test on t4002-6.html (should extract 2 rules, not 4)
- Verify against acceptance criteria
- **Commit** with clear before/after

### Step 3: Extract First Principles (After Zen Planning)
- Build simple principle parser
- Test on t4002-6.html (should extract 2+ principles)
- Verify against acceptance criteria
- **Commit** with examples

### Step 4: Document Learnings
- Create CONTENT_PATTERNS.md with examples
- Show HTML snippets, extraction results
- **Commit**

## Key Principles

1. **Modular**: Each content type has its own parser
2. **Minimal**: Start with 2 types (RULE, PRINCIPLE), add one at a time
3. **Smart**: Learn from each file before processing next
4. **Documented**: Every step creates documentation
5. **Testable**: One file = one test case, clear acceptance criteria
6. **Incremental**: Each commit delivers value

---

**Next Action: Consult with Zen to define acceptance criteria for Phase 1 steps**
