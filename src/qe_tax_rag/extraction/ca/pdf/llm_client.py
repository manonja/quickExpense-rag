"""Simple Gemini LLM client for PDF content structuring.

This module provides a minimal wrapper around Google's Generative AI API
for making structured content extraction calls.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def call_gemini(prompt: str, model: str = "gemini-1.5-flash") -> str:
    """Call Gemini API with a prompt and return the response text.

    Args:
        prompt: The prompt to send to Gemini
        model: Gemini model to use (default: gemini-1.5-flash for speed/cost)

    Returns:
        Response text from Gemini

    Raises:
        ValueError: If GEMINI_API_KEY not set in environment
        RuntimeError: If API call fails

    Example:
        >>> response = call_gemini("Extract content: ...")
        >>> content = json.loads(response)
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = (
            "GEMINI_API_KEY environment variable not set. "
            "Set it in .env.local or export it."
        )
        raise ValueError(msg)

    try:
        import google.generativeai as genai
    except ImportError as e:
        msg = "google-generativeai not installed. Run: uv add google-generativeai"
        raise ImportError(msg) from e

    # Configure API
    genai.configure(api_key=api_key)

    # Create model
    model_instance = genai.GenerativeModel(model)

    # Generate content
    logger.debug(f"Calling Gemini {model} with prompt length: {len(prompt)}")
    try:
        response = model_instance.generate_content(prompt)
        result = response.text
        logger.debug(f"Received response length: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise RuntimeError(f"Gemini API call failed: {e}") from e
