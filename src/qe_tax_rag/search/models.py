"""Pydantic models for search queries and results."""

from __future__ import annotations

from datetime import datetime
from typing import Tuple

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    computed_field,
    field_validator,
)

from quickexpense_rag.search.enums import BusinessType, Province

# Regex for CRA citation IDs, e.g., "S3-F2-C1-p1.25"
CITATION_ID_PATTERN = r"S\d+-F\d+-C\d+-p\d+\.?\d*"

# Regex for YYYY.MM version format
DATA_VERSION_PATTERN = r"^\d{4}\.\d{2}$"


class ExpenseQuery(BaseModel):
    """Represents a user's search query and filters."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(..., min_length=3, description="Natural language search query.")
    province: Province | None = Field(
        None, description="Filter by province or territory."
    )
    business_type: BusinessType | None = Field(
        None, description="Filter by business type."
    )
    expense_types: list[str] | None = Field(
        None,
        description="Filter by expense types (matches rules with ANY of these types).",
    )
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return.")


class SearchResult(BaseModel):
    """A single search result item with critical legal disclaimers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content: str = Field(
        ..., description="The relevant text content from the CRA document."
    )
    citation_id: str = Field(
        ...,
        pattern=CITATION_ID_PATTERN,
        description="The unique CRA citation identifier for the content.",
    )
    source_url: HttpUrl = Field(..., description="The URL of the source CRA document.")
    score: float = Field(..., ge=0.0, le=1.0, description="The search relevance score.")
    province: Province | None
    business_type: BusinessType | None
    expense_types: list[str]
    retrieved_at: datetime = Field(
        ..., description="The timestamp when the source document was retrieved."
    )

    @field_validator("source_url")
    @classmethod
    def _validate_source_url(cls, v: HttpUrl) -> HttpUrl:
        """Ensure the source URL is a secure link to the official canada.ca domain."""
        if v.scheme != "https":
            raise ValueError("source_url must use HTTPS.")
        host = v.host
        if host is None:
            raise ValueError("source_url must have a valid host.")
        if host != "www.canada.ca" and not host.endswith(".canada.ca"):
            raise ValueError("source_url must be a 'canada.ca' domain.")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def disclaimer(self) -> str:
        """A non-suppressible legal disclaimer attached to every result."""
        return (
            "⚠️ INFORMATIONAL ONLY - NOT TAX ADVICE\n"
            "This information is for educational purposes only and does not "
            "constitute tax advice. CRA rules are complex and change frequently. "
            "Always consult a qualified tax professional or accountant. "
            "The data may be incomplete, outdated, or incorrectly interpreted."
        )


class SourceFile(BaseModel):
    """Metadata for a single source file used in the index build."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    url: HttpUrl
    hash: str


class IndexManifest(BaseModel):
    """Metadata for a specific build of the search index database."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(
        ...,
        pattern=DATA_VERSION_PATTERN,
        description="Data version in YYYY.MM format.",
    )
    schema_version: str = Field(..., description="The database schema version.")
    source_files: Tuple[SourceFile, ...] = Field(
        ..., description="An immutable tuple of source files used in the index build."
    )
    embedding_model: str = Field(
        ..., description="Name of the sentence-transformer model used."
    )
    chunk_count: int = Field(
        ..., gt=0, description="Total number of content chunks in the index."
    )
    created_at: datetime = Field(..., description="Timestamp of the index build.")
    sha256: str = Field(
        ..., description="SHA256 hash of the final database file for integrity checks."
    )
