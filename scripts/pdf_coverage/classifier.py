"""Page classifier for PDF coverage validation.

Classifies PDF pages as "already_covered", "blank", or "needs_extraction"
based on fuzzy matching against YAML corpus.
"""

from __future__ import annotations

import logging

from thefuzz import fuzz

from scripts.pdf_coverage.models import PageClassification

logger = logging.getLogger(__name__)


def classify_pages(
    pdf_pages: dict[int, str],
    yaml_corpus: str,
    threshold: int = 90,
    blank_threshold: int = 50,
) -> tuple[list[PageClassification], list[PageClassification]]:
    """Classify PDF pages based on similarity to YAML corpus.

    Args:
        pdf_pages: Dictionary mapping page numbers to normalized text
        yaml_corpus: Normalized YAML corpus text
        threshold: Similarity threshold for "already_covered" (0-100)
        blank_threshold: Character count threshold for "blank" pages

    Returns:
        Tuple of (keep_pages, discard_pages) lists

    Classification logic:
    - score > threshold → "already_covered" (discard)
    - text length < blank_threshold → "blank" (discard)
    - otherwise → "needs_extraction" (keep)

    Examples:
        >>> pdf_pages = {1: "chapter 1...", 2: "", 3: "new content..."}
        >>> corpus = "chapter 1... other content..."
        >>> keep, discard = classify_pages(pdf_pages, corpus)
        >>> len(keep)  # Page 3 needs extraction
        1
        >>> len(discard)  # Pages 1 (covered) and 2 (blank)
        2

    """
    keep_pages: list[PageClassification] = []
    discard_pages: list[PageClassification] = []

    total_pages = len(pdf_pages)
    logger.info(f"Classifying {total_pages} pages (threshold={threshold})...")

    for page_num, page_text in pdf_pages.items():
        # Calculate fuzzy match score using token_set_ratio
        # (order-independent, handles word reordering)
        score = fuzz.token_set_ratio(page_text, yaml_corpus)

        # Classify based on score and text length
        if score > threshold:
            # High similarity - already covered in YAML
            classification = PageClassification(
                page=page_num,
                reason="already_covered",
                score=score,
                confidence=score,
                justification=f"High similarity ({score}%) to existing YAML content",
            )
            discard_pages.append(classification)

        elif len(page_text) < blank_threshold:
            # Very short text - likely blank page
            classification = PageClassification(
                page=page_num,
                reason="blank",
                text_length=len(page_text),
                justification=f"Page contains minimal text ({len(page_text)} chars)",
            )
            discard_pages.append(classification)

        else:
            # Low similarity - needs extraction
            classification = PageClassification(
                page=page_num,
                reason="needs_extraction",
                score=score,
                justification=f"Low similarity ({score}%) - likely new content",
            )
            keep_pages.append(classification)

        # Log progress every 10 pages
        if page_num % 10 == 0:
            logger.info(f"Classified {page_num}/{total_pages} pages...")

    # Summary stats
    covered_count = len([p for p in discard_pages if p.reason == "already_covered"])
    blank_count = len([p for p in discard_pages if p.reason == "blank"])

    logger.info(f"Classification complete:")
    logger.info(f"  - Already covered: {covered_count} pages")
    logger.info(f"  - Blank: {blank_count} pages")
    logger.info(f"  - Needs extraction: {len(keep_pages)} pages")

    return keep_pages, discard_pages


def calculate_similarity_score(text1: str, text2: str) -> int:
    """Calculate fuzzy similarity score between two texts.

    Uses thefuzz token_set_ratio for order-independent matching.

    Args:
        text1: First text (normalized)
        text2: Second text (normalized)

    Returns:
        Similarity score (0-100)

    Examples:
        >>> calculate_similarity_score("line 9600 other income", "other income line 9600")
        100

        >>> calculate_similarity_score("hello world", "goodbye world")
        66

    """
    return fuzz.token_set_ratio(text1, text2)
