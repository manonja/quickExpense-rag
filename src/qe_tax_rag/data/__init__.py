"""Data management module for database download, caching, and schema."""

from qe_tax_rag.data.manager import DataManager
from qe_tax_rag.data.schema import SCHEMA_VERSION

__all__ = ["SCHEMA_VERSION", "DataManager"]
