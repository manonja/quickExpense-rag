"""
Shared Pydantic models for database ingestion.

This module defines the single source of truth for database chunk models,
consumed by IndexBuilder and produced by both:
- ExtractedRule (extraction pipeline): RuleSet.to_database_chunks()
- ParsedDocument (legacy Gemini parser): ParsedDocument.to_database_chunks()

Architecture:
    DatabaseChunk: Flattened chunk ready for database insertion
    ChunkMetadata: Nested metadata stored as JSON in SQLite

Design Principles:
    - Type safety: Replaces dict[str, Any] with strict Pydantic models
    - Immutability: frozen=True, extra="forbid"
    - Single source of truth: Both pipelines converge here
    - DRY: Eliminates redundant transformation layers
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from qe_tax_rag.extraction.ca.schema import LineageMetadata


class ChunkMetadata(BaseModel):
    """
    Metadata stored as JSON in SQLite metadata_json column.

    This nested structure contains document-level and chunk-level metadata
    that doesn't need SQL filtering (stored as JSON for flexibility).

    Fields:
        income_type: List of income types (business, farming, fishing)
        section_title: Section where this chunk appears
        document_id: Source document identifier
        extraction_source: Parser that generated this chunk (classic, llm, adjudicated)
        extraction_confidence: Confidence score from extraction (0.0-1.0)
        source_anchor: HTML anchor ID for debugging and traceability
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Document-level metadata
    income_type: list[str] = Field(default_factory=list, description="Income types")
    section_title: str | None = Field(default=None, description="Section title")
    document_id: str | None = Field(default=None, description="Source document ID")

    # Chunk-level extraction metadata
    extraction_source: str | None = Field(
        default=None, description="Parser source (classic, llm, adjudicated)"
    )
    extraction_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Extraction confidence score"
    )
    source_anchor: str | None = Field(default=None, description="HTML anchor ID")

    # Lineage tracking (PRE-143): Full extraction pipeline provenance
    lineage: Optional["LineageMetadata"] = Field(
        default=None, description="Pipeline lineage with timestamps and stages"
    )


class DatabaseChunk(BaseModel):
    """
    Flattened chunk ready for database insertion.

    Single source of truth consumed by IndexBuilder. Can be produced by:
    - ExtractedRule (extraction pipeline) via RuleSet.to_database_chunks()
    - ParsedDocument (Gemini parser) via ParsedDocument.to_database_chunks()

    This model replaces the previous dict[str, Any] usage for type safety.

    Fields:
        content: Full text content for embedding and search
        citation_id: Citation ID (LINE-XXXX or S#-F#-C#-p# format)
        source_url: Source URL from SourceFile
        source_hash: SHA256 hash of source file
        province: List of provinces (for SQL filtering)
        business_type: List of business types (for SQL filtering)
        expense_types: List of expense types (for SQL filtering)
        metadata: Nested metadata (stored as JSON in SQLite)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Content fields
    content: str = Field(description="Full text content")
    citation_id: str = Field(description="Citation ID (LINE-XXXX or S-F-C-p format)")
    source_url: str = Field(description="Source URL from SourceFile")
    source_hash: str = Field(description="SHA256 hash of source file")

    # Metadata fields (top-level for SQL filtering)
    province: list[str] | None = Field(None, description="List of provinces")
    business_type: list[str] | None = Field(None, description="List of business types")
    expense_types: list[str] = Field(
        default_factory=list, description="List of expense types"
    )

    # Nested metadata (stored as JSON in SQLite)
    metadata: ChunkMetadata = Field(description="Nested metadata for JSON storage")
