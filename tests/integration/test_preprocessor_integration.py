"""Integration tests for preprocessing with real CRA document samples."""

from pathlib import Path

import pytest

from scripts.preprocessor.text_extractor import TextExtractor


class TestPreprocessorIntegration:
    """Integration test with real CRA document samples."""

    def test_preprocess_real_html_document(self, tmp_path: Path) -> None:
        """Preprocess sample CRA HTML folio."""
        # Load sample CRA HTML
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "preprocessor"
        sample_html = fixtures_dir / "sample_cra_folio.html"

        assert sample_html.exists(), f"Fixture not found: {sample_html}"

        # Preprocess
        output_file = tmp_path / "output.txt"
        extractor = TextExtractor()
        sha256 = extractor.preprocess_file(sample_html, output_file, compute_hash=True)

        # Verify output created
        assert output_file.exists()

        # Read and verify content
        text = output_file.read_text(encoding="utf-8")

        # Should contain main content
        assert "Income Tax Folio S3-F2-C1" in text
        assert "Capital Cost of Depreciable Property" in text
        assert "Introduction" in text
        assert "Determining Capital Cost" in text
        assert "Passenger Vehicles" in text

        # Should preserve list structure
        assert "Purchase price" in text
        assert "Legal fees" in text
        assert "Installation costs" in text

        # Should preserve monetary amounts
        assert "$30,000" in text

        # Should NOT contain header/footer content
        assert "Home" not in text  # Navigation
        assert "All Folios" not in text
        assert "Canada Revenue Agency" not in text  # Footer

        # Should NOT contain script/style content
        assert "console.log" not in text
        assert "font-family" not in text
        assert "background" not in text

        # Verify SHA256 computed
        assert sha256 is not None
        assert len(sha256) == 64

        # Verify text is reasonably clean (no excessive whitespace)
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in text

    def test_preprocess_real_pdf_document(self, tmp_path: Path) -> None:
        """Preprocess sample CRA PDF folio."""
        # Skip - no real PDF fixture available
        # Real PDF testing would require downloading actual CRA PDF
        # For now, we verify HTML extraction is sufficient
        pytest.skip("PDF integration test requires actual CRA PDF - manual testing")

    def test_end_to_end_html_preprocessing(self, tmp_path: Path) -> None:
        """End-to-end test: HTML input → clean text output."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "preprocessor"
        sample_html = fixtures_dir / "sample_cra_folio.html"

        output_file = tmp_path / "preprocessed.txt"

        # Run preprocessing
        extractor = TextExtractor()
        extractor.preprocess_file(sample_html, output_file)

        # Verify output is parseable and structured
        text = output_file.read_text(encoding="utf-8")

        # Should have multiple paragraphs/sections
        # Note: BeautifulSoup's get_text() with separator='\n' creates single newlines
        # Our normalization preserves at most 2 consecutive newlines
        lines = text.split("\n")
        assert len(lines) > 10  # Multiple lines of content

        # Should have headings
        assert "Introduction" in text
        assert "Determining Capital Cost" in text

        # Should have readable content
        assert len(text) > 500  # Substantial text content
