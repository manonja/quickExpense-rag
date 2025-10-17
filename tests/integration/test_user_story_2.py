"""
Integration test for User Story 2: Maintainer Indexing Workflow.

User Story 2: As a library maintainer, I want to build a searchable database
from manually downloaded CRA documents so that users can query up-to-date tax rules.

Workflow:
1. Manually download CRA HTML/PDF files to data/raw/
2. Run: `uv run python scripts/cli.py pipeline --output-db data/cra_rules_v2024.12.db`
3. Pipeline executes: preprocess → parse → build → validate
4. Produces: versioned database + manifest.json with full provenance
5. Cost: ~$1.59 for 50 documents (Gemini API usage)

This test verifies the complete end-to-end indexing workflow:
1. Create sample JSONL with ParsedDocument objects
2. Call IndexBuilder.build_from_jsonl()
3. Verify database created with correct schema
4. Verify manifest created with provenance metadata
5. Verify data integrity (counts, FTS sync, foreign keys)
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
from qe_tax_rag.data.builder import IndexBuilder
from qe_tax_rag.search.models import SourceFile
from qe_tax_rag.parser.schema import Metadata, ParsedDocument, Section, TextChunk


class TestUserStory2:
    """
    Integration test for User Story 2: Maintainer Indexing Workflow.

    Tests the complete database build process from JSONL to searchable index.
    """

    def test_complete_indexing_workflow(self, tmp_path):
        """
        GIVEN: JSONL file with realistic ParsedDocument objects and source files
        WHEN: Maintainer runs IndexBuilder.build_from_jsonl()
        THEN: Creates versioned database + manifest with full provenance
        """
        # Step 1: Create test JSONL with 3 realistic documents
        jsonl_path = tmp_path / "parsed_docs.jsonl"

        doc1 = ParsedDocument(
            title="Meals and Entertainment Expenses",
            document_id="S3-F2-C1",
            metadata=Metadata(
                province=["BC", "AB"],
                business_type=["sole_proprietorship"],
                expense_type=["meals", "entertainment"],
            ),
            sections=[
                Section(
                    section_title="General Rules",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="You can deduct 50% of meals and entertainment expenses incurred for business purposes.",
                            citation_id="S3-F2-C1-p1.1",
                        ),
                        TextChunk(
                            type="paragraph",
                            text="Long-haul truck drivers may deduct 80% of meal expenses.",
                            citation_id="S3-F2-C1-p1.2",
                        ),
                    ],
                )
            ],
        )

        doc2 = ParsedDocument(
            title="Vehicle Expenses",
            document_id="S3-F2-C2",
            metadata=Metadata(
                province=["ON"],
                business_type=["corporation", "partnership"],
                expense_type=["vehicle", "travel"],
            ),
            sections=[
                Section(
                    section_title="Motor Vehicle Expenses",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="You can deduct motor vehicle expenses if you use your vehicle for business purposes.",
                            citation_id="S3-F2-C2-p1.1",
                        )
                    ],
                )
            ],
        )

        doc3 = ParsedDocument(
            title="Home Office Expenses",
            document_id="S3-F2-C3",
            metadata=Metadata(
                province=["QC"],
                business_type=["sole_proprietorship"],
                expense_type=["home_office"],
            ),
            sections=[
                Section(
                    section_title="Home Office Deduction",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="You can deduct expenses for a workspace in your home if it is your principal place of business.",
                            citation_id="S3-F2-C3-p1.1",
                        )
                    ],
                )
            ],
        )

        with open(jsonl_path, "w") as f:
            f.write(doc1.model_dump_json() + "\n")
            f.write(doc2.model_dump_json() + "\n")
            f.write(doc3.model_dump_json() + "\n")

        # Step 2: Create source files with provenance metadata
        source_files = [
            SourceFile(
                path="data/raw/S3-F2-C1.html",
                url="https://www.canada.ca/en/revenue-agency/services/forms-publications/guide-t4002/chapter-2-meals-entertainment.html",
                hash="abc123",
            ),
            SourceFile(
                path="data/raw/S3-F2-C2.html",
                url="https://www.canada.ca/en/revenue-agency/services/forms-publications/guide-t4002/chapter-4-vehicle.html",
                hash="def456",
            ),
            SourceFile(
                path="data/raw/S3-F2-C3.html",
                url="https://www.canada.ca/en/revenue-agency/services/forms-publications/guide-t4002/chapter-6-home-office.html",
                hash="ghi789",
            ),
        ]

        # Step 3: Create mock encoder (integration test doesn't need real embeddings)
        mock_encoder = Mock()

        # Return realistic-shaped embeddings (batch_size x 384)
        def mock_embed(texts):
            return np.random.rand(len(texts), 384).astype(np.float32)

        mock_encoder.embed_documents.side_effect = mock_embed
        mock_encoder.model_name = "BAAI/bge-small-en-v1.5"

        # Step 4: Run build_from_jsonl (User Story 2 workflow)
        db_path = tmp_path / "cra_rules_v2024.12.db"
        manifest_path = tmp_path / "manifest.json"

        builder = IndexBuilder(db_path=str(db_path), encoder=mock_encoder)
        builder.build_from_jsonl(
            jsonl_path=str(jsonl_path),
            manifest_path=str(manifest_path),
            source_files=source_files,
            data_version="2024.12",
            continue_on_error=False,
        )

        # Step 5: Verify database file created
        assert db_path.exists(), "Database file should be created"

        # Step 6: Verify manifest file created
        assert manifest_path.exists(), "Manifest file should be created"

        # Step 7: Verify database schema and data
        conn = sqlite3.connect(str(db_path))

        # Load sqlite-vec extension for querying
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

        # Check total chunks (2 from doc1, 1 from doc2, 1 from doc3 = 4 total)
        cursor = conn.execute("SELECT COUNT(*) FROM rules")
        rule_count = cursor.fetchone()[0]
        assert rule_count == 4, f"Expected 4 rules (chunks), got {rule_count}"

        # Check unique expense types populated
        cursor = conn.execute("SELECT COUNT(*) FROM expense_types")
        expense_type_count = cursor.fetchone()[0]
        assert (
            expense_type_count == 5
        ), "Expected 5 unique expense types (meals, entertainment, vehicle, travel, home_office)"

        # Verify specific expense types exist
        cursor = conn.execute("SELECT name FROM expense_types ORDER BY name")
        expense_types = [row[0] for row in cursor.fetchall()]
        assert "meals" in expense_types
        assert "vehicle" in expense_types
        assert "home_office" in expense_types

        # Check rules_vec has embeddings for all rules
        cursor = conn.execute("SELECT COUNT(*) FROM rules_vec")
        vec_count = cursor.fetchone()[0]
        assert vec_count == 4, "All rules should have embeddings"

        # Check FTS table synced (via triggers)
        cursor = conn.execute("SELECT COUNT(*) FROM rules_fts")
        fts_count = cursor.fetchone()[0]
        assert fts_count == 4, "FTS table should be synced"

        # Verify FTS search works (join with rules to get citation_id)
        cursor = conn.execute(
            """
            SELECT r.citation_id
            FROM rules_fts f
            JOIN rules r ON f.rowid = r.id
            WHERE f.content MATCH 'truck driver'
            """
        )
        fts_results = cursor.fetchall()
        assert len(fts_results) == 1, "FTS search should find 'truck driver' text"
        assert fts_results[0][0] == "S3-F2-C1-p1.2", "Should match correct citation_id"

        # Check metadata table
        cursor = conn.execute("SELECT value FROM metadata WHERE key = 'data_version'")
        data_version = cursor.fetchone()[0]
        assert data_version == "2024.12", "Data version should match"

        cursor = conn.execute("SELECT value FROM metadata WHERE key = 'schema_version'")
        schema_version = cursor.fetchone()[0]
        assert schema_version == "1.0", "Schema version should be 1.0"

        cursor = conn.execute(
            "SELECT value FROM metadata WHERE key = 'embedding_model'"
        )
        embedding_model = cursor.fetchone()[0]
        assert (
            embedding_model == "BAAI/bge-small-en-v1.5"
        ), "Embedding model should match"

        # Check many-to-many links exist
        cursor = conn.execute("SELECT COUNT(*) FROM rule_expense_type_links")
        link_count = cursor.fetchone()[0]
        # doc1 has 2 chunks × 2 expense types (meals, entertainment) = 4 links
        # doc2 has 1 chunk × 2 expense types (vehicle, travel) = 2 links
        # doc3 has 1 chunk × 1 expense type (home_office) = 1 link
        # Total = 7 links
        assert link_count == 7, f"Expected 7 expense type links, got {link_count}"

        conn.close()

        # Step 8: Verify manifest contents
        with open(manifest_path) as f:
            manifest_data = json.load(f)

        assert manifest_data["version"] == "2024.12", "Manifest version should match"
        assert manifest_data["chunk_count"] == 4, "Manifest chunk count should match"
        assert manifest_data["embedding_model"] == "BAAI/bge-small-en-v1.5"
        assert manifest_data["schema_version"] == "1.0"
        assert "sha256" in manifest_data, "Manifest should include SHA256 hash"
        assert "created_at" in manifest_data, "Manifest should include timestamp"
        assert (
            len(manifest_data["source_files"]) == 3
        ), "Manifest should list all source files"

        # Verify source files have correct structure
        assert manifest_data["source_files"][0]["url"].startswith(
            "https://www.canada.ca"
        )
        assert "hash" in manifest_data["source_files"][0]

    def test_indexing_workflow_with_continue_on_error(self, tmp_path):
        """
        GIVEN: Encoder that fails on some batches
        WHEN: Maintainer runs build with continue_on_error=True
        THEN: Creates partial database with successfully embedded chunks
        """
        # Create test JSONL with 65 chunks (3 batches of 32, 32, 1)
        jsonl_path = tmp_path / "parsed_docs.jsonl"

        docs = []
        for i in range(65):
            doc = ParsedDocument(
                title=f"Test Document {i}",
                document_id=f"S1-F1-C{i}",
                metadata=Metadata(expense_type=["meals"]),
                sections=[
                    Section(
                        section_title="Section 1",
                        section_level=1,
                        content=[
                            TextChunk(
                                type="paragraph",
                                text=f"Test content {i}",
                                citation_id=f"S1-F1-C{i}-p1.1",
                            )
                        ],
                    )
                ],
            )
            docs.append(doc)

        with open(jsonl_path, "w") as f:
            for doc in docs:
                f.write(doc.model_dump_json() + "\n")

        source_files = [
            SourceFile(
                path=f"data/raw/S1-F1-C{i}.html",
                url=f"https://www.canada.ca/test{i}",
                hash=f"hash{i}",
            )
            for i in range(65)
        ]

        # Mock encoder that fails on second batch
        mock_encoder = Mock()
        mock_encoder.embed_documents.side_effect = [
            np.random.rand(32, 384).astype(np.float32),  # Batch 1: success
            Exception("Timeout"),  # Batch 2: failure
            np.random.rand(1, 384).astype(np.float32),  # Batch 3: success
        ]
        mock_encoder.model_name = "BAAI/bge-small-en-v1.5"

        db_path = tmp_path / "cra_rules_partial.db"
        manifest_path = tmp_path / "manifest.json"

        builder = IndexBuilder(db_path=str(db_path), encoder=mock_encoder)
        builder.build_from_jsonl(
            jsonl_path=str(jsonl_path),
            manifest_path=str(manifest_path),
            source_files=source_files,
            data_version="2024.12",
            continue_on_error=True,  # Graceful error handling
        )

        # Verify partial database created
        assert db_path.exists()
        assert manifest_path.exists()

        conn = sqlite3.connect(str(db_path))

        # Load sqlite-vec extension
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

        cursor = conn.execute("SELECT COUNT(*) FROM rules")
        count = cursor.fetchone()[0]
        conn.close()

        # Only batches 1 and 3 succeeded (32 + 1 = 33 chunks)
        assert count == 33, f"Expected 33 chunks (batch 2 failed), got {count}"

        # Verify manifest reflects partial count
        with open(manifest_path) as f:
            manifest_data = json.load(f)
            assert (
                manifest_data["chunk_count"] == 33
            ), "Manifest should reflect actual chunk count"
