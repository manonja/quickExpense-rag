"""Pydantic models for document preprocessing manifest."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class DownloadMetadata(BaseModel):
    """
    Metadata for a single downloaded document.

    Tracks provenance information for CRA documents downloaded manually
    by the maintainer during the preprocessing workflow.
    """

    filename: str = Field(..., description="File name (e.g., S3-F2-C1.html)")
    source_url: str = Field(..., description="Original CRA URL")
    downloaded_at: datetime = Field(..., description="Download timestamp (UTC)")
    sha256: str = Field(
        ..., pattern=r"^[a-f0-9]{64}$", description="SHA256 hash (64 hex chars)"
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Ensure filename has .html or .pdf extension."""
        if not v.endswith((".html", ".pdf")):
            msg = "Filename must end with .html or .pdf"
            raise ValueError(msg)
        return v


class PreprocessManifest(BaseModel):
    """
    Manifest of all downloaded documents.

    Aggregates metadata for all documents processed during a preprocessing run.
    Stored as `data/raw/manifest.json` for provenance tracking.
    """

    documents: list[DownloadMetadata] = Field(
        default_factory=list, description="List of document metadata"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Manifest creation timestamp (UTC)",
    )
