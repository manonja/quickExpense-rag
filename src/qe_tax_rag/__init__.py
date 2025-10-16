"""
QE Tax RAG: Semantic search over CRA business expense rules.

⚠️ LEGAL DISCLAIMER:
This library provides informational content only and does not constitute
professional tax advice. CRA rules are complex and change frequently.
Always consult a qualified tax professional or accountant.
"""

import logging

__version__ = "0.1.0"

from qe_tax_rag.api import get_version, init, search
from qe_tax_rag.exceptions import (
    ChecksumMismatchError,
    DatabaseNotInitializedError,
    DataVersionMismatchError,
    EmbeddingError,
    NetworkError,
    ParsingError,
    QeTaxRagError,
)
from qe_tax_rag.search.enums import BusinessType, Province
from qe_tax_rag.search.models import ExpenseQuery, SearchResult
from qe_tax_rag.settings import settings

__all__ = [
    "BusinessType",
    "ChecksumMismatchError",
    "DataVersionMismatchError",
    "DatabaseNotInitializedError",
    "EmbeddingError",
    "ExpenseQuery",
    "NetworkError",
    "ParsingError",
    "Province",
    "QeTaxRagError",
    "SearchResult",
    "__version__",
    "get_version",
    "init",
    "search",
    "settings",
]

# Configure a NullHandler for the library's logger.
# This prevents log messages from being output to stderr if the user of the
# library has not configured logging. See:
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())
