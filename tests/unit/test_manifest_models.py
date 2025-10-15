"""Unit tests for preprocessing manifest Pydantic models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from scripts.preprocessor.models import DownloadMetadata, PreprocessManifest


class TestDownloadMetadata:
    """Test DownloadMetadata Pydantic model."""

    def test_valid_html_metadata(self) -> None:
        """Valid HTML metadata validates successfully."""
        metadata = DownloadMetadata(
            filename="S3-F2-C1.html",
            source_url="https://www.canada.ca/example",
            downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
            sha256="a" * 64,  # Valid SHA256 hash (64 hex chars)
        )

        assert metadata.filename == "S3-F2-C1.html"
        assert metadata.source_url == "https://www.canada.ca/example"
        assert metadata.sha256 == "a" * 64

    def test_valid_pdf_metadata(self) -> None:
        """Valid PDF metadata validates successfully."""
        metadata = DownloadMetadata(
            filename="S4-F8-C3.pdf",
            source_url="https://www.canada.ca/example.pdf",
            downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
            sha256="b" * 64,
        )

        assert metadata.filename == "S4-F8-C3.pdf"
        assert metadata.sha256 == "b" * 64

    def test_invalid_filename_extension_raises(self) -> None:
        """Invalid filename extension raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DownloadMetadata(
                filename="document.txt",  # Invalid extension
                source_url="https://www.canada.ca/example",
                downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                sha256="a" * 64,
            )

        error = exc_info.value
        assert "filename" in str(error).lower()

    def test_invalid_sha256_format_raises(self) -> None:
        """Invalid SHA256 format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DownloadMetadata(
                filename="S3-F2-C1.html",
                source_url="https://www.canada.ca/example",
                downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                sha256="invalid_hash",  # Too short, invalid pattern
            )

        error = exc_info.value
        assert "sha256" in str(error).lower()

    def test_sha256_must_be_64_hex_chars(self) -> None:
        """SHA256 must be exactly 64 hexadecimal characters."""
        # Too short
        with pytest.raises(ValidationError):
            DownloadMetadata(
                filename="S3-F2-C1.html",
                source_url="https://www.canada.ca/example",
                downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                sha256="a" * 63,
            )

        # Too long
        with pytest.raises(ValidationError):
            DownloadMetadata(
                filename="S3-F2-C1.html",
                source_url="https://www.canada.ca/example",
                downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                sha256="a" * 65,
            )

        # Non-hex characters
        with pytest.raises(ValidationError):
            DownloadMetadata(
                filename="S3-F2-C1.html",
                source_url="https://www.canada.ca/example",
                downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                sha256="g" * 64,  # 'g' is not hexadecimal
            )


class TestPreprocessManifest:
    """Test PreprocessManifest Pydantic model."""

    def test_empty_manifest(self) -> None:
        """Empty manifest with no documents validates."""
        manifest = PreprocessManifest(documents=[])

        assert len(manifest.documents) == 0
        assert isinstance(manifest.created_at, datetime)

    def test_manifest_with_single_document(self) -> None:
        """Manifest with one document validates."""
        doc = DownloadMetadata(
            filename="S3-F2-C1.html",
            source_url="https://www.canada.ca/example",
            downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
            sha256="a" * 64,
        )
        manifest = PreprocessManifest(documents=[doc])

        assert len(manifest.documents) == 1
        assert manifest.documents[0].filename == "S3-F2-C1.html"

    def test_manifest_with_multiple_documents(self) -> None:
        """Manifest with multiple documents validates."""
        docs = [
            DownloadMetadata(
                filename="S3-F2-C1.html",
                source_url="https://www.canada.ca/example1",
                downloaded_at=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                sha256="a" * 64,
            ),
            DownloadMetadata(
                filename="S4-F8-C3.pdf",
                source_url="https://www.canada.ca/example2",
                downloaded_at=datetime(2024, 12, 15, 11, 0, 0, tzinfo=timezone.utc),
                sha256="b" * 64,
            ),
        ]
        manifest = PreprocessManifest(documents=docs)

        assert len(manifest.documents) == 2
        assert manifest.documents[0].filename == "S3-F2-C1.html"
        assert manifest.documents[1].filename == "S4-F8-C3.pdf"

    def test_created_at_defaults_to_now(self) -> None:
        """created_at defaults to current UTC time if not provided."""
        manifest = PreprocessManifest(documents=[])

        # Should be very close to now (within a few seconds)
        now = datetime.now(timezone.utc)
        time_diff = abs((now - manifest.created_at).total_seconds())
        assert time_diff < 5  # Within 5 seconds
