"""
Create reproducible test fixture database with deterministic synthetic data.

This script generates tests/fixtures/test_database.db with:
- Synthetic test data (not realistic CRA content)
- Deterministic embeddings (seeded random, no ML model dependency)
- Coverage across provinces, business types, and expense types

Run this script when the schema changes to regenerate the fixture:
    uv run python tests/fixtures/create_fixture_db.py

The generated database is tracked with Git LFS to avoid repository bloat.
"""

import sqlite3

# Import schema from source (TICKET 2 dependency)
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from quickexpense_rag.data.schema import (
    CREATE_TABLES_SQL,
    SCHEMA_VERSION,
    init_metadata,
    optimize_database,
)
from quickexpense_rag.search.enums import ExpenseType

# Reproducible seed for deterministic embeddings
RANDOM_SEED = 42
EMBEDDING_DIM = 384


def generate_deterministic_embeddings(
    num_rows: int, seed: int = RANDOM_SEED
) -> np.ndarray:
    """
    Generate deterministic embeddings using seeded random.

    These vectors are NOT semantically meaningful but have the correct
    dimensions and properties for testing search logic.

    Args:
        num_rows: Number of embedding vectors to generate
        seed: Random seed for reproducibility

    Returns:
        Array of shape (num_rows, 384) with L2-normalized vectors

    """
    rng = np.random.default_rng(seed)
    embeddings = rng.standard_normal((num_rows, EMBEDDING_DIM), dtype=np.float32)

    # Normalize to unit vectors (like real embeddings)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / norms


def create_fixture_database(output_path: Path) -> None:
    """
    Create reproducible test database with deterministic synthetic data.

    Args:
        output_path: Path to output SQLite database file

    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if output_path.exists():
        output_path.unlink()

    # Connect and initialize schema
    conn = sqlite3.connect(output_path)

    # Load sqlite-vec extension
    conn.enable_load_extension(True)
    import sqlite_vec

    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    conn.executescript(CREATE_TABLES_SQL)

    # Define synthetic test data with many-to-many expense types
    # Coverage: 4 provinces, 3 business types, multiple expense type combinations
    test_rules = [
        # Province: BC - Single and multiple expense types
        {
            "content": "BC sole proprietorship meals deduction test case",
            "citation_id": "TEST-BC-001",
            "source_url": "https://canada.ca/test/bc-meals",
            "source_hash": "hash_bc_001",
            "province": "BC",
            "business_type": "sole_proprietorship",
            "expense_types": ["meals"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-01T00:00:00Z",
        },
        {
            "content": "BC corporation travel and meals expense test case",
            "citation_id": "TEST-BC-002",
            "source_url": "https://canada.ca/test/bc-travel-meals",
            "source_hash": "hash_bc_002",
            "province": "BC",
            "business_type": "corporation",
            "expense_types": ["travel", "meals"],  # Multiple types
            "metadata_json": "{}",
            "retrieved_at": "2024-01-02T00:00:00Z",
        },
        # Province: AB
        {
            "content": "Alberta partnership vehicle expense test case",
            "citation_id": "TEST-AB-001",
            "source_url": "https://canada.ca/test/ab-vehicle",
            "source_hash": "hash_ab_001",
            "province": "AB",
            "business_type": "partnership",
            "expense_types": ["vehicle", "travel"],  # Multiple types
            "metadata_json": "{}",
            "retrieved_at": "2024-01-03T00:00:00Z",
        },
        {
            "content": "Alberta sole proprietorship home office test case",
            "citation_id": "TEST-AB-002",
            "source_url": "https://canada.ca/test/ab-home",
            "source_hash": "hash_ab_002",
            "province": "AB",
            "business_type": "sole_proprietorship",
            "expense_types": ["home_office"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-04T00:00:00Z",
        },
        # Province: ON
        {
            "content": "Ontario corporation meals expense test case",
            "citation_id": "TEST-ON-001",
            "source_url": "https://canada.ca/test/on-meals",
            "source_hash": "hash_on_001",
            "province": "ON",
            "business_type": "corporation",
            "expense_types": ["meals"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-05T00:00:00Z",
        },
        {
            "content": "Ontario partnership travel deduction test case",
            "citation_id": "TEST-ON-002",
            "source_url": "https://canada.ca/test/on-travel",
            "source_hash": "hash_on_002",
            "province": "ON",
            "business_type": "partnership",
            "expense_types": ["travel"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-06T00:00:00Z",
        },
        # Province: QC
        {
            "content": "Quebec sole proprietorship vehicle test case",
            "citation_id": "TEST-QC-001",
            "source_url": "https://canada.ca/test/qc-vehicle",
            "source_hash": "hash_qc_001",
            "province": "QC",
            "business_type": "sole_proprietorship",
            "expense_types": ["vehicle"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-07T00:00:00Z",
        },
        {
            "content": "Quebec corporation home office and utilities deduction test case",
            "citation_id": "TEST-QC-002",
            "source_url": "https://canada.ca/test/qc-home",
            "source_hash": "hash_qc_002",
            "province": "QC",
            "business_type": "corporation",
            "expense_types": ["home_office", "utilities"],  # Multiple types
            "metadata_json": "{}",
            "retrieved_at": "2024-01-08T00:00:00Z",
        },
        # Additional rows for keyword search testing
        {
            "content": "T2125 form keyword search test case for BC",
            "citation_id": "TEST-KW-001",
            "source_url": "https://canada.ca/test/keyword-t2125",
            "source_hash": "hash_kw_001",
            "province": "BC",
            "business_type": "sole_proprietorship",
            "expense_types": ["meals"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-09T00:00:00Z",
        },
        {
            "content": "Restaurant dining expense entertainment test case",
            "citation_id": "TEST-KW-002",
            "source_url": "https://canada.ca/test/keyword-restaurant",
            "source_hash": "hash_kw_002",
            "province": "ON",
            "business_type": "corporation",
            "expense_types": ["meals"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-10T00:00:00Z",
        },
        # Edge cases
        {
            "content": "Test case with NULL province for filtering edge cases",
            "citation_id": "TEST-EDGE-001",
            "source_url": "https://canada.ca/test/edge-null",
            "source_hash": "hash_edge_001",
            "province": None,
            "business_type": "corporation",
            "expense_types": ["travel"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-11T00:00:00Z",
        },
        {
            "content": "Test case with NULL business type for filtering edge cases",
            "citation_id": "TEST-EDGE-002",
            "source_url": "https://canada.ca/test/edge-null-biz",
            "source_hash": "hash_edge_002",
            "province": "BC",
            "business_type": None,
            "expense_types": ["vehicle"],
            "metadata_json": "{}",
            "retrieved_at": "2024-01-12T00:00:00Z",
        },
    ]

    num_rows = len(test_rules)

    # Populate expense_types table with canonical list
    expense_type_values = ExpenseType.all_values()
    conn.executemany(
        "INSERT INTO expense_types (name) VALUES (?)",
        [(name,) for name in expense_type_values],
    )

    # Create mapping from expense type name to ID
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM expense_types")
    expense_type_id_map = {name: id_ for id_, name in cursor.fetchall()}

    # Insert rules and their expense type links
    for rule in test_rules:
        # Insert into rules table (without expense_type column)
        cursor.execute(
            """
            INSERT INTO rules (
                content, citation_id, source_url, source_hash,
                province, business_type, metadata_json, retrieved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule["content"],
                rule["citation_id"],
                rule["source_url"],
                rule["source_hash"],
                rule["province"],
                rule["business_type"],
                rule["metadata_json"],
                rule["retrieved_at"],
            ),
        )

        # Get the auto-generated rule ID
        rule_id = cursor.lastrowid

        # Insert links to expense_types for this rule
        for expense_type_name in rule["expense_types"]:
            expense_type_id = expense_type_id_map[expense_type_name]
            cursor.execute(
                """
                INSERT INTO rule_expense_type_links (rule_id, expense_type_id)
                VALUES (?, ?)
                """,
                (rule_id, expense_type_id),
            )

    # Generate deterministic embeddings
    embeddings = generate_deterministic_embeddings(num_rows)

    # Insert embeddings into vector table
    for row_id, embedding in enumerate(embeddings, start=1):
        conn.execute(
            "INSERT INTO rules_vec (rowid, embedding) VALUES (?, ?)",
            (row_id, embedding.tobytes()),
        )

    # Initialize metadata
    init_metadata(
        conn,
        data_version="fixture-v1",
        embedding_model="deterministic-random-seeded",
    )

    # Optimize database
    optimize_database(conn)

    conn.commit()
    conn.close()

    print(f"Created fixture database at {output_path}")
    print(f"  Rows: {num_rows}")
    print(f"  Embeddings: {num_rows} x {EMBEDDING_DIM} (deterministic)")
    print(f"  Schema version: {SCHEMA_VERSION}")
    print(f"  Data version: fixture-v1")


if __name__ == "__main__":
    output_path = Path(__file__).parent / "test_database.db"
    create_fixture_database(output_path)
