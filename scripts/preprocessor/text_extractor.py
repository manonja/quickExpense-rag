"""Text extraction from HTML and PDF files."""

import hashlib
import logging
import re
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup
from src.quickexpense_rag.exceptions import ParsingError

logger = logging.getLogger(__name__)


class TextExtractor:
    """
    Extract clean text from HTML and PDF documents.

    Provides methods to convert CRA HTML and PDF files into clean text
    suitable for downstream LLM parsing (Gemini Flash in TICKET 9B).
    """

    def extract_from_html(self, html_path: Path) -> str:
        """
        Extract clean text from HTML using BeautifulSoup.

        Strategy (80/20 approach):
        1. Try to find main content area using CSS selectors (<main>, <article>)
        2. Fallback to <body> if semantic tags not found
        3. Remove script/style tags
        4. Extract text preserving structure

        Args:
            html_path: Path to HTML file

        Returns:
            Clean text with preserved structure

        Raises:
            FileNotFoundError: If file doesn't exist
            ParsingError: If HTML is unparseable

        """
        if not html_path.exists():
            msg = f"File not found: {html_path}"
            raise FileNotFoundError(msg)

        try:
            # Read HTML file
            html_content = html_path.read_text(encoding="utf-8")

            # Parse with BeautifulSoup (lxml parser for speed)
            soup = BeautifulSoup(html_content, "lxml")

            # Remove script and style tags
            for tag in soup(["script", "style"]):
                tag.decompose()

            # Try to find main content area (80/20 heuristics)
            content_element = None

            # Priority 1: <main> tag (most semantic)
            if soup.main:
                content_element = soup.main
                logger.debug("Found <main> tag in %s", html_path.name)

            # Priority 2: <article> tag
            elif soup.article:
                content_element = soup.article
                logger.debug("Found <article> tag in %s", html_path.name)

            # Fallback: Use <body> tag
            elif soup.body:
                content_element = soup.body
                logger.debug("Fallback to <body> tag in %s", html_path.name)

            else:
                # Last resort: use entire document
                content_element = soup
                logger.warning(
                    "No semantic tags found in %s, using full document", html_path.name
                )

            # Extract text with preserved structure
            # separator='\n' preserves line breaks, strip=True removes extra whitespace
            text = content_element.get_text(separator="\n", strip=True)

            # Normalize whitespace
            text = self._normalize_whitespace(text)

            return text

        except Exception as e:
            msg = f"Failed to parse HTML file {html_path}: {e}"
            logger.error(msg)
            raise ParsingError(msg) from e

    def extract_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract clean text from PDF using pdfplumber.

        Strategy (80/20 approach):
        1. Iterate pages in order
        2. Use pdfplumber's default layout extraction
        3. Join pages with newlines
        4. Accept minor ordering issues in multi-column layouts (LLM can handle)

        Args:
            pdf_path: Path to PDF file

        Returns:
            Clean text preserving reading order

        Raises:
            FileNotFoundError: If file doesn't exist
            ParsingError: If PDF is unparseable

        """
        if not pdf_path.exists():
            msg = f"File not found: {pdf_path}"
            raise FileNotFoundError(msg)

        try:
            pages_text = []

            # Open PDF and extract text from each page
            with pdfplumber.open(pdf_path) as pdf:
                logger.debug(
                    "Extracting text from %d pages in %s", len(pdf.pages), pdf_path.name
                )

                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text using pdfplumber's default layout
                    page_text = page.extract_text()

                    if page_text:
                        pages_text.append(page_text)
                        logger.debug(
                            "Extracted %d chars from page %d", len(page_text), page_num
                        )
                    else:
                        logger.warning(
                            "No text extracted from page %d in %s",
                            page_num,
                            pdf_path.name,
                        )

            # Join pages with double newlines (paragraph break)
            text = "\n\n".join(pages_text)

            # Normalize whitespace
            text = self._normalize_whitespace(text)

            if not text:
                logger.warning("No text extracted from PDF: %s", pdf_path)

            return text

        except Exception as e:
            msg = f"Failed to parse PDF file {pdf_path}: {e}"
            logger.error(msg)
            raise ParsingError(msg) from e

    def preprocess_file(
        self,
        input_path: Path,
        output_path: Path,
        *,
        compute_hash: bool = True,
    ) -> str | None:
        """
        Auto-detect format and convert to clean text.

        Strategy:
        1. Detect file format by extension (.html, .pdf)
        2. Route to appropriate extractor
        3. Write clean text to output file
        4. Optionally compute SHA256 hash of input file

        Args:
            input_path: Path to HTML or PDF file
            output_path: Path for output .txt file
            compute_hash: Whether to compute SHA256 hash of input file

        Returns:
            SHA256 hash if compute_hash=True, else None

        Raises:
            ValueError: If file format not supported
            FileNotFoundError: If input file doesn't exist
            ParsingError: If extraction fails

        """
        # Check input file exists
        if not input_path.exists():
            msg = f"Input file not found: {input_path}"
            raise FileNotFoundError(msg)

        # Detect file format by extension
        suffix = input_path.suffix.lower()

        # Route to appropriate extractor
        if suffix == ".html":
            logger.debug("Processing HTML file: %s", input_path.name)
            text = self.extract_from_html(input_path)
        elif suffix == ".pdf":
            logger.debug("Processing PDF file: %s", input_path.name)
            text = self.extract_from_pdf(input_path)
        else:
            msg = f"Unsupported file format: {suffix} (expected .html or .pdf)"
            raise ValueError(msg)

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write clean text to output file
        output_path.write_text(text, encoding="utf-8")
        logger.info(
            "Preprocessed %s → %s (%d chars)",
            input_path.name,
            output_path.name,
            len(text),
        )

        # Optionally compute SHA256 hash of input file
        if compute_hash:
            return self.compute_sha256(input_path)

        return None

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """
        Compute SHA256 hash of file.

        Args:
            file_path: Path to file to hash

        Returns:
            SHA256 hash as 64-character hex string

        Raises:
            FileNotFoundError: If file doesn't exist

        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            # Read in 64KB chunks for memory efficiency
            for chunk in iter(lambda: f.read(65536), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """
        Normalize whitespace in text.

        Strategy:
        - Strip leading/trailing whitespace
        - Collapse 3+ consecutive newlines to exactly 2 (preserve paragraph breaks)
        - Preserve single and double newlines

        Args:
            text: Input text

        Returns:
            Normalized text

        """
        # Strip leading/trailing whitespace
        text = text.strip()

        # Collapse 3+ consecutive newlines to 2
        # Pattern: 3 or more newlines → exactly 2 newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text
