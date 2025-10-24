# Data Model Normalization Plan: HTML→YAML→SQLite Pipeline

## Executive Summary

After critical analysis with Zen, identified that we have **TWO competing pipelines**
creating unnecessary schema translation:

1. **Legacy Pipeline** (`scripts/`): TextExtractor → Gemini Parser → ParsedDocument →
   SQLite
1. **Current Pipeline** (`src/extraction/ca/`): HTML → Classic/LLM → ExtractedRule →
   **Transformer** → ParsedDocument → SQLite

**Root Cause**: The extraction pipeline forces `ExtractedRule` through `ParsedDocument`
just to reuse `IndexBuilder`, creating ~500 LOC of translation logic.

**Solution**: Bypass `ParsedDocument` in extraction pipeline - go directly from
`RuleSet` to database-ready chunks.

______________________________________________________________________

## Critical Analysis: Why Current Separation Is Not Justified

### Where Consolidation WOULD Help

**1. The `ParsedDocument` schema is NOT being used by the Gemini parser anymore**

- `scripts/parser/gemini_parser.py` exists but is a **DIFFERENT** Gemini parser than the
  extraction pipeline
- The extraction pipeline (`src/qe_tax_rag/extraction/ca/`) uses `ExtractedRule` →
  `RuleSet` → YAML
- The `scripts/parser/` Gemini parser uses `ParsedDocument` for a **separate legacy
  workflow** (preprocess → parse → build)
- **This is duplication, not separation of concerns!**

**2. The Transformer is doing unnecessary schema translation**

- `YAMLTransformer` converts `ExtractedRule` → `ParsedDocument` → JSONL

- But `ExtractedRule` already has ALL the information needed for the database:

  - `rule_number` → `LINE-{number}` (citation_id)
  - `content` → content
  - `applies_to` → income_type
  - `expert_source` + `confidence_score` → extraction metadata
  - `anchor_id` → source_anchor

- **The transformer is creating artificial complexity by forcing extraction data through
  a generic "document parser" schema**

**3. ParsedDocument has features the extraction pipeline doesn't need**

- `ListChunk`, `TableChunk`, nested `ListItem.sub_items`
- Section hierarchy with `section_level`
- These exist for the **Gemini parser** use case, not the HTML extraction use case
- Extraction pipeline flattens everything immediately anyway!

### Where Separation IS Justified

**1. Different input sources, different concerns**

- Extraction pipeline: HTML with line numbers, icons, anchors → highly structured
- Gemini parser: Raw text → needs to infer structure
- **BUT**: These use DIFFERENT pipelines today, so shared schema isn't helping

**2. Future extensibility argument is weak**

- "We might add PDF parser or API scraper" - speculative (YAGNI)
- Current extraction pipeline is CRA-HTML-specific by design (`/ca/` subdirectory)
- If we add another jurisdiction or source, create `/us/` or `/pdf/` with appropriate
  schemas

### The Real Problem: Two Competing Pipelines

```
Pipeline 1 (LEGACY - scripts/):
HTML/PDF → TextExtractor → Gemini Parser → ParsedDocument → JSONL → SQLite

Pipeline 2 (CURRENT - src/qe_tax_rag/extraction/ca/):
HTML → Classic+LLM Parser → ExtractedRule → Transformer → ParsedDocument → JSONL → SQLite
```

**The extraction pipeline is being forced through ParsedDocument just to reuse
IndexBuilder!**

### Verdict

**The current separation is NOT justified**. It's not elegant layering - it's
**accidental complexity** from having two parallel pipelines that converged at the wrong
layer.

**Recommendation**: Skip ParsedDocument entirely in the extraction pipeline. Have
`RuleSet` provide a `.to_database_chunks()` method that returns properly typed chunks
directly consumable by `IndexBuilder`.

This would:

- ✅ Remove the entire transformer module (500+ LOC eliminated)
- ✅ Remove impedance mismatch between extraction and database
- ✅ Keep schemas DRY (Don't Repeat Yourself)
- ✅ Preserve type safety end-to-end
- ✅ Allow legacy Gemini parser pipeline to keep using `ParsedDocument` if needed

______________________________________________________________________

## Proposed Architecture

### Phase 1: Create Shared Chunk Model (2 hours)

**Location**: `src/qe_tax_rag/data/models.py` (NEW FILE - shared between extraction and
parsing)

```python
"""Shared models for database ingestion."""

from pydantic import BaseModel, ConfigDict, Field


class ChunkMetadata(BaseModel):
    """Metadata stored as JSON in SQLite metadata_json column."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Document-level metadata
    income_type: list[str] = Field(default_factory=list)
    section_title: str | None = None
    document_id: str | None = None

    # Chunk-level extraction metadata
    extraction_source: str | None = None
    extraction_confidence: float | None = Field(None, ge=0.0, le=1.0)
    source_anchor: str | None = None


class DatabaseChunk(BaseModel):
    """Flattened chunk ready for database insertion.

    Single source of truth consumed by IndexBuilder.
    Can be produced by EITHER:
    - ExtractedRule (extraction pipeline)
    - ParsedDocument.to_database_chunks() (Gemini parser pipeline)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Content fields
    content: str = Field(description="Full text content")
    citation_id: str = Field(description="Citation ID (LINE-XXXX or S-F-C-p format)")
    source_url: str = Field(description="Source URL from SourceFile")
    source_hash: str = Field(description="SHA256 hash of source file")

    # Metadata fields (top-level for SQL filtering)
    province: list[str] | None = Field(default=None, description="List of provinces")
    business_type: list[str] | None = Field(default=None, description="List of business types")
    expense_types: list[str] = Field(default_factory=list, description="List of expense types")

    # Nested metadata (stored as JSON in SQLite)
    metadata: ChunkMetadata = Field(description="Nested metadata for JSON storage")
```

### Phase 2: Eliminate Transformer - Add Direct Conversion (3 hours)

**Update**: `src/qe_tax_rag/extraction/ca/schema.py`

Add method to `RuleSet`:

```python
from qe_tax_rag.data.models import DatabaseChunk, ChunkMetadata
from qe_tax_rag.search.models import SourceFile


class RuleSet(BaseModel):
    """Collection of extracted rules with schema metadata."""

    # ... existing fields ...

    def to_database_chunks(
        self,
        source_files: dict[str, SourceFile],  # filename → SourceFile
        expense_classifier: "ExpenseTypeClassifier",
    ) -> list[DatabaseChunk]:
        """
        Convert rules directly to database-ready chunks.

        REPLACES: YAMLTransformer.transform_yaml_to_jsonl()
        ELIMINATES: ParsedDocument intermediate representation

        Args:
            source_files: Mapping of source filename to SourceFile metadata
            expense_classifier: Classifier for inferring expense types

        Returns:
            List of DatabaseChunk objects ready for IndexBuilder
        """
        chunks = []

        for rule in self.rules:
            source_file = source_files.get(rule.source_file)
            if not source_file:
                raise ValueError(f"No SourceFile found for {rule.source_file}")

            chunks.append(
                DatabaseChunk(
                    content=rule.content,
                    citation_id=f"LINE-{rule.rule_number}",
                    source_url=str(source_file.url),
                    source_hash=source_file.hash,
                    province=None,  # Federal rules
                    business_type=None,  # Not mapped from applies_to
                    expense_types=expense_classifier.infer_expense_types(rule),
                    metadata=ChunkMetadata(
                        income_type=[at.value for at in rule.applies_to],
                        section_title=rule.chapter,
                        document_id=rule.source_file.replace(".html", ""),
                        extraction_source=rule.expert_source.value,
                        extraction_confidence=rule.confidence_score,
                        source_anchor=rule.anchor_id,
                    ),
                )
            )

        return chunks
```

### Phase 3: Update IndexBuilder (1 hour)

**Update**: `src/qe_tax_rag/data/builder.py`

Replace `_load_and_flatten_chunks` to support both YAML and JSONL:

```python
from pathlib import Path
from qe_tax_rag.data.models import DatabaseChunk


def _load_and_flatten_chunks(
    self, input_path: Path, source_files: list[SourceFile]
) -> list[DatabaseChunk]:
    """
    Load chunks from YAML (extraction) or JSONL (legacy parser).

    Auto-detects format and returns unified DatabaseChunk list.

    Args:
        input_path: Path to YAML or JSONL file
        source_files: List of SourceFile metadata

    Returns:
        List of DatabaseChunk objects ready for embedding and insertion
    """
    if input_path.suffix == ".yml" or input_path.suffix == ".yaml":
        # Extraction pipeline: YAML → DatabaseChunk
        import yaml
        from qe_tax_rag.extraction.ca.schema import RuleSet
        from qe_tax_rag.extraction.ca.transformer import ExpenseTypeClassifier

        logger.info(f"Loading extraction YAML: {input_path}")

        with open(input_path) as f:
            data = yaml.safe_load(f)

        ruleset = RuleSet.model_validate(data)

        # Create filename → SourceFile mapping
        source_map = {Path(sf.path).stem: sf for sf in source_files}

        # Initialize expense classifier
        classifier = ExpenseTypeClassifier()

        return ruleset.to_database_chunks(source_map, classifier)

    elif input_path.suffix == ".jsonl":
        # Legacy Gemini parser: JSONL → DatabaseChunk
        from qe_tax_rag.parser.schema import ParsedDocument

        logger.info(f"Loading legacy JSONL: {input_path}")

        chunks = []
        with open(input_path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    doc = ParsedDocument.model_validate_json(line)
                    chunks.extend(doc.to_database_chunks(source_files))
                except Exception as e:
                    logger.error(f"Failed to parse line {line_num}: {e}")
                    raise

        return chunks

    else:
        raise ValueError(
            f"Unsupported input format: {input_path.suffix}. "
            f"Expected .yml, .yaml, or .jsonl"
        )
```

Update method signature for `build_from_jsonl` → `build_from_file`:

```python
def build_from_file(
    self,
    input_path: str | Path,  # Auto-detect YAML or JSONL
    manifest_path: str,
    source_files: list[SourceFile],
    data_version: str,
    continue_on_error: bool = False,
) -> None:
    """
    Main entry point to build index from YAML or JSONL file.

    Auto-detects format based on file extension.

    Args:
        input_path: Path to YAML or JSONL file with rules/documents
        manifest_path: Where to write manifest.json
        source_files: List of SourceFile models with hash/URL metadata
        data_version: Version string (YYYY.MM format)
        continue_on_error: If True, skip chunks with embedding errors

    Raises:
        ValueError: Duplicate citation_id found or unsupported format
        EmbeddingError: Embedding generation failed (if continue_on_error=False)
        sqlite3.IntegrityError: Database constraint violation
    """
    input_path = Path(input_path)

    logger.info(f"Starting index build: {input_path} → {self.db_path}")
    logger.info(f"Data version: {data_version}, continue_on_error: {continue_on_error}")

    # ... rest of implementation using self._load_and_flatten_chunks(input_path, source_files)
```

### Phase 4: Update Legacy Pipeline to Use DatabaseChunk (1 hour)

**Update**: `src/qe_tax_rag/parser/schema.py`

Replace `to_flat_chunks()` with `to_database_chunks()`:

```python
from qe_tax_rag.data.models import DatabaseChunk, ChunkMetadata
from qe_tax_rag.search.models import SourceFile


class ParsedDocument(BaseModel):
    """Root model for parsed CRA document."""

    # ... existing fields ...

    def to_database_chunks(
        self,
        source_files: list[SourceFile]
    ) -> list[DatabaseChunk]:
        """
        Convert hierarchical ParsedDocument to flat DatabaseChunk list.

        REPLACES: to_flat_chunks() returning dict[str, object]

        Args:
            source_files: List of SourceFile metadata for lookup

        Returns:
            List of DatabaseChunk objects ready for IndexBuilder
        """
        chunks = []

        # Find matching source file
        source_file = self._find_source_file(source_files)

        for section in self.sections:
            for content_item in section.content:
                if isinstance(content_item, TextChunk):
                    chunks.append(
                        DatabaseChunk(
                            content=content_item.text,
                            citation_id=content_item.citation_id or "",
                            source_url=str(source_file.url),
                            source_hash=source_file.hash,
                            province=self.metadata.province,
                            business_type=self.metadata.business_type,
                            expense_types=self.metadata.expense_type,
                            metadata=ChunkMetadata(
                                income_type=self.metadata.income_type,
                                section_title=section.section_title,
                                document_id=self.document_id,
                                extraction_source=content_item.extraction_source,
                                extraction_confidence=content_item.extraction_confidence,
                                source_anchor=content_item.source_anchor,
                            ),
                        )
                    )
                elif isinstance(content_item, ListChunk):
                    # Flatten list items recursively
                    for item in content_item.items:
                        chunks.extend(
                            self._flatten_list_item_to_chunks(
                                item=item,
                                section=section,
                                source_file=source_file,
                            )
                        )
                elif isinstance(content_item, TableChunk):
                    # Convert table to text representation
                    table_text = self._table_to_text(content_item.data)
                    chunks.append(
                        DatabaseChunk(
                            content=table_text,
                            citation_id=content_item.citation_id or "",
                            source_url=str(source_file.url),
                            source_hash=source_file.hash,
                            province=self.metadata.province,
                            business_type=self.metadata.business_type,
                            expense_types=self.metadata.expense_type,
                            metadata=ChunkMetadata(
                                income_type=self.metadata.income_type,
                                section_title=section.section_title,
                                document_id=self.document_id,
                            ),
                        )
                    )

        return chunks

    def _find_source_file(self, source_files: list[SourceFile]) -> SourceFile:
        """Find SourceFile matching this document's document_id."""
        for sf in source_files:
            if Path(sf.path).stem == self.document_id:
                return sf

        # Fallback to first source file
        if source_files:
            logger.warning(
                f"No exact SourceFile match for document_id '{self.document_id}', "
                f"using first source file"
            )
            return source_files[0]

        raise ValueError("No source files provided")

    def _flatten_list_item_to_chunks(
        self,
        item: ListItem,
        section: Section,
        source_file: SourceFile,
    ) -> list[DatabaseChunk]:
        """Recursively flatten a ListItem to DatabaseChunk objects."""
        chunks = []

        # Add parent item
        chunks.append(
            DatabaseChunk(
                content=item.text,
                citation_id=item.citation_id or "",
                source_url=str(source_file.url),
                source_hash=source_file.hash,
                province=self.metadata.province,
                business_type=self.metadata.business_type,
                expense_types=self.metadata.expense_type,
                metadata=ChunkMetadata(
                    income_type=self.metadata.income_type,
                    section_title=section.section_title,
                    document_id=self.document_id,
                ),
            )
        )

        # Recursively add sub-items
        for sub_item in item.sub_items:
            chunks.extend(
                self._flatten_list_item_to_chunks(
                    item=sub_item,
                    section=section,
                    source_file=source_file,
                )
            )

        return chunks
```

### Phase 5: Update CLI Pipeline (1 hour)

**Update**: `scripts/cli.py::pipeline_extraction()`

Simplify from 3 stages to 2 stages:

```python
@app.command(name="pipeline-extraction")
def pipeline_extraction(
    input_dir: Path = typer.Option(..., "--input-dir", "-i"),
    output_db: Path = typer.Option(..., "--output-db", "-o"),
    intermediate_dir: Path | None = typer.Option(None, "--intermediate-dir"),
    keep_intermediate: bool = typer.Option(False, "--keep-intermediate"),
) -> None:
    """
    Run complete extraction-to-database pipeline.

    UPDATED: Now 2 stages instead of 3 (transformer eliminated)

    This command orchestrates:
    1. Extract rules from HTML → YAML (canonical orchestrator)
    2. Build RAG database directly from YAML (IndexBuilder auto-detects format)
    3. Validate database integrity

    Example:
        uv run python scripts/cli.py pipeline-extraction \
          --input-dir cra_documents/cra_t4002e_rev24_dump/ \
          --output-db data/cra_rules.db
    """
    import shutil
    import tempfile

    console.print("[bold blue]QE Tax RAG Extraction Pipeline[/bold blue]")
    console.print(f"Input: {input_dir}")
    console.print(f"Output DB: {output_db}\n")

    # Setup intermediate directory
    temp_dir_created = False
    if intermediate_dir:
        work_dir = intermediate_dir
        work_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"Using intermediate directory: {work_dir}")
    else:
        temp_dir = tempfile.mkdtemp(prefix="qetax_extract_")
        work_dir = Path(temp_dir)
        temp_dir_created = True
        console.print(f"Using temporary directory: {work_dir}")

    # Define intermediate file paths
    yml_path = work_dir / "rules.yml"
    manual_path = work_dir / "manual_review.yml"

    pipeline_success = False
    try:
        # =====================================================================
        # Stage 1/3: Extract rules to YAML
        # =====================================================================
        try:
            console.print(
                "\n[bold cyan]Stage 1/3: Extracting rules from HTML[/bold cyan]"
            )

            # Find HTML files
            html_files = sorted(input_dir.glob("*.html"))
            if not html_files:
                console.print(f"[red]Error: No HTML files found in {input_dir}[/red]")
                raise typer.Exit(code=1)

            console.print(f"Found {len(html_files)} HTML files to process")

            # Run extraction (HTML → YAML) via canonical orchestrator
            logger.info("Calling canonical orchestrator for extraction")
            extraction_result = run_extraction(
                input_path=input_dir,
                output_yaml=yml_path,
                manual_review_yaml=manual_path,
            )

            console.print(
                f"✅ Extracted {extraction_result['total_rules']} rules to YAML"
            )

        except Exception as e:
            console.print(f"\n[red]❌ Stage 1/3 (Extraction) failed: {e}[/red]")
            logger.exception("Stage 1 (Extraction) failed")
            raise

        # =====================================================================
        # Stage 2/3: Build database directly from YAML
        # =====================================================================
        try:
            console.print(
                "\n[bold cyan]Stage 2/3: Building searchable database[/bold cyan]"
            )

            # Create manifest for extraction pipeline
            manifest_path = work_dir / "manifest.json"
            source_files = [
                SourceFile(
                    path=f.name,
                    url=f"file://{f.absolute()}",
                    hash="",  # Hash not critical for extraction pipeline
                )
                for f in html_files
            ]

            # Build index (IndexBuilder auto-detects YAML format)
            output_db.parent.mkdir(parents=True, exist_ok=True)
            builder = IndexBuilder(db_path=str(output_db), encoder=embedding_service)
            builder.build_from_file(  # UPDATED: was build_from_jsonl
                input_path=yml_path,  # Pass YAML directly (auto-detected)
                manifest_path=str(manifest_path),
                source_files=source_files,
                data_version="2024.12",
                continue_on_error=False,
            )

            console.print(f"✅ Database built: {output_db}")

            # Show database size
            db_size_mb = output_db.stat().st_size / (1024 * 1024)
            console.print(f"   Database size: {db_size_mb:.2f} MB")

        except Exception as e:
            console.print(f"\n[red]❌ Stage 2/3 (Build) failed: {e}[/red]")
            logger.exception("Stage 2 (Build) failed")
            raise

        # =====================================================================
        # Stage 3/3: Validate database
        # =====================================================================
        try:
            console.print("\n[bold cyan]Stage 3/3: Validating database[/bold cyan]")

            validator = IndexValidator(db_path=output_db)
            validation_report = validator.validate()

            if validation_report["overall_passed"]:
                console.print("✅ Validation passed")
            else:
                console.print("[yellow]⚠️  Some validation checks failed[/yellow]")

        except Exception as e:
            console.print(f"\n[red]❌ Stage 3/3 (Validation) failed: {e}[/red]")
            logger.exception("Stage 3 (Validation) failed")
            raise

        pipeline_success = True

    except typer.Exit:
        raise

    except Exception as e:
        raise typer.Exit(code=1) from e

    finally:
        # Cleanup intermediate files if applicable
        if temp_dir_created:
            if not pipeline_success:
                console.print(
                    f"\n[yellow]⚠️  Pipeline failed. "
                    f"Intermediate files kept for debugging:[/yellow]"
                )
                console.print(f"   {work_dir}")
            elif not keep_intermediate:
                console.print("\n🧹 Cleaning up intermediate files")
                shutil.rmtree(work_dir, ignore_errors=True)
            else:
                console.print(f"\nIntermediate files kept at: {work_dir}")

    # Success summary
    console.print("\n[bold green]🎉 Pipeline complete![/bold green]")
    console.print(f"✅ Database: {output_db}")
```

### Phase 6: Remove Dead Code (30 min)

**DELETE**:

- [ ] `src/qe_tax_rag/extraction/ca/transformer.py` (~600 LOC)
- [ ] `tests/unit/extraction/ca/test_transformer.py` (~400 LOC)

**UPDATE** (deprecation):

- [ ] `ParsedDocument.to_flat_chunks()` - mark as deprecated, keep for backward compat
- [ ] Add migration guide in docstring

______________________________________________________________________

## Benefits

### Immediate Wins

- ✅ **Eliminate 1000+ LOC** (transformer + tests)
- ✅ **Single source of truth**: `DatabaseChunk` consumed by `IndexBuilder`
- ✅ **Type safety**: No more `dict[str, Any]` between stages
- ✅ **Faster pipeline**: Skip YAML→JSONL conversion step entirely
- ✅ **Clearer architecture**: Extraction pipeline is self-contained

### Long-Term Wins

- ✅ **Easier testing**: Mock `DatabaseChunk` instead of dict structures
- ✅ **Better validation**: Pydantic validates at conversion, not insertion
- ✅ **Simpler debugging**: One fewer transformation layer to trace through
- ✅ **Flexible input**: `IndexBuilder` accepts YAML OR JSONL automatically

______________________________________________________________________

## Migration Risk Assessment

**LOW RISK** - Changes are additive with clear rollback:

1. **Phase 1-2**: Add new methods alongside existing (no breakage)
1. **Phase 3-4**: Update IndexBuilder to use new methods (backward compatible via
   auto-detection)
1. **Phase 5**: Update CLI to skip transformer (opt-in change)
1. **Phase 6**: Remove old code only after full validation

**Rollback Strategy**: Revert CLI changes in Phase 5, transformer continues to work

______________________________________________________________________

## Acceptance Criteria

- [ ] All unit tests pass (update assertions to use `DatabaseChunk`)
- [ ] All integration tests pass
- [ ] `pipeline-extraction` completes successfully with 2 stages (not 3)
- [ ] Legacy `pipeline` command still works (uses JSONL path)
- [ ] mypy strict + pyright strict pass
- [ ] Database schema unchanged (backward compatible)
- [ ] Performance neutral or improved (less I/O, fewer conversions)
- [ ] Documentation updated (CLAUDE.md, architecture diagrams)

______________________________________________________________________

## Estimated Effort

**8 hours total** for clean implementation + comprehensive testing:

- **2 hours**: Create `DatabaseChunk` + `ChunkMetadata` models with full validation
- **3 hours**: Add `RuleSet.to_database_chunks()` + comprehensive unit tests
- **1 hour**: Update `IndexBuilder` with format auto-detection logic
- **1 hour**: Update `ParsedDocument.to_database_chunks()` for legacy pipeline
- **1 hour**: Update CLI + integration tests + documentation

**Bonus**: Delete 1000+ LOC afterward 🎉

______________________________________________________________________

## Follow-Up Work (Optional)

After successful migration:

1. **Performance benchmarking**: Measure pipeline speed improvement (expect 10-20%
   faster)
1. **Memory profiling**: Verify reduced memory usage (one less full-data copy)
1. **Documentation**: Update architecture diagrams showing simplified flow
1. **Monitoring**: Add metrics for YAML vs JSONL input detection

______________________________________________________________________

## Questions for User

1. Should we keep `to_flat_chunks()` for backward compatibility, or break the API?
1. Do we want to support both YAML and JSONL in production, or deprecate JSONL?
1. Should `DatabaseChunk` go in `data/models.py` or a new `models/` package?

______________________________________________________________________

## References

- Current transformer: `src/qe_tax_rag/extraction/ca/transformer.py`
- Current IndexBuilder: `src/qe_tax_rag/data/builder.py`
- Extraction schema: `src/qe_tax_rag/extraction/ca/schema.py`
- Parser schema: `src/qe_tax_rag/parser/schema.py`
- CLI orchestration: `scripts/cli.py::pipeline_extraction()`
