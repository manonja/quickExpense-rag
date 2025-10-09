"""Pydantic models for search queries and results."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from quickexpense_rag.search.enums import BusinessType, ExpenseType, Province


class ExpenseQuery(BaseModel):
    """
    Query model for searching expense rules.

    All models are immutable (frozen) and strictly validated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(..., min_length=3, description="Search query")
    province: Province | None = None
    business_type: BusinessType | None = None
    expense_type: ExpenseType | None = None
    top_k: int = Field(5, ge=1, le=50)


class SearchResult(BaseModel):
    """
    Individual search result with CRA citation and metadata.

    Includes automatic legal disclaimer via computed field.
    """

    model_config = ConfigDict(frozen=True)

    content: str
    citation_id: str
    source_url: str
    score: float = Field(..., ge=0.0, le=1.0)
    province: Province | None
    business_type: BusinessType | None
    expense_type: ExpenseType | None
    retrieved_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def disclaimer(self) -> str:
        """
        Legal disclaimer for all search results.

        Returns:
            Disclaimer text warning this is not tax advice.

        """
        return (
            "⚠️ INFORMATIONAL ONLY - NOT TAX ADVICE\n"
            "This information is for educational purposes only and does not "
            "constitute tax advice. CRA rules are complex and change frequently. "
            "Always consult a qualified tax professional or accountant. "
            "The data may be incomplete, outdated, or incorrectly interpreted."
        )


class IndexManifest(BaseModel):
    """
    Metadata manifest for database versioning and integrity.

    Used during indexing pipeline to track data provenance.
    """

    version: str  # YYYY.MM format
    schema_version: str
    source_files: list[dict[str, str]]  # [{path, hash}]
    embedding_model: str
    chunk_count: int
    created_at: datetime
    sha256: str  # Hash of the database file
