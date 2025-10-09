"""Unit tests for fixture database integrity and structure."""

import sqlite3
from pathlib import Path

import numpy as np
import pytest


@pytest.mark.unit
def test_fixture_db_exists(fixture_db_path: Path) -> None:
    """Verify fixture database file exists."""
    assert fixture_db_path.exists(), f"Fixture database not found at {fixture_db_path}"
    assert fixture_db_path.is_file(), f"Expected file, got directory: {fixture_db_path}"


@pytest.mark.unit
def test_fixture_db_row_count(fixture_db_path: Path) -> None:
    """Verify fixture database has expected number of rows."""
    conn = sqlite3.connect(fixture_db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM rules")
    count = cursor.fetchone()[0]
    conn.close()

    assert count >= 10, f"Expected at least 10 rows, got {count}"
    assert count <= 20, f"Expected at most 20 rows, got {count}"


@pytest.mark.unit
def test_fixture_db_embeddings_present(fixture_db_path: Path) -> None:
    """Verify all rows have embeddings with correct dimensions."""
    conn = sqlite3.connect(fixture_db_path)

    # Load sqlite-vec extension
    conn.enable_load_extension(True)
    import sqlite_vec

    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    # Count rules
    cursor = conn.execute("SELECT COUNT(*) FROM rules")
    rules_count = cursor.fetchone()[0]

    # Count embeddings
    cursor = conn.execute("SELECT COUNT(*) FROM rules_vec")
    vec_count = cursor.fetchone()[0]

    assert (
        rules_count == vec_count
    ), f"Mismatch: {rules_count} rules but {vec_count} embeddings"

    # Verify embedding dimensions
    cursor = conn.execute("SELECT embedding FROM rules_vec LIMIT 1")
    row = cursor.fetchone()
    assert row is not None, "No embeddings found"

    embedding = np.frombuffer(row[0], dtype=np.float32)
    assert (
        len(embedding) == 384
    ), f"Expected 384 dimensions, got {len(embedding)}"

    conn.close()


@pytest.mark.unit
def test_fixture_db_fts_searchable(fixture_db_path: Path) -> None:
    """Verify FTS5 index is searchable."""
    conn = sqlite3.connect(fixture_db_path)

    # Search for keyword "T2125" which exists in test data
    cursor = conn.execute(
        "SELECT COUNT(*) FROM rules_fts WHERE rules_fts MATCH 'T2125'"
    )
    count = cursor.fetchone()[0]

    assert count > 0, "FTS5 search for 'T2125' returned no results"

    # Search for keyword "meals" which exists in multiple rows
    cursor = conn.execute(
        "SELECT COUNT(*) FROM rules_fts WHERE rules_fts MATCH 'meals'"
    )
    count = cursor.fetchone()[0]

    assert count > 0, "FTS5 search for 'meals' returned no results"

    conn.close()


@pytest.mark.unit
def test_fixture_db_vector_search_works(fixture_db_path: Path) -> None:
    """Verify vector search table is functional."""
    conn = sqlite3.connect(fixture_db_path)

    # Load sqlite-vec extension
    conn.enable_load_extension(True)
    import sqlite_vec

    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    # Create a random query vector
    query_vec = np.random.randn(384).astype(np.float32)
    query_vec = query_vec / np.linalg.norm(query_vec)  # Normalize

    # Perform vector search (cosine distance)
    cursor = conn.execute(
        """
        SELECT rowid, distance
        FROM rules_vec
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT 5
        """,
        (query_vec.tobytes(),),
    )

    results = cursor.fetchall()
    assert len(results) > 0, "Vector search returned no results"
    assert len(results) <= 5, "Vector search returned more than 5 results"

    # Verify results have valid rowid and distance
    for rowid, distance in results:
        assert isinstance(rowid, int), f"Expected int rowid, got {type(rowid)}"
        assert isinstance(
            distance, (int, float)
        ), f"Expected numeric distance, got {type(distance)}"
        assert distance >= 0, f"Distance should be non-negative, got {distance}"

    conn.close()


@pytest.mark.unit
def test_fixture_db_metadata_populated(fixture_db_path: Path) -> None:
    """Verify metadata table has required version info."""
    conn = sqlite3.connect(fixture_db_path)

    cursor = conn.execute("SELECT key, value FROM metadata")
    metadata = dict(cursor.fetchall())

    assert "schema_version" in metadata, "Missing schema_version in metadata"
    assert "data_version" in metadata, "Missing data_version in metadata"
    assert "embedding_model" in metadata, "Missing embedding_model in metadata"

    # Verify schema version format
    assert metadata["schema_version"] == "1.0", (
        f"Expected schema_version='1.0', " f"got '{metadata['schema_version']}'"
    )

    # Verify data version
    assert metadata["data_version"] == "fixture-v1", (
        f"Expected data_version='fixture-v1', "
        f"got '{metadata['data_version']}'"
    )

    conn.close()


@pytest.mark.unit
def test_fixture_db_province_coverage(fixture_db_path: Path) -> None:
    """Verify fixture has coverage across provinces."""
    conn = sqlite3.connect(fixture_db_path)

    cursor = conn.execute("SELECT DISTINCT province FROM rules WHERE province IS NOT NULL")
    provinces = {row[0] for row in cursor.fetchall()}

    expected_provinces = {"BC", "AB", "ON", "QC"}
    assert provinces >= expected_provinces, (
        f"Missing provinces: {expected_provinces - provinces}"
    )

    conn.close()


@pytest.mark.unit
def test_fixture_db_business_type_coverage(fixture_db_path: Path) -> None:
    """Verify fixture has coverage across business types."""
    conn = sqlite3.connect(fixture_db_path)

    cursor = conn.execute(
        "SELECT DISTINCT business_type FROM rules WHERE business_type IS NOT NULL"
    )
    business_types = {row[0] for row in cursor.fetchall()}

    expected_types = {"sole_proprietorship", "corporation", "partnership"}
    assert business_types >= expected_types, (
        f"Missing business types: {expected_types - business_types}"
    )

    conn.close()


@pytest.mark.unit
def test_fixture_db_expense_type_coverage(fixture_db_path: Path) -> None:
    """Verify fixture has coverage across expense types."""
    conn = sqlite3.connect(fixture_db_path)

    cursor = conn.execute(
        "SELECT DISTINCT expense_type FROM rules WHERE expense_type IS NOT NULL"
    )
    expense_types = {row[0] for row in cursor.fetchall()}

    expected_types = {"meals", "travel", "vehicle", "home_office"}
    assert expense_types >= expected_types, (
        f"Missing expense types: {expected_types - expense_types}"
    )

    conn.close()
