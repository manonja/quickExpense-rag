"""Custom exception hierarchy for QE Tax RAG library."""


class QeTaxRagError(Exception):
    """Base exception for all QE Tax RAG library errors."""


class DatabaseNotInitializedError(QeTaxRagError):
    """
    Database not found or not initialized.

    Raised when attempting operations before calling init().
    """


class DataVersionMismatchError(QeTaxRagError):
    """
    Database version incompatible with library version.

    Raised when the database schema or data version is incompatible
    with the current library version.
    """


class ChecksumMismatchError(QeTaxRagError):
    """
    Downloaded database failed integrity check.

    Raised when SHA256 checksum verification fails during download.
    """


class NetworkError(QeTaxRagError):
    """
    Network operation failed.

    Raised when database download or network requests fail.
    """


class ParsingError(QeTaxRagError):
    """
    Document parsing failed.

    Raised during indexing when document parsing encounters errors.
    """


class EmbeddingError(QeTaxRagError):
    """
    Embedding generation failed.

    Raised when text embedding generation encounters errors.
    """


class ModelLoadingError(QeTaxRagError):
    """
    Model loading failed.

    Raised when SentenceTransformer model fails to load.
    """
