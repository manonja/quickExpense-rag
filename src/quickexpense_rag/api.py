"""
Public API for QuickExpense RAG library.

This module provides the main user-facing functions for initializing
the library and searching CRA expense rules.
"""

from quickexpense_rag.exceptions import DatabaseNotInitializedError
from quickexpense_rag.search.models import SearchResult


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
    _query: str,
    _province: str | None = None,
    _business_type: str | None = None,
    _expense_type: str | None = None,
    _top_k: int = 5,
) -> list[SearchResult]:
    """
    Search CRA expense rules.

    ⚠️ NOT TAX ADVICE - Informational purposes only.

    Args:
        query: Natural language expense description.
        province: Filter by province (e.g., "BC", "ON").
        business_type: Filter by business type.
        expense_type: Filter by expense category.
        top_k: Number of results to return (1-50).

    Returns:
        List of SearchResult objects with citations and disclaimers.

    Raises:
        DatabaseNotInitializedError: If init() not called.
        ValidationError: If invalid parameters provided.

    """
    raise DatabaseNotInitializedError(
        "Database not initialized. Call init() first. "
        "This will be implemented in TICKET 8."
    )


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
