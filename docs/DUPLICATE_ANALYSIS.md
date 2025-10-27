# Duplicate Citation ID Analysis

**Investigation Date**: 2025-10-24
**Resolution Date**: 2025-10-27
**Issue**: Database build fails with duplicate `citation_id` errors
**Duplicates Found**: LINE-9600, LINE-9604
**Status**: ✅ RESOLVED (Phase 1 implementation)

## Findings

### LINE-9600: Rule Definition vs. Rule Reference

**Definition (t4002-4.html:632)**:
```html
<h3><a id="tocch2ln9600"></a><span class="nowrap">Line 9600 –</span> Other income</h3>
```
- **Type**: RULE (line-numbered definition)
- **Pattern**: Has anchor ID `tocch2ln9600`
- **Context**: Chapter 2 – Income (Farming income section)
- **Content**: Full rule definition explaining what to report at line 9600

**References (t4002-6.html:458-459)**:
```html
<li><span class="nowrap">line 9600</span> for farming income</li>
<li><span class="nowrap">line 9600</span> for fishing income</li>
```
- **Type**: PRINCIPLE/GUIDANCE (references the rule)
- **Pattern**: NO anchor ID, just mentions "line 9600"
- **Context**: Chapter 3 – Expenses (instructions on where to report income)
- **Content**: Cross-reference telling users to report income at line 9600

**Conclusion**:
- t4002-4.html has the CANONICAL RULE DEFINITION
- t4002-6.html has REFERENCES to that rule
- Our classic parser extracted BOTH as separate "rules" → duplicate

### LINE-9604: Rule Definition vs. Rule Reference

**Definition (t4002-4.html:666)**:
```html
<h3><a id="tocch2ln9604"></a><span class="nowrap">Line 9604 –</span> Insurance proceeds</h3>
```
- **Type**: RULE (line-numbered definition)
- **Pattern**: Has anchor ID `tocch2ln9604`
- **Context**: Chapter 2 – Income (Farming income section)
- **Content**: Full rule definition for insurance proceeds

**References (t4002-6.html:336, 424)**:
```html
<p>For more information, see <a href="t4002-4.html#tocch2ln9604">
<span class="nowrap">Line 9604 –</span> Insurance proceeds</a>.</p>
```
- **Type**: PRINCIPLE/GUIDANCE (cross-reference with hyperlink)
- **Pattern**: NO anchor ID, has `<a href=` to the definition
- **Context**: Chapter 3 – Expenses (cross-references to income section)
- **Content**: "For more information, see Line 9604..."

**Conclusion**:
- t4002-4.html has the CANONICAL RULE DEFINITION
- t4002-6.html has CROSS-REFERENCES (hyperlinks) to that definition
- Our classic parser extracted hyperlink text as a "rule" → duplicate

## Root Cause

**Classic Parser Logic Flaw**:
Our parser looks for patterns like "Line 9XXX" in the HTML text but doesn't distinguish between:
1. **Rule definitions**: Have anchor IDs (`id="tocch2ln9604"`), are headings, contain full content
2. **Rule references**: No anchor IDs, are links or mentions, point to definitions

Both get extracted as separate rules with same `citation_id = "LINE-9604"` → database unique constraint violation.

## Impact

From the 20 rules extracted:
- **16 rules from t4002-4.html**: Likely ALL are canonical definitions (Chapter 2 – Income)
- **4 rules from t4002-6.html**: Some are definitions, some are references
- **2 confirmed duplicates**: LINE-9600, LINE-9604 (references in t4002-6.html)
- **Possibly more**: Need to check if other t4002-6.html "rules" are also references

## Solutions

### Option 1: Source File Prefix (RECOMMENDED)
Add source file to citation_id: `t4002-4-LINE-9600` vs `t4002-6-LINE-9600`

**Pros**:
- Simple to implement
- Preserves all extracted content
- Makes source file explicit in citation

**Cons**:
- Breaks backwards compatibility with production database (LINE-9600 format)
- References and definitions treated equally (both become searchable "rules")
- Doesn't solve the semantic problem (references aren't rules)

### Option 2: Filter Out References
Update classic parser to only extract content with anchor IDs (`id="tocch2ln9XXX"`)

**Pros**:
- Only extracts canonical rule definitions
- No duplicates
- Maintains backwards compatibility (same LINE-XXXX format)

**Cons**:
- Loses reference content (though references aren't rules anyway)
- Need to update parser logic

### Option 3: Hybrid - Different Content Types
- Definitions: `citation_id = "LINE-9600"`, `content_type = "RULE"`
- References: `citation_id = "t4002-6-REF-1"`, `content_type = "PRINCIPLE"`

**Pros**:
- Semantically correct
- Preserves all content
- Sets up V2 architecture

**Cons**:
- Requires V2 schema implementation
- Most complex solution
- Delays delivery

## Recommended Approach

**Phase 1 (NOW - Quick Fix)**: Option 2
- Update classic parser to only extract headings with anchor IDs
- This gives us TRUE rule definitions only
- Maintains backwards compatibility
- Delivers value immediately

**Phase 2 (LATER - V2)**: Option 3
- Implement multi-content-type extraction
- References become "PRINCIPLE" content type
- Full semantic model

## Validation Strategy

After implementing fix, verify:
```bash
# 1. Check extracted YAML for duplicates
grep "^- rule_number:" output/rules.yml | awk '{print $3}' | sort | uniq -d

# 2. Verify only anchor-ID rules extracted from t4002-6.html
grep "source_file: t4002-6.html" output/rules.yml -A 5 | grep "anchor_id:"

# 3. Count total unique rules
grep -c "^- rule_number:" output/rules.yml
```

Expected result after fix:
- **t4002-4.html**: 16 rules (unchanged)
- **t4002-6.html**: 2 rules (down from 4 - removed 2 references)
- **Total**: 18 rules (no duplicates)

## Resolution (Phase 1 - Completed 2025-10-27)

**Implemented**: Option 2 (Filter Out References)

### Changes Made

1. **Added `is_rule_definition()` function** to classic parser
   - Validates anchor IDs match pattern `^tocch\dln\d{4}(?:\w+)?$`
   - Filters rule definitions (with anchors) from references (without anchors)

2. **Updated `parse()` filtering logic**
   - Combined `is_line_rule()` and `is_rule_definition()` checks
   - Only extracts h3 tags with both line number pattern AND anchor IDs

3. **Enhanced pattern matching**
   - Handles combined heading patterns: "Line 9790or9270 –", "Line 8960 and Line 8963 –"
   - Non-greedy match: `r"Line (\d+).*?–\s*(.+)"`

### Validation Results

**Zero duplicates achieved**:
```bash
cat output/t4002-*/rules.yml | grep "rule_number:" | sort | uniq -d | wc -l
# Output: 0 ✅
```

**Extraction counts**:
- **t4002-4.html**: 16 rules (classic parser) ✅
- **t4002-6.html**: 0 rules (classic parser) - All references correctly filtered ✅
- **t4002-5.html**: 65 rules (classic parser) - Improved from 63 (found 2 missed combined headings) ✅

### Commits

- `b07fd2e`: Initial anchor ID validation
- `0ea9ea2`: CONTENT_PATTERNS.md documentation
- `b96a759`: Enhanced pattern matching for combined headings
- `06aa44c`: Phase 1 validation results

### Documentation

- Implementation details: `docs/IMPROVED_CAPTURE_PLAN.md` (Phase 1)
- Validation results: `docs/PHASE1_VALIDATION_RESULTS.md`
- Pattern documentation: `docs/CONTENT_PATTERNS.md`

**Next Phase**: Phase 2 will implement Option 3 (multi-content-type extraction) to capture references as PRINCIPLE content type.
