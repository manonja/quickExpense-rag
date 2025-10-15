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
