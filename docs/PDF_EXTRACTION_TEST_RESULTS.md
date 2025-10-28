# PDF Extraction Test Results

This document tracks test results for the PDF extraction pipeline implemented in Phase 1.

## Test 1: Introduction Section (Pages 1-9)

**Date**: 2025-10-27
**Command**: `uv run extract-pdf T4002-Business-Expenses-Guide.pdf output/pdf_test/introduction.yml --start-page 1 --end-page 9`

### Results

**Extraction Statistics**:
- Sections processed: 1 (Introduction: pages 1-9)
- Content items extracted: 34 total
  - 17 DEFINITION items (glossary terms from pages 8-9)
  - 17 PRINCIPLE items (cross-references, procedural guidance)
- LLM API calls: 1
- Extraction time: ~22 seconds
- YAML output: 427 lines

**Quality Metrics**:
- ✅ Citation ID format: All items follow `T4002-P{page}-ITEM{n}` pattern
- ✅ Page number accuracy: All items correctly tagged with page 1-9
- ✅ Section attribution: All items have `section_title: "Introduction"`
- ✅ Content type classification: Correctly distinguished DEFINITION vs PRINCIPLE
- ✅ Lineage tracking: Complete source_file, page_number, section_title metadata

**Sample Extractions**:

DEFINITION example (page 8):
```yaml
- citation_id: T4002-P8-ITEM18
  content_type: DEFINITION
  text: "Accelerated investment incentive property (AIIP) – property that is eligible for an enhanced first-year allowance..."
  page_number: 8
  section_title: Introduction
```

PRINCIPLE example (page 2):
```yaml
- citation_id: T4002-P2-ITEM1
  content_type: PRINCIPLE
  text: "If you are a trust, use Guide T4013, T3 Trust Guide."
  page_number: 2
  section_title: Introduction
```

### Issues Fixed During Testing

1. **Gemini Model Name (llm_client.py)**
   - Error: `404 models/gemini-1.5-flash is not found for API version v1beta`
   - Fix: Changed default model from `gemini-1.5-flash` → `gemini-2.0-flash-exp`
   - Aligned with existing adjudicator/llm_parser model names

2. **Markdown Code Fences (pdf_parser.py)**
   - Error: `Failed to parse LLM response as JSON: Expecting value: line 1 column 1`
   - Issue: Gemini wraps JSON responses in markdown fences (```json ... ```)
   - Fix: Added removeprefix/removesuffix logic to strip fences before json.loads()

3. **YAML Generator Incompatibility (pdf_cli.py)**
   - Error: `generate() got an unexpected keyword argument 'content'`
   - Issue: yaml_generator.generate() expects `list[ExtractedRule]`, PDF pipeline uses `list[ExtractedContent]`
   - Fix: Implemented inline YAML writer with schema metadata wrapper

### Architecture Validation

**Two-Pass Approach Performance**:
- Pass 1 (structure discovery): <1 second, no LLM calls
- Pass 2 (content extraction): ~22 seconds, 1 LLM call

**Cost Efficiency**:
- Pages processed: 9
- API calls: 1
- Per-page approach would require: 9 calls
- Savings: 89% reduction in API costs for this section

### Status

✅ **PASSED** - Introduction section extraction working end-to-end with proper lineage tracking and content type classification.

---

## Test 2: Chapter 1 - General Information (Pages 10-23)

**Status**: Pending
**Expected content types**: RULE, PRINCIPLE, DEFINITION, possibly FORMULA

---

## Full Document Projection

**Document structure** (discovered by structure_detector.py):
1. Introduction: pages 1-9
2. Chapter 1 – General information: pages 10-23
3. Chapter 2 – Income: pages 24-37
4. Chapter 3 – Expenses: pages 38-68
5. Chapter 4 – Capital cost allowance: pages 69-91
6. Chapter 5: pages 92-94
7. Chapter 6: pages 95-113

**Full extraction estimate**:
- Total sections: 7
- Total API calls: 7
- Cost reduction vs per-page: 93% (7 calls instead of 113)
- Estimated total time: ~2-3 minutes (assuming similar per-section times)
