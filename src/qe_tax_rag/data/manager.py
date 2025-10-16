"""
Data manager for database download, caching, and verification.

Handles downloading database from GitHub Releases, SHA256 verification,
version compatibility checking, and offline mode support.
"""

import hashlib
import logging
import sqlite3
from pathlib import Path

import httpx

from ..exceptions import ChecksumMismatchError, DataVersionMismatchError, NetworkError
from ..settings import Settings

logger = logging.getLogger(__name__)


class DataManager:
    """
    Manages database download, caching, and integrity verification.

    Provides a single public method `get_database_path()` that handles all
    download, caching, and verification logic internally. Supports offline
    mode by returning cached database if available.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize data manager.

        Args:
            settings: Application settings instance.

        """
        self.settings = settings

    def get_database_path(self) -> Path:
        """
        Get path to valid cached database.

        Downloads and verifies database if not cached. Supports offline mode
        by returning cached database if it exists and is valid.

        Returns:
            Path to valid database file.

        Raises:
            NetworkError: If download fails and no cached DB exists.
            ChecksumMismatchError: If downloaded file checksum invalid.
            DataVersionMismatchError: If DB version incompatible.

        """
        cache_path = self.settings.cache_dir / self.settings.db_filename

        # If cached DB exists, use it (offline mode)
        if cache_path.exists():
            logger.info("Using cached database: %s", cache_path)
            return cache_path

        # No cached DB - must download
        logger.info("No cached database found, downloading...")
        return self._download_and_verify()

    def _download_and_verify(self) -> Path:
        """
        Download database, verify checksum, check version, save to cache.

        Returns:
            Path to downloaded and verified database file.

        Raises:
            NetworkError: If download fails.
            ChecksumMismatchError: If checksum verification fails.
            DataVersionMismatchError: If version check fails.

        """
        # Ensure cache directory exists
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)

        temp_path = self.settings.cache_dir / f"{self.settings.db_filename}.part"
        final_path = self.settings.cache_dir / self.settings.db_filename

        try:
            # Download to temp file
            logger.info(
                "Downloading database from %s...", self.settings.db_download_url
            )

            with httpx.stream(
                "GET",
                self.settings.db_download_url,
                timeout=self.settings.request_timeout,
                follow_redirects=True,
            ) as response:
                response.raise_for_status()

                with open(temp_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

            logger.info("Database download complete")

            # Verify checksum (if configured)
            if self.settings.database_sha256:
                self._verify_checksum(temp_path)
                logger.info("Checksum verification passed")

            # Check version compatibility
            self._check_version_compatibility(temp_path)
            logger.info("Version compatibility check passed")

            # Atomic rename to final location
            temp_path.rename(final_path)
            logger.info("Database cached at %s", final_path)

            return final_path

        except httpx.HTTPError as e:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            raise NetworkError(
                f"Failed to download database from {self.settings.db_download_url}: {e}"
            ) from e

    def _verify_checksum(self, db_path: Path) -> None:
        """
        Verify SHA256 checksum against expected value.

        Args:
            db_path: Path to database file to verify.

        Raises:
            ChecksumMismatchError: If checksum doesn't match expected value.

        """
        sha256 = hashlib.sha256()

        with open(db_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        actual = sha256.hexdigest()
        expected = self.settings.database_sha256

        if actual != expected:
            # Delete corrupted file
            db_path.unlink()
            raise ChecksumMismatchError(
                f"Database checksum mismatch. Expected {expected}, got {actual}. "
                "The downloaded file may be corrupted. Please try again."
            )

    def _check_version_compatibility(self, db_path: Path) -> None:
        """
        Check schema and data versions are compatible with library.

        Args:
            db_path: Path to database file to check.

        Raises:
            DataVersionMismatchError: If schema version is incompatible.

        """
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute(
                "SELECT key, value FROM metadata "
                "WHERE key IN ('schema_version', 'data_version')"
            )
            metadata = dict(cursor.fetchall())

            schema_version = metadata.get("schema_version")
            data_version = metadata.get("data_version")

            # Check schema version (major version must match)
            expected_major = self.settings.schema_version.split(".")[0]

            if not schema_version:
                raise DataVersionMismatchError(
                    f"Database is missing schema_version metadata. "
                    f"Expected schema version {self.settings.schema_version}."
                )

            actual_major = schema_version.split(".")[0]

            if actual_major != expected_major:
                raise DataVersionMismatchError(
                    f"Incompatible schema version. "
                    f"Library expects {self.settings.schema_version}, "
                    f"database has {schema_version}. "
                    f"Please upgrade the library or use a compatible database."
                )

            # Check data version (informational - warn but don't fail)
            if data_version and data_version != self.settings.database_version:
                logger.warning(
                    "Data version mismatch. Library expects %s, "
                    "database has %s. This may work but is not tested.",
                    self.settings.database_version,
                    data_version,
                )

        finally:
            conn.close()
