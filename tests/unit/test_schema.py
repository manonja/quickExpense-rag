"""Unit tests for database schema."""

import sqlite3
from pathlib import Path

import pytest
import sqlite_vec
from qe_tax_rag.data.schema import (
    CREATE_TABLES_SQL,
    SCHEMA_VERSION,
    init_metadata,
    optimize_database,
)


def _create_test_connection(db_path: Path) -> sqlite3.Connection:
    """Create a test SQLite connection with sqlite-vec loaded."""
    conn = sqlite3.connect(db_path)
    # Some Python builds don't support enable_load_extension
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        pass
    sqlite_vec.load(conn)
    try:
        conn.enable_load_extension(False)
    except AttributeError:
        pass
    return conn


def test_schema_creation(tmp_path: Path) -> None:
    """Verify schema creates all tables and indexes."""
    db_path = tmp_path / "test.db"
    conn = _create_test_connection(db_path)
    conn.executescript(CREATE_TABLES_SQL)

    # Verify tables exist
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "metadata" in tables
    assert "rules" in tables
    assert "rules_fts" in tables
    assert "rules_vec" in tables
    assert "expense_types" in tables
    assert "rule_expense_type_links" in tables

    # Verify indexes exist
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}
    assert "idx_province" in indexes
    assert "idx_business_type" in indexes
    assert "idx_citation" in indexes
    assert "idx_link_rule" in indexes
    assert "idx_link_type" in indexes

    conn.close()


def test_metadata_without_rowid(tmp_path: Path) -> None:
    """Verify metadata table uses WITHOUT ROWID optimization."""
    db_path = tmp_path / "test.db"
    conn = _create_test_connection(db_path)
    conn.executescript(CREATE_TABLES_SQL)

    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE name='metadata'")
    sql = cursor.fetchone()[0]
    assert "WITHOUT ROWID" in sql

    conn.close()


def test_metadata_initialization(tmp_path: Path) -> None:
    """Verify metadata table populated with versions."""
    db_path = tmp_path / "test.db"
    conn = _create_test_connection(db_path)
    conn.executescript(CREATE_TABLES_SQL)
    init_metadata(
        conn, data_version="2024.12", embedding_model="BAAI/bge-small-en-v1.5"
    )

    cursor = conn.execute("SELECT key, value FROM metadata")
    metadata = dict(cursor.fetchall())

    assert metadata["schema_version"] == SCHEMA_VERSION
    assert metadata["data_version"] == "2024.12"
    assert metadata["embedding_model"] == "BAAI/bge-small-en-v1.5"

    conn.close()


def test_fts_triggers_sync(tmp_path: Path) -> None:
    """Verify FTS5 triggers keep rules_fts in sync with rules."""
    db_path = tmp_path / "test.db"
    conn = _create_test_connection(db_path)
    conn.executescript(CREATE_TABLES_SQL)

    # Insert test data
    conn.execute(
        """
        INSERT INTO rules (content, citation_id, source_url, source_hash, retrieved_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            "Test content",
            "S1-F1-C1-p1",
            "https://test.com",
            "abc123",
            "2024-01-01T00:00:00Z",
        ),
    )

    # Verify FTS table updated
    cursor = conn.execute("SELECT content FROM rules_fts WHERE content MATCH 'Test'")
    assert cursor.fetchone() is not None

    # Update and verify
    conn.execute(
        "UPDATE rules SET content = ? WHERE citation_id = ?",
        ("Updated content", "S1-F1-C1-p1"),
    )
    cursor = conn.execute("SELECT content FROM rules_fts WHERE content MATCH 'Updated'")
    assert cursor.fetchone() is not None

    # Delete and verify FTS cleaned up
    conn.execute("DELETE FROM rules WHERE citation_id = ?", ("S1-F1-C1-p1",))

    # Verify the row is gone from rules table
    cursor = conn.execute("SELECT * FROM rules WHERE citation_id = ?", ("S1-F1-C1-p1",))
    assert cursor.fetchone() is None

    # Verify FTS has no more rows (external content table cleanup)
    cursor = conn.execute("SELECT COUNT(*) FROM rules_fts")
    assert cursor.fetchone()[0] == 0

    conn.close()


def test_citation_id_uniqueness(tmp_path: Path) -> None:
    """Verify UNIQUE constraint on citation_id."""
    db_path = tmp_path / "test.db"
    conn = _create_test_connection(db_path)
    conn.executescript(CREATE_TABLES_SQL)

    conn.execute(
        """
        INSERT INTO rules (content, citation_id, source_url, source_hash, retrieved_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            "Content 1",
            "S1-F1-C1-p1",
            "https://test.com",
            "abc123",
            "2024-01-01T00:00:00Z",
        ),
    )

    # Attempt duplicate insert
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        conn.execute(
            """
            INSERT INTO rules (content, citation_id, source_url, source_hash, retrieved_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "Content 2",
                "S1-F1-C1-p1",
                "https://test.com",
                "def456",
                "2024-01-01T00:00:00Z",
            ),
        )

    conn.close()


def test_analyze_optimization(tmp_path: Path) -> None:
    """Verify ANALYZE command updates query planner statistics."""
    db_path = tmp_path / "test.db"
    conn = _create_test_connection(db_path)
    conn.executescript(CREATE_TABLES_SQL)

    # Insert sample data
    for i in range(10):
        conn.execute(
            """
            INSERT INTO rules (content, citation_id, source_url, source_hash, retrieved_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                f"Content {i}",
                f"S1-F1-C1-p{i}",
                "https://test.com",
                f"hash{i}",
                "2024-01-01T00:00:00Z",
            ),
        )

    # Run optimization
    optimize_database(conn)

    # Verify sqlite_stat tables exist (created by ANALYZE)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE name LIKE 'sqlite_stat%'"
    )
    stat_tables = [row[0] for row in cursor.fetchall()]
    assert len(stat_tables) > 0  # ANALYZE creates sqlite_stat1, possibly sqlite_stat4

    conn.close()


def test_rules_table_structure(tmp_path: Path) -> None:
    """Verify rules table has expected columns."""
    db_path = tmp_path / "test.db"
    conn = _create_test_connection(db_path)
    conn.executescript(CREATE_TABLES_SQL)

    cursor = conn.execute("PRAGMA table_info(rules)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        "id",
        "content",
        "citation_id",
        "source_url",
        "source_hash",
        "province",
        "business_type",
        "metadata_json",
        "retrieved_at",
        "created_at",
    }

    assert columns == expected_columns

    conn.close()


def test_fts5_external_content_configuration(tmp_path: Path) -> None:
    """Verify FTS5 uses external content table configuration."""
    db_path = tmp_path / "test.db"
    conn = _create_test_connection(db_path)
    conn.executescript(CREATE_TABLES_SQL)

    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE name='rules_fts'")
    sql = cursor.fetchone()[0]

    # Verify external content configuration
    assert "content='rules'" in sql
    assert "content_rowid='id'" in sql
    assert "tokenize='porter unicode61'" in sql

    conn.close()
