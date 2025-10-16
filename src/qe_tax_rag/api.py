"""
Public API for QE Tax RAG library.

This module provides the main user-facing functions for initializing
the library and searching CRA expense rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from qe_tax_rag.data.manager import DataManager
from qe_tax_rag.embeddings.encoder import _EmbeddingService
from qe_tax_rag.exceptions import DatabaseNotInitializedError
from qe_tax_rag.search.enums import BusinessType, Province
from qe_tax_rag.search.hybrid import HybridSearchEngine
from qe_tax_rag.search.models import ExpenseQuery, SearchResult
from qe_tax_rag.settings import settings

if TYPE_CHECKING:
    pass

# Module-level state for search engine (initialized once via init())
_search_engine: HybridSearchEngine | None = None
_db_path: Path | None = None


def init(force_update: bool = False) -> None:  # noqa: ARG001
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
    global _search_engine, _db_path

    # Step 1: Initialize DataManager and get database path
    data_manager = DataManager(settings=settings)
    db_path = data_manager.get_database_path()

    # Step 2: Initialize embedding service (singleton)
    encoder = _EmbeddingService()

    # Step 3: Create HybridSearchEngine with database and encoder
    search_engine = HybridSearchEngine(db_path=db_path, encoder=encoder)

    # Step 4: Store in module state for reuse
    _search_engine = search_engine
    _db_path = db_path


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
        expense_types: Filter by expense categories (matches rules with
            ANY of these types).
        top_k: Number of results to return (1-50).

    Returns:
        List of SearchResult objects with citations and disclaimers.

    Raises:
        DatabaseNotInitializedError: If init() not called.
        ValidationError: If invalid parameters provided.

    Security:
        String parameters are validated against enum values before query
        construction. All database queries use parameterized statements.

    """
    if _search_engine is None:
        raise DatabaseNotInitializedError(
            "Database not initialized. Please call init() before using search()."
        )

    # Construct ExpenseQuery (Pydantic will validate all parameters including enums)
    query_obj = ExpenseQuery(
        query=query,
        province=Province(province) if province else None,
        business_type=BusinessType(business_type) if business_type else None,
        expense_types=expense_types,
        top_k=top_k,
    )

    # Execute search
    return _search_engine.search(query_obj)


def get_version() -> dict[str, str]:
    """
    Get library and database versions.

    Returns:
        Dictionary with library_version, data_version, schema_version.

    """
    from qe_tax_rag import __version__

    return {
        "library_version": __version__,
        "data_version": "not_initialized",
        "schema_version": "not_initialized",
    }
