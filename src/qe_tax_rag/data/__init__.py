"""Data management module for database download, caching, and schema."""

from quickexpense_rag.data.manager import DataManager
from quickexpense_rag.data.schema import SCHEMA_VERSION

__all__ = ["SCHEMA_VERSION", "DataManager"]
