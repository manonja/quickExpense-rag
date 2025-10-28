# PDF Search Baseline Results
**Database**: `output/pdf_full/t4002_pdf.db` (757 items, 43% duplicates)
**Test Date**: 2025-10-28
**Evaluator**: Manual review of top-3 results per query

## Evaluation Criteria
✅ **Success**: At least one result in top-3 correctly answers the query
❌ **Fail**: No result in top-3 provides a correct/relevant answer
⚠️ **Partial**: Result is related but doesn't directly answer the query

---

## Query Results

### 1. "travel expenses"
**Status**: ❌ **FAIL**
**Top Results**:
1. `T4002-P18-adadfd6c` - EXAMPLE: Daycare expense journal (irrelevant)
2. `T4002-P4-06b4cff7` - RULE: Automobile leasing costs (somewhat related to travel, but not general travel expenses)
3. `T4002-P4-ad7181e9` - RULE: Automobile deduction limits (vehicle-specific, not general travel)

**Assessment**: No result covers general travel expenses (flights, hotels, meals while traveling). Only vehicle-related.

---

### 2. "vehicle deductions"
**Status**: ✅ **SUCCESS**
**Top Results**:
1. `T4002-P4-ad7181e9` - RULE: Automobile deduction limits for Class 10.1 vehicles (CORRECT - directly answers query)
2. `T4002-P9-a8b65066` - DEFINITION: Motor vehicle definition
3. `T4002-P9-a282f8c6-DUP2` - DEFINITION: Passenger vehicle definition

**Assessment**: First result directly answers the query with specific deduction limits.

---

### 3. "home office expenses"
**Status**: ⚠️ **PARTIAL**
**Top Results**:
1. `T4002-P25-021b498c` - PRINCIPLE: Reference to "Business-use-of-home expenses" on page 67 (indirect, but helpful)
2. `T4002-P15-9b70eb4a` - PRINCIPLE: Prepaid expenses reference (not relevant)
3. `T4002-P14-9b70eb4a` - PRINCIPLE: Prepaid expenses reference (duplicate, not relevant)

**Assessment**: First result references the topic but doesn't provide the actual rule. User would need to search further.

---

### 4. "GST/HST requirements"
**Status**: ✅ **SUCCESS**
**Top Results**:
1. `T4002-P21-b62f55a9` - PRINCIPLE: Registration information for GST/HST with reference to memorandum (CORRECT)
2. `T4002-P21-12942ae3-DUP1` - PRINCIPLE: General GST/HST information reference
3. `T4002-P21-12942ae3-DUP2` - PRINCIPLE: General GST/HST information reference (duplicate)

**Assessment**: First result provides registration guidance, though it's a reference to another document.

---

### 5. "can I deduct my car lease"
**Status**: ✅ **SUCCESS**
**Top Results**:
1. `T4002-P4-06b4cff7` - RULE: Maximum deductible automobile leasing costs ($950 to $1,050/month) (CORRECT - directly answers)
2. `T4002-P8-7451c2df-DUP2` - DEFINITION: Capital cost allowance definition
3. `T4002-P4-6328030e` - RULE: Short-term rental deduction restrictions

**Assessment**: First result directly answers with specific limits.

---

## Summary Statistics (5 queries tested)

| Metric | Count | Percentage |
|--------|-------|------------|
| ✅ Success | 3 | 60% |
| ⚠️ Partial | 1 | 20% |
| ❌ Fail | 1 | 20% |

**Baseline Success Rate**: **60%** (3/5 queries)
**Target Success Rate**: **80%** (4/5 queries)

---

## Key Observations

### Issues Identified:
1. **Duplicate content in results** - Seeing `-DUP1`, `-DUP2` suffixes polluting top results
2. **Missing content coverage** - "travel expenses" query finds only vehicle-related, not general travel (flights, hotels)
3. **Cross-references instead of content** - Results often point to "see page X" rather than actual rules
4. **Limited scope extraction** - Only extracted pages 1-47 (Introduction + Chapter 1-2), missing later chapters with more expense rules

### Positive Findings:
1. **Search is functional** - Hybrid search (FTS5 + vector) returns relevant results
2. **Lineage tracking works** - All results have proper citation IDs and source tracking
3. **Specific queries work well** - Targeted queries like "car lease" return precise answers
4. **Content quality appears accurate** - Sample spot-checks show extraction matches source PDF

---

## Recommendations

1. **Fix duplicate pollution** (Phase 2) - Deduplication will remove `-DUP#` results, improving result quality
2. **Expand coverage** - Current extraction only covers 47/113 pages (42% of PDF)
3. **Investigate "travel expenses" gap** - May need to extract Chapter 3 (Expenses) for comprehensive coverage
4. **Improve cross-reference handling** - Consider extracting referenced content or providing page context

**Next Step**: Continue baseline testing with remaining 16 queries to get comprehensive metrics.
