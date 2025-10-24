"""Persistent, content-addressable cache for LLM API responses."""

import hashlib
import logging
from pathlib import Path

from diskcache import Cache

logger = logging.getLogger(__name__)


class LLMResponseCache:
    """
    A content-addressable cache for LLM responses.

    Uses diskcache to store raw text responses from an LLM, keyed by a hash
    of the inputs that generated the response (prompt, model name, and content).
    This avoids expensive, duplicate API calls during development and testing.
    """

    def __init__(self, cache_dir: str | Path):
        """
        Initializes the cache in the specified directory.

        Args:
            cache_dir: The directory where cache data will be stored.

        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(str(self.cache_dir))
        logger.info(f"LLM response cache initialized at: {self.cache_dir}")

    def _generate_key(self, prompt: str, model_name: str, content: str) -> str:
        """
        Generates a deterministic SHA256 hash from the inputs.

        Args:
            prompt: The LLM prompt text.
            model_name: The name of the LLM model.
            content: The source content being sent to the LLM.

        Returns:
            A SHA256 hex digest to use as a cache key.

        """
        hasher = hashlib.sha256()
        hasher.update(prompt.encode("utf-8"))
        hasher.update(model_name.encode("utf-8"))
        hasher.update(content.encode("utf-8"))
        return hasher.hexdigest()

    def get(self, prompt: str, model_name: str, content: str) -> str | None:
        """
        Retrieves a cached response if one exists.

        Args:
            prompt: The LLM prompt text.
            model_name: The name of the LLM model.
            content: The source content.

        Returns:
            The cached response text, or None if not found.

        """
        key = self._generate_key(prompt, model_name, content)
        cached_value = self._cache.get(key)
        if cached_value:
            logger.debug(f"Cache HIT for key: {key[:10]}...")
            return str(cached_value)
        logger.debug(f"Cache MISS for key: {key[:10]}...")
        return None

    def set(
        self, prompt: str, model_name: str, content: str, response_text: str
    ) -> None:
        """
        Stores an LLM response in the cache.

        Args:
            prompt: The LLM prompt text.
            model_name: The name of the LLM model.
            content: The source content.
            response_text: The raw text of the LLM response to cache.

        """
        key = self._generate_key(prompt, model_name, content)
        self._cache.set(key, response_text)
        logger.debug(f"Cache SET for key: {key[:10]}...")

    def close(self) -> None:
        """Closes the cache connection."""
        self._cache.close()
