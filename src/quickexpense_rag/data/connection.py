"""SQLite connection configuration for optimal performance."""

import sqlite3
from pathlib import Path


def configure_build_connection(db_path: Path) -> sqlite3.Connection:
    """
    Configure SQLite connection for database build (write-heavy).

    Applies PRAGMAs for maximum write throughput:
    - WAL mode for concurrent access and better performance
    - NORMAL synchronous mode (faster, safe for non-critical data)

    Args:
        db_path: Path to database file

    Returns:
        Configured SQLite connection

    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def configure_runtime_connection(db_path: Path) -> sqlite3.Connection:
    """
    Configure SQLite connection for runtime queries (read-only).

    Applies PRAGMAs for optimal read performance:
    - WAL mode for concurrent reads without locking
    - Read-only mode for safety

    Args:
        db_path: Path to database file

    Returns:
        Configured SQLite connection

    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
