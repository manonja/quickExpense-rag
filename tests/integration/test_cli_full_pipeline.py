"""End-to-end integration test for full CLI pipeline (TICKET-9D Task 6)."""

import json
import sqlite3
from pathlib import Path

import pytest
import sqlite_vec

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture
def sample_cra_html_files(tmp_path: Path) -> Path:
    """Create 3 realistic CRA HTML files for E2E testing."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    # Document 1: Meals and entertainment
    (raw_dir / "S1-F1-C1.html").write_text(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Business Expenses - Meals and Entertainment</title>
        </head>
        <body>
            <h1>Deductible Business Expenses: Meals and Entertainment</h1>

            <h2>General Rules</h2>
            <p>You can deduct meals and entertainment expenses incurred for
            business purposes. However, these expenses are generally limited
            to 50% of the amount paid.</p>

            <h2>Eligible Expenses</h2>
            <ul>
                <li>Meals with clients or customers</li>
                <li>Meals while traveling for business</li>
                <li>Entertainment expenses for business promotion</li>
            </ul>

            <h2>Record Keeping</h2>
            <p>You must keep detailed receipts showing the date, amount,
            location, and business purpose of the expense.</p>

            <p>Province: All provinces. Business type: All types.
            Expense type: meals, entertainment.</p>
        </body>
        </html>
        """,
        encoding="utf-8",
    )

    # Document 2: Vehicle expenses
    (raw_dir / "S2-F1-C1.html").write_text(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Business Expenses - Vehicle</title>
        </head>
        <body>
            <h1>Vehicle Expenses for Business Use</h1>

            <h2>Deductibility Rules</h2>
            <p>You can deduct vehicle expenses based on the percentage of
            business use. Track all kilometers driven for business purposes.</p>

            <h2>Allowable Expenses</h2>
            <ul>
                <li>Fuel and oil</li>
                <li>Insurance</li>
                <li>License and registration fees</li>
                <li>Maintenance and repairs</li>
                <li>Lease payments or depreciation</li>
            </ul>

            <h2>Documentation Requirements</h2>
            <p>Maintain a detailed logbook showing business kilometers versus
            total kilometers driven. This is required to calculate the business
            use percentage.</p>

            <p>Province: BC, ON, AB. Business type: sole_proprietorship,
            corporation. Expense type: vehicle.</p>
        </body>
        </html>
        """,
        encoding="utf-8",
    )

    # Document 3: Home office expenses
    (raw_dir / "S3-F1-C1.html").write_text(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Business Expenses - Home Office</title>
        </head>
        <body>
            <h1>Home Office Expense Deductions</h1>

            <h2>Eligibility Criteria</h2>
            <p>You can claim home office expenses if your workspace meets
            one of these conditions:</p>
            <ol>
                <li>The space is your principal place of business, or</li>
                <li>You use the space only to earn business income and use
                it on a regular basis for meeting clients or customers</li>
            </ol>

            <h2>Deductible Expenses</h2>
            <p>Calculate expenses based on the percentage of your home used
            for business:</p>
            <ul>
                <li>Rent or mortgage interest</li>
                <li>Property taxes</li>
                <li>Utilities (heat, electricity, water)</li>
                <li>Home insurance</li>
                <li>Maintenance and repairs</li>
            </ul>

            <h2>Calculation Method</h2>
            <p>Divide the area of your workspace by the total area of your
            home to determine the business-use percentage.</p>

            <p>Province: All provinces. Business type: sole_proprietorship.
            Expense type: home_office.</p>
        </body>
        </html>
        """,
        encoding="utf-8",
    )

    return raw_dir


def test_full_pipeline_e2e(
    sample_cra_html_files: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test 6a (E2E): Full pipeline from 3 HTML files to validated searchable database.

    This test verifies the complete workflow:
    1. Preprocess: 3 HTML → 3 TXT files + manifest
    2. Parse: 3 TXT → chunks.jsonl (skipped - requires real API key)
    3. Build: chunks.jsonl → SQLite database
    4. Validate: Database passes smoke tests
    5. Search: Database is queryable

    Note: This test creates a database manually (skipping parse step) because
    parsing requires a real GEMINI_API_KEY. In production, parse would be run
    with a valid API key.
    """
    # Set up directories
    preprocessed_dir = tmp_path / "preprocessed"
    processed_dir = tmp_path / "processed"
    output_db = tmp_path / "cra_rules.db"
    output_manifest = tmp_path / "manifest.json"

    # ============================================================================
    # Stage 1: Preprocess (run via CLI)
    # ============================================================================
    from scripts.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "preprocess",
            "--input-dir",
            str(sample_cra_html_files),
            "--output-dir",
            str(preprocessed_dir),
        ],
    )

    assert result.exit_code == 0, f"Preprocess failed: {result.stdout}"
    assert preprocessed_dir.exists()
    assert len(list(preprocessed_dir.glob("*.txt"))) == 3
    assert (sample_cra_html_files / "manifest.json").exists()

    # ============================================================================
    # Stage 2: Parse (create mock JSONL - requires real API key in production)
    # ============================================================================
    # In production, this would be:
    # result = runner.invoke(app, ["parse", "--input-dir", str(preprocessed_dir), ...])
    #
    # For testing, we create a mock JSONL file with ParsedDocument structure
    processed_dir.mkdir(parents=True, exist_ok=True)
    chunks_file = processed_dir / "chunks.jsonl"

    # Create 3 realistic ParsedDocument objects
    mock_documents = [
        {
            "title": "Business Expenses - Meals and Entertainment",
            "document_id": "S1-F1-C1",
            "metadata": {
                "province": ["ALL"],
                "business_type": ["ALL"],
                "expense_type": ["meals", "entertainment"],
            },
            "sections": [
                {
                    "section_title": "General Rules",
                    "section_level": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "text": (
                                "You can deduct meals and entertainment expenses "
                                "incurred for business purposes. However, these "
                                "expenses are generally limited to 50% of the amount paid."
                            ),
                            "citation_id": "S1-F1-C1-p1.1",
                        }
                    ],
                },
                {
                    "section_title": "Record Keeping",
                    "section_level": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "text": (
                                "You must keep detailed receipts showing the date, "
                                "amount, location, and business purpose of the expense."
                            ),
                            "citation_id": "S1-F1-C1-p2.1",
                        }
                    ],
                },
            ],
        },
        {
            "title": "Vehicle Expenses for Business Use",
            "document_id": "S2-F1-C1",
            "metadata": {
                "province": ["BC", "ON", "AB"],
                "business_type": ["sole_proprietorship", "corporation"],
                "expense_type": ["vehicle"],
            },
            "sections": [
                {
                    "section_title": "Deductibility Rules",
                    "section_level": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "text": (
                                "You can deduct vehicle expenses based on the percentage "
                                "of business use. Track all kilometers driven for business purposes."
                            ),
                            "citation_id": "S2-F1-C1-p1.1",
                        }
                    ],
                },
            ],
        },
        {
            "title": "Home Office Expense Deductions",
            "document_id": "S3-F1-C1",
            "metadata": {
                "province": ["ALL"],
                "business_type": ["sole_proprietorship"],
                "expense_type": ["home_office"],
            },
            "sections": [
                {
                    "section_title": "Eligibility Criteria",
                    "section_level": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "text": (
                                "You can claim home office expenses if your workspace "
                                "is your principal place of business."
                            ),
                            "citation_id": "S3-F1-C1-p1.1",
                        }
                    ],
                },
                {
                    "section_title": "Calculation Method",
                    "section_level": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "text": (
                                "Divide the area of your workspace by the total area "
                                "of your home to determine the business-use percentage."
                            ),
                            "citation_id": "S3-F1-C1-p2.1",
                        }
                    ],
                },
            ],
        },
    ]

    with chunks_file.open("w", encoding="utf-8") as f:
        for doc in mock_documents:
            f.write(json.dumps(doc) + "\n")

    assert chunks_file.exists()

    # ============================================================================
    # Stage 3: Build (run via CLI)
    # ============================================================================
    result = runner.invoke(
        app,
        [
            "build",
            "--input-file",
            str(chunks_file),
            "--manifest-file",
            str(sample_cra_html_files / "manifest.json"),
            "--output-db",
            str(output_db),
            "--output-manifest",
            str(output_manifest),
            "--data-version",
            "2024.12",
        ],
    )

    assert result.exit_code == 0, f"Build failed: {result.stdout}"
    assert output_db.exists()
    assert output_manifest.exists()

    # ============================================================================
    # Stage 4: Validate database structure and content
    # ============================================================================

    # Verify database schema
    conn = sqlite3.connect(output_db)

    # Load sqlite-vec
    try:
        conn.enable_load_extension(True)
    except AttributeError:
        pass

    sqlite_vec.load(conn)

    try:
        conn.enable_load_extension(False)
    except AttributeError:
        pass

    # Check tables exist
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert "rules" in tables
    assert "rules_fts" in tables
    assert "rules_vec" in tables
    assert "metadata" in tables
    assert "expense_types" in tables

    # Check row counts (should have entries from flattened sections)
    rules_count = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
    assert rules_count > 0, "Database should have rules"

    # Verify metadata
    cursor = conn.execute("SELECT key, value FROM metadata")
    metadata_dict = {row[0]: row[1] for row in cursor.fetchall()}
    assert metadata_dict["schema_version"] == "1.0"
    assert metadata_dict["data_version"] == "2024.12"
    assert metadata_dict["embedding_model"] == "BAAI/bge-small-en-v1.5"

    # Verify embeddings exist and have correct dimensions
    cursor = conn.execute("SELECT embedding FROM rules_vec LIMIT 1")
    row = cursor.fetchone()
    assert row is not None, "Should have at least one embedding"

    import numpy as np

    embedding = np.frombuffer(row[0], dtype=np.float32)
    assert len(embedding) == 384, "BGE embeddings should be 384-dimensional"

    # Verify FTS5 search works
    cursor = conn.execute(
        "SELECT COUNT(*) FROM rules_fts WHERE content MATCH 'business'"
    )
    fts_matches = cursor.fetchone()[0]
    assert fts_matches > 0, "FTS5 search should find 'business'"

    # Verify expense types
    cursor = conn.execute("SELECT name FROM expense_types ORDER BY name")
    expense_types = {row[0] for row in cursor.fetchall()}
    assert "meals" in expense_types
    assert "vehicle" in expense_types
    assert "home_office" in expense_types

    conn.close()

    # ============================================================================
    # Stage 5: Validate via CLI
    # ============================================================================
    result = runner.invoke(
        app,
        [
            "validate",
            "--db-path",
            str(output_db),
        ],
    )

    assert result.exit_code == 0, f"Validation failed: {result.stdout}"
    assert "✅" in result.stdout or "passed" in result.stdout.lower()

    # ============================================================================
    # Stage 6: Verify manifest output
    # ============================================================================
    with output_manifest.open() as f:
        manifest = json.load(f)

    assert "schema_version" in manifest
    assert "version" in manifest  # Data version is called 'version' in manifest
    assert manifest["version"] == "2024.12"
    assert "source_files" in manifest
    assert len(manifest["source_files"]) == 3

    # ============================================================================
    # Success: E2E test passed
    # ============================================================================
    # At this point we have verified:
    # ✅ HTML files preprocessed to text
    # ✅ Text parsed to structured JSONL (mocked, but structure validated)
    # ✅ Database built with FTS5 and vector indexes
    # ✅ Embeddings generated with correct dimensions
    # ✅ Metadata stored correctly
    # ✅ Expense types tracked
    # ✅ Validation passes
    # ✅ Manifest created with source file provenance
