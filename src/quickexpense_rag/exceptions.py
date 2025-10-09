"""Custom exception hierarchy for QuickExpense RAG library."""


class QuickExpenseError(Exception):
    """Base exception for all QuickExpense RAG library errors."""


class DatabaseNotInitializedError(QuickExpenseError):
    """
    Database not found or not initialized.

    Raised when attempting operations before calling init().
    """


class DataVersionMismatchError(QuickExpenseError):
    """
    Database version incompatible with library version.

    Raised when the database schema or data version is incompatible
    with the current library version.
    """


class ChecksumMismatchError(QuickExpenseError):
    """
    Downloaded database failed integrity check.

    Raised when SHA256 checksum verification fails during download.
    """


class NetworkError(QuickExpenseError):
    """
    Network operation failed.

    Raised when database download or network requests fail.
    """


class ParsingError(QuickExpenseError):
    """
    Document parsing failed.

    Raised during indexing when document parsing encounters errors.
    """


class EmbeddingError(QuickExpenseError):
    """
    Embedding generation failed.

    Raised when text embedding generation encounters errors.
    """
