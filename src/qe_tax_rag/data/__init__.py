"""Data management module for database download, caching, and schema."""

# Lazy imports to avoid loading httpx dependency when just accessing bundled data
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qe_tax_rag.data.manager import DataManager
    from qe_tax_rag.data.schema import SCHEMA_VERSION

__all__ = ["SCHEMA_VERSION", "DataManager"]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """Lazy load module attributes to avoid importing httpx on package access."""
    if name == "DataManager":
        from qe_tax_rag.data.manager import DataManager
        return DataManager
    if name == "SCHEMA_VERSION":
        from qe_tax_rag.data.schema import SCHEMA_VERSION
        return SCHEMA_VERSION
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
