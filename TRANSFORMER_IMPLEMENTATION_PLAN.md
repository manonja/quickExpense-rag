# YAML-to-JSONL Transformer: Implementation Plan

**Date**: 2025-10-17 (Updated: 2025-10-18) **Status**: Phases 1-3 ✅ COMPLETE, Phases 4-5 IN PROGRESS **Based on**:
TRANSFORMER_DESIGN_PLAN.md (Zen MCP Planner Analysis) + Zen MCP Review (2025-10-18)

______________________________________________________________________

## 🚀 Executive Summary

This implementation plan breaks down the YAML-to-JSONL transformer into **13 MECE
tickets** across **5 phases** (scoped for 80/20 and YAGNI principles).

**Current Status**: Phases 1-3 complete, ~6-8 hours remaining for scoped Phases 4-5

### Key Deliverables

- **Phase 1**: Schema compatibility (3 tickets) - ✅ **COMPLETE**
- **Phase 2**: Core transformer (3 tickets) - ✅ **COMPLETE**
- **Phase 3**: CLI integration (3 tickets) - ✅ **COMPLETE**
- **Phase 4**: Testing & validation (2 tickets + 1 deferred) - 🔄 **IN PROGRESS**
  - T4.1: Unit tests (~85% coverage on critical logic)
  - T4.2: Integration tests (3 already passing ✅) + performance baseline
  - T4.3: Search quality tests - ⏸️ **DEFERRED** (post-launch)
- **Phase 5**: Documentation (MVD approach) - 🔄 **IN PROGRESS**

### Timeline Estimate (Updated for 80/20 Scope)

- **Original Estimate**: 5-7 days (1-1.5 weeks)
- **Actual with Scoping**: ~4 days
- **Remaining Work**: ~6-8 hours (1 day) for Phases 4-5

______________________________________________________________________

## Architecture Context

### The Gap We're Filling

```
[EXISTING - Extraction Pipeline]
HTML → Classic Parser → Adjudicator → ExtractedRule (YAML)
                            |
                            X  <-- GAP (no transformer)
                            |
[EXISTING - RAG Pipeline]   v
ParsedDocument (JSONL) → IndexBuilder → SQLite → Search
```

### What We're Building

```
ExtractedRule (YAML)
    |
    v
[TRANSFORMER] ← THIS IS WHAT WE'RE IMPLEMENTING
    |-- Schema mapping (rule_number → citation_id)
    |-- Metadata enrichment (applies_to → income_type)
    |-- Hierarchical grouping (by source_file → chapter → section)
    |-- Expense type inference (keyword classifier)
    |
    v
ParsedDocument (JSONL)
```

______________________________________________________________________

## PHASE 1: Schema Compatibility

**Goal**: Make ExtractedRule and ParsedDocument schemas compatible without breaking
existing functionality.

______________________________________________________________________

## TICKET T1.1: Citation ID Pattern Relaxation

**Scope**: Update citation ID validation to accept both legacy format (S#-F#-C#-p#) and
new LINE-{number} format

### Acceptance Criteria

- [ ] **File**: `src/qe_tax_rag/search/models.py`

  - Line 20: Update `CITATION_ID_PATTERN` constant:
    ```python
    # FROM:
    CITATION_ID_PATTERN = r"S\d+-F\d+-C\d+-p\d+\.?\d*"

    # TO:
    CITATION_ID_PATTERN = r"^(S\d+-F\d+-C\d+-p\d+\.?\d*|LINE-\d+)$"
    ```
  - Line 55: Update Field description:
    ```python
    citation_id: str = Field(
        ...,
        pattern=CITATION_ID_PATTERN,
        description="CRA citation identifier (S-F-C-p or LINE-XXXX format)."
    )
    ```

- [ ] **File**: `scripts/parser/validator.py`

  - Line 7: Update `CITATION_REGEX_PATTERN`:
    ```python
    # FROM:
    CITATION_REGEX_PATTERN = r"^S\d+-F\d+-C\d+-p\d+(\.\d+)?$"

    # TO:
    CITATION_REGEX_PATTERN = r"^(S\d+-F\d+-C\d+-p\d+(\.\d+)?|LINE-\d+)$"
    ```

- [ ] **Backward Compatibility Test**: Existing citations still validate

  - `"S3-F2-C1-p1"` → Valid
  - `"S3-F2-C1-p1.25"` → Valid
  - `"S10-F20-C30-p40.50"` → Valid

- [ ] **New Format Test**: LINE-{number} format validates

  - `"LINE-8523"` → Valid
  - `"LINE-9200"` → Valid
  - `"LINE-12345"` → Valid

- [ ] **Invalid Format Test**: Invalid formats rejected

  - `"LINE-"` → Invalid
  - `"LINE-abc"` → Invalid
  - `"8523"` → Invalid (missing prefix)

- [ ] **Unit Tests** (`tests/unit/test_models.py`):

  ```python
  @pytest.mark.parametrize(
      "valid_citation",
      [
          "S3-F2-C1-p1",
          "S3-F2-C1-p1.25",
          "LINE-8523",
          "LINE-9200",
      ]
  )
  def test_citation_id_formats_pass(valid_citation: str) -> None:
      """Both legacy and LINE formats should pass validation."""
      result = SearchResult(
          content="Test",
          citation_id=valid_citation,
          source_url="https://www.canada.ca/test",
          score=0.5,
          province=None,
          business_type=None,
          expense_types=[],
          retrieved_at=datetime.now(timezone.utc),
      )
      assert result.citation_id == valid_citation
  ```

- [ ] **Validator Unit Tests** (`tests/unit/parser/test_validator.py`):

  ```python
  def test_line_citation_format_validates() -> None:
      """LINE-{number} format should validate."""
      assert validate_citation_format("LINE-8523") is True
      assert validate_citation_format("LINE-9200") is True

  def test_invalid_line_format_fails() -> None:
      """Invalid LINE formats should fail."""
      assert validate_citation_format("LINE-") is False
      assert validate_citation_format("LINE-abc") is False
  ```

- [ ] **Verification Commands**:

  ```bash
  uv run pytest tests/unit/test_models.py::TestSearchResultValidation -v
  uv run pytest tests/unit/parser/test_validator.py -v
  uv run mypy src/qe_tax_rag/search/models.py
  ```

**Dependency**: None (foundational change) **Enables**: T2.1 (Transformer can use
LINE-{number} format) **Risk**: Low (purely additive, no breaking changes)

______________________________________________________________________

## TICKET T1.2: Metadata Schema Extension

**Scope**: Add income_type field to Metadata and extraction metadata to TextChunk

### Acceptance Criteria

- [ ] **File**: `scripts/parser/schema.py`

  - Add `income_type` to Metadata class (line 8-15):

    ```python
    class Metadata(BaseModel):
        """Metadata extracted from CRA documents."""

        model_config = ConfigDict(frozen=True)

        province: list[str] = Field(default_factory=list)
        business_type: list[str] = Field(default_factory=list)
        expense_type: list[str] = Field(default_factory=list)
        income_type: list[str] = Field(  # NEW
            default_factory=list,
            description="Income types: business, farming, fishing"
        )
    ```

  - Add extraction metadata to TextChunk class (line 18-26):

    ```python
    class TextChunk(BaseModel):
        """Text content chunk (paragraph or footnote)."""

        model_config = ConfigDict(frozen=True)

        type: Literal["paragraph", "footnote"]
        text: str
        citation_id: str | None = None

        # NEW: Extraction pipeline provenance
        extraction_source: str | None = Field(
            default=None,
            description="Expert source: classic, llm, adjudicated"
        )
        extraction_confidence: float | None = Field(
            default=None,
            ge=0.0,
            le=1.0,
            description="Confidence score from extraction pipeline"
        )
        source_anchor: str | None = Field(
            default=None,
            description="HTML anchor ID for debugging"
        )
    ```

- [ ] **Backward Compatibility**: Existing JSONL files still parse

  - New fields are optional (default=None)
  - Old ParsedDocument objects validate without new fields
  - Test with existing Gemini-generated JSONL

- [ ] **Forward Compatibility**: New fields work correctly

  - Can create Metadata with income_type
  - Can create TextChunk with extraction metadata
  - All new fields serialize to JSON correctly

- [ ] **Unit Tests** (`tests/unit/parser/test_schema.py`):

  ```python
  def test_metadata_with_income_type() -> None:
      """Metadata should accept income_type field."""
      metadata = Metadata(
          province=["BC"],
          business_type=["sole_proprietorship"],
          expense_type=["meals"],
          income_type=["business", "fishing"]  # NEW
      )
      assert metadata.income_type == ["business", "fishing"]

  def test_metadata_without_income_type() -> None:
      """Metadata should work without income_type (backward compat)."""
      metadata = Metadata(
          province=["BC"],
          business_type=["sole_proprietorship"],
          expense_type=["meals"]
      )
      assert metadata.income_type == []  # Default empty list

  def test_text_chunk_with_extraction_metadata() -> None:
      """TextChunk should accept extraction metadata."""
      chunk = TextChunk(
          type="paragraph",
          text="Test content",
          citation_id="LINE-8523",
          extraction_source="adjudicated",
          extraction_confidence=0.95,
          source_anchor="tocch3ln8523"
      )
      assert chunk.extraction_source == "adjudicated"
      assert chunk.extraction_confidence == 0.95
      assert chunk.source_anchor == "tocch3ln8523"

  def test_text_chunk_without_extraction_metadata() -> None:
      """TextChunk should work without extraction metadata (backward compat)."""
      chunk = TextChunk(
          type="paragraph",
          text="Test content",
          citation_id="S3-F2-C1-p1"
      )
      assert chunk.extraction_source is None
      assert chunk.extraction_confidence is None
      assert chunk.source_anchor is None
  ```

- [ ] **Integration Test**: Parse existing JSONL with Pydantic

  ```python
  def test_backward_compatibility_with_existing_jsonl() -> None:
      """Existing JSONL files should still parse with new schema."""
      # Load a Gemini-generated JSONL file
      with open("data/processed/chunks.jsonl") as f:
          for line in f:
              doc = ParsedDocument.model_validate_json(line)
              # Should parse without errors
              assert doc.metadata is not None
  ```

- [ ] **Verification Commands**:

  ```bash
  uv run pytest tests/unit/parser/test_schema.py -v
  uv run mypy scripts/parser/schema.py
  ```

**Dependency**: None **Enables**: T2.1 (Transformer can populate new fields) **Risk**:
Low (optional fields maintain backward compatibility)

______________________________________________________________________

## TICKET T1.3: Database Schema Migration (Optional Metadata Storage)

**Scope**: Verify metadata_json column can store extraction metadata (no schema changes
needed)

### Acceptance Criteria

- [ ] **Verification**: Confirm `metadata_json TEXT` column exists

  - File: `src/qe_tax_rag/data/schema.py`
  - Line 38: `metadata_json TEXT,`
  - This column already stores arbitrary JSON, so no schema changes needed

- [ ] **Documentation**: Document what goes in metadata_json

  - Add comment in schema.py:
    ```python
    metadata_json TEXT,  -- Stores: income_type, extraction_source, extraction_confidence, source_anchor, section_title, document_id
    ```

- [ ] **Test Storage**: Verify extraction metadata can be stored

  ```python
  def test_extraction_metadata_storage(tmp_path: Path) -> None:
      """Extraction metadata should store in metadata_json column."""
      db_path = tmp_path / "test.db"
      conn = _create_test_connection(db_path)
      conn.executescript(CREATE_TABLES_SQL)

      # Insert rule with extraction metadata
      metadata = {
          "income_type": ["business", "fishing"],
          "extraction_source": "adjudicated",
          "extraction_confidence": 0.95,
          "source_anchor": "tocch3ln8523",
          "section_title": "Chapter 3",
          "document_id": "t4002-5"
      }

      conn.execute(
          """
          INSERT INTO rules (content, citation_id, source_url, source_hash,
                             metadata_json, retrieved_at)
          VALUES (?, ?, ?, ?, ?, ?)
          """,
          (
              "Test content",
              "LINE-8523",
              "https://canada.ca/test",
              "abc123",
              json.dumps(metadata),
              "2024-01-01T00:00:00Z",
          ),
      )

      # Retrieve and verify
      cursor = conn.execute(
          "SELECT metadata_json FROM rules WHERE citation_id = ?",
          ("LINE-8523",)
      )
      stored = json.loads(cursor.fetchone()[0])
      assert stored["income_type"] == ["business", "fishing"]
      assert stored["extraction_source"] == "adjudicated"
      assert stored["extraction_confidence"] == 0.95
  ```

- [ ] **Unit Test** (`tests/unit/test_schema.py`):

  - Add test to existing test file
  - Verify JSON serialization/deserialization works
  - Verify no data loss

- [ ] **Verification Commands**:

  ```bash
  uv run pytest tests/unit/test_schema.py::test_extraction_metadata_storage -v
  ```

**Dependency**: None **Enables**: T2.1 (Transformer can store metadata) **Risk**: None
(no schema changes, just verification) **Rationale**: No migration needed -
metadata_json column is flexible enough to store all extraction metadata as JSON

______________________________________________________________________

## PHASE 2: Core Transformer Implementation

**Goal**: Build the YAML-to-JSONL transformation logic with robust error handling.

______________________________________________________________________

## TICKET T2.1: Core Transformer Module

**Scope**: Implement main transformation logic, schema mapping, and document grouping

### Acceptance Criteria

- [ ] **File**: `src/qe_tax_rag/extraction/ca/transformer.py` (NEW)

  ```python
  """YAML-to-JSONL transformer for extraction pipeline."""

  from pathlib import Path
  from collections import defaultdict
  from datetime import datetime

  from pydantic import BaseModel, Field
  from qe_tax_rag.extraction.ca.schema import ExtractedRule, RuleSet
  from scripts.parser.schema import (
      Metadata,
      ParsedDocument,
      Section,
      TextChunk,
  )


  class TransformationReport(BaseModel):
      """Report on transformation success/failures."""

      timestamp: str
      input_file: str
      output_file: str
      total_rules: int
      successful: int
      skipped: int
      errors: list[dict[str, str]]


  class YAMLTransformer:
      """Transform ExtractedRule YAML to ParsedDocument JSONL."""

      def __init__(
          self,
          expense_type_classifier: "ExpenseTypeClassifier | None" = None
      ):
          """Initialize transformer with optional classifier."""
          self.classifier = expense_type_classifier or ExpenseTypeClassifier()

      def transform_yaml_to_jsonl(
          self,
          yaml_path: Path,
          jsonl_path: Path,
          continue_on_error: bool = True,
      ) -> TransformationReport:
          """
          Transform YAML to JSONL.

          Args:
              yaml_path: Input YAML file from extract-rules
              jsonl_path: Output JSONL file for IndexBuilder
              continue_on_error: Skip errors and continue (default: True)

          Returns:
              TransformationReport with success/error counts

          Raises:
              CriticalTransformationError: For fatal errors (invalid YAML, etc.)
          """
          # 1. Load and validate YAML
          rule_set = self._load_yaml(yaml_path)

          # 2. Pre-transformation validation
          self._validate_yaml_input(rule_set)

          # 3. Group rules by source_file
          grouped = self._group_by_source_file(rule_set.rules)

          # 4. Transform each group to ParsedDocument
          documents: list[ParsedDocument] = []
          errors: list[dict[str, str]] = []
          successful = 0
          skipped = 0

          for source_file, rules in grouped.items():
              try:
                  doc = self._transform_rules_to_document(source_file, rules)
                  documents.append(doc)
                  successful += len(rules)
              except SkippableTransformationError as e:
                  if continue_on_error:
                      errors.append({
                          "source_file": source_file,
                          "error": str(e),
                          "severity": "skippable",
                          "action": "Skipped this document, continued processing"
                      })
                      skipped += len(rules)
                  else:
                      raise

          # 5. Write JSONL
          self._write_jsonl(documents, jsonl_path)

          # 6. Post-transformation validation
          self._validate_jsonl_output(jsonl_path)

          # 7. Generate report
          return TransformationReport(
              timestamp=datetime.utcnow().isoformat() + "Z",
              input_file=str(yaml_path),
              output_file=str(jsonl_path),
              total_rules=len(rule_set.rules),
              successful=successful,
              skipped=skipped,
              errors=errors
          )

      def _load_yaml(self, yaml_path: Path) -> RuleSet:
          """Load and parse YAML file."""
          import yaml

          with open(yaml_path) as f:
              data = yaml.safe_load(f)

          return RuleSet.model_validate(data)

      def _validate_yaml_input(self, rule_set: RuleSet) -> None:
          """Run pre-transformation validation checks."""
          # Check for duplicate rule_numbers
          rule_numbers = [r.rule_number for r in rule_set.rules]
          duplicates = [n for n in set(rule_numbers) if rule_numbers.count(n) > 1]

          if duplicates:
              raise CriticalTransformationError(
                  f"Duplicate rule_numbers found: {duplicates}"
              )

          # Check all rules have required fields
          for rule in rule_set.rules:
              if not rule.source_file:
                  raise CriticalTransformationError(
                      f"Rule {rule.rule_number} missing source_file"
                  )
              if not rule.chapter:
                  raise CriticalTransformationError(
                      f"Rule {rule.rule_number} missing chapter"
                  )

      def _group_by_source_file(
          self,
          rules: list[ExtractedRule]
      ) -> dict[str, list[ExtractedRule]]:
          """Group rules by source_file."""
          grouped: dict[str, list[ExtractedRule]] = defaultdict(list)

          for rule in rules:
              grouped[rule.source_file].append(rule)

          return dict(grouped)

      def _transform_rules_to_document(
          self,
          source_file: str,
          rules: list[ExtractedRule]
      ) -> ParsedDocument:
          """
          Transform rules from one source file into a ParsedDocument.

          Strategy:
          - title: Derived from source_file (e.g., "CRA T4002 - Part 5")
          - document_id: Extracted from source_file (e.g., "t4002-5")
          - sections: Hierarchical by chapter → section
          - content: Each rule → TextChunk
          """
          # Extract document_id from source_file
          # e.g., "t4002-5.html" → "t4002-5"
          document_id = source_file.replace(".html", "").replace(".pdf", "")

          # Create title
          title = f"CRA {document_id.upper().replace('-', ' - Part ')}"

          # Build hierarchical sections
          sections = self._build_sections(rules)

          # Aggregate metadata across all rules
          metadata = self._aggregate_metadata(rules)

          return ParsedDocument(
              title=title,
              document_id=document_id,
              metadata=metadata,
              sections=sections
          )

      def _build_sections(
          self,
          rules: list[ExtractedRule]
      ) -> list[Section]:
          """Build hierarchical section structure."""
          # Group by chapter
          chapters: dict[str, list[ExtractedRule]] = defaultdict(list)
          for rule in rules:
              chapters[rule.chapter].append(rule)

          sections: list[Section] = []

          for chapter_title, chapter_rules in chapters.items():
              # Group by section within chapter
              subsections: dict[str | None, list[ExtractedRule]] = defaultdict(list)
              for rule in chapter_rules:
                  subsections[rule.section].append(rule)

              # Build chapter section
              chapter_content: list[TextChunk] = []

              for section_title, section_rules in subsections.items():
                  if section_title:
                      # Create subsection
                      subsection_chunks = [
                          self._rule_to_text_chunk(rule)
                          for rule in section_rules
                      ]

                      # Note: ParsedDocument schema doesn't support nested sections
                      # So we flatten: chapter with all rules
                      chapter_content.extend(subsection_chunks)
                  else:
                      # Rules without section go directly in chapter
                      chapter_content.extend([
                          self._rule_to_text_chunk(rule)
                          for rule in section_rules
                      ])

              sections.append(Section(
                  section_title=chapter_title,
                  section_level=1,
                  content=chapter_content
              ))

          return sections

      def _rule_to_text_chunk(self, rule: ExtractedRule) -> TextChunk:
          """Convert ExtractedRule to TextChunk."""
          # Combine title and content
          text = f"{rule.title}\n\n{rule.content}"

          # Create citation_id
          citation_id = f"LINE-{rule.rule_number}"

          return TextChunk(
              type="paragraph",
              text=text,
              citation_id=citation_id,
              extraction_source=rule.expert_source,
              extraction_confidence=rule.confidence_score,
              source_anchor=rule.anchor_id
          )

      def _aggregate_metadata(
          self,
          rules: list[ExtractedRule]
      ) -> Metadata:
          """Aggregate metadata across all rules in document."""
          # Collect all unique values
          income_types: set[str] = set()
          expense_types: set[str] = set()

          for rule in rules:
              # applies_to → income_type
              income_types.update(rule.applies_to)

              # Infer expense_type from content
              inferred = self.classifier.infer_expense_types(rule)
              expense_types.update(inferred)

          return Metadata(
              province=[],  # Federal rules, no province
              business_type=[],  # Not mapped from applies_to
              expense_type=sorted(expense_types),
              income_type=sorted(income_types)
          )

      def _write_jsonl(
          self,
          documents: list[ParsedDocument],
          jsonl_path: Path
      ) -> None:
          """Write ParsedDocuments to JSONL file."""
          jsonl_path.parent.mkdir(parents=True, exist_ok=True)

          with open(jsonl_path, "w") as f:
              for doc in documents:
                  f.write(doc.model_dump_json() + "\n")

      def _validate_jsonl_output(self, jsonl_path: Path) -> None:
          """Post-transformation validation."""
          # Verify JSONL format
          with open(jsonl_path) as f:
              for i, line in enumerate(f, 1):
                  try:
                      ParsedDocument.model_validate_json(line)
                  except Exception as e:
                      raise CriticalTransformationError(
                          f"Invalid JSONL at line {i}: {e}"
                      )


  # Exception classes (defined at module level)
  class TransformationError(Exception):
      """Base exception for transformation errors."""
      pass


  class CriticalTransformationError(TransformationError):
      """Fatal error - stops transformation immediately."""
      pass


  class SkippableTransformationError(TransformationError):
      """Non-fatal error - skip this rule/document, continue."""
      pass
  ```

- [ ] **Unit Tests** (`tests/unit/test_transformer.py`):

  ```python
  def test_group_by_source_file() -> None:
      """Rules should be grouped by source_file."""
      rules = [
          ExtractedRule(
              rule_number=8523,
              title="Meals",
              content="...",
              applies_to=["business"],
              source_citation="Line 8523",
              chapter="Chapter 3",
              section=None,
              source_file="t4002-5.html",
              expert_source="classic",
              confidence_score=1.0
          ),
          ExtractedRule(
              rule_number=9200,
              title="Travel",
              content="...",
              applies_to=["business"],
              source_citation="Line 9200",
              chapter="Chapter 3",
              section=None,
              source_file="t4002-6.html",
              expert_source="classic",
              confidence_score=1.0
          ),
      ]

      transformer = YAMLTransformer()
      grouped = transformer._group_by_source_file(rules)

      assert len(grouped) == 2
      assert len(grouped["t4002-5.html"]) == 1
      assert len(grouped["t4002-6.html"]) == 1

  def test_rule_to_text_chunk() -> None:
      """ExtractedRule should convert to TextChunk."""
      rule = ExtractedRule(
          rule_number=8523,
          title="Meals and entertainment",
          content="You can deduct...",
          applies_to=["business", "fishing"],
          source_citation="Line 8523",
          chapter="Chapter 3",
          section="Part 4",
          source_file="t4002-5.html",
          expert_source="adjudicated",
          anchor_id="tocch3ln8523",
          confidence_score=0.95
      )

      transformer = YAMLTransformer()
      chunk = transformer._rule_to_text_chunk(rule)

      assert chunk.citation_id == "LINE-8523"
      assert "Meals and entertainment" in chunk.text
      assert "You can deduct" in chunk.text
      assert chunk.extraction_source == "adjudicated"
      assert chunk.extraction_confidence == 0.95
      assert chunk.source_anchor == "tocch3ln8523"

  def test_aggregate_metadata() -> None:
      """Metadata should aggregate from all rules."""
      rules = [
          ExtractedRule(
              rule_number=8523,
              title="Meals",
              content="restaurant dining",
              applies_to=["business", "fishing"],
              source_citation="Line 8523",
              chapter="Chapter 3",
              section=None,
              source_file="t4002-5.html",
              expert_source="classic",
              confidence_score=1.0
          ),
          ExtractedRule(
              rule_number=9200,
              title="Vehicle",
              content="car mileage fuel",
              applies_to=["farming"],
              source_citation="Line 9200",
              chapter="Chapter 3",
              section=None,
              source_file="t4002-5.html",
              expert_source="classic",
              confidence_score=1.0
          ),
      ]

      transformer = YAMLTransformer()
      metadata = transformer._aggregate_metadata(rules)

      # income_type from applies_to
      assert set(metadata.income_type) == {"business", "fishing", "farming"}

      # expense_type from inference
      assert "meals" in metadata.expense_type  # inferred from "restaurant dining"
      assert "vehicle" in metadata.expense_type  # inferred from "car mileage"
  ```

- [ ] **Verification Commands**:

  ```bash
  uv run pytest tests/unit/test_transformer.py -v
  uv run mypy src/qe_tax_rag/extraction/ca/transformer.py
  ```

**Dependency**: T1.1, T1.2 **Enables**: T2.2 (needs expense type classifier), T3.1 (CLI
can use transformer) **Complexity**: High (core transformation logic)

______________________________________________________________________

## TICKET T2.2: Expense Type Inference Classifier

**Scope**: Keyword-based classifier to infer expense types from rule content

### Acceptance Criteria

- [ ] **File**: `src/qe_tax_rag/extraction/ca/transformer.py` (add to existing file)

  ```python
  class ExpenseTypeClassifier:
      """Keyword-based expense type classifier."""

      # Canonical expense types from database schema
      EXPENSE_TYPE_KEYWORDS = {
          "meals": ["meal", "food", "restaurant", "dining", "entertainment"],
          "travel": ["travel", "transportation", "airfare", "hotel", "lodging"],
          "vehicle": ["vehicle", "automobile", "car", "motor", "mileage", "fuel"],
          "home_office": ["home office", "workspace", "rent"],
          "advertising": ["advertising", "marketing", "promotion"],
          "supplies": ["supplies", "materials", "stationery"],
          "professional_fees": ["professional fees", "legal", "accounting"],
          "utilities": ["telephone", "utilities", "internet", "electricity"],
          "insurance": ["insurance", "premium"],
          "capital": ["capital cost", "cca", "depreciation", "asset"],
          "maintenance": ["maintenance", "repair"],
          "salaries": ["salaries", "wages", "employee"],
          "office_equipment": ["office equipment", "furniture", "computer"],
          "telecommunications": ["telecommunications", "phone", "mobile"],
          "interest": ["interest", "loan", "financing"],
          "bad_debts": ["bad debts", "uncollectible"],
      }

      def infer_expense_types(self, rule: ExtractedRule) -> list[str]:
          """
          Infer expense types from rule title and content.

          Returns:
              List of expense types (can be multiple)
              Falls back to ["general"] if no matches
          """
          # Combine title and content for matching
          text = (rule.title + " " + rule.content).lower()

          matched: list[str] = []

          for expense_type, keywords in self.EXPENSE_TYPE_KEYWORDS.items():
              if any(keyword in text for keyword in keywords):
                  matched.append(expense_type)

          # Fallback to "general" if no matches
          return matched if matched else ["general"]
  ```

- [ ] **Unit Tests** (`tests/unit/test_transformer.py`):

  ```python
  def test_expense_type_inference_meals() -> None:
      """Meals keywords should infer meals type."""
      rule = ExtractedRule(
          rule_number=8523,
          title="Meals and entertainment",
          content="You can deduct 50% of restaurant and dining expenses...",
          applies_to=["business"],
          source_citation="Line 8523",
          chapter="Chapter 3",
          section=None,
          source_file="t4002-5.html",
          expert_source="classic",
          confidence_score=1.0
      )

      classifier = ExpenseTypeClassifier()
      types = classifier.infer_expense_types(rule)

      assert "meals" in types

  def test_expense_type_inference_vehicle() -> None:
      """Vehicle keywords should infer vehicle type."""
      rule = ExtractedRule(
          rule_number=9200,
          title="Motor vehicle expenses",
          content="Deductible car expenses include fuel, mileage, maintenance...",
          applies_to=["business"],
          source_citation="Line 9200",
          chapter="Chapter 3",
          section=None,
          source_file="t4002-5.html",
          expert_source="classic",
          confidence_score=1.0
      )

      classifier = ExpenseTypeClassifier()
      types = classifier.infer_expense_types(rule)

      assert "vehicle" in types

  def test_expense_type_inference_multiple() -> None:
      """Rule can match multiple expense types."""
      rule = ExtractedRule(
          rule_number=9999,
          title="Travel and accommodation",
          content="Hotel, airfare, and restaurant meals during business trips...",
          applies_to=["business"],
          source_citation="Line 9999",
          chapter="Chapter 3",
          section=None,
          source_file="t4002-5.html",
          expert_source="classic",
          confidence_score=1.0
      )

      classifier = ExpenseTypeClassifier()
      types = classifier.infer_expense_types(rule)

      # Should match both travel and meals
      assert "travel" in types
      assert "meals" in types

  def test_expense_type_inference_fallback() -> None:
      """No matches should return 'general'."""
      rule = ExtractedRule(
          rule_number=9999,
          title="Miscellaneous",
          content="Other deductible expenses...",
          applies_to=["business"],
          source_citation="Line 9999",
          chapter="Chapter 3",
          section=None,
          source_file="t4002-5.html",
          expert_source="classic",
          confidence_score=1.0
      )

      classifier = ExpenseTypeClassifier()
      types = classifier.infer_expense_types(rule)

      assert types == ["general"]

  def test_expense_type_case_insensitive() -> None:
      """Matching should be case-insensitive."""
      rule = ExtractedRule(
          rule_number=9999,
          title="MEALS AND ENTERTAINMENT",
          content="RESTAURANT expenses...",
          applies_to=["business"],
          source_citation="Line 9999",
          chapter="Chapter 3",
          section=None,
          source_file="t4002-5.html",
          expert_source="classic",
          confidence_score=1.0
      )

      classifier = ExpenseTypeClassifier()
      types = classifier.infer_expense_types(rule)

      assert "meals" in types
  ```

- [ ] **Documentation**: Add docstring explaining limitations

  - Simple keyword matching (not ML-based)
  - Good enough for MVP
  - Can be improved later with ML classifier

- [ ] **Verification Commands**:

  ```bash
  uv run pytest tests/unit/test_transformer.py::test_expense_type_inference* -v
  ```

**Dependency**: T2.1 **Enables**: T2.1 (used in transformer) **Complexity**: Low (simple
keyword matching) **Future Enhancement**: Replace with ML classifier if needed

______________________________________________________________________

## TICKET T2.3: Error Handling & Validation Layer

**Scope**: Implement robust error handling with fail-fast and graceful degradation
strategies

### Acceptance Criteria

- [ ] **Exception Hierarchy** (already in T2.1, just document here):

  ```python
  # Module-level exceptions defined
  class TransformationError(Exception):
      """Base exception for transformation errors."""

  class CriticalTransformationError(TransformationError):
      """Fatal error - stops transformation immediately."""
      # Examples:
      # - Invalid YAML syntax
      # - Schema version mismatch
      # - Duplicate citation IDs
      # - Missing required fields (source_file, chapter)

  class SkippableTransformationError(TransformationError):
      """Non-fatal error - skip this rule/document, continue."""
      # Examples:
      # - Individual rule missing optional field
      # - Metadata inference failure (falls back to defaults)
      # - Section parsing fails for one rule
  ```

- [ ] **Error Reporting**: TransformationReport already defined in T2.1

  - Includes: timestamp, input_file, output_file, total_rules, successful, skipped,
    errors
  - errors list contains: source_file, error message, severity, action taken

- [ ] **Validation Functions** (add to transformer.py):

  ```python
  def _validate_yaml_input(self, rule_set: RuleSet) -> None:
      """Pre-transformation validation (fail-fast)."""
      # Check for duplicate rule_numbers
      rule_numbers = [r.rule_number for r in rule_set.rules]
      duplicates = [n for n in set(rule_numbers) if rule_numbers.count(n) > 1]

      if duplicates:
          raise CriticalTransformationError(
              f"Duplicate rule_numbers found: {duplicates}. "
              f"Each rule must have a unique number."
          )

      # Check all rules have required fields
      for rule in rule_set.rules:
          if not rule.source_file:
              raise CriticalTransformationError(
                  f"Rule {rule.rule_number} missing required field 'source_file'"
              )
          if not rule.chapter:
              raise CriticalTransformationError(
                  f"Rule {rule.rule_number} missing required field 'chapter'"
              )

      # Verify all citation IDs will be unique
      citation_ids = [f"LINE-{r.rule_number}" for r in rule_set.rules]
      if len(citation_ids) != len(set(citation_ids)):
          raise CriticalTransformationError(
              "Generated citation IDs are not unique"
          )

  def _validate_jsonl_output(self, jsonl_path: Path) -> None:
      """Post-transformation validation."""
      with open(jsonl_path) as f:
          for i, line in enumerate(f, 1):
              try:
                  doc = ParsedDocument.model_validate_json(line)

                  # Verify document has content
                  if not doc.sections:
                      raise ValueError("Document has no sections")

                  # Verify all chunks have citation_ids
                  for section in doc.sections:
                      for item in section.content:
                          if hasattr(item, 'citation_id') and not item.citation_id:
                              raise ValueError("TextChunk missing citation_id")

              except Exception as e:
                  raise CriticalTransformationError(
                      f"Invalid JSONL at line {i}: {e}"
                  )
  ```

- [ ] **Unit Tests** (`tests/unit/test_transformer.py`):

  ```python
  def test_duplicate_rule_numbers_raise_error() -> None:
      """Duplicate rule_numbers should raise CriticalTransformationError."""
      rule_set = RuleSet(
          schema_version="1.0",
          extraction_timestamp="2025-01-01T00:00:00Z",
          rules=[
              ExtractedRule(
                  rule_number=8523,  # Duplicate
                  title="Rule 1",
                  content="...",
                  applies_to=["business"],
                  source_citation="Line 8523",
                  chapter="Chapter 3",
                  section=None,
                  source_file="t4002-5.html",
                  expert_source="classic",
                  confidence_score=1.0
              ),
              ExtractedRule(
                  rule_number=8523,  # Duplicate
                  title="Rule 2",
                  content="...",
                  applies_to=["business"],
                  source_citation="Line 8523",
                  chapter="Chapter 3",
                  section=None,
                  source_file="t4002-5.html",
                  expert_source="classic",
                  confidence_score=1.0
              ),
          ]
      )

      transformer = YAMLTransformer()

      with pytest.raises(CriticalTransformationError, match="Duplicate rule_numbers"):
          transformer._validate_yaml_input(rule_set)

  def test_missing_source_file_raises_error() -> None:
      """Missing source_file should raise CriticalTransformationError."""
      rule_set = RuleSet(
          schema_version="1.0",
          extraction_timestamp="2025-01-01T00:00:00Z",
          rules=[
              ExtractedRule(
                  rule_number=8523,
                  title="Rule 1",
                  content="...",
                  applies_to=["business"],
                  source_citation="Line 8523",
                  chapter="Chapter 3",
                  section=None,
                  source_file="",  # Missing
                  expert_source="classic",
                  confidence_score=1.0
              ),
          ]
      )

      transformer = YAMLTransformer()

      with pytest.raises(CriticalTransformationError, match="missing required field"):
          transformer._validate_yaml_input(rule_set)

  def test_invalid_jsonl_raises_error(tmp_path: Path) -> None:
      """Invalid JSONL should raise CriticalTransformationError."""
      jsonl_path = tmp_path / "invalid.jsonl"
      jsonl_path.write_text('{"invalid": "json"\n')  # Invalid JSON

      transformer = YAMLTransformer()

      with pytest.raises(CriticalTransformationError, match="Invalid JSONL"):
          transformer._validate_jsonl_output(jsonl_path)

  def test_continue_on_error_flag(tmp_path: Path) -> None:
      """continue_on_error should allow skipping failed documents."""
      # Create YAML with one valid and one problematic rule
      # (implementation depends on what can fail gracefully)
      # Test that successful count is correct and error is logged
      pass  # Detailed test needed
  ```

- [ ] **Error Message Quality**: All exceptions should have:

  - Clear description of what went wrong
  - Which rule/document caused the error
  - Actionable suggestion for fixing

- [ ] **Verification Commands**:

  ```bash
  uv run pytest tests/unit/test_transformer.py::test_*error* -v
  uv run pytest tests/unit/test_transformer.py::test_*validation* -v
  ```

**Dependency**: T2.1 **Enables**: T3.1 (CLI can report errors) **Complexity**: Medium
(error handling logic)

______________________________________________________________________

## PHASE 3: CLI Integration

**Goal**: Expose transformer functionality through user-friendly CLI commands.

______________________________________________________________________

## TICKET T3.1: Transform Command

**Scope**: Add `transform` subcommand to extract-rules CLI

### Acceptance Criteria

- [ ] **File**: `scripts/extract_rules.py` (modify existing)

  ```python
  import typer
  from pathlib import Path
  from qe_tax_rag.extraction.ca.transformer import YAMLTransformer

  app = typer.Typer()

  # ... existing commands ...

  @app.command()
  def transform(
      input_yaml: Path = typer.Argument(
          ...,
          help="Input YAML file from extract-rules",
          exists=True,
          file_okay=True,
          dir_okay=False,
      ),
      output_jsonl: Path = typer.Argument(
          ...,
          help="Output JSONL file for IndexBuilder",
      ),
      continue_on_error: bool = typer.Option(
          True,
          help="Skip errors and continue processing"
      ),
      error_report: Path | None = typer.Option(
          None,
          help="Path for error report YAML (optional)"
      ),
      verbose: bool = typer.Option(
          False,
          "--verbose",
          "-v",
          help="Enable verbose logging"
      ),
  ) -> None:
      """
      Transform YAML extraction output to JSONL for database indexing.

      This command bridges the extraction pipeline (TICKETS 1-6) with the
      RAG database by converting ExtractedRule objects to ParsedDocument format.

      Example:
          uv run extract-rules transform output/rules.yml data/chunks.jsonl
      """
      import logging

      if verbose:
          logging.basicConfig(level=logging.DEBUG)
      else:
          logging.basicConfig(level=logging.INFO)

      logger = logging.getLogger(__name__)

      logger.info(f"Transforming {input_yaml} → {output_jsonl}")

      try:
          transformer = YAMLTransformer()
          report = transformer.transform_yaml_to_jsonl(
              yaml_path=input_yaml,
              jsonl_path=output_jsonl,
              continue_on_error=continue_on_error
          )

          # Print summary
          typer.echo(f"✅ Transformation complete!")
          typer.echo(f"   Total rules: {report.total_rules}")
          typer.echo(f"   Successful: {report.successful}")
          typer.echo(f"   Skipped: {report.skipped}")
          typer.echo(f"   Errors: {len(report.errors)}")

          if report.errors:
              typer.echo("\n⚠️  Errors encountered:")
              for error in report.errors[:5]:  # Show first 5
                  typer.echo(f"   - {error['source_file']}: {error['error']}")
              if len(report.errors) > 5:
                  typer.echo(f"   ... and {len(report.errors) - 5} more")

          # Write error report if requested
          if error_report and report.errors:
              import yaml
              with open(error_report, "w") as f:
                  yaml.dump(report.model_dump(), f)
              typer.echo(f"\n📄 Error report written to {error_report}")

          # Exit code based on errors
          if report.errors and not continue_on_error:
              raise typer.Exit(code=1)

      except Exception as e:
          typer.echo(f"❌ Transformation failed: {e}", err=True)
          raise typer.Exit(code=1)
  ```

- [ ] **Usage Examples**:

  ```bash
  # Basic transformation
  uv run extract-rules transform output/cra_rules.yml data/chunks.jsonl

  # With error reporting
  uv run extract-rules transform output/rules.yml data/chunks.jsonl \
    --error-report errors.yml --verbose

  # Fail on first error (no continue)
  uv run extract-rules transform output/rules.yml data/chunks.jsonl \
    --no-continue-on-error
  ```

- [ ] **Help Output**:

  ```bash
  uv run extract-rules transform --help

  # Should show:
  # - Command description
  # - Argument descriptions
  # - Option descriptions
  # - Example usage
  ```

- [ ] **Integration Test** (`tests/integration/test_cli_integration.py`):

  ```python
  def test_transform_command_success(tmp_path: Path) -> None:
      """Transform command should convert YAML to JSONL."""
      # Create test YAML file
      yaml_path = tmp_path / "test_rules.yml"
      # ... create minimal valid YAML ...

      jsonl_path = tmp_path / "chunks.jsonl"

      # Run command
      result = subprocess.run(
          [
              "uv", "run", "extract-rules", "transform",
              str(yaml_path),
              str(jsonl_path)
          ],
          capture_output=True,
          text=True
      )

      assert result.returncode == 0
      assert "Transformation complete" in result.stdout
      assert jsonl_path.exists()

  def test_transform_command_with_errors(tmp_path: Path) -> None:
      """Transform command should handle errors gracefully."""
      # Create test YAML with errors
      yaml_path = tmp_path / "bad_rules.yml"
      # ... create YAML with duplicate rule_numbers ...

      jsonl_path = tmp_path / "chunks.jsonl"
      error_report = tmp_path / "errors.yml"

      # Run command
      result = subprocess.run(
          [
              "uv", "run", "extract-rules", "transform",
              str(yaml_path),
              str(jsonl_path),
              "--error-report", str(error_report)
          ],
          capture_output=True,
          text=True
      )

      # Should exit with error but still write report
      assert result.returncode == 1
      assert error_report.exists()
  ```

- [ ] **Verification Commands**:

  ```bash
  uv run extract-rules transform --help
  uv run pytest tests/integration/test_cli_integration.py::test_transform* -v
  ```

**Dependency**: T2.1, T2.2, T2.3 **Enables**: Users can manually transform YAML to JSONL
**Complexity**: Low (thin CLI wrapper)

______________________________________________________________________

## TICKET T3.2: Auto-Transform Flag

**Scope**: Add `--auto-transform` flag to existing `extract-rules` command

### Acceptance Criteria

- [ ] **File**: `scripts/extract_rules.py` (modify existing `run` command)

  ```python
  @app.command(name="run")  # or whatever the main extraction command is called
  def run(
      html_dir: Path,
      output_yml: Path,
      # ... existing parameters ...
      auto_transform: bool = typer.Option(
          False,
          "--auto-transform",
          help="Automatically transform YAML to JSONL after extraction"
      ),
      output_jsonl: Path | None = typer.Option(
          None,
          "--output-jsonl",
          help="JSONL output path (required if --auto-transform is set)"
      ),
  ) -> None:
      """
      Extract rules from HTML documents to YAML.

      Optionally transforms YAML to JSONL in a single command.
      """
      # ... existing extraction logic ...

      # After YAML is written successfully:
      if auto_transform:
          if not output_jsonl:
              typer.echo(
                  "❌ --output-jsonl is required when using --auto-transform",
                  err=True
              )
              raise typer.Exit(code=1)

          typer.echo("\n🔄 Auto-transforming to JSONL...")

          transformer = YAMLTransformer()
          report = transformer.transform_yaml_to_jsonl(
              yaml_path=output_yml,
              jsonl_path=output_jsonl,
              continue_on_error=True
          )

          typer.echo(f"✅ Transformation complete!")
          typer.echo(f"   JSONL written to: {output_jsonl}")
          typer.echo(f"   Rules processed: {report.successful}/{report.total_rules}")
  ```

- [ ] **Usage Example**:

  ```bash
  # Extract and transform in one command
  uv run extract-rules run cra_documents/cra_t4002e_rev24_dump/ \
    output/rules.yml \
    --auto-transform \
    --output-jsonl data/chunks.jsonl
  ```

- [ ] **Validation**:

  - `--auto-transform` without `--output-jsonl` should error with clear message
  - `--output-jsonl` without `--auto-transform` should warn (or ignore)
  - Both flags together should work seamlessly

- [ ] **Integration Test** (`tests/integration/test_cli_integration.py`):

  ```python
  def test_auto_transform_flag(tmp_path: Path) -> None:
      """Auto-transform should chain extraction → transformation."""
      html_dir = tmp_path / "html"
      html_dir.mkdir()
      # Create test HTML file

      yml_path = tmp_path / "rules.yml"
      jsonl_path = tmp_path / "chunks.jsonl"

      result = subprocess.run(
          [
              "uv", "run", "extract-rules", "run",
              str(html_dir),
              str(yml_path),
              "--auto-transform",
              "--output-jsonl", str(jsonl_path)
          ],
          capture_output=True,
          text=True
      )

      assert result.returncode == 0
      assert yml_path.exists()
      assert jsonl_path.exists()
      assert "Auto-transforming" in result.stdout

  def test_auto_transform_without_output_jsonl_fails(tmp_path: Path) -> None:
      """Auto-transform without output-jsonl should fail."""
      html_dir = tmp_path / "html"
      html_dir.mkdir()
      yml_path = tmp_path / "rules.yml"

      result = subprocess.run(
          [
              "uv", "run", "extract-rules", "run",
              str(html_dir),
              str(yml_path),
              "--auto-transform"
          ],
          capture_output=True,
          text=True
      )

      assert result.returncode == 1
      assert "--output-jsonl is required" in result.stderr
  ```

- [ ] **Verification Commands**:

  ```bash
  uv run extract-rules run --help  # Should show new flags
  uv run pytest tests/integration/test_cli_integration.py::test_auto_transform* -v
  ```

**Dependency**: T2.1, T3.1 **Enables**: One-command workflow for convenience
**Complexity**: Low (flag addition)

______________________________________________________________________

## TICKET T3.3: Pipeline-Extraction Command

**Scope**: Add end-to-end `pipeline-extraction` command to main CLI

### Acceptance Criteria

- [ ] **File**: `scripts/cli.py` (add new command)

  ```python
  @app.command()
  def pipeline_extraction(
      input_dir: Path = typer.Option(
          ...,
          "--input-dir",
          help="Directory containing HTML files",
          exists=True,
          file_okay=False,
          dir_okay=True,
      ),
      output_db: Path = typer.Option(
          ...,
          "--output-db",
          help="Output SQLite database path"
      ),
      intermediate_dir: Path = typer.Option(
          None,
          "--intermediate-dir",
          help="Directory for intermediate files (YAML, JSONL). Default: temp dir"
      ),
      keep_intermediate: bool = typer.Option(
          False,
          "--keep-intermediate",
          help="Keep intermediate YAML and JSONL files after completion"
      ),
  ) -> None:
      """
      Run complete extraction-to-database pipeline.

      This command orchestrates:
      1. Extract rules from HTML (extract-rules)
      2. Transform YAML to JSONL (transformer)
      3. Build RAG database (IndexBuilder)
      4. Validate database (validator)

      Example:
          uv run python scripts/cli.py pipeline-extraction \\
            --input-dir cra_documents/cra_t4002e_rev24_dump/ \\
            --output-db data/cra_rules.db
      """
      import tempfile
      import subprocess
      from qe_tax_rag.data.builder import IndexBuilder

      # Setup intermediate directory
      if intermediate_dir:
          intermediate_dir.mkdir(parents=True, exist_ok=True)
          yml_path = intermediate_dir / "rules.yml"
          jsonl_path = intermediate_dir / "chunks.jsonl"
      else:
          temp_dir = tempfile.mkdtemp()
          yml_path = Path(temp_dir) / "rules.yml"
          jsonl_path = Path(temp_dir) / "chunks.jsonl"

      try:
          # Stage 1: Extract rules
          typer.echo("📥 Stage 1/4: Extracting rules from HTML...")
          result = subprocess.run(
              [
                  "uv", "run", "extract-rules", "run",
                  str(input_dir),
                  str(yml_path)
              ],
              capture_output=True,
              text=True,
              check=True
          )
          typer.echo(f"   ✅ Extracted to {yml_path}")

          # Stage 2: Transform to JSONL
          typer.echo("\n🔄 Stage 2/4: Transforming YAML to JSONL...")
          transformer = YAMLTransformer()
          report = transformer.transform_yaml_to_jsonl(
              yaml_path=yml_path,
              jsonl_path=jsonl_path,
              continue_on_error=True
          )
          typer.echo(f"   ✅ Transformed {report.successful}/{report.total_rules} rules")

          # Stage 3: Build database
          typer.echo("\n🏗️  Stage 3/4: Building RAG database...")
          result = subprocess.run(
              [
                  "uv", "run", "python", "scripts/cli.py", "build",
                  "--input-file", str(jsonl_path),
                  "--output-db", str(output_db)
              ],
              capture_output=True,
              text=True,
              check=True
          )
          typer.echo(f"   ✅ Database built: {output_db}")

          # Stage 4: Validate
          typer.echo("\n✅ Stage 4/4: Validating database...")
          result = subprocess.run(
              [
                  "uv", "run", "python", "scripts/cli.py", "validate",
                  "--db-path", str(output_db)
              ],
              capture_output=True,
              text=True,
              check=True
          )
          typer.echo("   ✅ Validation passed")

          typer.echo(f"\n🎉 Pipeline complete! Database: {output_db}")

      except subprocess.CalledProcessError as e:
          typer.echo(f"\n❌ Pipeline failed at stage: {e.cmd[0]}", err=True)
          typer.echo(f"   Error: {e.stderr}", err=True)
          raise typer.Exit(code=1)

      finally:
          # Cleanup intermediate files if not keeping
          if not keep_intermediate and not intermediate_dir:
              import shutil
              shutil.rmtree(temp_dir, ignore_errors=True)
              typer.echo("\n🧹 Cleaned up intermediate files")
  ```

- [ ] **Usage Example**:

  ```bash
  # Basic usage (auto-cleanup intermediates)
  uv run python scripts/cli.py pipeline-extraction \
    --input-dir cra_documents/cra_t4002e_rev24_dump/ \
    --output-db data/cra_rules.db

  # Keep intermediate files for debugging
  uv run python scripts/cli.py pipeline-extraction \
    --input-dir cra_documents/cra_t4002e_rev24_dump/ \
    --output-db data/cra_rules.db \
    --intermediate-dir output/ \
    --keep-intermediate
  ```

- [ ] **Progress Reporting**:

  - Each stage should print clear status
  - Show progress bars for long operations
  - Print summary at the end

- [ ] **Error Handling**:

  - If any stage fails, stop pipeline
  - Print clear error message with stage that failed
  - Optionally keep intermediate files for debugging

- [ ] **Integration Test** (`tests/integration/test_cli_pipeline.py`):

  ```python
  def test_pipeline_extraction_end_to_end(tmp_path: Path) -> None:
      """Pipeline should run all stages successfully."""
      # Setup test HTML directory
      html_dir = tmp_path / "html"
      html_dir.mkdir()
      # Create minimal test HTML

      db_path = tmp_path / "test.db"

      result = subprocess.run(
          [
              "uv", "run", "python", "scripts/cli.py", "pipeline-extraction",
              "--input-dir", str(html_dir),
              "--output-db", str(db_path)
          ],
          capture_output=True,
          text=True
      )

      assert result.returncode == 0
      assert "Stage 1/4" in result.stdout
      assert "Stage 2/4" in result.stdout
      assert "Stage 3/4" in result.stdout
      assert "Stage 4/4" in result.stdout
      assert "Pipeline complete" in result.stdout
      assert db_path.exists()
  ```

- [ ] **Verification Commands**:

  ```bash
  uv run python scripts/cli.py pipeline-extraction --help
  uv run pytest tests/integration/test_cli_pipeline.py -v
  ```

**Dependency**: T2.1, T3.1, existing build and validate commands **Enables**:
One-command end-to-end workflow **Complexity**: Medium (orchestration logic)

______________________________________________________________________

## PHASE 4: Testing & Validation (Scoped for 80/20)

**Goal**: Essential testing to ensure transformer correctness and production readiness.

**Status**: ✅ Phases 1-3 COMPLETE
**Updated**: 2025-10-18 (Based on Zen MCP Analysis)

**Philosophy**: Focus on critical logic testing (~85% coverage) rather than vanity
metrics (≥95%). Defer search quality analysis to post-launch.

______________________________________________________________________

## TICKET T4.1: Essential Unit Tests (~85% Coverage)

**Scope**: Focus unit tests on critical transformation logic, not trivial code

**Rationale**: Chasing 95% coverage leads to testing getters/setters with diminishing
returns. Target 85-90% on **critical logic** only.

### Acceptance Criteria

- [ ] **Test Coverage**: ~85% for transformer module (focus on critical logic)

  ```bash
  uv run pytest tests/unit/test_transformer.py --cov=src/qe_tax_rag/extraction/ca/transformer --cov-report=term --cov-report=html
  ```

- [ ] **Test File**: `tests/unit/test_transformer.py` (comprehensive suite)

  - Core tests already covered in T2.1, T2.2, T2.3
  - Add edge case tests focusing on critical logic

**TDD Approach**:
- Write failing test → GREEN → Refactor
- Commit after each passing test milestone
- Focus on transformation logic, error handling, and metadata aggregation

  ```python
  def test_empty_rules_list() -> None:
      """Empty rules list should be handled gracefully."""
      transformer = YAMLTransformer()
      grouped = transformer._group_by_source_file([])
      assert grouped == {}

  def test_rule_without_section() -> None:
      """Rules without section should still work."""
      rule = ExtractedRule(
          rule_number=8523,
          title="Test",
          content="...",
          applies_to=["business"],
          source_citation="Line 8523",
          chapter="Chapter 3",
          section=None,  # No section
          source_file="t4002-5.html",
          expert_source="classic",
          confidence_score=1.0
      )

      transformer = YAMLTransformer()
      doc = transformer._transform_rules_to_document("t4002-5.html", [rule])

      assert len(doc.sections) == 1
      assert doc.sections[0].section_title == "Chapter 3"

  def test_multiple_chapters_in_one_file() -> None:
      """Multiple chapters should create multiple sections."""
      rules = [
          ExtractedRule(
              rule_number=8523,
              title="Rule 1",
              content="...",
              applies_to=["business"],
              source_citation="Line 8523",
              chapter="Chapter 3",
              section=None,
              source_file="t4002-5.html",
              expert_source="classic",
              confidence_score=1.0
          ),
          ExtractedRule(
              rule_number=9200,
              title="Rule 2",
              content="...",
              applies_to=["business"],
              source_citation="Line 9200",
              chapter="Chapter 4",  # Different chapter
              section=None,
              source_file="t4002-5.html",
              expert_source="classic",
              confidence_score=1.0
          ),
      ]

      transformer = YAMLTransformer()
      doc = transformer._transform_rules_to_document("t4002-5.html", rules)

      assert len(doc.sections) == 2
      chapter_titles = {s.section_title for s in doc.sections}
      assert chapter_titles == {"Chapter 3", "Chapter 4"}

  def test_special_characters_in_content() -> None:
      """Special characters should be preserved."""
      rule = ExtractedRule(
          rule_number=8523,
          title="Meals & Entertainment",
          content="50% deductible: $100 → $50",
          applies_to=["business"],
          source_citation="Line 8523",
          chapter="Chapter 3",
          section=None,
          source_file="t4002-5.html",
          expert_source="classic",
          confidence_score=1.0
      )

      transformer = YAMLTransformer()
      chunk = transformer._rule_to_text_chunk(rule)

      assert "&" in chunk.text
      assert "→" in chunk.text
      assert "$" in chunk.text

  def test_very_long_content() -> None:
      """Very long content should not cause issues."""
      long_content = "A" * 10000  # 10KB content

      rule = ExtractedRule(
          rule_number=8523,
          title="Long rule",
          content=long_content,
          applies_to=["business"],
          source_citation="Line 8523",
          chapter="Chapter 3",
          section=None,
          source_file="t4002-5.html",
          expert_source="classic",
          confidence_score=1.0
      )

      transformer = YAMLTransformer()
      chunk = transformer._rule_to_text_chunk(rule)

      assert len(chunk.text) >= 10000
  ```

- [ ] **Parametrized Tests** for edge cases:

  ```python
  @pytest.mark.parametrize(
      "applies_to,expected_income_types",
      [
          (["business"], ["business"]),
          (["farming"], ["farming"]),
          (["fishing"], ["fishing"]),
          (["business", "farming"], ["business", "farming"]),
          (["business", "farming", "fishing"], ["business", "farming", "fishing"]),
      ]
  )
  def test_income_type_mapping(applies_to, expected_income_types) -> None:
      """All applies_to values should map to income_type."""
      rules = [
          ExtractedRule(
              rule_number=8523,
              title="Test",
              content="...",
              applies_to=applies_to,
              source_citation="Line 8523",
              chapter="Chapter 3",
              section=None,
              source_file="t4002-5.html",
              expert_source="classic",
              confidence_score=1.0
          )
      ]

      transformer = YAMLTransformer()
      metadata = transformer._aggregate_metadata(rules)

      assert set(metadata.income_type) == set(expected_income_types)
  ```

- [ ] **Verification Commands**:

  ```bash
  # Run all unit tests
  uv run pytest tests/unit/test_transformer.py -v

  # Run with coverage
  uv run pytest tests/unit/test_transformer.py \
    --cov=src/qe_tax_rag/extraction/ca/transformer \
    --cov-report=term \
    --cov-report=html

  # Open coverage report
  open htmlcov/index.html
  ```

**Dependency**: T2.1, T2.2, T2.3 **Enables**: Confidence in transformer correctness
**Complexity**: Medium (comprehensive test writing)

______________________________________________________________________

## TICKET T4.2: Integration Tests (Already Passing ✅)

**Scope**: End-to-end integration tests with real YAML → JSONL → Database flow

**Status**: ✅ **3 integration tests already passing** in `tests/integration/test_cli_pipeline.py`:
- `test_pipeline_extraction_end_to_end` (lines 199-233)
- `test_pipeline_extraction_with_intermediate_dir` (lines 236-260)
- `test_pipeline_extraction_keeps_intermediate_on_success` (lines 263-286)

**New Addition**: Add 1 slow performance baseline test

### Acceptance Criteria

- [ ] **Test File**: `tests/integration/test_extraction_pipeline.py`

  ```python
  """Integration tests for extraction pipeline with transformer."""

  import subprocess
  from pathlib import Path
  import sqlite3
  import json

  import pytest
  from qe_tax_rag.data.schema import CREATE_TABLES_SQL


  @pytest.mark.integration
  def test_yaml_to_jsonl_to_database(tmp_path: Path) -> None:
      """Full flow: YAML → JSONL → Database should work end-to-end."""
      # 1. Create test YAML
      yaml_path = tmp_path / "test_rules.yml"
      yaml_content = """
      schema_version: "1.0"
      extraction_timestamp: "2025-01-01T00:00:00Z"
      rules:
        - rule_number: 8523
          title: "Meals and entertainment"
          content: "You can deduct 50% of restaurant expenses..."
          applies_to:
            - business
            - fishing
          source_citation: "Line 8523"
          chapter: "Chapter 3 – Expenses"
          section: "Part 4 – Net income"
          source_file: "t4002-5.html"
          expert_source: "adjudicated"
          anchor_id: "tocch3ln8523"
          confidence_score: 0.95
        - rule_number: 9200
          title: "Motor vehicle expenses"
          content: "Deductible car expenses include fuel and mileage..."
          applies_to:
            - business
          source_citation: "Line 9200"
          chapter: "Chapter 3 – Expenses"
          section: "Part 5 – Vehicle"
          source_file: "t4002-5.html"
          expert_source: "classic"
          anchor_id: "tocch3ln9200"
          confidence_score: 1.0
      """
      yaml_path.write_text(yaml_content)

      # 2. Transform to JSONL
      jsonl_path = tmp_path / "chunks.jsonl"
      result = subprocess.run(
          [
              "uv", "run", "extract-rules", "transform",
              str(yaml_path),
              str(jsonl_path)
          ],
          capture_output=True,
          text=True
      )

      assert result.returncode == 0, f"Transform failed: {result.stderr}"
      assert jsonl_path.exists()

      # 3. Verify JSONL structure
      with open(jsonl_path) as f:
          lines = f.readlines()
          assert len(lines) == 1  # One document (grouped by source_file)

          doc_data = json.loads(lines[0])
          assert doc_data["document_id"] == "t4002-5"
          assert "t4002" in doc_data["title"].lower()

          # Verify metadata
          assert set(doc_data["metadata"]["income_type"]) == {"business", "fishing"}
          assert "meals" in doc_data["metadata"]["expense_type"]
          assert "vehicle" in doc_data["metadata"]["expense_type"]

          # Verify sections
          assert len(doc_data["sections"]) == 1  # One chapter
          assert "Chapter 3" in doc_data["sections"][0]["section_title"]

          # Verify content
          chunks = doc_data["sections"][0]["content"]
          assert len(chunks) == 2  # Two rules

          # Verify LINE-{number} citation format
          citations = [c["citation_id"] for c in chunks]
          assert "LINE-8523" in citations
          assert "LINE-9200" in citations

          # Verify extraction metadata preserved
          chunk_8523 = next(c for c in chunks if c["citation_id"] == "LINE-8523")
          assert chunk_8523["extraction_source"] == "adjudicated"
          assert chunk_8523["extraction_confidence"] == 0.95
          assert chunk_8523["source_anchor"] == "tocch3ln8523"

      # 4. Build database
      db_path = tmp_path / "test.db"
      result = subprocess.run(
          [
              "uv", "run", "python", "scripts/cli.py", "build",
              "--input-file", str(jsonl_path),
              "--output-db", str(db_path)
          ],
          capture_output=True,
          text=True
      )

      assert result.returncode == 0, f"Build failed: {result.stderr}"
      assert db_path.exists()

      # 5. Verify database content
      conn = sqlite3.connect(db_path)

      # Check rules inserted
      cursor = conn.execute("SELECT COUNT(*) FROM rules")
      count = cursor.fetchone()[0]
      assert count == 2, f"Expected 2 rules, got {count}"

      # Check LINE-{number} citations
      cursor = conn.execute("SELECT citation_id FROM rules ORDER BY citation_id")
      citations = [row[0] for row in cursor.fetchall()]
      assert citations == ["LINE-8523", "LINE-9200"]

      # Check metadata_json
      cursor = conn.execute(
          "SELECT metadata_json FROM rules WHERE citation_id = ?",
          ("LINE-8523",)
      )
      metadata = json.loads(cursor.fetchone()[0])
      assert metadata["extraction_source"] == "adjudicated"
      assert metadata["extraction_confidence"] == 0.95
      assert metadata["income_type"] == ["business", "fishing"]

      # Check FTS5 index
      cursor = conn.execute(
          "SELECT COUNT(*) FROM rules_fts WHERE content MATCH 'restaurant'"
      )
      assert cursor.fetchone()[0] > 0

      # Check vector embeddings
      cursor = conn.execute("SELECT COUNT(*) FROM rules_vec")
      vec_count = cursor.fetchone()[0]
      assert vec_count == 2

      conn.close()


  @pytest.mark.integration
  def test_transformer_with_gemini_comparison(tmp_path: Path) -> None:
      """
      Compare extraction pipeline output with Gemini pipeline.

      Both should create valid databases that work with search.
      """
      # This test would compare:
      # 1. Create DB from extraction pipeline (YAML → JSONL → DB)
      # 2. Create DB from Gemini pipeline (HTML → JSONL → DB)
      # 3. Run same search on both
      # 4. Verify both return results (different results OK)

      pass  # Detailed implementation needed


  @pytest.mark.integration
  @pytest.mark.slow
  def test_pipeline_extraction_command(tmp_path: Path) -> None:
      """Pipeline-extraction command should create working database."""
      # Setup test HTML directory
      html_dir = tmp_path / "html"
      html_dir.mkdir()

      # Create minimal test HTML file
      html_file = html_dir / "test.html"
      html_file.write_text("""
      <html>
      <body>
      <h2>Line 8523</h2>
      <p>Meals and entertainment expenses...</p>
      </body>
      </html>
      """)

      db_path = tmp_path / "test.db"

      # Run pipeline
      result = subprocess.run(
          [
              "uv", "run", "python", "scripts/cli.py", "pipeline-extraction",
              "--input-dir", str(html_dir),
              "--output-db", str(db_path),
              "--keep-intermediate"
          ],
          capture_output=True,
          text=True
      )

      assert result.returncode == 0
      assert db_path.exists()

      # Verify database is searchable
      import qe_tax_rag as qe
      qe.init(db_path=db_path)  # Assuming init can take custom db_path
      results = qe.search("meals", top_k=5)

      assert len(results) > 0
  ```

- [ ] **Performance Baseline Test** (NEW - addresses Zen recommendation):

  ```python
  @pytest.mark.integration
  @pytest.mark.slow
  def test_full_document_set_performance_baseline(tmp_path: Path) -> None:
      """Establish performance baseline with full document set to detect regressions."""
      # Use realistic full T4002 document set (~247 rules)
      html_dir = Path("cra_documents/cra_t4002e_rev24_dump/")
      db_path = tmp_path / "baseline.db"

      import time
      start = time.time()

      result = subprocess.run(
          [
              "uv", "run", "python", "scripts/cli.py", "pipeline-extraction",
              "--input-dir", str(html_dir),
              "--output-db", str(db_path)
          ],
          capture_output=True,
          text=True,
          timeout=600  # 10 min timeout
      )

      elapsed = time.time() - start

      assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
      assert db_path.exists()

      # Record baseline for future regression detection
      print(f"\n⏱️  Performance Baseline: {elapsed:.2f}s for full T4002 extraction")

      # Verify database quality
      conn = sqlite3.connect(db_path)
      rule_count = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
      assert rule_count > 200, f"Expected >200 rules, got {rule_count}"
      conn.close()
  ```

- [ ] **Verification Commands**:

  ```bash
  # Run fast integration tests
  uv run pytest tests/integration/test_extraction_pipeline.py -v -m "integration and not slow"

  # Run all integration tests including performance baseline
  uv run pytest tests/integration/test_extraction_pipeline.py -v -m integration
  ```

**Dependency**: T2.1, T2.2, T2.3, T3.1, T3.3 **Enables**: Confidence in end-to-end
workflow + regression detection **Complexity**: High (full integration testing)

______________________________________________________________________

## TICKET T4.3: Search Quality Tests (DEFERRED - Post-Launch)

**Scope**: Measure search quality impact of extraction pipeline vs Gemini pipeline

**Status**: ⏸️  **DEFERRED** per Zen MCP analysis

**Rationale (YAGNI)**:
- Transformer's job is **valid database structure**, not search quality analysis
- Search quality depends on downstream RAG system, not transformer correctness
- Testing 50 queries with MRR/precision/recall is analysis work, not production blocker
- **Recommendation**: Defer to post-launch as optional monitoring/improvement task

**If/When Implemented** (post-launch only):

### Acceptance Criteria (Optional Future Work)

- [ ] **Test File**: `tests/integration/test_search_quality.py`

  ```python
  """Search quality comparison: Extraction vs Gemini pipelines."""

  import pytest
  from pathlib import Path
  import qe_tax_rag as qe


  # Golden dataset of test queries
  TEST_QUERIES = [
      {
          "query": "restaurant meal expenses",
          "expected_keywords": ["meals", "50%", "deduct"],
          "query_type": "line_item"
      },
      {
          "query": "vehicle mileage",
          "expected_keywords": ["vehicle", "car", "mileage"],
          "query_type": "line_item"
      },
      {
          "query": "What is a business expense?",
          "expected_keywords": ["business", "expense", "deductible"],
          "query_type": "conceptual"
      },
      {
          "query": "home office deduction",
          "expected_keywords": ["home", "office", "workspace"],
          "query_type": "line_item"
      },
      # Add 46 more for 50 total
  ]


  @pytest.mark.integration
  @pytest.mark.slow
  def test_extraction_pipeline_search_quality(
      extraction_db: Path,  # Fixture providing extraction DB
      gemini_db: Path  # Fixture providing Gemini DB
  ) -> None:
      """
      Compare search quality between extraction and Gemini pipelines.

      Measures:
      - Precision: Relevance of returned results
      - Recall: Coverage of expected results
      - MRR: Mean Reciprocal Rank
      """
      results = {
          "extraction": {"precision": [], "recall": [], "mrr": []},
          "gemini": {"precision": [], "recall": [], "mrr": []}
      }

      for query_data in TEST_QUERIES:
          query = query_data["query"]
          expected = query_data["expected_keywords"]

          # Test extraction DB
          qe.init(db_path=extraction_db)
          extraction_results = qe.search(query, top_k=5)
          extraction_metrics = _calculate_metrics(extraction_results, expected)

          results["extraction"]["precision"].append(extraction_metrics["precision"])
          results["extraction"]["recall"].append(extraction_metrics["recall"])
          results["extraction"]["mrr"].append(extraction_metrics["mrr"])

          # Test Gemini DB
          qe.init(db_path=gemini_db)
          gemini_results = qe.search(query, top_k=5)
          gemini_metrics = _calculate_metrics(gemini_results, expected)

          results["gemini"]["precision"].append(gemini_metrics["precision"])
          results["gemini"]["recall"].append(gemini_metrics["recall"])
          results["gemini"]["mrr"].append(gemini_metrics["mrr"])

      # Calculate averages
      extraction_avg_precision = sum(results["extraction"]["precision"]) / len(TEST_QUERIES)
      gemini_avg_precision = sum(results["gemini"]["precision"]) / len(TEST_QUERIES)

      extraction_avg_mrr = sum(results["extraction"]["mrr"]) / len(TEST_QUERIES)
      gemini_avg_mrr = sum(results["gemini"]["mrr"]) / len(TEST_QUERIES)

      # Print comparison report
      print("\n=== Search Quality Comparison ===")
      print(f"Extraction Pipeline - Precision: {extraction_avg_precision:.2%}")
      print(f"Gemini Pipeline     - Precision: {gemini_avg_precision:.2%}")
      print(f"Extraction Pipeline - MRR: {extraction_avg_mrr:.3f}")
      print(f"Gemini Pipeline     - MRR: {gemini_avg_mrr:.3f}")

      # Document findings (don't fail, just record)
      # Expected: Extraction better on line-item queries, Gemini better on conceptual


  def _calculate_metrics(results, expected_keywords):
      """Calculate precision, recall, MRR for search results."""
      # Count how many expected keywords appear in results
      matches = 0
      first_match_rank = None

      for i, result in enumerate(results):
          content_lower = result.content.lower()
          if any(kw.lower() in content_lower for kw in expected_keywords):
              matches += 1
              if first_match_rank is None:
                  first_match_rank = i + 1

      precision = matches / len(results) if results else 0.0
      recall = min(matches / len(expected_keywords), 1.0)
      mrr = 1.0 / first_match_rank if first_match_rank else 0.0

      return {"precision": precision, "recall": recall, "mrr": mrr}


  @pytest.mark.integration
  def test_line_item_query_precision(extraction_db: Path) -> None:
      """Extraction pipeline should excel at line-item queries."""
      qe.init(db_path=extraction_db)

      # Query for specific line item
      results = qe.search("Line 8523 meals", top_k=5)

      # Should return LINE-8523 as top result
      assert len(results) > 0
      assert results[0].citation_id == "LINE-8523"
      assert results[0].score > 0.8  # High confidence


  @pytest.mark.integration
  def test_conceptual_query_coverage(gemini_db: Path) -> None:
      """Gemini pipeline should handle conceptual queries better."""
      qe.init(db_path=gemini_db)

      # Conceptual query
      results = qe.search("What expenses can I deduct?", top_k=10)

      # Should return diverse results (not just one line item)
      assert len(results) >= 5

      # Results should cover multiple expense types
      expense_types = set()
      for result in results[:5]:
          expense_types.update(result.expense_types)

      assert len(expense_types) >= 3  # Multiple categories
  ```

- [ ] **Fixtures** (`tests/conftest.py`):

  ```python
  @pytest.fixture(scope="session")
  def extraction_db(tmp_path_factory) -> Path:
      """Build extraction pipeline database once per session."""
      # Create minimal extraction DB
      # Return path
      pass

  @pytest.fixture(scope="session")
  def gemini_db(tmp_path_factory) -> Path:
      """Build Gemini pipeline database once per session."""
      # Create minimal Gemini DB
      # Return path
      pass
  ```

- [ ] **Quality Report**: Document findings in `docs/search_quality_report.md`

  - Precision/recall by query type
  - Trade-offs between pipelines
  - Recommendations for which to use when

- [ ] **Verification Commands**:

  ```bash
  uv run pytest tests/integration/test_search_quality.py -v -s
  ```

**Dependency**: T4.2 (integration tests) **Enables**: Data-driven decision on pipeline
recommendation **Complexity**: Medium (metrics calculation)

______________________________________________________________________

## PHASE 5: Documentation & Rollout

**Goal**: Document transformer functionality and provide migration guidance.

______________________________________________________________________

## TICKET T5.1: Documentation & Examples (MVD Approach)

**Scope**: Minimal Viable Documentation - Update CLAUDE.md + create pipeline guide

**Rationale**: Follow 80/20 principle - focus on essential docs that unblock usage

**MVD Approach**:
- ✅ Update CLAUDE.md extraction pipeline section (already exists, needs transformer update)
- ✅ Create "Choosing a Pipeline" guide (high-value decision doc)
- ⏸️  DEFER: Full tutorial (users can reference CLAUDE.md)
- ⏸️  DEFER: Programmatic examples (transformer.py docstrings suffice)

### Acceptance Criteria (Scoped for MVD)

- [ ] **Update CLAUDE.md**: Add transformer section

  ````markdown
  ## Transformer Pipeline (YAML to JSONL)

  The transformer bridges the extraction pipeline (TICKETS 1-6) with the RAG database.

  ### What It Does
  - Converts ExtractedRule (YAML) to ParsedDocument (JSONL)
  - Maps `rule_number` to `LINE-{number}` citation format
  - Infers expense types from content
  - Preserves extraction metadata (source, confidence, anchor)

  ### Usage

  **Option 1: Manual transformation**
  ```bash
  uv run extract-rules transform output/rules.yml data/chunks.jsonl
  ````

  **Option 2: Auto-transform**

  ```bash
  uv run extract-rules run HTML_DIR output/rules.yml \
    --auto-transform --output-jsonl data/chunks.jsonl
  ```

  **Option 3: Full pipeline**

  ```bash
  uv run python scripts/cli.py pipeline-extraction \
    --input-dir HTML_DIR --output-db data/cra_rules.db
  ```

  ### Schema Compatibility

  - Citation ID: Accepts both `S#-F#-C#-p#` and `LINE-{number}`
  - Metadata: Added `income_type` field
  - TextChunk: Added extraction provenance fields

  ```

  ```

- [ ] **Create "Choosing a Pipeline" Guide**: `docs/howto/choosing-extraction-vs-gemini.md`

  ````markdown
  # How-To: Choosing Between Extraction and Gemini Pipelines

  ## Quick Decision Matrix

  | Use Case | Pipeline | Why |
  |----------|----------|-----|
  | Line-item queries ("Line 8523") | **Extraction** | Higher precision, metadata-rich |
  | Conceptual queries ("What is deductible?") | **Gemini** | More context, explanatory |
  | No API key available | **Extraction** | No runtime API dependency |
  | Need income_type metadata | **Extraction** | Structured metadata included |

  ## Pipeline Comparison

  ### Extraction Pipeline (Recommended for Production)
  - ✅ No API key needed (after initial extraction)
  - ✅ Structured metadata (income types, confidence scores)
  - ✅ Precise LINE-{number} citations
  - ✅ ~247 focused chunks (T4002)
  - ⚠️  Less narrative context

  ### Gemini Pipeline (Original)
  - ✅ Rich narrative content
  - ✅ Better for conceptual queries
  - ✅ ~1000 chunks (T4002)
  - ⚠️  Requires GEMINI_API_KEY
  - ⚠️  Broader, less precise chunks

  ## Usage Commands

  **Extraction Pipeline**:
  ```bash
  uv run python scripts/cli.py pipeline-extraction \
    --input-dir cra_documents/ --output-db extraction_rules.db
  ````

  **Gemini Pipeline**:

  ```bash
  # See existing CLAUDE.md section for Gemini usage
  ```

  ```

  ```

- [ ] **Verification**:

  - CLAUDE.md transformer section is complete
  - Choosing-a-pipeline guide is clear and actionable
  - Command examples work as documented

**Dependency**: T4.1, T4.2 (need working transformer) **Enables**: Users can understand and choose pipelines **Complexity**: Low (MVD approach - ~1-2 hours)

______________________________________________________________________

## Dependency Graph

```
PHASE 1: Schema Compatibility
├─ T1.1 (Citation ID Pattern) ──┐
├─ T1.2 (Metadata Extension) ───┼─┐
└─ T1.3 (DB Schema Verify) ─────┘ │
                                   │
PHASE 2: Core Transformer          │
├─ T2.1 (Transformer) ← T1.1, T1.2 │
├─ T2.2 (Classifier) ← T2.1 ───────┤
└─ T2.3 (Error Handling) ← T2.1 ───┤
                                   │
PHASE 3: CLI Integration           │
├─ T3.1 (Transform Cmd) ← T2.1,2.2,2.3
├─ T3.2 (Auto-Transform) ← T2.1, T3.1
└─ T3.3 (Pipeline Cmd) ← T2.1, T3.1
                                   │
PHASE 4: Testing                   │
├─ T4.1 (Unit Tests) ← T2.1,2.2,2.3 │
├─ T4.2 (Integration) ← T2.*,T3.1,3.3
└─ T4.3 (Quality) ← T4.2 ───────────┤
                                   │
PHASE 5: Documentation             │
└─ T5.1 (Docs) ← ALL ──────────────┘
```

**Critical Path**: T1.1 → T1.2 → T2.1 → T2.2 → T2.3 → T3.1 → T4.2 → T5.1

______________________________________________________________________

## Timeline Estimate (Updated for 80/20 Scope)

### Solo Developer (Sequential)

- **Phases 1-3**: ✅ COMPLETE (schema + transformer + CLI)
- **Phase 4**: 4-6 hours (unit tests ~85% coverage + verify integration tests)
- **Phase 5**: 1-2 hours (MVD - update CLAUDE.md + create choosing guide)
- **Total Remaining**: ~6-8 hours (1 day)

### Original Estimates (Pre-Scoping)

- **Phase 1**: 0.5 days (schema changes) - ✅ COMPLETE
- **Phase 2**: 2 days (transformer core) - ✅ COMPLETE
- **Phase 3**: 1 day (CLI integration) - ✅ COMPLETE
- **Phase 4**: 1.5 days → **Reduced to 4-6 hours** (scoped to ~85% coverage)
- **Phase 5**: 0.5 days → **Reduced to 1-2 hours** (MVD approach)
- **Total Original**: 5.5 days → **Actual with scoping**: ~4 days

______________________________________________________________________

## Success Metrics (Updated for 80/20)

### Short-Term (Remaining Work - 1 day)

- [x] Phases 1-3 complete (schema + transformer + CLI) - ✅ DONE
- [ ] Unit test coverage ~85% on critical logic (not ≥95% vanity metric)
- [x] Integration tests passing (3 tests already passing) - ✅ DONE
- [ ] MVD documentation complete (CLAUDE.md + choosing guide)
- [x] Can run: HTML → YAML → JSONL → DB → Search - ✅ DONE

### Long-Term (Post-Launch - Optional)

- [ ] Performance baseline tracked (1 slow test added)
- [ ] Search quality analysis (T4.3 - deferred to post-launch)
- [ ] User feedback collected on pipeline choice
- [ ] Pipeline recommendation refined based on data

______________________________________________________________________

## Risk Mitigation

| Risk                               | Impact | Mitigation                                              |
| ---------------------------------- | ------ | ------------------------------------------------------- |
| **Search quality regression**      | High   | Dual indexing, A/B testing, gather data before decision |
| **Citation ID conflicts**          | Medium | Validation in transformer, fail-fast on duplicates      |
| **Metadata inference errors**      | Low    | Keyword classifier is simple, fallback to "general"     |
| **User confusion (two pipelines)** | Medium | Clear documentation, default recommendation             |
| **Performance issues**             | Low    | Benchmark transformation time, optimize if needed       |

______________________________________________________________________

## Next Steps

1. **Review this plan** with stakeholders
1. **Approve ticket breakdown** and estimates
1. **Assign tickets** to team members
1. **Start with Phase 1** (foundational changes)
1. **Track progress** using todo list

______________________________________________________________________

**Generated**: 2025-10-17 **Based on**: TRANSFORMER_DESIGN_PLAN.md (Zen MCP Planning)
**Structure**: Following plan.md format (MECE tickets) **Status**: Ready for
Implementation
