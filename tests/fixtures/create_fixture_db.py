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
from pathlib import Path

import numpy as np

# Import schema from source (TICKET 2 dependency)
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from quickexpense_rag.data.schema import (
    CREATE_TABLES_SQL,
    SCHEMA_VERSION,
    init_metadata,
    optimize_database,
)

# Reproducible seed for deterministic embeddings
RANDOM_SEED = 42
EMBEDDING_DIM = 384


def generate_deterministic_embeddings(num_rows: int, seed: int = RANDOM_SEED) -> np.ndarray:
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
    conn.executescript(CREATE_TABLES_SQL)

    # Define synthetic test data
    # Coverage: 4 provinces, 3 business types, 4 expense types
    test_rules = [
        # Province: BC
        (
            1,
            "BC sole proprietorship meals deduction test case",
            "TEST-BC-001",
            "https://canada.ca/test/bc-meals",
            "hash_bc_001",
            "BC",
            "sole_proprietorship",
            "meals",
            "{}",
            "2024-01-01T00:00:00Z",
        ),
        (
            2,
            "BC corporation travel expense test case",
            "TEST-BC-002",
            "https://canada.ca/test/bc-travel",
            "hash_bc_002",
            "BC",
            "corporation",
            "travel",
            "{}",
            "2024-01-02T00:00:00Z",
        ),
        # Province: AB
        (
            3,
            "Alberta partnership vehicle expense test case",
            "TEST-AB-001",
            "https://canada.ca/test/ab-vehicle",
            "hash_ab_001",
            "AB",
            "partnership",
            "vehicle",
            "{}",
            "2024-01-03T00:00:00Z",
        ),
        (
            4,
            "Alberta sole proprietorship home office test case",
            "TEST-AB-002",
            "https://canada.ca/test/ab-home",
            "hash_ab_002",
            "AB",
            "sole_proprietorship",
            "home_office",
            "{}",
            "2024-01-04T00:00:00Z",
        ),
        # Province: ON
        (
            5,
            "Ontario corporation meals expense test case",
            "TEST-ON-001",
            "https://canada.ca/test/on-meals",
            "hash_on_001",
            "ON",
            "corporation",
            "meals",
            "{}",
            "2024-01-05T00:00:00Z",
        ),
        (
            6,
            "Ontario partnership travel deduction test case",
            "TEST-ON-002",
            "https://canada.ca/test/on-travel",
            "hash_on_002",
            "ON",
            "partnership",
            "travel",
            "{}",
            "2024-01-06T00:00:00Z",
        ),
        # Province: QC
        (
            7,
            "Quebec sole proprietorship vehicle test case",
            "TEST-QC-001",
            "https://canada.ca/test/qc-vehicle",
            "hash_qc_001",
            "QC",
            "sole_proprietorship",
            "vehicle",
            "{}",
            "2024-01-07T00:00:00Z",
        ),
        (
            8,
            "Quebec corporation home office deduction test case",
            "TEST-QC-002",
            "https://canada.ca/test/qc-home",
            "hash_qc_002",
            "QC",
            "corporation",
            "home_office",
            "{}",
            "2024-01-08T00:00:00Z",
        ),
        # Additional rows for keyword search testing
        (
            9,
            "T2125 form keyword search test case for BC",
            "TEST-KW-001",
            "https://canada.ca/test/keyword-t2125",
            "hash_kw_001",
            "BC",
            "sole_proprietorship",
            "meals",
            "{}",
            "2024-01-09T00:00:00Z",
        ),
        (
            10,
            "Restaurant dining expense entertainment test case",
            "TEST-KW-002",
            "https://canada.ca/test/keyword-restaurant",
            "hash_kw_002",
            "ON",
            "corporation",
            "meals",
            "{}",
            "2024-01-10T00:00:00Z",
        ),
        # Edge cases
        (
            11,
            "Test case with NULL province for filtering edge cases",
            "TEST-EDGE-001",
            "https://canada.ca/test/edge-null",
            "hash_edge_001",
            None,
            "corporation",
            "travel",
            "{}",
            "2024-01-11T00:00:00Z",
        ),
        (
            12,
            "Test case with NULL business type for filtering edge cases",
            "TEST-EDGE-002",
            "https://canada.ca/test/edge-null-biz",
            "hash_edge_002",
            "BC",
            None,
            "vehicle",
            "{}",
            "2024-01-12T00:00:00Z",
        ),
    ]

    num_rows = len(test_rules)

    # Insert test data into rules table
    conn.executemany(
        """
        INSERT INTO rules (
            id, content, citation_id, source_url, source_hash,
            province, business_type, expense_type, metadata_json, retrieved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        test_rules,
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
