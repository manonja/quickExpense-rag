"""Pydantic models for Gemini Flash parser structured output."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from qe_tax_rag.data.models import DatabaseChunk
    from qe_tax_rag.search.models import SourceFile


class Metadata(BaseModel):
    """Metadata extracted from CRA documents."""

    model_config = ConfigDict(frozen=True)

    province: list[str] = Field(default_factory=list)
    business_type: list[str] = Field(default_factory=list)
    expense_type: list[str] = Field(default_factory=list)
    income_type: list[str] = Field(
        default_factory=list, description="Income types: business, farming, fishing"
    )


class TextChunk(BaseModel):
    """Text content chunk (paragraph or footnote)."""

    model_config = ConfigDict(frozen=True)

    type: Literal["paragraph", "footnote"]
    text: str
    citation_id: str | None = None

    # NEW: Extraction pipeline provenance
    extraction_source: str | None = Field(
        default=None, description="Expert source: classic, llm, adjudicated"
    )
    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score from extraction pipeline",
    )
    source_anchor: str | None = Field(
        default=None, description="HTML anchor ID for debugging"
    )


class ListItem(BaseModel):
    """List item with optional nested sub-items."""

    model_config = ConfigDict(frozen=True)

    type: Literal["list_item"]
    text: str
    citation_id: str | None = None
    sub_items: list["ListItem"] = Field(default_factory=list)


class ListChunk(BaseModel):
    """List structure containing multiple items."""

    model_config = ConfigDict(frozen=True)

    type: Literal["list"]
    items: list[ListItem]


class TableChunk(BaseModel):
    """Table structure with 2D data."""

    model_config = ConfigDict(frozen=True)

    type: Literal["table"]
    data: list[list[str]]
    citation_id: str | None = None


# Union type for all content items
ContentItem = TextChunk | ListChunk | TableChunk


class Section(BaseModel):
    """Document section with title and content."""

    model_config = ConfigDict(frozen=True)

    section_title: str
    section_level: int
    content: list[ContentItem]


class ParsedDocument(BaseModel):
    """Root model for parsed CRA document."""

    model_config = ConfigDict(frozen=True)

    title: str
    document_id: str | None = None  # e.g., "S3-F2-C1"
    metadata: Metadata
    sections: list[Section]

    def to_flat_chunks(self, source_url: str = "") -> list[dict[str, object]]:
        """
        Convert hierarchical ParsedDocument to flat list of chunk dictionaries.

        Args:
            source_url: Source URL to include in each chunk

        Returns:
            List of chunk dictionaries compatible with TICKET 9C indexing format

        """
        chunks: list[dict[str, object]] = []

        for section in self.sections:
            for content_item in section.content:
                # Handle different content item types
                if isinstance(content_item, TextChunk):
                    chunks.append(
                        self._create_chunk_dict(
                            content=content_item.text,
                            citation_id=content_item.citation_id,
                            section_title=section.section_title,
                            source_url=source_url,
                            extraction_source=content_item.extraction_source,
                            extraction_confidence=content_item.extraction_confidence,
                            source_anchor=content_item.source_anchor,
                        )
                    )
                elif isinstance(content_item, ListChunk):
                    # Flatten list items recursively
                    for item in content_item.items:
                        chunks.extend(
                            self._flatten_list_item(
                                item=item,
                                section_title=section.section_title,
                                source_url=source_url,
                            )
                        )
                elif isinstance(content_item, TableChunk):
                    # Convert table to text representation
                    table_text = self._table_to_text(content_item.data)
                    chunks.append(
                        self._create_chunk_dict(
                            content=table_text,
                            citation_id=content_item.citation_id,
                            section_title=section.section_title,
                            source_url=source_url,
                        )
                    )

        return chunks

    def _create_chunk_dict(  # noqa: PLR0913
        self,
        content: str,
        citation_id: str | None,
        section_title: str,
        source_url: str,
        extraction_source: str | None = None,
        extraction_confidence: float | None = None,
        source_anchor: str | None = None,
    ) -> dict[str, object]:
        """Create a chunk dictionary with all metadata."""
        return {
            "content": content,
            "citation_id": citation_id,
            "source_url": source_url,
            "metadata": {
                # Document-level metadata
                "province": self.metadata.province,
                "business_type": self.metadata.business_type,
                "expense_type": self.metadata.expense_type,
                "income_type": self.metadata.income_type,
                "section_title": section_title,
                "document_id": self.document_id,
                # Chunk-level metadata
                "extraction_source": extraction_source,
                "extraction_confidence": extraction_confidence,
                "source_anchor": source_anchor,
            },
        }

    def _flatten_list_item(
        self, item: ListItem, section_title: str, source_url: str
    ) -> list[dict[str, object]]:
        """Recursively flatten a ListItem and its sub-items."""
        chunks: list[dict[str, object]] = []

        # Add the parent item
        chunks.append(
            self._create_chunk_dict(
                content=item.text,
                citation_id=item.citation_id,
                section_title=section_title,
                source_url=source_url,
            )
        )

        # Recursively add sub-items
        for sub_item in item.sub_items:
            chunks.extend(
                self._flatten_list_item(
                    item=sub_item, section_title=section_title, source_url=source_url
                )
            )

        return chunks

    def _table_to_text(self, data: list[list[str]]) -> str:
        """Convert table data to text representation."""
        if not data:
            return ""

        # Simple text representation: join rows with newlines, cells with " | "
        return "\n".join(" | ".join(row) for row in data)

    def to_database_chunks(
        self, source_files: list[SourceFile]
    ) -> list[DatabaseChunk]:
        """Convert hierarchical ParsedDocument to flat DatabaseChunk list.

        REPLACES: to_flat_chunks() returning dict[str, object]

        Args:
            source_files: List of SourceFile metadata for lookup

        Returns:
            List of DatabaseChunk objects ready for IndexBuilder

        Example:
            >>> from qe_tax_rag.search.models import SourceFile
            >>> source_files = [
            ...     SourceFile(
            ...         path="S3-F2-C1.html",
            ...         url="https://www.canada.ca/...",
            ...         hash="abc123"
            ...     )
            ... ]
            >>> doc = ParsedDocument.model_validate(data)
            >>> chunks = doc.to_database_chunks(source_files)
        """
        from qe_tax_rag.data.models import ChunkMetadata, DatabaseChunk

        # Find matching source file
        source_file = self._find_source_file(source_files)

        chunks: list[DatabaseChunk] = []

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
        import logging

        logger = logging.getLogger(__name__)

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
        from qe_tax_rag.data.models import ChunkMetadata, DatabaseChunk

        chunks: list[DatabaseChunk] = []

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
