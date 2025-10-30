"""
Public API for QE Tax RAG library.

This module provides the main user-facing functions for initializing
the library and searching CRA expense rules.
"""

from __future__ import annotations

import os
import sqlite3
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from qe_tax_rag import __version__
from qe_tax_rag.embeddings.encoder import _EmbeddingService
from qe_tax_rag.exceptions import DatabaseNotInitializedError
from qe_tax_rag.search.enums import BusinessType, Province
from qe_tax_rag.search.hybrid import HybridSearchEngine
from qe_tax_rag.search.models import ExpenseQuery, SearchResult

if TYPE_CHECKING:
    pass

# Module-level state for search engine (initialized once via init())
_search_engine: HybridSearchEngine | None = None
_db_path: Path | None = None


def init(db_path: str | None = None) -> None:
    """
    Initialize library with bundled database.

    ⚠️ LEGAL DISCLAIMER:
    This library provides informational content only and does not
    constitute professional tax advice. Always consult a qualified
    tax professional or accountant. CRA rules are complex and change
    frequently. The data may be incomplete or outdated.

    The function determines the database path in the following order:
    1. A path provided directly to the function (db_path parameter)
    2. A path specified by the QE_TAX_RAG_DATA_PATH environment variable
    3. The database file bundled with the package (default)

    Args:
        db_path: Optional custom path to database file. If provided, this path
                is used instead of the bundled database or environment variable.

    Raises:
        FileNotFoundError: If specified path doesn't exist.
        RuntimeError: If bundled database cannot be located.

    """
    global _search_engine, _db_path

    # Priority 1: Direct parameter override
    if db_path:
        path = Path(db_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"Database not found at specified path: {db_path}"
            )
        resolved_path = path
    else:
        # Priority 2: Environment variable override
        env_path_str = os.getenv("QE_TAX_RAG_DATA_PATH")
        if env_path_str:
            path = Path(env_path_str)
            if not path.is_file():
                raise FileNotFoundError(
                    f"Database not found at environment variable path: {env_path_str}"
                )
            resolved_path = path
        else:
            # Priority 3: Bundled database (default)
            # The recommended pattern for bundled data that needs to persist is to
            # copy it to a stable user-accessible location on first use. This
            # avoids issues with `importlib.resources.as_file` creating temporary
            # files that are deleted after the context exits.
            cache_dir = Path.home() / ".qe_tax_rag"
            cache_dir.mkdir(parents=True, exist_ok=True)
            resolved_path = cache_dir / "t4002.db"
            version_file = cache_dir / "version.txt"

            # Check if the cached DB is present and its version matches the library version.
            # This ensures that if the user updates the package, the DB is re-extracted.
            cached_version = (
                version_file.read_text().strip() if version_file.exists() else None
            )

            if not resolved_path.is_file() or cached_version != __version__:
                try:
                    # Modern approach for Python 3.9+
                    # Access bundled database using resources.files()
                    # The qe_tax_rag.data package uses lazy loading to avoid httpx import
                    db_bytes = (
                        resources.files("qe_tax_rag.data")
                        .joinpath("t4002.db")
                        .read_bytes()
                    )
                except AttributeError:
                    # Fallback for Python < 3.9
                    db_bytes = resources.read_binary("qe_tax_rag.data", "t4002.db")

                # Write the new database file and update the version file.
                resolved_path.write_bytes(db_bytes)
                version_file.write_text(__version__)

    # Final validation
    if not resolved_path or not resolved_path.is_file():
        raise RuntimeError(
            "Could not locate the bundled database. "
            "The package installation may be corrupted. "
            "Try reinstalling: pip install --force-reinstall qe-tax-rag"
        )

    # Step 2: Initialize embedding service (singleton)
    encoder = _EmbeddingService()

    # Step 3: Create HybridSearchEngine with database and encoder
    search_engine = HybridSearchEngine(db_path=resolved_path, encoder=encoder)

    # Step 4: Store in module state for reuse
    _search_engine = search_engine
    _db_path = resolved_path


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
        If database not initialized, version fields return "not_initialized".

    """
    # If database not initialized, return stubs
    if _db_path is None:
        return {
            "library_version": __version__,
            "data_version": "not_initialized",
            "schema_version": "not_initialized",
        }

    # Query database metadata table
    conn = sqlite3.connect(_db_path)
    try:
        cursor = conn.execute(
            "SELECT key, value FROM metadata "
            "WHERE key IN ('schema_version', 'data_version')"
        )
        metadata = dict(cursor.fetchall())

        return {
            "library_version": __version__,
            "data_version": metadata.get("data_version", "unknown"),
            "schema_version": metadata.get("schema_version", "unknown"),
        }
    finally:
        conn.close()
