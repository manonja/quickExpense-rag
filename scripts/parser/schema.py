"""Pydantic models for Gemini Flash parser structured output."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Metadata(BaseModel):
    """Metadata extracted from CRA documents."""

    model_config = ConfigDict(frozen=True)

    province: list[str] = Field(default_factory=list)
    business_type: list[str] = Field(default_factory=list)
    expense_type: list[str] = Field(default_factory=list)


class TextChunk(BaseModel):
    """Text content chunk (paragraph or footnote)."""

    model_config = ConfigDict(frozen=True)

    type: Literal["paragraph", "footnote"]
    text: str
    citation_id: str | None = None


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

    def to_flat_chunks(self, source_url: str = "") -> list[dict]:
        """
        Convert hierarchical ParsedDocument to flat list of chunk dictionaries.

        Args:
            source_url: Source URL to include in each chunk

        Returns:
            List of chunk dictionaries compatible with TICKET 9C indexing format

        """
        chunks: list[dict] = []

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

    def _create_chunk_dict(
        self, content: str, citation_id: str | None, section_title: str, source_url: str
    ) -> dict:
        """Create a chunk dictionary with all metadata."""
        return {
            "content": content,
            "citation_id": citation_id,
            "source_url": source_url,
            "metadata": {
                "province": self.metadata.province,
                "business_type": self.metadata.business_type,
                "expense_type": self.metadata.expense_type,
                "section_title": section_title,
                "document_id": self.document_id,
            },
        }

    def _flatten_list_item(
        self, item: ListItem, section_title: str, source_url: str
    ) -> list[dict]:
        """Recursively flatten a ListItem and its sub-items."""
        chunks: list[dict] = []

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
