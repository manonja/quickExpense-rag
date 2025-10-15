"""Text extraction from HTML and PDF files."""

import hashlib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class TextExtractor:
    """
    Extract clean text from HTML and PDF documents.

    Provides methods to convert CRA HTML and PDF files into clean text
    suitable for downstream LLM parsing (Gemini Flash in TICKET 9B).
    """

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
