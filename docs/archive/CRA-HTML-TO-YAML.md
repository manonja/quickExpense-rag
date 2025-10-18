# Final Plan: Grounded MoE Pipeline with Text-Based LLM & Self-Correction

This plan details a state-of-the-art Python pipeline to convert local CRA HTML documents
into a verifiably accurate YAML file containing line-numbered expense rules.

______________________________________________________________________

### Phase 1: Schema and Environment Setup

This foundational step ensures the entire pipeline operates on a consistent and strict
data structure, which is critical for validation and preventing data drift.

1. **Define YAML Schema:** Create a new script, `scripts/parser/yaml_schema.py`, to
   define the canonical data structure for the output using Pydantic models. This will
   include an `ExtractedRule` model (with fields like `rule_number`, `content`,
   `business_type`, `source_citation`) and a root `RuleSet` model.
1. **Environment Setup:** Check `pyproject.toml` and `uv.lock` for necessary
   dependencies (`BeautifulSoup4`, `PyYAML`, `playwright`, `pillow`) and add them if
   they are missing.

**Latent Risk Covered:** Inconsistent or malformed data output. A Pydantic-based schema
acts as the single source of truth for data structure throughout the pipeline.

______________________________________________________________________

### Phase 2: Text-Based "Mixture-of-Experts" (MoE) Extraction

This phase uses two complementary parsing approaches on HTML text, with the LLM
providing semantic understanding without visual complexity.

1. **Expert 1: Classic Parser:**
   - **Logic (`scripts/parser/classic_parser.py`):** The `BeautifulSoup` parser uses
     regex pattern matching to find h3 tags with "Line XXXX –" structure. It extracts:
     - Line number and title from header text
     - Icon alt attributes to build `applies_to` list (income types)
     - Content from subsequent paragraphs and lists
     - Context fields (chapter from h1, section from preceding h2)
   - **Advantage:** Fast, deterministic, and reliable for well-structured HTML.
1. **Expert 2: Text-Based LLM Parser:**
   - **Logic (`scripts/parser/llm_parser.py`):** This expert uses semantic understanding
     of HTML structure: a. Use `BeautifulSoup` to extract the `<main>` tag content
     (reduces token usage) b. Pass the HTML text to **Gemini Flash/Pro** (text model,
     not Vision) c. The prompt instructs the model to extract line-numbered rules with
     clear JSON schema: *"Extract all rules matching 'Line XXXX –' pattern. For each
     rule, extract line number, title, content, icon applicability, and context fields
     (chapter, section, anchor_id). Return JSON array."*
   - **Advantage:** Resilient to HTML structural changes through semantic understanding.
     Can infer context and relationships between elements without rigid pattern
     matching.

**Key Simplification:** Text-based parsing eliminates browser automation (Playwright),
screenshot capture, and multimodal Vision API complexity. All CRA rules are available as
HTML files on disk - no visual rendering needed.

**Latent Risk Covered:** Icon semantics are preserved through alt text extraction (both
parsers). Text-based approach is sufficient since we have raw HTML source.

______________________________________________________________________

### Phase 3: Grounded Adjudication and Self-Correction

This phase is redesigned to align with the latest best practices for grounding LLM
outputs, ensuring all corrections are transparent, auditable, and factually tied to the
source document.

1. **Merge and Triage Logic:** The initial triage process (identifying "Perfect Match,"
   "Conflict," or "Orphan" rules) remains the same.
1. **The Grounding Adjudicator (Enhanced Auto-Correction):**
   - For each "Conflict" or "Orphan," a call is made to a powerful model (e.g., Gemini
     Pro) with a carefully structured, grounding-focused prompt.
   - **State-of-the-Art Prompting:** The prompt will require the model to perform a
     **Chain-of-Thought (CoT)** reasoning process and provide citations for its claims.
     The model will be required to return a JSON object with the following structure:
     ```json
     {
       "analysis": "A brief explanation of the discrepancy found.",
       "reasoning": "A step-by-step explanation of how the source HTML resolves the discrepancy.",
       "citation": "The exact quote from the source text that justifies the correction.",
       "corrected_rule": { ... The final, corrected rule object ... }
     }
     ```
   - **Audit Trail:** The `analysis`, `reasoning`, and `citation` fields will be logged
     for every correction made. This creates a complete, auditable trail that explains
     *why* every change was made, making the process transparent and debuggable.
   - **Human-in-the-Loop Fallback:** If the model's response fails schema validation or
     if it indicates insufficient information in the `analysis` field, the entire JSON
     object (including the reasoning) is appended to the `manual_review.yml` file for
     human inspection.

**Latent Risk Covered:** Ungrounded or hallucinated corrections from the LLM. This
rigorous grounding process forces the model to justify its corrections with evidence and
a logical rationale, dramatically increasing the reliability of the auto-fix mechanism.

______________________________________________________________________

### Phase 4 & 5: YAML Generation and Orchestration

These final phases will culminate in the generation of a schema-verified `cra_rules.yml`
file and a summary report, all executed via a single command from an orchestration
script.
