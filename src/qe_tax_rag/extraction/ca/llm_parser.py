"""LLM-based parser for CRA tax documents using Gemini API."""

import json
import logging
import random
import time
from pathlib import Path

import google.generativeai as genai
from bs4 import BeautifulSoup
from google.api_core import exceptions as google_exceptions

from qe_tax_rag.extraction.ca.cache import LLMResponseCache
from qe_tax_rag.extraction.ca.exceptions import ParserError
from qe_tax_rag.extraction.ca.rate_limiter import RateLimiter, RateLimitError
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
)
from qe_tax_rag.extraction.ca.settings import settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
You are an expert data extraction agent specializing in Canadian tax law documents. Your task is to extract all line-numbered expense rules from the provided HTML content of a CRA guide.

Follow these rules precisely:
1. Identify `<h3>` tags that match the pattern "Line XXXX –", where XXXX is a number.
2. SKIP any `<h3>` tags that do not match this pattern (e.g., "Prepaid expenses").
3. For each matched rule, extract the following fields:
   - `rule_number`: The integer from the "Line XXXX" pattern.
   - `title`: The text immediately following "–" in the `<h3>` tag.
   - `content`: All text from the subsequent `<p>`, `<ul>`, and `<ol>` tags, up to the next `<h3>` tag.
   - `applies_to`: A list of income types derived from `<img>` tags within the `<h3>`. Map the `alt` text as follows: "business icon" -> "business", "farm icon" -> "farming", "fish icon" -> "fishing". If no icons are present, the list should be empty.
   - `chapter`: The text content of the `<h1>` tag.
   - `section`: The text content of the nearest preceding `<h2>` tag. If none, this should be null.
   - `anchor_id`: The `id` attribute of the `<a>` tag inside the `<h3>`. If none, this should be null.
4. The `source_citation` should be the full text of the `<h3>` tag (e.g., "Line 8523 – Meals and entertainment").

Respond with a single JSON object containing a "rules" key, which holds a list of the extracted rule objects.
"""

# Module-level rate limiter cache (initialized per cache_dir)
_rate_limiters: dict[str, RateLimiter] = {}


def parse(html_path: str, cache_dir: str | Path | None = None) -> list[ExtractedRule]:
    """
    Parse HTML file using text-based LLM to extract line-numbered expense rules.

    Uses Gemini (Flash/Pro) to semantically understand HTML structure and extract
    rules matching "Line XXXX –" pattern. More resilient to HTML changes than
    rule-based parsing. Serves as the "LLM" expert in the Mixture-of-Experts pipeline.

    Extracts same fields as classic parser: line number, title, applies_to list,
    content, and context fields (chapter, section, source_file, anchor_id).

    Args:
        html_path: Absolute path to the local HTML file.
        cache_dir: Directory to cache LLM responses. If None, caching is disabled.

    Returns:
        List of ExtractedRule objects with expert_source set to LLM.
        Returns empty list if no line-numbered rules are found or if JSON
        parsing fails (allowing fallback to Classic Parser).

    Raises:
        ParserError: If file cannot be read or API call fails permanently.

    """
    # Initialize cache if a directory is provided
    cache = LLMResponseCache(cache_dir) if cache_dir else None

    # Initialize rate limiter for this cache_dir (singleton per directory)
    rate_limiter = None
    if cache_dir:
        cache_key = str(Path(cache_dir).resolve())
        if cache_key not in _rate_limiters:
            state_file = Path(cache_dir) / "rate_limiter_state.json"
            _rate_limiters[cache_key] = RateLimiter(
                rpm_limit=settings.gemini_rpm_limit,
                rpd_limit=settings.gemini_rpd_limit,
                state_file=state_file,
            )
        rate_limiter = _rate_limiters[cache_key]

    # Read HTML file
    try:
        html_content = Path(html_path).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        msg = f"HTML file not found: {html_path}"
        logger.error(msg)
        raise ParserError(msg) from e
    except OSError as e:
        msg = f"Failed to read HTML file: {html_path}"
        logger.error(msg, exc_info=True)
        raise ParserError(msg) from e

    # Extract <main> content using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    main_tag = soup.find("main")
    if not main_tag:
        msg = f"No <main> tag found in {html_path}"
        logger.warning(msg)
        main_content_text = soup.get_text()
    else:
        main_content_text = main_tag.get_text()

    # Check cache first
    response_text = None
    if cache:
        response_text = cache.get(
            prompt=EXTRACTION_PROMPT,
            model_name=settings.llm_model_name,
            content=main_content_text,
        )

    if response_text:
        logger.info(f"Cache HIT for {html_path}. Skipping API call.")
    else:
        logger.info(f"Cache MISS for {html_path}. Calling Gemini API.")

        # Respect rate limits before making an API call
        if rate_limiter:
            try:
                rate_limiter.wait_if_needed()
            except RateLimitError as e:
                raise ParserError(str(e)) from e

        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)  # type: ignore[attr-defined]
        model = genai.GenerativeModel(settings.llm_model_name)  # type: ignore[attr-defined]

        # Token safety check
        try:
            token_count = model.count_tokens(main_content_text)
            if token_count.total_tokens > 1_000_000:
                logger.warning(
                    f"Content of {html_path} exceeds token limit: "
                    f"{token_count.total_tokens} tokens (max: 1M). "
                    "Extraction may fail or be incomplete."
                )
        except Exception as e:
            # Don't fail on token counting errors - it's a safety check
            logger.debug(f"Token counting failed for {html_path}: {e}")

        # Call LLM with retry logic
        retries = 4  # Increased from 3 for better recovery
        backoff_factor = 5  # Increased from 2 for longer delays
        last_exception = None

        for attempt in range(retries):
            try:
                response = model.generate_content(
                    [EXTRACTION_PROMPT, main_content_text],
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json"
                    ),
                )
                response_text = response.text
                break  # Success - exit retry loop
            except (
                google_exceptions.ResourceExhausted,  # 429
                google_exceptions.ServiceUnavailable,  # 503
                google_exceptions.InternalServerError,  # 500
            ) as e:
                last_exception = e
                if attempt + 1 == retries:
                    msg = f"API call failed permanently for {html_path} after {retries} attempts"
                    logger.error(msg, exc_info=True)
                    raise ParserError(msg) from e

                # Add jitter to prevent thundering herd
                wait_time = (backoff_factor ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"API error for {html_path}, attempt {attempt + 1}/{retries}. "
                    f"Retrying in {wait_time:.2f} seconds... Error: {e}"
                )
                time.sleep(wait_time)
        else:
            # If we exhausted retries without success
            msg = f"API call failed for {html_path}"
            logger.error(msg, exc_info=True)
            raise ParserError(msg) from last_exception

        # Store the successful response in the cache
        if cache and response_text:
            cache.set(
                prompt=EXTRACTION_PROMPT,
                model_name=settings.llm_model_name,
                content=main_content_text,
                response_text=response_text,
            )

    # Parse JSON response
    try:
        data = json.loads(response_text or "{}")
        rules_data = data.get("rules", [])
    except json.JSONDecodeError as e:
        msg = f"Failed to parse JSON response for {html_path} (malformed/truncated JSON)"
        logger.warning(
            f"{msg}. Gemini may have truncated the response for large files. "
            "Returning empty list to allow fallback to Classic Parser results. "
            f"Error: {e}"
        )
        return []

    # Convert to ExtractedRule objects
    rules = []
    source_file = Path(html_path).name

    for rule_dict in rules_data:
        try:
            # Map applies_to strings to enum
            applies_to_str = rule_dict.get("applies_to", [])
            applies_to_enum = [ApplicabilityType(s) for s in applies_to_str]

            rule = ExtractedRule(
                rule_number=rule_dict["rule_number"],
                title=rule_dict["title"],
                content=rule_dict["content"],
                applies_to=applies_to_enum,
                source_citation=rule_dict["source_citation"],
                chapter=rule_dict["chapter"],
                section=rule_dict.get("section"),
                source_file=source_file,
                expert_source=ExpertSource.LLM,
                anchor_id=rule_dict.get("anchor_id"),
                confidence_score=0.8,  # LLM confidence default
            )
            rules.append(rule)
        except (KeyError, ValueError) as e:
            msg = f"Failed to validate rule data in {html_path}"
            logger.error(f"{msg}. Invalid data: {rule_dict}", exc_info=True)
            raise ParserError(msg) from e

    logger.info(f"LLM parser extracted {len(rules)} rules from {html_path}")
    return rules
