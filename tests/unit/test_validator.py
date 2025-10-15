"""Unit tests for IndexValidator (TICKET-9D)."""

import sqlite3
from pathlib import Path

import numpy as np
import pytest
from quickexpense_rag.data.validator import IndexValidator


@pytest.mark.unit
def test_check_schema_tables_exist(fixture_db_path: Path) -> None:
    """Test 1a (RED): Verify check_schema() detects required tables."""
    validator = IndexValidator(fixture_db_path)

    result = validator.check_schema()

    assert result["passed"] is True
    assert "tables" in result
    assert set(result["tables"]) >= {"rules", "rules_fts", "rules_vec", "metadata"}


@pytest.mark.unit
def test_check_schema_missing_table(tmp_path: Path) -> None:
    """Test 1a (RED): Verify check_schema() fails when table is missing."""
    # Create incomplete database
    db_path = tmp_path / "incomplete.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE rules (id INTEGER PRIMARY KEY)")
    conn.close()

    validator = IndexValidator(db_path)
    result = validator.check_schema()

    assert result["passed"] is False
    assert "missing" in result or "error" in result


@pytest.mark.unit
def test_check_row_counts_match(fixture_db_path: Path) -> None:
    """Test 1b (RED): Verify check_row_counts() ensures rules, rules_vec, rules_fts match."""
    validator = IndexValidator(fixture_db_path)

    result = validator.check_row_counts()

    assert result["passed"] is True
    assert result["rules_count"] == result["rules_vec_count"]
    assert result["rules_count"] == result["rules_fts_count"]
    assert result["rules_count"] > 0


@pytest.mark.unit
def test_check_row_counts_mismatch(tmp_path: Path) -> None:
    """Test 1b (RED): Verify check_row_counts() detects mismatch."""
    # Create database with mismatched counts
    db_path = tmp_path / "mismatch.db"
    conn = sqlite3.connect(db_path)

    # Load sqlite-vec before creating schema
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        pass

    import sqlite_vec

    sqlite_vec.load(conn)

    try:
        conn.enable_load_extension(False)
    except AttributeError:
        pass

    # Create schema
    from quickexpense_rag.data.schema import CREATE_TABLES_SQL

    conn.executescript(CREATE_TABLES_SQL)

    # Insert into rules but not rules_vec
    conn.execute(
        "INSERT INTO rules (content, citation_id, source_url, source_hash, retrieved_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("Test content", "S1-F1-C1-p1", "http://test.com", "abc123", "2024-01-01"),
    )
    conn.commit()
    conn.close()

    validator = IndexValidator(db_path)
    result = validator.check_row_counts()

    # FTS should match (auto-synced via triggers), but vec should be 0
    assert result["passed"] is False


@pytest.mark.unit
def test_check_embeddings_valid_dimensions(fixture_db_path: Path) -> None:
    """Test 1c (RED): Verify check_embeddings() validates 384 dimensions."""
    validator = IndexValidator(fixture_db_path)

    result = validator.check_embeddings()

    assert result["passed"] is True
    assert result["embedding_dim"] == 384
    assert result["sample_count"] >= 1


@pytest.mark.unit
def test_check_embeddings_no_embeddings(tmp_path: Path) -> None:
    """Test 1c (RED): Verify check_embeddings() fails when no embeddings exist."""
    db_path = tmp_path / "no_embeddings.db"
    conn = sqlite3.connect(db_path)

    # Load sqlite-vec before creating schema
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        pass

    import sqlite_vec

    sqlite_vec.load(conn)

    try:
        conn.enable_load_extension(False)
    except AttributeError:
        pass

    from quickexpense_rag.data.schema import CREATE_TABLES_SQL

    conn.executescript(CREATE_TABLES_SQL)
    conn.close()

    validator = IndexValidator(db_path)
    result = validator.check_embeddings()

    assert result["passed"] is False


@pytest.mark.unit
def test_check_search_executes_without_error(fixture_db_path: Path) -> None:
    """Test 1d (RED): Verify check_search() runs generic query successfully."""
    validator = IndexValidator(fixture_db_path)

    result = validator.check_search()

    assert result["passed"] is True, (
        f"Search failed: {result.get('error', 'unknown error')}"
    )
    assert result["query"] == "what is an expense"
    assert "result_count" in result
    # Search might return 0 results if query doesn't match, that's ok


@pytest.mark.unit
def test_check_search_handles_errors(tmp_path: Path) -> None:
    """Test 1d (RED): Verify check_search() catches database errors."""
    # Create database with empty schema (no tables at all)
    db_path = tmp_path / "broken.db"
    conn = sqlite3.connect(db_path)
    # Just create an empty database, don't add any tables
    conn.close()

    validator = IndexValidator(db_path)
    result = validator.check_search()

    # Should fail because database lacks the required schema
    assert result["passed"] is False
    assert "error" in result


@pytest.mark.unit
def test_validate_returns_comprehensive_report(fixture_db_path: Path) -> None:
    """Test 1e (RED): Verify validate() returns full validation report."""
    validator = IndexValidator(fixture_db_path)

    report = validator.validate()

    # Check top-level structure
    assert "overall_passed" in report
    assert "checks" in report
    assert "statistics" in report

    # Check individual checks present
    checks = report["checks"]
    assert "schema" in checks
    assert "row_counts" in checks
    assert "embeddings" in checks
    assert "search" in checks

    # Check statistics present
    stats = report["statistics"]
    assert "total_chunks" in stats
    assert "provinces" in stats
    assert "business_types" in stats
    assert "expense_types" in stats

    # Overall should pass for fixture DB
    assert report["overall_passed"] is True


@pytest.mark.unit
def test_validate_fails_if_any_check_fails(tmp_path: Path) -> None:
    """Test 1e (RED): Verify validate() overall_passed=False if any check fails."""
    # Create database with missing vector table
    db_path = tmp_path / "partial.db"
    conn = sqlite3.connect(db_path)

    # Load sqlite-vec before creating schema
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        pass

    import sqlite_vec

    sqlite_vec.load(conn)

    try:
        conn.enable_load_extension(False)
    except AttributeError:
        pass

    from quickexpense_rag.data.schema import CREATE_TABLES_SQL

    # Create schema but don't add any data
    conn.executescript(CREATE_TABLES_SQL)
    conn.close()

    validator = IndexValidator(db_path)
    report = validator.validate()

    # Should fail due to missing embeddings or mismatched counts
    assert report["overall_passed"] is False

    # At least one check should have failed
    failed_checks = [
        name for name, check in report["checks"].items() if not check["passed"]
    ]
    assert len(failed_checks) > 0
