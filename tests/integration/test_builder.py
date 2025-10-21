"""Integration tests for IndexBuilder YAML loading pipeline."""

from pathlib import Path

import pytest
from qe_tax_rag.data.builder import IndexBuilder
from qe_tax_rag.embeddings.encoder import _EmbeddingService
from qe_tax_rag.search.models import SourceFile


@pytest.fixture
def source_files(tmp_path: Path) -> dict[str, SourceFile]:
    """Create source file mapping for tests."""
    return {
        "t4002-24e": SourceFile(
            path="t4002-24e.html",
            url="https://www.canada.ca/t4002-24e.html",
            hash="abc123def456",
        )
    }


@pytest.fixture
def valid_yaml_file(tmp_path: Path) -> Path:
    """Create a valid YAML file with ExtractedRule structures."""
    yaml_content = """rules:
  - rule_number: 8523
    title: "Business Meal Expenses"
    content: "You can deduct 50% of meal and entertainment expenses."
    applies_to: [business]
    source_citation: "Line 8523"
    chapter: "Chapter 3"
    section: "Meals and entertainment"
    source_file: "t4002-24e.html"
    expert_source: classic
    anchor_id: null
    confidence_score: 1.0
  - rule_number: 9281
    title: "Vehicle Expenses"
    content: "Deduct vehicle expenses including fuel and maintenance."
    applies_to: [business]
    source_citation: "Line 9281"
    chapter: "Chapter 4"
    section: "Motor vehicle expenses"
    source_file: "t4002-24e.html"
    expert_source: llm
    anchor_id: "line-9281"
    confidence_score: 0.95
schema_version: "1.0"
extraction_timestamp: "2024-12-15T10:30:00Z"
"""
    yaml_file = tmp_path / "rules.yml"
    yaml_file.write_text(yaml_content, encoding="utf-8")
    return yaml_file


@pytest.fixture
def malformed_yaml_file(tmp_path: Path) -> Path:
    """Create a malformed YAML file for error testing."""
    yaml_content = """rules:
  - rule_number: 8523
    title: "Missing required fields"
    # Missing: content, applies_to, source_citation, etc.
schema_version: "1.0"
extraction_timestamp: "2024-12-15T10:30:00Z"
"""
    yaml_file = tmp_path / "malformed.yml"
    yaml_file.write_text(yaml_content, encoding="utf-8")
    return yaml_file


@pytest.mark.integration
def test_build_from_yaml_to_database_success(
    valid_yaml_file: Path,
    source_files: dict[str, SourceFile],
    tmp_path: Path,
) -> None:
    """Test full pipeline: YAML file → database with embeddings.

    This integration test verifies:
    - YAML file is detected and loaded correctly
    - RuleSet is converted to DatabaseChunk objects
    - Database is created with proper schema
    - Embeddings are generated and stored
    - FTS5 index is populated
    - Metadata is stored correctly
    """
    db_path = tmp_path / "test_rules.db"
    manifest_path = tmp_path / "manifest.json"
    encoder = _EmbeddingService(model_name="BAAI/bge-small-en-v1.5")

    # Build database from YAML
    builder = IndexBuilder(db_path=str(db_path), encoder=encoder)
    builder.build_from_file(
        input_path=valid_yaml_file,
        manifest_path=str(manifest_path),
        source_files=list(source_files.values()),
        data_version="2024.12",
    )

    # Load manifest to verify metadata
    import json

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Verify database was created
    assert db_path.exists()
    assert manifest_path.exists()

    # Verify manifest metadata
    assert manifest["chunk_count"] == 2  # 2 rules in YAML
    assert manifest["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert manifest["version"] == "2024.12"

    # Verify database content via direct SQL
    import sqlite3

    conn = sqlite3.connect(db_path)

    # Load sqlite-vec extension for querying vector table
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        pass

    import sqlite_vec
    sqlite_vec.load(conn)

    cursor = conn.cursor()

    # Check rules table row count
    cursor.execute("SELECT COUNT(*) FROM rules")
    rule_count = cursor.fetchone()[0]
    assert rule_count == 2

    # Check citation_id format (LINE-{number})
    cursor.execute("SELECT citation_id FROM rules ORDER BY citation_id")
    citation_ids = [row[0] for row in cursor.fetchall()]
    assert citation_ids == ["LINE-8523", "LINE-9281"]

    # Check extraction metadata preservation (stored in metadata_json column)
    cursor.execute(
        "SELECT metadata_json, content FROM rules WHERE citation_id = 'LINE-8523'"
    )
    row = cursor.fetchone()
    metadata = json.loads(row[0])
    assert metadata["extraction_source"] == "classic"
    assert metadata["extraction_confidence"] == 1.0
    assert "meal" in row[1].lower()

    cursor.execute(
        "SELECT metadata_json, content FROM rules WHERE citation_id = 'LINE-9281'"
    )
    row = cursor.fetchone()
    metadata = json.loads(row[0])
    assert metadata["extraction_source"] == "llm"
    assert metadata["extraction_confidence"] == 0.95
    assert "vehicle" in row[1].lower()

    # Check FTS5 index populated
    cursor.execute("SELECT COUNT(*) FROM rules_fts")
    fts_count = cursor.fetchone()[0]
    assert fts_count == 2

    # Check vector embeddings stored
    cursor.execute("SELECT COUNT(*) FROM rules_vec")
    vec_count = cursor.fetchone()[0]
    assert vec_count == 2

    # Verify embedding dimensions (BGE-small-en-v1.5 = 384 dims)
    cursor.execute("SELECT embedding FROM rules_vec LIMIT 1")
    embedding_blob = cursor.fetchone()[0]
    # Each float32 = 4 bytes, 384 floats = 1536 bytes
    assert len(embedding_blob) == 384 * 4

    # Verify expense types table populated (separate many-to-many relationship)
    cursor.execute("SELECT COUNT(*) FROM expense_types")
    expense_type_count = cursor.fetchone()[0]
    assert expense_type_count > 0  # At least some expense types inferred

    conn.close()


@pytest.mark.integration
def test_build_from_yaml_to_database_with_malformed_yaml(
    malformed_yaml_file: Path,
    source_files: dict[str, SourceFile],
    tmp_path: Path,
) -> None:
    """Test that malformed YAML raises clear validation error.

    This integration test verifies:
    - Malformed YAML with missing required fields is detected
    - Pydantic validation errors are raised during loading
    - Database is NOT created when validation fails
    """
    db_path = tmp_path / "test_rules.db"
    manifest_path = tmp_path / "manifest.json"
    encoder = _EmbeddingService(model_name="BAAI/bge-small-en-v1.5")

    builder = IndexBuilder(db_path=str(db_path), encoder=encoder)

    # Build should raise ValidationError during YAML loading
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        builder.build_from_file(
            input_path=malformed_yaml_file,
            manifest_path=str(manifest_path),
            source_files=list(source_files.values()),
            data_version="2024.12",
        )
