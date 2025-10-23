"""Integration tests for full YAML → SQLite conversion pipeline.

Tests validate end-to-end conversion from YAML ExtractedRule objects
through DatabaseChunk transformation to actual SQLite database insertion.

Coverage:
- AC3: DatabaseChunk correctly inserts into SQLite
- AC5: FTS5 table automatically synced via triggers
- AC6: Vector table populated with embeddings
- Full round-trip: YAML → RuleSet → DatabaseChunk → SQLite → Query

Uses:
- Real YAML fixtures (tests/fixtures/conversion/)
- Temporary file-based SQLite database (tests/conftest.py::temp_db)
- Mock embeddings (384-dim zero vectors for speed)
"""

import sqlite3
from pathlib import Path

import pytest
from qe_tax_rag.data.builder import IndexBuilder
from qe_tax_rag.embeddings.encoder import embedding_service
from qe_tax_rag.search.models import SourceFile


@pytest.fixture
def simple_rule_yaml_path():
    """Path to simple_rule.yml fixture."""
    return Path(__file__).parent.parent / "fixtures" / "conversion" / "simple_rule.yml"


@pytest.fixture
def complex_rule_yaml_path():
    """Path to complex_rule.yml fixture."""
    return (
        Path(__file__).parent.parent / "fixtures" / "conversion" / "complex_rule.yml"
    )


@pytest.fixture
def test_source_files():
    """Source files for test fixtures."""
    return [
        SourceFile(
            path="simple_rule.html",
            url="file://tests/fixtures/extraction/ca/simple_rule.html",
            hash="abc123simple",
        ),
        SourceFile(
            path="complex_rule.html",
            url="file://tests/fixtures/extraction/ca/complex_rule.html",
            hash="abc123complex",
        ),
        SourceFile(
            path="t4002-3.html",
            url="file://cra_documents/t4002-3.html",
            hash="abc123t4002",
        ),
    ]


# =============================================================================
# AC3: DatabaseChunk Insertion
# =============================================================================


def test_simple_rule_inserts_into_database(
    simple_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """Simple rule YAML inserts into SQLite rules table."""
    # Build database using IndexBuilder
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=simple_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Verify insertion
    conn = sqlite3.connect(temp_db)
    cursor = conn.execute("SELECT COUNT(*) FROM rules")
    count = cursor.fetchone()[0]
    assert count == 1

    # Verify content
    cursor = conn.execute(
        "SELECT citation_id, content FROM rules WHERE citation_id = ?",
        ("LINE-8523",),
    )
    row = cursor.fetchone()
    assert row is not None
    citation_id, content = row
    assert citation_id == "LINE-8523"
    assert content.startswith("Meals and entertainment\n\n")

    conn.close()


def test_complex_rules_insert_into_database(
    complex_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """Multiple rules from complex YAML insert into SQLite."""
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=complex_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Verify insertion count
    conn = sqlite3.connect(temp_db)
    cursor = conn.execute("SELECT COUNT(*) FROM rules")
    count = cursor.fetchone()[0]
    assert count == 3

    # Verify citation IDs
    cursor = conn.execute("SELECT citation_id FROM rules ORDER BY citation_id")
    citation_ids = [row[0] for row in cursor.fetchall()]
    assert citation_ids == ["LINE-8000", "LINE-8523", "LINE-9270"]

    conn.close()


def test_metadata_json_stored_correctly(
    simple_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """Metadata stored as JSON in metadata_json column."""
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=simple_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Verify metadata JSON
    conn = sqlite3.connect(temp_db)
    cursor = conn.execute(
        "SELECT metadata_json FROM rules WHERE citation_id = ?",
        ("LINE-8523",),
    )
    row = cursor.fetchone()
    assert row is not None

    metadata_json = row[0]
    assert metadata_json is not None

    # Parse JSON and verify fields
    import json

    metadata = json.loads(metadata_json)
    assert metadata["extraction_source"] == "adjudicated"
    assert metadata["extraction_confidence"] == 0.95
    assert metadata["source_anchor"] == "tocch3ln8523"

    conn.close()


# =============================================================================
# AC5: FTS5 Table Auto-Sync
# =============================================================================


def test_fts5_table_synced_via_trigger(
    simple_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """FTS5 table automatically synced when rules inserted (via trigger)."""
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=simple_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Verify FTS5 table has matching row count
    conn = sqlite3.connect(temp_db)
    cursor = conn.execute("SELECT COUNT(*) FROM rules_fts")
    fts_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM rules")
    rules_count = cursor.fetchone()[0]

    assert fts_count == rules_count == 1

    conn.close()


def test_fts5_search_works(
    complex_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """FTS5 keyword search returns correct results."""
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=complex_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Search for "meals" (should match LINE-8523)
    conn = sqlite3.connect(temp_db)
    cursor = conn.execute(
        """
        SELECT r.citation_id
        FROM rules_fts fts
        JOIN rules r ON fts.rowid = r.id
        WHERE rules_fts MATCH 'meals'
        """
    )
    results = [row[0] for row in cursor.fetchall()]
    assert "LINE-8523" in results

    conn.close()


# =============================================================================
# AC6: Vector Table Population
# =============================================================================


def test_vector_table_populated(
    simple_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """Vector table populated with embeddings (384-dim)."""
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=simple_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Verify vector table has matching row count
    conn = sqlite3.connect(temp_db)
    # Load sqlite-vec extension
    try:
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (AttributeError, ImportError):
        pytest.skip("sqlite-vec extension not available")

    cursor = conn.execute("SELECT COUNT(*) FROM rules_vec")
    vec_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM rules")
    rules_count = cursor.fetchone()[0]

    assert vec_count == rules_count == 1

    conn.close()


def test_vector_dimensions_correct(
    simple_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """Vector embeddings have correct dimensions (384-dim for BGE-small)."""
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=simple_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Query vector dimensions
    conn = sqlite3.connect(temp_db)
    # Load sqlite-vec extension
    try:
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (AttributeError, ImportError):
        pytest.skip("sqlite-vec extension not available")

    # Query using chunk_id which is the citation_id
    cursor = conn.execute(
        "SELECT rowid, length(embedding) FROM rules_vec WHERE rowid = (SELECT id FROM rules WHERE citation_id = ?)",
        ("LINE-8523",),
    )
    row = cursor.fetchone()
    assert row is not None

    # Blob length = 384 floats * 4 bytes = 1536 bytes
    _, embedding_blob_size = row
    assert embedding_blob_size == 384 * 4  # 1536 bytes

    conn.close()


# =============================================================================
# Expense Types Table Population
# =============================================================================


def test_expense_types_table_populated(
    complex_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """Expense types table populated from DatabaseChunk.expense_types."""
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=complex_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Verify expense_types table has entries
    conn = sqlite3.connect(temp_db)
    cursor = conn.execute("SELECT COUNT(*) FROM expense_types")
    count = cursor.fetchone()[0]
    assert count > 0

    conn.close()


def test_expense_types_inferred_correctly(
    complex_rule_yaml_path,
    test_source_files,
    temp_db,
    mock_embedding_service,
    tmp_path,
):
    """Expense types correctly inferred from rule content."""
    manifest_path = tmp_path / "manifest.json"

    builder = IndexBuilder(str(temp_db), embedding_service)
    builder.build_index(
        input_path=complex_rule_yaml_path,
        manifest_path=str(manifest_path),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Query expense types for LINE-8523 (Meals and entertainment)
    conn = sqlite3.connect(temp_db)
    cursor = conn.execute(
        """
        SELECT et.name FROM expense_types et
        JOIN rule_expense_type_links link ON et.id = link.expense_type_id
        JOIN rules r ON link.rule_id = r.id
        WHERE r.citation_id = ?
        ORDER BY et.name
        """,
        ("LINE-8523",),
    )
    expense_types = [row[0] for row in cursor.fetchall()]

    # Should include "meals" (keyword match in title/content)
    assert "meals" in expense_types

    conn.close()


# =============================================================================
# Database Constraint Enforcement
# =============================================================================


def test_duplicate_citation_id_rejected(
    simple_rule_yaml_path,
    test_source_files,
    tmp_path,
    mock_embedding_service,
):
    """Database rejects duplicate citation_id (UNIQUE constraint)."""
    # Build database first time
    db_path_1 = tmp_path / "test1.db"
    manifest_path_1 = tmp_path / "manifest1.json"

    builder = IndexBuilder(str(db_path_1), embedding_service)
    builder.build_index(
        input_path=simple_rule_yaml_path,
        manifest_path=str(manifest_path_1),
        source_files=test_source_files,
        data_version="2025.10",
    )

    # Attempt to build again with same data (should fail due to duplicate citation_id)
    # We need to manually try inserting duplicate data since build_index creates a fresh DB
    conn = sqlite3.connect(db_path_1)

    # Try to insert duplicate citation_id directly
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed"):
        conn.execute(
            """
            INSERT INTO rules (
                content, citation_id, source_url, source_hash,
                province, business_type, metadata_json, retrieved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Duplicate content",
                "LINE-8523",  # Duplicate citation_id
                "file://test.html",
                "abc123",
                "[]",
                "[]",
                "{}",
                "2025-10-22T00:00:00Z",
            ),
        )

    conn.close()
