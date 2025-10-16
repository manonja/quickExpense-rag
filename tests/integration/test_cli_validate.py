"""Integration tests for validate command (TICKET-9D Task 4)."""

import json
import sqlite3
from pathlib import Path

import pytest
import sqlite_vec
from scripts.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def valid_database(tmp_path: Path) -> Path:
    """Create a valid database with all required schema and data."""
    db_path = tmp_path / "valid.db"
    conn = sqlite3.connect(db_path)

    # Load sqlite-vec extension
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        pass

    sqlite_vec.load(conn)

    try:
        conn.enable_load_extension(False)
    except AttributeError:
        pass

    # Create schema
    from qe_tax_rag.data.schema import CREATE_TABLES_SQL

    conn.executescript(CREATE_TABLES_SQL)

    # Add metadata
    conn.execute(
        """
        INSERT INTO metadata (key, value)
        VALUES
            ('schema_version', '1.0'),
            ('data_version', '2024.12'),
            ('embedding_model', 'BAAI/bge-small-en-v1.5'),
            ('embedding_dimension', '384')
        """
    )

    # Add sample rule with embedding
    import numpy as np

    embedding = np.random.rand(384).astype(np.float32)

    conn.execute(
        """
        INSERT INTO rules (
            citation_id, content, source_url, source_hash,
            province, business_type, retrieved_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "S1-F1-C1-p1.1",
            "Sample rule content for validation testing",
            "https://www.canada.ca/test",
            "abc123",
            "BC",
            "sole_proprietorship",
            "2024-01-01T00:00:00Z",
        ),
    )

    # Get the last inserted row ID
    cursor = conn.execute("SELECT id FROM rules WHERE citation_id = 'S1-F1-C1-p1.1'")
    rule_id = cursor.fetchone()[0]

    # Add expense type and link
    cursor = conn.execute("INSERT INTO expense_types (name) VALUES (?)", ("meals",))
    expense_type_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO rule_expense_type_links (rule_id, expense_type_id) VALUES (?, ?)",
        (rule_id, expense_type_id),
    )

    # Insert into FTS
    conn.execute(
        """
        INSERT INTO rules_fts (rowid, content)
        VALUES (?, ?)
        """,
        (rule_id, "Sample rule content for validation testing"),
    )

    # Insert embedding into vec table
    conn.execute(
        "INSERT INTO rules_vec (rowid, embedding) VALUES (?, ?)",
        (rule_id, embedding.tobytes()),
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def invalid_database(tmp_path: Path) -> Path:
    """Create an invalid database missing required tables."""
    db_path = tmp_path / "invalid.db"
    conn = sqlite3.connect(db_path)

    # Create incomplete schema (missing rules_vec)
    conn.execute(
        """
        CREATE TABLE rules (
            id INTEGER PRIMARY KEY,
            citation_id TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            province TEXT,
            business_type TEXT,
            expense_type TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE VIRTUAL TABLE rules_fts USING fts5(
            content,
            content='rules',
            content_rowid='id'
        )
        """
    )

    # Missing metadata, rules_vec tables

    conn.commit()
    conn.close()

    return db_path


@pytest.mark.integration
def test_validate_command_passes_with_valid_database(valid_database: Path) -> None:
    """Test 4a (RED): Verify validate command returns exit code 0 on success."""
    result = runner.invoke(
        app,
        [
            "validate",
            "--db-path",
            str(valid_database),
        ],
    )

    # Should succeed with exit code 0
    assert result.exit_code == 0
    assert "✅" in result.stdout or "passed" in result.stdout.lower()


@pytest.mark.integration
def test_validate_command_fails_with_invalid_database(invalid_database: Path) -> None:
    """Test 4b (RED): Verify validate command returns exit code 1 on failure."""
    result = runner.invoke(
        app,
        [
            "validate",
            "--db-path",
            str(invalid_database),
        ],
    )

    # Should fail with exit code 1
    assert result.exit_code == 1
    assert "❌" in result.stdout or "failed" in result.stdout.lower()


@pytest.mark.integration
def test_validate_command_missing_database_fails(tmp_path: Path) -> None:
    """Test 4b (RED): Verify validate command fails when database missing."""
    nonexistent_db = tmp_path / "nonexistent.db"

    result = runner.invoke(
        app,
        [
            "validate",
            "--db-path",
            str(nonexistent_db),
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


@pytest.mark.integration
def test_validate_command_shows_statistics(valid_database: Path) -> None:
    """Test 4c (RED): Verify validate command displays statistics."""
    result = runner.invoke(
        app,
        [
            "validate",
            "--db-path",
            str(valid_database),
        ],
    )

    assert result.exit_code == 0

    # Should show some statistics
    output = result.stdout.lower()
    assert "chunk" in output or "rule" in output or "row" in output


@pytest.mark.integration
def test_validate_command_uses_rich_formatting(valid_database: Path) -> None:
    """Test 4c (RED): Verify validate command uses rich formatting."""
    result = runner.invoke(
        app,
        [
            "validate",
            "--db-path",
            str(valid_database),
        ],
    )

    assert result.exit_code == 0

    # Rich formatting typically uses box characters or bold markers
    # Just verify output is not empty and has some structure
    assert len(result.stdout) > 0
    assert "Validation" in result.stdout or "Database" in result.stdout
