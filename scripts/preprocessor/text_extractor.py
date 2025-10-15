"""Text extraction from HTML and PDF files."""

import hashlib
import logging
import re
from pathlib import Path

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
                logger.warning("No semantic tags found in %s, using full document", html_path.name)

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
