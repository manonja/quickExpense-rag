# Improved HTML Content Capture: Modular & Minimal Approach

**Date**: 2025-10-24
**Goal**: Build toward comprehensive HTML content capture in a smart, modular, and minimal way
**Philosophy**: Small steps, clear documentation, test one file at a time

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

### Phase 1: Build Better Rule Extraction (Week 1)

**Goal**: Fix current extraction to distinguish definitions from references

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

**Commit**: "fix: distinguish rule definitions from references in classic parser"

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

**Commit**: "docs: document rule definition vs reference patterns"

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

**Commit**: "feat: extract 18 unique rule definitions from t4002-4 and t4002-6"

### Phase 2: Add ONE New Content Type (Week 1)

**Goal**: Prove modular approach works by adding PRINCIPLES as second content type

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

**Acceptance Criteria**: TBD (plan with Zen)

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

**Acceptance Criteria**: TBD (plan with Zen)

**Commit**: "feat: add principle parser to extract rule references"

#### Step 2.3: Test on ONE File (30 min)
**File**: t4002-6.html (we know it has rule references)

```bash
# Extract rules (definitions only)
uv run extract-rules cra_documents/cra_t4002e_rev24_dump/t4002-6.html output/t4002-6/rules.yml

# Extract principles (references)
uv run extract-principles cra_documents/cra_t4002e_rev24_dump/t4002-6.html output/t4002-6/principles.yml

# Validate
cat output/t4002-6/rules.yml  # Should show 2 rules
cat output/t4002-6/principles.yml  # Should show 2+ principles
```

**Acceptance Criteria**: TBD (plan with Zen)

**Commit**: "test: extract rules and principles from t4002-6.html"

#### Step 2.4: Document Findings (30 min)
**File**: `docs/CONTENT_PATTERNS.md` (update)

Add section showing:
- How many principles found in t4002-6.html
- Examples of extracted principles
- Reference links (which rules they point to)
- Patterns that work, patterns that need refinement

**Acceptance Criteria**: TBD (plan with Zen)

**Commit**: "docs: document principle extraction results from t4002-6.html"

### Phase 3: Repeat for Each Content Type (Week 2)

Use same pattern for TABLES, EXAMPLES, GUIDANCE:
1. Build parser for ONE content type
2. Test on ONE representative file
3. Document patterns and findings
4. Commit
5. Move to next type

**One file, one content type, one commit at a time**

**Acceptance Criteria**: TBD (plan with Zen for each content type)

### Phase 4: Unified Orchestrator (Week 2)

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
