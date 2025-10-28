# PDF Extraction Plan: Lightweight Semantic Chunking (REVISED)

## Philosophy

**Simplicity with Transparency + API Efficiency**
- Two lightweight passes: structure discovery (local, fast) → content extraction (LLM)
- 15-25 API calls (not 113) by respecting document structure
- Perfect lineage: file → section → page → item
- Simple heuristics (font size) instead of complex MoE architecture

## The Problem We're Solving

- ❌ 113 LLM calls (one per page): Expensive, rate limit risk, slow
- ❌ Fixed 4-page chunks: Arbitrary boundaries split semantic units (tables, rules)
- ✅ Semantic chunks based on document structure: Natural boundaries, optimal context, 15-25 API calls

## Architecture (Lightweight Two-Pass)

```
T4002.pdf (113 pages)
    ↓
PASS 1: Structure Discovery (LOCAL - NO LLM, FAST)
    ├─> Scan all pages for heading patterns (PyMuPDF)
    ├─> Heuristic: font_size > 16pt + matches "Chapter \d+" regex
    └─> Output: List of semantic sections
         [
           {"title": "Chapter 1 – General information", "pages": (10, 37)},
           {"title": "Chapter 3 – Expenses", "pages": (38, 68)},
           {"title": "Chapter 4 – Capital cost allowance", "pages": (69, 91)},
           ...
         ]
         (~15-25 sections for T4002)
    ↓
PASS 2: Content Extraction (ONE LLM CALL PER SECTION)
    For each semantic section (e.g., Chapter 3, pages 38-68):
        ├─> Extract all text + tables from page range (pdfplumber)
        ├─> Send to LLM (Gemini - detailed prompt)
        │    └─> Returns structured JSON for all rules/principles/tables
        ├─> Convert to ExtractedContent with lineage:
        │    ├─> page_number: specific page within section
        │    ├─> section_title: "Chapter 3 – Expenses"
        │    ├─> citation_id: "T4002-P{page}-ITEM{i}"
        └─> Collect all chunks
    ↓
YAML generation → DatabaseChunk → SQLite (FTS5 + vector)
```

## Implementation Plan

### Phase 1: Package Setup (0.5 days)

- Create `src/qe_tax_rag/extraction/ca/pdf/` package
- Add dependencies: `pdfplumber = "^0.11.0"`, `PyMuPDF = "^1.23.0"`
- Files: `__init__.py`, `structure_detector.py`, `pdf_parser.py`, `pdf_cli.py`

### Phase 2: Structure Detector (0.5 days)

**New module**: `structure_detector.py`

```python
@dataclass
class SemanticSection:
    title: str
    page_range: tuple[int, int]  # (start, end) inclusive

def discover_sections(pdf_path: Path) -> list[SemanticSection]:
    """
    Scan PDF for chapter/section headings using font metadata.

    Simple heuristic:
    - font_size > 16pt
    - text matches r"Chapter \d+|Appendix"

    Returns:
        List of semantic sections with natural boundaries.
        Example: [SemanticSection("Chapter 1", (10, 37)), ...]
    """
```

**Implementation**:

1. Use PyMuPDF to extract text blocks with font metadata
2. Identify headings: `font_size > 16 AND matches("Chapter \d+")`
3. Build section list: first section starts at page 1, ends before next heading
4. LOCAL operation, no LLM, runs once at start (~1-2 seconds for 113 pages)

### Phase 3: PDF Parser (1 day)

**Module**: `pdf_parser.py`

```python
def parse_section(
    pdf_path: Path,
    section: SemanticSection,
    cache_dir: Path | None = None,
) -> list[ExtractedContent]:
    """
    Extract and structure content from a semantic section.

    Args:
        section: SemanticSection with title and page_range

    Returns:
        List of ExtractedContent with:
        - citation_id: "T4002-P{page}-ITEM{i}"
        - page_number: specific page within section
        - section_title: from SemanticSection
        - table_data: structured when applicable
    """
```

**Steps per section**:

1. Extract text + tables from all pages in section.page_range
2. Consolidate into single LLM context string
3. Call Gemini with detailed prompt (specifying RULE/PRINCIPLE/DEFINITION/FORMULA/TABLE/EXAMPLE)
4. Parse JSON → list of ExtractedContent
5. Set lineage: page_number (within range), section_title

### Phase 4: Simple Orchestrator (0.5 days)

**Module**: `pdf_cli.py`

```python
def extract_pdf(
    pdf_path: Path,
    output_yaml: Path,
) -> dict:
    """Extract PDF using semantic chunking."""

    # Pass 1: Discover structure (local, fast)
    sections = structure_detector.discover_sections(pdf_path)
    logger.info(f"Discovered {len(sections)} semantic sections")

    # Pass 2: Extract content (LLM per section)
    all_content = []
    for section in sections:
        chunks = pdf_parser.parse_section(pdf_path, section)
        all_content.extend(chunks)

    # Generate YAML
    yaml_generator.generate(content=all_content, output_path=output_yaml)

    return {
        "total_sections": len(sections),
        "total_chunks": len(all_content),
        "api_calls": len(sections),  # 15-25 instead of 113!
    }
```

**Key improvement**: No chunk range generation, no overlap, no deduplication!

### Phase 5: Model Extension (0.5 days)

**Extend `ExtractedContent`** in `ca/models.py`:

```python
class ExtractedContent(BaseModel):
    # ... existing fields ...

    # PDF-specific lineage
    page_number: int | None = Field(
        default=None,
        description="PDF page number (1-indexed)"
    )

    section_title: str | None = Field(
        default=None,
        description="Section/chapter title from structure detection"
    )
```

**Lineage**: `source_file → section_title → page_range → page_number → citation_id`

### Phase 6: LLM Prompt Engineering (0.5 days)

**Detailed prompt** optimized for semantic sections:

```
You are extracting structured content from "{section.title}"
(pages {section.page_range[0]}-{section.page_range[1]}) of the T4002 CRA guide.

Extract ALL instances of these content types:
- RULE: Tax rules with line numbers (e.g., "Line 8523 – Meals")
- PRINCIPLE: Cross-references to other sections/forms
- DEFINITION: Glossary terms and definitions
- FORMULA: Calculation methods and examples
- TABLE: Structured data (already extracted separately)
- EXAMPLE: Illustrative cases

For each item, include:
- type: content type
- text: full text content
- page_number: specific page where found
- applies_to: ["business"|"farming"|"fishing"]

Return JSON array: [{"type": "RULE", "page_number": 42, ...}, ...]
```

### Phase 7: Testing & Validation (1 day)

1. **Structure detection test**: Verify ~15-25 sections discovered with correct boundaries
2. **Unit tests**: Section extraction, citation_id generation, table handling
3. **Integration test**: Extract Chapter 3 (pages 38-68), cross-validate with HTML
4. **Full extraction**: All 113 pages via ~15-25 API calls
5. **Cost analysis**: Compare actual API calls vs. per-page approach
6. **Search quality test**: Run 10 test queries, measure RAG quality
7. **Lineage audit**: Verify every chunk traces to section + page

## Success Criteria

✅ Structure discovery finds 15-25 semantic sections (no LLM required)
✅ Total API calls: 15-25 (not 113!) - 78% cost reduction
✅ Citation IDs: "T4002-P{page}-ITEM{i}" format
✅ Lineage: source_file → section_title → page_range → page_number
✅ Tables stored as structured data
✅ No content split across section boundaries (optimal RAG context)
✅ CLI works: `uv run extract-pdf input.pdf output.yml`
✅ Search quality baseline ≥ per-page approach (likely better due to complete semantic units)

## Timeline

- Phase 1: 0.5 days (package setup)
- Phase 2: 0.5 days (structure detector)
- Phase 3: 1 day (pdf_parser)
- Phase 4: 0.5 days (orchestrator)
- Phase 5: 0.5 days (model extension)
- Phase 6: 0.5 days (prompt engineering)
- Phase 7: 1 day (testing)

**Total: ~4.5 days**

## API Call Comparison

- ❌ Per-page approach: 113 API calls
- ❌ Fixed 4-page chunks: ~29 API calls (but splits semantic units)
- ✅ Lightweight semantic: 15-25 API calls (respects document structure)

**Cost savings**: 78-87% reduction vs. per-page, with BETTER RAG quality!

## What We're NOT Building (Kept Simple)

❌ Complex multi-level hierarchy mapping
❌ Mixture-of-Experts architecture
❌ Overlap and deduplication logic
❌ Circuit breakers and retry logic (can add later if needed)
❌ ML-based heading detection (simple heuristics work)

## Key Advantages Over Original Plan

1. **Simpler**: Single structure_detector module replaces complex two-pass MoE
2. **Cheaper**: 15-25 API calls vs. 113 (78% cost reduction)
3. **Better RAG quality**: Complete semantic units, no arbitrary splits
4. **Better lineage**: section_title + page_number provides rich context
5. **Still transparent**: Simple font-based heuristics, easy to debug

## Design Decisions

### Why Lightweight Two-Pass?

**Original concerns that led to this design**:

- **Cost/Rate limits**: 113 API calls for per-page extraction is expensive and risky
- **Quality**: Arbitrary page boundaries split tables, rules, and their explanations
- **Simplicity**: Complex MoE with overlap/deduplication was over-engineered

**This approach solves all three**:

- Reduces API calls by 78-87% (15-25 vs. 113)
- Preserves complete semantic units (chapters/sections)
- Simple deterministic structure detection (no complex ML)

### Why Font-Based Heuristics?

Tax documents have consistent visual hierarchy:

- Chapter headings: Large font (>16pt), bold, specific patterns
- Section headings: Medium font (14-16pt)
- Body text: Normal font (<12pt)

Simple pattern matching is sufficient and debuggable.

### Why Section-Level Chunking?

**RAG quality depends on context completeness**:

- A rule explanation might reference a table on the next page
- Examples often span multiple pages within a chapter
- Cross-references assume the reader has section context

Semantic chunking preserves this context, improving LLM extraction quality and downstream RAG accuracy.

## Zen MCP Analysis Summary

This plan was validated through collaborative analysis with Zen MCP (gemini-2.5-pro), which identified:

1. **Original plan contradiction**: Claimed semantic chunking but implemented fixed 4-page windows
2. **Over-engineering**: MoE, overlap, deduplication solved problems created by arbitrary chunking
3. **Sweet spot**: Lightweight structure detection + semantic chunking balances simplicity and efficiency
4. **Risk mitigation**: Fixed chunks guarantee split content; semantic chunks minimize this risk

**Key insight**: "The optimal 'size' isn't a fixed number of pages. It's a variable page range defined by the document's logical sections."

## Next Steps After Approval

1. Create `src/qe_tax_rag/extraction/ca/pdf/` package
2. Implement `structure_detector.py` with font-based heading detection
3. Implement `pdf_parser.py` with section-level extraction
4. Build `pdf_cli.py` orchestrator
5. Extend `ExtractedContent` model with page_number and section_title
6. Test structure detection on T4002 (verify ~15-25 sections found)
7. Full extraction and RAG quality baseline
