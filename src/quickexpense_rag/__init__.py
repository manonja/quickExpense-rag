"""
QuickExpense RAG: Semantic search over CRA business expense rules.

⚠️ LEGAL DISCLAIMER:
This library provides informational content only and does not constitute
professional tax advice. CRA rules are complex and change frequently.
Always consult a qualified tax professional or accountant.
"""

__version__ = "0.1.0"

from quickexpense_rag.api import get_version, init, search
from quickexpense_rag.exceptions import (
    ChecksumMismatchError,
    DatabaseNotInitializedError,
    DataVersionMismatchError,
    EmbeddingError,
    NetworkError,
    ParsingError,
    QuickExpenseError,
)
from quickexpense_rag.search.enums import BusinessType, ExpenseType, Province
from quickexpense_rag.search.models import ExpenseQuery, SearchResult

__all__ = [
    "BusinessType",
    "ChecksumMismatchError",
    "DataVersionMismatchError",
    "DatabaseNotInitializedError",
    "EmbeddingError",
    "ExpenseQuery",
    "ExpenseType",
    "NetworkError",
    "ParsingError",
    "Province",
    "QuickExpenseError",
    "SearchResult",
    "__version__",
    "get_version",
    "init",
    "search",
]
