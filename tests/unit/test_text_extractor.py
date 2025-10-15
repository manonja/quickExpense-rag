"""Unit tests for text extraction from HTML and PDF files."""

import hashlib
from pathlib import Path

import pytest

from scripts.preprocessor.text_extractor import TextExtractor


class TestSHA256Utility:
    """Test SHA256 hash computation."""

    def test_compute_sha256_for_text_file(self, tmp_path: Path) -> None:
        """SHA256 computed correctly for text file."""
        # Create test file with known content
        test_file = tmp_path / "test.txt"
        content = "Hello, world!"
        test_file.write_text(content, encoding="utf-8")

        # Compute expected hash
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Test
        extractor = TextExtractor()
        actual_hash = extractor.compute_sha256(test_file)

        assert actual_hash == expected_hash
        assert len(actual_hash) == 64  # SHA256 is 64 hex chars
        assert all(c in "0123456789abcdef" for c in actual_hash)

    def test_compute_sha256_for_binary_file(self, tmp_path: Path) -> None:
        """SHA256 computed correctly for binary file."""
        test_file = tmp_path / "test.bin"
        content = b"\x00\x01\x02\xFF"
        test_file.write_bytes(content)

        expected_hash = hashlib.sha256(content).hexdigest()

        extractor = TextExtractor()
        actual_hash = extractor.compute_sha256(test_file)

        assert actual_hash == expected_hash

    def test_compute_sha256_for_empty_file(self, tmp_path: Path) -> None:
        """SHA256 computed correctly for empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.touch()

        expected_hash = hashlib.sha256(b"").hexdigest()

        extractor = TextExtractor()
        actual_hash = extractor.compute_sha256(test_file)

        assert actual_hash == expected_hash

    def test_compute_sha256_missing_file_raises(self, tmp_path: Path) -> None:
        """SHA256 computation raises FileNotFoundError for missing file."""
        missing_file = tmp_path / "missing.txt"

        extractor = TextExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.compute_sha256(missing_file)


class TestNormalizeWhitespace:
    """Test whitespace normalization."""

    def test_normalize_multiple_newlines(self) -> None:
        """Multiple consecutive newlines reduced to max 2."""
        text = "Line 1\n\n\n\nLine 2"
        expected = "Line 1\n\nLine 2"

        extractor = TextExtractor()
        result = extractor._normalize_whitespace(text)

        assert result == expected

    def test_normalize_preserves_single_newline(self) -> None:
        """Single newlines are preserved."""
        text = "Line 1\nLine 2\nLine 3"

        extractor = TextExtractor()
        result = extractor._normalize_whitespace(text)

        assert result == text  # Unchanged

    def test_normalize_preserves_double_newline(self) -> None:
        """Double newlines (paragraph breaks) are preserved."""
        text = "Paragraph 1\n\nParagraph 2"

        extractor = TextExtractor()
        result = extractor._normalize_whitespace(text)

        assert result == text  # Unchanged

    def test_normalize_strips_leading_trailing_whitespace(self) -> None:
        """Leading and trailing whitespace is stripped."""
        text = "  \n\n  Content here  \n\n  "
        expected = "Content here"

        extractor = TextExtractor()
        result = extractor._normalize_whitespace(text)

        assert result == expected
