"""Pydantic models for PDF coverage validation reports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PageClassification(BaseModel):
    """Classification result for a single PDF page.

    Attributes:
        page: Page number (1-indexed)
        reason: Classification reason
        score: Fuzzy match score (0-100), if applicable
        confidence: Confidence score for "already_covered" pages
        text_length: Character count for "blank" pages
        justification: Human-readable explanation

    """

    page: int = Field(description="Page number (1-indexed)")
    reason: Literal["already_covered", "blank", "needs_extraction"] = Field(
        description="Classification reason"
    )
    score: int | None = Field(
        None, ge=0, le=100, description="Fuzzy match score (0-100)"
    )
    confidence: int | None = Field(
        None, ge=0, le=100, description="Confidence score for already_covered pages"
    )
    text_length: int | None = Field(
        None, ge=0, description="Character count for blank pages"
    )
    justification: str = Field(description="Human-readable explanation")


class CoverageReport(BaseModel):
    """Complete coverage validation report.

    Attributes:
        pdf_source: Path to PDF file
        yaml_sources: List of YAML files used to build corpus
        total_pdf_pages: Total pages in PDF
        keep_pages: Pages requiring extraction
        discard_pages: Pages to skip (already covered or blank)
        threshold: Similarity threshold used (0-100)

    """

    pdf_source: str = Field(description="Path to PDF file")
    yaml_sources: list[str] = Field(description="YAML files used to build corpus")
    total_pdf_pages: int = Field(ge=0, description="Total pages in PDF")
    keep_pages: list[PageClassification] = Field(
        description="Pages requiring extraction"
    )
    discard_pages: list[PageClassification] = Field(
        description="Pages to skip (already covered or blank)"
    )
    threshold: int = Field(ge=0, le=100, description="Similarity threshold (0-100)")

    @property
    def coverage_percentage(self) -> float:
        """Calculate percentage of pages already covered."""
        if self.total_pdf_pages == 0:
            return 0.0
        covered_pages = len(
            [p for p in self.discard_pages if p.reason == "already_covered"]
        )
        return (covered_pages / self.total_pdf_pages) * 100

    @property
    def summary_stats(self) -> dict[str, int]:
        """Get summary statistics for the report."""
        return {
            "total_pages": self.total_pdf_pages,
            "covered_pages": len(
                [p for p in self.discard_pages if p.reason == "already_covered"]
            ),
            "blank_pages": len(
                [p for p in self.discard_pages if p.reason == "blank"]
            ),
            "needs_extraction": len(self.keep_pages),
        }
