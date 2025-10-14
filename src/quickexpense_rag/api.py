"""
Public API for QuickExpense RAG library.

This module provides the main user-facing functions for initializing
the library and searching CRA expense rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from quickexpense_rag.data.manager import DataManager
from quickexpense_rag.embeddings.encoder import _EmbeddingService
from quickexpense_rag.exceptions import DatabaseNotInitializedError
from quickexpense_rag.search.enums import BusinessType, Province
from quickexpense_rag.search.hybrid import HybridSearchEngine
from quickexpense_rag.search.models import ExpenseQuery, SearchResult
from quickexpense_rag.settings import settings

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

    """
    if _search_engine is None:
        raise DatabaseNotInitializedError(
            "Database not initialized. Please call init() before using search()."
        )

    # Convert string parameters to enums if provided
    province_enum: Province | None = None
    if province is not None:
        try:
            province_enum = Province(province)
        except ValueError as e:
            valid_provinces = [p.value for p in Province]
            raise ValueError(
                f"Invalid province '{province}'. Valid options: {valid_provinces}"
            ) from e

    business_type_enum: BusinessType | None = None
    if business_type is not None:
        try:
            business_type_enum = BusinessType(business_type)
        except ValueError as e:
            valid_types = [bt.value for bt in BusinessType]
            raise ValueError(
                f"Invalid business_type '{business_type}'. Valid options: {valid_types}"
            ) from e

    # Construct ExpenseQuery (Pydantic will validate)
    query_obj = ExpenseQuery(
        query=query,
        province=province_enum,
        business_type=business_type_enum,
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
    from quickexpense_rag import __version__

    return {
        "library_version": __version__,
        "data_version": "not_initialized",
        "schema_version": "not_initialized",
    }
