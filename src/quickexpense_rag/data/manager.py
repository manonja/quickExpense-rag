"""
Data manager for database download, caching, and verification.

Handles downloading database from GitHub Releases, SHA256 verification,
version compatibility checking, and offline mode support.
"""

from pathlib import Path


class DataManager:
    """
    Manages database download, caching, and integrity verification.

    Will be implemented in TICKET 6.
    """

    def __init__(self) -> None:
        """Initialize data manager."""
        raise NotImplementedError("DataManager will be implemented in TICKET 6")

    def get_database_path(self) -> Path:
        """
        Get path to cached database, download if missing.

        Returns:
            Path to local database file.

        Raises:
            NetworkError: If download fails and no cache exists.

        """
        raise NotImplementedError("get_database_path() will be implemented in TICKET 6")

    def download_database(self, force: bool = False) -> Path:
        """
        Download database from GitHub Releases.

        Args:
            force: Force re-download even if cached.

        Returns:
            Path to downloaded database.

        Raises:
            NetworkError: If download fails.
            ChecksumMismatchError: If integrity check fails.

        """
        raise NotImplementedError("download_database() will be implemented in TICKET 6")

    def verify_integrity(self, db_path: Path) -> bool:
        """
        Verify database SHA256 against manifest.

        Args:
            db_path: Path to database file.

        Returns:
            True if checksum matches.

        """
        raise NotImplementedError("verify_integrity() will be implemented in TICKET 6")

    def check_version_compatibility(self, db_path: Path) -> None:
        """
        Check schema and data versions, raise if incompatible.

        Args:
            db_path: Path to database file.

        Raises:
            DataVersionMismatchError: If versions incompatible.

        """
        raise NotImplementedError(
            "check_version_compatibility() will be implemented in TICKET 6"
        )

    def get_metadata(self, db_path: Path) -> dict[str, str]:
        """
        Read metadata table from database.

        Args:
            db_path: Path to database file.

        Returns:
            Dictionary of metadata key-value pairs.

        """
        raise NotImplementedError("get_metadata() will be implemented in TICKET 6")
