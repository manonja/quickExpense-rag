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


class TestHTMLExtraction:
    """Test HTML text extraction."""

    def test_extract_from_html_with_main_tag(self, tmp_path: Path) -> None:
        """HTML with <main> tag extracts content correctly."""
        html_file = tmp_path / "test.html"
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <header>Header content (should be excluded)</header>
                <main>
                    <h1>Main heading</h1>
                    <p>First paragraph.</p>
                    <p>Second paragraph.</p>
                </main>
                <footer>Footer content (should be excluded)</footer>
            </body>
        </html>
        """
        html_file.write_text(html_content, encoding="utf-8")

        extractor = TextExtractor()
        result = extractor.extract_from_html(html_file)

        # Should extract only <main> content
        assert "Main heading" in result
        assert "First paragraph." in result
        assert "Second paragraph." in result
        assert "Header content" not in result
        assert "Footer content" not in result

    def test_extract_from_html_with_article_tag(self, tmp_path: Path) -> None:
        """HTML with <article> tag extracts content correctly."""
        html_file = tmp_path / "test.html"
        html_content = """
        <html>
            <body>
                <nav>Navigation (should be excluded)</nav>
                <article>
                    <h2>Article title</h2>
                    <p>Article content here.</p>
                </article>
            </body>
        </html>
        """
        html_file.write_text(html_content, encoding="utf-8")

        extractor = TextExtractor()
        result = extractor.extract_from_html(html_file)

        assert "Article title" in result
        assert "Article content here." in result
        assert "Navigation" not in result

    def test_extract_from_html_removes_scripts(self, tmp_path: Path) -> None:
        """Script and style tags are removed from extraction."""
        html_file = tmp_path / "test.html"
        html_content = """
        <html>
            <head>
                <style>body { color: red; }</style>
            </head>
            <body>
                <main>
                    <p>Visible content.</p>
                    <script>alert('hidden');</script>
                </main>
            </body>
        </html>
        """
        html_file.write_text(html_content, encoding="utf-8")

        extractor = TextExtractor()
        result = extractor.extract_from_html(html_file)

        assert "Visible content." in result
        assert "alert" not in result
        assert "color: red" not in result

    def test_extract_from_html_preserves_structure(self, tmp_path: Path) -> None:
        """Paragraph breaks are preserved in extracted text."""
        html_file = tmp_path / "test.html"
        html_content = """
        <html>
            <body>
                <main>
                    <p>First paragraph.</p>
                    <p>Second paragraph.</p>
                    <p>Third paragraph.</p>
                </main>
            </body>
        </html>
        """
        html_file.write_text(html_content, encoding="utf-8")

        extractor = TextExtractor()
        result = extractor.extract_from_html(html_file)

        # Should have newlines between paragraphs
        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "Third paragraph" in result
        # Count newlines (should be at least 2 between paragraphs)
        assert result.count("\n") >= 2

    def test_extract_from_html_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing HTML file raises FileNotFoundError."""
        missing_file = tmp_path / "missing.html"

        extractor = TextExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract_from_html(missing_file)

    def test_extract_from_html_fallback_to_body(self, tmp_path: Path) -> None:
        """HTML without <main>/<article> falls back to <body> extraction."""
        html_file = tmp_path / "test.html"
        html_content = """
        <html>
            <body>
                <div id="content">
                    <h1>Title</h1>
                    <p>Content without semantic tags.</p>
                </div>
            </body>
        </html>
        """
        html_file.write_text(html_content, encoding="utf-8")

        extractor = TextExtractor()
        result = extractor.extract_from_html(html_file)

        assert "Title" in result
        assert "Content without semantic tags." in result
