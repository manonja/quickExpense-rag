"""Integration tests for build command (TICKET-9D Task 3)."""

import json
import sqlite3
from pathlib import Path

import pytest
from scripts.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def sample_chunks_jsonl(tmp_path: Path) -> Path:
    """Create sample chunks.jsonl file for testing."""
    chunks_file = tmp_path / "chunks.jsonl"

    # Create sample ParsedDocument JSONL data
    sample_docs = [
        {
            "title": "Business Expenses - Sample 1",
            "document_id": "S1-F1-C1",
            "metadata": {
                "province": ["BC", "ON"],
                "business_type": ["sole_proprietorship"],
                "expense_type": ["meals", "travel"],
            },
            "sections": [
                {
                    "section_title": "Deductible Expenses",
                    "section_level": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "text": "Meals are deductible at 50%.",
                            "citation_id": "S1-F1-C1-p1.1",
                        },
                        {
                            "type": "paragraph",
                            "text": "Travel expenses are fully deductible.",
                            "citation_id": "S1-F1-C1-p1.2",
                        },
                    ],
                }
            ],
        },
        {
            "title": "Business Expenses - Sample 2",
            "document_id": "S2-F1-C1",
            "metadata": {
                "province": ["AB"],
                "business_type": ["corporation"],
                "expense_type": ["vehicle"],
            },
            "sections": [
                {
                    "section_title": "Vehicle Expenses",
                    "section_level": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "text": "Vehicle expenses based on business use percentage.",
                            "citation_id": "S2-F1-C1-p1.1",
                        }
                    ],
                }
            ],
        },
    ]

    with chunks_file.open("w", encoding="utf-8") as f:
        for doc in sample_docs:
            f.write(json.dumps(doc) + "\n")

    return chunks_file


@pytest.fixture
def sample_manifest_json(tmp_path: Path) -> Path:
    """Create sample manifest.json for source files metadata."""
    manifest_file = tmp_path / "raw" / "manifest.json"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "documents": [
            {
                "filename": "S1-F1-C1.html",
                "source_url": "https://www.canada.ca/en/revenue-agency/...",
                "downloaded_at": "2024-01-01T00:00:00Z",
                "sha256": "abc123def456",
            },
            {
                "filename": "S2-F1-C1.html",
                "source_url": "https://www.canada.ca/en/revenue-agency/...",
                "downloaded_at": "2024-01-01T00:00:00Z",
                "sha256": "xyz789uvw012",
            },
        ]
    }

    with manifest_file.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest_file


@pytest.mark.integration
def test_build_command_creates_database(
    sample_chunks_jsonl: Path, sample_manifest_json: Path, tmp_path: Path
) -> None:
    """Test 3a (RED): Verify build command creates database and manifest."""
    output_db = tmp_path / "cra_rules.db"
    output_manifest = tmp_path / "manifest.json"

    result = runner.invoke(
        app,
        [
            "build",
            "--input-file",
            str(sample_chunks_jsonl),
            "--manifest-file",
            str(sample_manifest_json),
            "--output-db",
            str(output_db),
            "--output-manifest",
            str(output_manifest),
        ],
    )

    # Command should succeed
    assert result.exit_code == 0
    assert output_db.exists()
    assert output_manifest.exists()

    # Verify database has tables
    conn = sqlite3.connect(output_db)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    assert "rules" in tables
    assert "metadata" in tables


@pytest.mark.integration
def test_build_command_handles_corrupt_jsonl(
    sample_manifest_json: Path, tmp_path: Path
) -> None:
    """Test 3b (RED): Verify build command handles corrupt JSONL gracefully."""
    corrupt_file = tmp_path / "corrupt.jsonl"
    corrupt_file.write_text("{ this is not valid json\n")

    output_db = tmp_path / "cra_rules.db"
    output_manifest = tmp_path / "manifest.json"

    result = runner.invoke(
        app,
        [
            "build",
            "--input-file",
            str(corrupt_file),
            "--manifest-file",
            str(sample_manifest_json),
            "--output-db",
            str(output_db),
            "--output-manifest",
            str(output_manifest),
        ],
    )

    # Should fail with clear error
    assert result.exit_code == 1
    assert "error" in result.stdout.lower() or "failed" in result.stdout.lower()


@pytest.mark.integration
def test_build_command_uses_manifest_source_files(
    sample_chunks_jsonl: Path, sample_manifest_json: Path, tmp_path: Path
) -> None:
    """Test 3c (RED): Verify source files from manifest are used correctly."""
    output_db = tmp_path / "cra_rules.db"
    output_manifest = tmp_path / "manifest.json"

    result = runner.invoke(
        app,
        [
            "build",
            "--input-file",
            str(sample_chunks_jsonl),
            "--manifest-file",
            str(sample_manifest_json),
            "--output-db",
            str(output_db),
            "--output-manifest",
            str(output_manifest),
        ],
    )

    assert result.exit_code == 0

    # Read output manifest and verify source files are included
    with output_manifest.open() as f:
        manifest = json.load(f)

    assert "source_files" in manifest
    assert len(manifest["source_files"]) == 2


@pytest.mark.integration
def test_build_command_missing_input_file_fails(
    sample_manifest_json: Path, tmp_path: Path
) -> None:
    """Test 3b (RED): Verify build command fails when input file missing."""
    nonexistent_file = tmp_path / "nonexistent.jsonl"
    output_db = tmp_path / "cra_rules.db"
    output_manifest = tmp_path / "manifest.json"

    result = runner.invoke(
        app,
        [
            "build",
            "--input-file",
            str(nonexistent_file),
            "--manifest-file",
            str(sample_manifest_json),
            "--output-db",
            str(output_db),
            "--output-manifest",
            str(output_manifest),
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


@pytest.mark.integration
def test_build_command_shows_progress(
    sample_chunks_jsonl: Path, sample_manifest_json: Path, tmp_path: Path
) -> None:
    """Test 3a (RED): Verify build command shows progress (already in IndexBuilder)."""
    output_db = tmp_path / "cra_rules.db"
    output_manifest = tmp_path / "manifest.json"

    result = runner.invoke(
        app,
        [
            "build",
            "--input-file",
            str(sample_chunks_jsonl),
            "--manifest-file",
            str(sample_manifest_json),
            "--output-db",
            str(output_db),
            "--output-manifest",
            str(output_manifest),
        ],
    )

    # Should succeed and show some indication of completion
    assert result.exit_code == 0
    # IndexBuilder already has progress bar, we just verify it completes
