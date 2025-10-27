# T4002 HTML Content Patterns

**Purpose**: Document HTML patterns for different content types found in CRA T4002 guide dumps to enable accurate extraction and prevent duplicates.

**Created**: 2025-10-27
**Status**: Phase 1 (Rule Definitions vs Rule References)

## Rule Definitions

### What Makes It a Definition

A **rule definition** is the canonical source of truth for a line-numbered expense rule. It contains:

1. **Anchor ID with strict pattern**: `id="tocch{chapter}ln{line_number}"`
2. **Heading tag**: Usually `<h3>` with "Line {number} – {title}" format
3. **Full content**: Complete explanation, instructions, and examples

### HTML Structure

```html
<h3><a id="tocch2ln9600"></a><span class="nowrap">Line 9600 –</span> Other income</h3>
<p>Enter the total of any other farming income you have not specifically identified on another line. The following paragraphs identify some of these income items.</p>
```

**Key characteristics**:

- Anchor ID: `tocch2ln9600` (chapter 2, line 9600)
- Pattern: `tocch\dln\d{4}` (chapter digit + "ln" + 4-digit line number)
- Location: Definition appears in the chapter where the line is explained (e.g., Chapter 2 for farming income)
- Content: Multiple paragraphs, lists, examples follow the heading

### Another Example

```html
<h3><a id="tocch2ln9604"></a><span class="nowrap">Line 9604 –</span> Insurance proceeds</h3>
<p>Enter any proceeds you received from insurance that covered lost or destroyed inventory, livestock, or business equipment...</p>
```

**Pattern**: `tocch2ln9604` (chapter 2, line 9604)

### Negative Example: This is NOT a Definition

```html
<h3>Line 9600 – Where to report income</h3>
<p>Report your income on the following lines:</p>
<ul>
    <li><span class="nowrap">line 9600</span> for farming income</li>
    <li><span class="nowrap">line 9600</span> for fishing income</li>
</ul>
```

**Why this is NOT a definition**:

- ❌ NO anchor ID on the `<a>` tag
- ❌ This is a cross-reference in Chapter 3 (expenses) pointing back to the definition in Chapter 2 (income)
- ❌ Does not contain the full rule explanation
- ❌ Heading describes where to report, not what the rule is

## Rule References

### What Makes It a Reference

A **rule reference** mentions a line number but does NOT provide the canonical definition. It:

1. **Lacks anchor ID**: Either no `<a>` tag, or `<a>` without matching `tocch\dln\d{4}` pattern
2. **Cross-references other chapters**: Points to where the rule is defined
3. **Brief mentions**: Short text or list items mentioning line numbers

### HTML Structures

#### Type 1: Cross-Reference Link

```html
<p>For more information, see <a href="t4002-4.html#tocch2ln9604">
<span class="nowrap">Line 9604 –</span> Insurance proceeds</a>.</p>
```

**Characteristics**:

- `<a>` tag has `href` pointing to the definition (not an `id`)
- Text says "For more information, see..."
- Location: Chapter 3 (expenses) referencing Chapter 2 (income)

#### Type 2: List Item Reference

```html
<ul>
    <li><span class="nowrap">line 9600</span> for farming income</li>
    <li><span class="nowrap">line 9600</span> for fishing income</li>
</ul>
```

**Characteristics**:

- Plain `<span>` tags with lowercase "line"
- No anchor IDs
- Brief mentions in instructional context

#### Type 3: Heading-Style Reference

```html
<h3>Line 9600 – Where to report income</h3>
<p>Report your income on the following lines:</p>
```

**Characteristics**:

- Looks like a rule definition heading but NO anchor ID
- Context is instructional ("where to report"), not definitional
- May appear in different chapter from definition

## Programmatic Distinction

### Extraction Strategy

**Classic Parser Algorithm**:

1. Find all `<h3>` tags matching pattern "Line {number} –"
2. For each tag, check if it has an `<a>` child with `id` attribute
3. Validate anchor ID matches strict pattern: `^tocch\dln\d{4}$`
4. Extract ONLY tags passing both checks

**Code Implementation**:

```python
def is_rule_definition(tag: Tag) -> bool:
    """Check if tag is a rule definition (not reference)."""
    anchor_tag = tag.find("a")
    if not anchor_tag:
        return False
    anchor_id = anchor_tag.get("id")
    if not anchor_id:
        return False
    # Strict pattern: tocch{chapter}ln{4-digit line number}
    return bool(re.match(r"^tocch\dln\d{4}$", anchor_id))
```

### Pattern Recognition Rules

| Content Type      | Anchor ID Pattern   | Extraction |
| ----------------- | ------------------- | ---------- |
| Rule Definition   | `tocch\dln\d{4}`    | ✅ Extract |
| Rule Reference    | No matching pattern | ❌ Skip    |
| Conceptual Header | No "Line {num} –"   | ❌ Skip    |

### Validation Tests

**Test 1: Extract only definitions**

```bash
grep -c "^- rule_number:" output/t4002-4/rules.yml
# Expected: 16 (all are definitions with anchor IDs)
```

**Test 2: Skip references**

```bash
grep -c "^- rule_number:" output/t4002-6/rules.yml
# Expected: 2 (filters out 2 references without anchor IDs)
```

**Test 3: No duplicates**

```bash
cat output/**/rules.yml | grep "rule_number:" | sort | uniq -d | wc -l
# Expected: 0 (no duplicates across all files)
```

## File Distribution Examples

### t4002-4.html (Chapter 2 - Income)

**Content**: 16 rule definitions

- LINE-9600 (Other income)
- LINE-9604 (Insurance proceeds)
- LINE-9659 (Farming income)
- ... (13 more definitions)

**All have anchor IDs**: `tocch2ln9600`, `tocch2ln9604`, etc.

### t4002-6.html (Chapter 3 - Expenses)

**Content**: 2 rule definitions + 2 rule references

**Definitions** (have anchor IDs):

- LINE-8810 (Salaries and wages) - `tocch3ln8810`
- LINE-8960 (Office expenses) - `tocch3ln8960`

**References** (no anchor IDs):

- LINE-9600 mentioned in "Where to report income" section
- LINE-9604 cross-referenced with "For more information, see..."

### t4002-5.html (Chapter 3 - Business Expenses)

**Content**: 63 rule definitions (production database)

- All have anchor IDs matching `tocch3ln\d{4}` pattern
- Regression test ensures no impact from parser update

## Principle Content (Phase 2)

### What Makes It a Principle

A **principle** is text that references line-numbered rules in an instructional or cross-reference context, but is NOT a rule definition. It:

1. **Contains line references**: Mentions "line {number}" in text
2. **Lacks anchor ID**: No `tocch\dln\d{4}` anchor pattern
3. **Instructional context**: Explains how to use or apply rules

Principles are typically found in:
- Paragraphs (`<p>`) explaining form completion
- List items (`<li>`) showing where to report amounts
- Cross-references to other chapters

### HTML Structures

#### Type 1: Instructional Paragraph

```html
<p>Enter on line 9925 the total business part of the cost of the equipment.</p>
```

**Characteristics**:
- Plain `<p>` tag (no anchor ID)
- Imperative instruction ("Enter on...")
- References LINE-9925

#### Type 2: Cross-Reference Paragraph

```html
<p>For more information, see <a href="t4002-4.html#tocch2ln9604">
<span class="nowrap">Line 9604 –</span> Insurance proceeds</a>.</p>
```

**Characteristics**:
- Contains hyperlink to rule definition
- Text pattern: "For more information, see..."
- References LINE-9604

#### Type 3: List Item Reference

```html
<li><span class="nowrap">line 9600</span> for farming income</li>
```

**Characteristics**:
- List item with line reference
- Brief instructional text
- References LINE-9600

### Extraction Strategy

**Principle Parser Algorithm**:

1. Search `<p>` and `<li>` tags for text containing line references
2. Extract line numbers using pattern: `\bline\s+(\d{4})\b` (case-insensitive)
3. Exclude any tags where `is_rule_definition()` returns True
4. Create ExtractedContent with:
   - `content_type`: PRINCIPLE
   - `citation_id`: `{source_file}-PRINCIPLE-{seq}`
   - `references`: List of LINE-XXXX found in text

**Code Implementation**:

```python
def extract_line_references(text: str) -> list[str]:
    """Extract LINE-XXXX references from text."""
    pattern = r'\bline\s+(\d{4})\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return sorted(set(f"LINE-{num}" for num in matches))

def parse(html_path: str) -> list[ExtractedContent]:
    """Extract principles from HTML."""
    for tag in soup.find_all(['p', 'li']):
        if is_rule_definition(tag):
            continue  # Skip rule definitions

        text = tag.get_text(strip=True, separator=" ")
        references = extract_line_references(text)

        if references:
            # Create PRINCIPLE content
```

### YAML Output Format

```yaml
principles:
- citation_id: t4002-6-PRINCIPLE-2
  content_type: PRINCIPLE
  text: "Enter on line 9925 the total business part of the cost of the equipment."
  source_file: t4002-6.html
  anchor_id: null
  references:
    - LINE-9925
- citation_id: t4002-6-PRINCIPLE-3
  content_type: PRINCIPLE
  text: "Enter on line 9927 the total business part of the cost of the buildings.
         The cost includes the purchase price of the building, and any related
         expenses you should add to the capital cost of the building, such as
         legal fees, land transfer taxes and mortgage fees."
  source_file: t4002-6.html
  anchor_id: null
  references:
    - LINE-9927
```

### Validation Tests

**Test 1: Extract principles from t4002-6.html**

```bash
uv run extract-principles cra_documents/cra_t4002e_rev24_dump/t4002-6.html output/t4002-6/principles.yml
grep -c "citation_id:" output/t4002-6/principles.yml
# Expected: 30 principles extracted
```

**Test 2: Verify content type**

```bash
grep "content_type:" output/t4002-6/principles.yml | sort | uniq -c
# Expected: 30   content_type: PRINCIPLE
```

**Test 3: Verify references extracted**

```bash
grep -A 2 "references:" output/t4002-6/principles.yml | head -20
# Expected: Lists like "- LINE-9925", "- LINE-9927", etc.
```

### Extraction Results from t4002-6.html

**Total Principles**: 30

**Common Line References**:
- LINE-9925 (equipment costs)
- LINE-9927 (building costs)
- LINE-9923 (land acquisitions)
- LINE-9929 (quota acquisitions)
- LINE-9604 (insurance proceeds)
- LINE-9936 (CCA total)
- LINE-8230, LINE-9600, LINE-9270, LINE-9790 (income/expense reporting)

**Content Distribution**:
- Instructional paragraphs: ~22 principles
- Cross-references: ~4 principles
- List items: ~4 principles

### Phase 2 Status

✅ **Implementation Complete**
- Models: ContentType enum, ExtractedContent Pydantic model
- Parser: extract_line_references(), parse()
- CLI: extract-principles command
- Tests: 21 tests (6 model + 15 parser), all passing
- Documentation: Pattern examples, YAML format, validation commands

**Known Limitations** (baseline, not perfect):
- Simple regex pattern may miss complex line number formats
- Does not extract semantic relationships between principles
- No deduplication of similar instructional text
- Citation IDs are sequential (not stable across re-extraction)

**Future Enhancements** (Phase 3+):
- Add TABLES, EXAMPLES, GUIDANCE content types
- Semantic relationship extraction
- Stable citation ID generation

## Future Content Types

*This document will expand as we add support for:*

- **TABLES**: Structured data (CCA rates, deduction limits) ⏳
- **EXAMPLES**: Case studies with calculations ⏳
- **GUIDANCE**: General instructions and definitions ⏳

## References

- Duplicate analysis: `docs/DUPLICATE_ANALYSIS.md`
- Improved capture plan: `docs/IMPROVED_CAPTURE_PLAN.md`
- Classic parser implementation: `src/qe_tax_rag/extraction/ca/classic_parser.py`
