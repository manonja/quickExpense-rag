# T4002 HTML Content Patterns

**Purpose**: Document HTML patterns for different content types found in CRA T4002 guide
dumps to enable accurate extraction and prevent duplicates.

**Created**: 2025-10-27 **Updated**: 2025-10-27 (Phase 3 - TABLE content type)
**Status**: Phase 3 (Rule Definitions, Principles, Tables)

## Rule Definitions

### What Makes It a Definition

A **rule definition** is the canonical source of truth for a line-numbered expense rule.
It contains:

1. **Anchor ID with strict pattern**: `id="tocch{chapter}ln{line_number}"`
1. **Heading tag**: Usually `<h3>` with "Line {number} – {title}" format
1. **Full content**: Complete explanation, instructions, and examples

### HTML Structure

```html
<h3><a id="tocch2ln9600"></a><span class="nowrap">Line 9600 –</span> Other income</h3>
<p>Enter the total of any other farming income you have not specifically identified on another line. The following paragraphs identify some of these income items.</p>
```

**Key characteristics**:

- Anchor ID: `tocch2ln9600` (chapter 2, line 9600)
- Pattern: `tocch\dln\d{4}` (chapter digit + "ln" + 4-digit line number)
- Location: Definition appears in the chapter where the line is explained (e.g., Chapter
  2 for farming income)
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
- ❌ This is a cross-reference in Chapter 3 (expenses) pointing back to the definition in
  Chapter 2 (income)
- ❌ Does not contain the full rule explanation
- ❌ Heading describes where to report, not what the rule is

## Rule References

### What Makes It a Reference

A **rule reference** mentions a line number but does NOT provide the canonical
definition. It:

1. **Lacks anchor ID**: Either no `<a>` tag, or `<a>` without matching `tocch\dln\d{4}`
   pattern
1. **Cross-references other chapters**: Points to where the rule is defined
1. **Brief mentions**: Short text or list items mentioning line numbers

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
1. For each tag, check if it has an `<a>` child with `id` attribute
1. Validate anchor ID matches strict pattern: `^tocch\dln\d{4}$`
1. Extract ONLY tags passing both checks

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

A **principle** is text that references line-numbered rules in an instructional or
cross-reference context, but is NOT a rule definition. It:

1. **Contains line references**: Mentions "line {number}" in text
1. **Lacks anchor ID**: No `tocch\dln\d{4}` anchor pattern
1. **Instructional context**: Explains how to use or apply rules

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
1. Extract line numbers using pattern: `\bline\s+(\d{4})\b` (case-insensitive)
1. Exclude any tags where `is_rule_definition()` returns True
1. Create ExtractedContent with:
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

## Table Content (Phase 3)

### What Makes It a Table

A **table** is structured tabular data with column headers and row data. Tables are used
for:

- CCA (Capital Cost Allowance) rate schedules
- Property class assignments
- Deduction limits and thresholds

Phase 3 implements a baseline extractor (80/20 principle) that:

1. **Requires standard HTML structure**: `<table>` with `<thead>` and `<tbody>`
1. **Converts to list-of-dicts format**: RAG-friendly structured data
1. **Gracefully degrades**: Skips malformed tables with warnings

### HTML Structures

#### Type 1: CCA Property Classes Table

```html
<table class="table table-bordered table-striped table-responsive">
  <thead>
    <tr>
      <th>Depreciable property</th>
      <th>Class No.</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Chain-saws</td>
      <td>10</td>
    </tr>
    <tr>
      <td>Computer equipment and systems software – Acquired after March 22, 2004</td>
      <td>45</td>
    </tr>
    <!-- ~105 more rows -->
  </tbody>
</table>
```

**Characteristics**:

- Standard `<thead>` with `<th>` headers
- Standard `<tbody>` with `<tr>` rows and `<td>` cells
- Consistent column count across all rows

#### Type 2: CCA Rates Table

```html
<table class="table table-bordered table-striped table-responsive">
  <thead>
    <tr>
      <th>Class No.</th>
      <th>Rates</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Class 1</td>
      <td>4%</td>
    </tr>
    <tr>
      <td>Class 8</td>
      <td>20%</td>
    </tr>
    <!-- ~18 more rows -->
  </tbody>
</table>
```

**Characteristics**:

- Simple 2-column structure
- Numerical data (class numbers, percentages)
- Header row clearly defines column semantics

### Extraction Strategy

**Table Parser Algorithm**:

1. Find all `<table>` tags in HTML
1. For each table:
   - Extract column headers from `<thead>` `<th>` elements
   - Extract row data from `<tbody>` `<tr>` elements
   - Convert each row to dictionary: `{header1: cell1, header2: cell2, ...}`
1. Skip tables without proper structure (no `<thead>` or `<tbody>`)
1. Skip rows with mismatched column counts
1. Create ExtractedContent with:
   - `content_type`: TABLE
   - `citation_id`: `{source_file}-TABLE-{seq}`
   - `table_data`: List of row dictionaries

**Code Implementation**:

```python
def extract_table_data(table_tag: Tag) -> list[dict[str, str]] | None:
    """Extract structured data from a single table element."""
    # Extract headers from <thead>
    thead = table_tag.find("thead")
    if not thead:
        logger.debug("Skipping table without <thead>")
        return None

    headers = [th.get_text(strip=True) for th in thead.find_all("th")]
    if not headers:
        return None

    # Extract rows from <tbody>
    tbody = table_tag.find("tbody")
    if not tbody:
        return None

    table_data: list[dict[str, str]] = []
    for row in tbody.find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]

        # Skip rows with mismatched column count
        if len(cells) != len(headers):
            logger.warning(f"Skipping row with {len(cells)} cells (expected {len(headers)})")
            continue

        # Create row dictionary
        row_dict = dict(zip(headers, cells))
        table_data.append(row_dict)

    return table_data if table_data else None
```

### YAML Output Format

```yaml
tables:
- citation_id: t4002-10-TABLE-1
  content_type: TABLE
  text: Table 1 from t4002-10.html
  source_file: t4002-10.html
  anchor_id: null
  references: []
  table_data:
  - Depreciable property: Chain-saws
    Class No.: '10'
  - Depreciable property: Computer equipment and systems software – Acquired after March 22, 2004
    Class No.: '45'
  # ... 105 more rows
- citation_id: t4002-10-TABLE-2
  content_type: TABLE
  text: Table 2 from t4002-10.html
  source_file: t4002-10.html
  anchor_id: null
  references: []
  table_data:
  - Class No.: Class 1
    Rates: 4%
  - Class No.: Class 8
    Rates: 20%
  # ... 18 more rows
```

### Validation Tests

**Test 1: Extract tables from t4002-10.html**

```bash
uv run extract-tables cra_documents/cra_t4002e_rev24_dump/t4002-10.html output/t4002-10/tables.yml -v
# Expected: 2 tables extracted
```

**Test 2: Verify table structure**

```bash
grep -c "citation_id:" output/t4002-10/tables.yml
# Expected: 2 (one per table)

grep "content_type:" output/t4002-10/tables.yml | sort | uniq -c
# Expected: 2   content_type: TABLE
```

**Test 3: Verify table data format**

```bash
grep -A 5 "table_data:" output/t4002-10/tables.yml | head -20
# Expected: Lists of dictionaries with column headers as keys
```

### Extraction Results from t4002-10.html

**Total Tables**: 2

**Table 1: CCA Property Classes**

- Citation ID: `t4002-10-TABLE-1`
- Rows: 107
- Columns: 2 (Depreciable property, Class No.)
- Content: Property types mapped to CCA class numbers

**Table 2: CCA Rates**

- Citation ID: `t4002-10-TABLE-2`
- Rows: 20
- Columns: 2 (Class No., Rates)
- Content: CCA class numbers mapped to depreciation rates

### Phase 3 Status

✅ **Implementation Complete**

- Models: ContentType.TABLE enum, table_data field on ExtractedContent
- Parser: extract_table_data(), parse() in table_parser.py
- CLI: extract-tables command
- Tests: Manual validation on t4002-10.html, all passing
- Documentation: Pattern examples, YAML format, validation commands

**Known Limitations** (80/20 baseline, not perfect):

1. **No colspan/rowspan support**: Only simple grid structures (cells aligned in
   rows/columns)
1. **Nested tables extracted flat**: Loses hierarchical relationships if tables are
   nested
1. **Tables without `<thead>` or `<tbody>` skipped**: Requires standard HTML5 table
   structure
1. **No caption/title extraction**: Table metadata (captions, summaries) not captured
1. **Assumes consistent column counts**: Rows with mismatched cell counts are skipped
   with warnings

**Future Enhancements** (Phase 4+):

- Add caption/title extraction for table context
- Support for complex table structures (merged cells, nested tables)
- Semantic table type classification (rates vs properties vs limits)
- Extract table relationships (e.g., "see Table X for rates")

## Future Content Types

*This document will expand as we add support for:*

- **EXAMPLES**: Case studies with calculations ⏳
- **GUIDANCE**: General instructions and definitions ⏳

## References

- Duplicate analysis: `docs/DUPLICATE_ANALYSIS.md`
- Improved capture plan: `docs/IMPROVED_CAPTURE_PLAN.md`
- Classic parser implementation: `src/qe_tax_rag/extraction/ca/classic_parser.py`
