"""
Public API for QuickExpense RAG library.

This module provides the main user-facing functions for initializing
the library and searching CRA expense rules.
"""

from pathlib import Path

from quickexpense_rag.exceptions import DatabaseNotInitializedError
from quickexpense_rag.search.models import SearchResult

# Module-level state for search engine (initialized once via init())
_search_engine: "HybridSearchEngine | None" = None
_db_path: Path | None = None


def init(force_update: bool = False) -> None:
    """
    Initialize library and download database if needed.

    ⚠️ LEGAL DISCLAIMER:
    This library provides informational content only and does not
    constitute professional tax advice. Always consult a qualified
    tax professional or accountant. CRA rules are complex and change
    frequently. The data may be incomplete or outdated.

    Args:
        force_update: Force re-download even if cached DB exists.

    Raises:
        NetworkError: If download fails and no cached DB available.
        DataVersionMismatchError: If DB version incompatible.

    """
    raise NotImplementedError("init() will be implemented in TICKET 6")


def search(
    query: str,
    province: str | None = None,
    business_type: str | None = None,
    expense_types: list[str] | None = None,
    top_k: int = 5,
) -> list[SearchResult]:
    """
    Search CRA expense rules.

    ⚠️ NOT TAX ADVICE - Informational purposes only.

    Args:
        query: Natural language expense description.
        province: Filter by province (e.g., "BC", "ON").
        business_type: Filter by business type.
        expense_types: Filter by expense categories (matches rules with ANY of these types).
        top_k: Number of results to return (1-50).

    Returns:
        List of SearchResult objects with citations and disclaimers.

    Raises:
        DatabaseNotInitializedError: If init() not called.
        ValidationError: If invalid parameters provided.

    """
    if _search_engine is None:
        raise DatabaseNotInitializedError(
            "Database not initialized. Please call init() before using search()."
        )

    # TODO: Construct ExpenseQuery and call search engine
    raise NotImplementedError("Search implementation pending")


def get_version() -> dict[str, str]:
    """
    Get library and database versions.

    Returns:
        Dictionary with library_version, data_version, schema_version.

    """
    from quickexpense_rag import __version__

    return {
        "library_version": __version__,
        "data_version": "not_initialized",
        "schema_version": "not_initialized",
    }
