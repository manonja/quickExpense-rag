"""
Unit tests for IndexBuilder.

Tests User Story 2: Maintainer Indexing Workflow components.

User Story 2: As a library maintainer, I want to build a searchable database
from manually downloaded CRA documents so that users can query up-to-date tax rules.

These unit tests verify individual components of the index building process:
- Chunk loading and flattening from JSONL
- Duplicate citation_id detection
- Expense type population
- Batch embedding with error handling
- Data insertion (rules, vectors, links)
- Integrity checks

Integration test for complete workflow is in tests/integration/test_user_story_2.py
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from quickexpense_rag.data.builder import IndexBuilder
from quickexpense_rag.exceptions import EmbeddingError, QuickExpenseError
from quickexpense_rag.search.models import SourceFile
from scripts.parser.schema import ParsedDocument, Section, TextChunk, Metadata


class TestLoadAndFlattenChunks:
    """Tests for _load_and_flatten_chunks method."""

    def test_load_and_flatten_chunks_from_jsonl(self, tmp_path):
        """
        GIVEN: JSONL file with 3 ParsedDocument objects
        WHEN: _load_and_flatten_chunks is called
        THEN: Returns flat list of chunk dictionaries with all required fields
        """
        # Create test JSONL with 3 documents
        jsonl_path = tmp_path / "test_chunks.jsonl"

        # Create sample documents
        doc1 = ParsedDocument(
            title="Test Document 1",
            document_id="S1-F1-C1",
            metadata=Metadata(
                province=["BC"],
                business_type=["sole_proprietorship"],
                expense_type=["meals"]
            ),
            sections=[
                Section(
                    section_title="Section 1",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content 1",
                            citation_id="S1-F1-C1-p1.1"
                        )
                    ]
                )
            ]
        )

        doc2 = ParsedDocument(
            title="Test Document 2",
            document_id="S1-F1-C2",
            metadata=Metadata(
                province=["ON"],
                business_type=["corporation"],
                expense_type=["travel"]
            ),
            sections=[
                Section(
                    section_title="Section 1",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content 2",
                            citation_id="S1-F1-C2-p1.1"
                        )
                    ]
                )
            ]
        )

        # Write to JSONL
        with open(jsonl_path, "w") as f:
            f.write(doc1.model_dump_json() + "\n")
            f.write(doc2.model_dump_json() + "\n")

        # Create source files mapping
        source_files = [
            SourceFile(
                path="data/raw/S1-F1-C1.html",
                url="https://www.canada.ca/test1",
                hash="hash1",
            ),
            SourceFile(
                path="data/raw/S1-F1-C2.html",
                url="https://www.canada.ca/test2",
                hash="hash2",
            ),
        ]

        # Create builder and call method
        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        chunks = builder._load_and_flatten_chunks(str(jsonl_path), source_files)

        # Assert: returns list of dicts with required fields
        assert len(chunks) == 2
        assert all(isinstance(chunk, dict) for chunk in chunks)

        # Check first chunk has all required fields
        chunk1 = chunks[0]
        assert "citation_id" in chunk1
        assert "content" in chunk1
        assert "expense_types" in chunk1
        assert "source_url" in chunk1
        assert "source_hash" in chunk1

        # Verify content
        assert chunk1["citation_id"] == "S1-F1-C1-p1.1"
        assert "Test content 1" in chunk1["content"]
        assert chunk1["source_url"] == "https://www.canada.ca/test1"
        assert chunk1["source_hash"] == "hash1"

    def test_duplicate_citation_id_detection(self, tmp_path):
        """
        GIVEN: JSONL file with duplicate citation_id
        WHEN: _load_and_flatten_chunks is called
        THEN: Raises ValueError with citation_id in message
        """
        # Create test JSONL with duplicate citation_id
        jsonl_path = tmp_path / "test_chunks.jsonl"

        doc1 = ParsedDocument(
            title="Test Document 1",
            document_id="S1-F1-C1",
            metadata=Metadata(),
            sections=[
                Section(
                    section_title="Section 1",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content 1",
                            citation_id="S1-F1-C1-p1.1"  # Duplicate
                        )
                    ]
                )
            ]
        )

        doc2 = ParsedDocument(
            title="Test Document 2",
            document_id="S1-F1-C2",
            metadata=Metadata(),
            sections=[
                Section(
                    section_title="Section 1",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content 2",
                            citation_id="S1-F1-C1-p1.1"  # Duplicate!
                        )
                    ]
                )
            ]
        )

        with open(jsonl_path, "w") as f:
            f.write(doc1.model_dump_json() + "\n")
            f.write(doc2.model_dump_json() + "\n")

        source_files = [
            SourceFile(
                path="test1.html", url="https://www.canada.ca/test1", hash="hash1"
            ),
            SourceFile(
                path="test2.html", url="https://www.canada.ca/test2", hash="hash2"
            ),
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())

        # Should raise ValueError with citation_id in message
        with pytest.raises(ValueError) as exc_info:
            builder._load_and_flatten_chunks(str(jsonl_path), source_files)

        assert "S1-F1-C1-p1.1" in str(exc_info.value)
        assert "duplicate" in str(exc_info.value).lower()


class TestPopulateExpenseTypes:
    """Tests for _populate_expense_types method."""

    @pytest.fixture
    def in_memory_db(self):
        """Create in-memory SQLite database with schema."""
        conn = sqlite3.connect(":memory:")

        # Create expense_types table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expense_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        yield conn
        conn.close()

    def test_populate_expense_types_creates_table_entries(self, in_memory_db, tmp_path):
        """
        GIVEN: List of chunks with various expense types
        WHEN: _populate_expense_types is called
        THEN: expense_types table populated with unique types, returns name→id map
        """
        # Create chunks with different expense types
        chunks = [
            {"expense_types": ["meals", "travel"]},
            {"expense_types": ["vehicle"]},
            {"expense_types": ["meals", "home_office"]},
            {"expense_types": []},  # Empty expense types
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        expense_type_map = builder._populate_expense_types(in_memory_db, chunks)

        # Verify returned mapping
        assert isinstance(expense_type_map, dict)
        assert "meals" in expense_type_map
        assert "travel" in expense_type_map
        assert "vehicle" in expense_type_map
        assert "home_office" in expense_type_map

        # Verify all values are integers (database IDs)
        assert all(isinstance(v, int) for v in expense_type_map.values())

        # Verify unique IDs
        assert len(set(expense_type_map.values())) == len(expense_type_map)

        # Verify database table was populated
        cursor = in_memory_db.execute("SELECT name FROM expense_types ORDER BY name")
        db_types = [row[0] for row in cursor.fetchall()]
        assert db_types == ["home_office", "meals", "travel", "vehicle"]

    def test_populate_expense_types_handles_empty_chunks(self, in_memory_db, tmp_path):
        """
        GIVEN: Chunks with no expense types
        WHEN: _populate_expense_types is called
        THEN: Returns empty dict without error
        """
        chunks = [
            {"expense_types": []},
            {"expense_types": []},
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        expense_type_map = builder._populate_expense_types(in_memory_db, chunks)

        assert expense_type_map == {}

        # Verify table is empty
        cursor = in_memory_db.execute("SELECT COUNT(*) FROM expense_types")
        count = cursor.fetchone()[0]
        assert count == 0

    def test_populate_expense_types_handles_duplicates_across_chunks(
        self, in_memory_db, tmp_path
    ):
        """
        GIVEN: Multiple chunks with overlapping expense types
        WHEN: _populate_expense_types is called
        THEN: Each unique type inserted only once
        """
        chunks = [
            {"expense_types": ["meals", "travel"]},
            {"expense_types": ["meals"]},  # Duplicate
            {"expense_types": ["travel", "vehicle"]},  # Partial duplicates
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        expense_type_map = builder._populate_expense_types(in_memory_db, chunks)

        # Should have exactly 3 unique types
        assert len(expense_type_map) == 3
        assert set(expense_type_map.keys()) == {"meals", "travel", "vehicle"}

        # Verify database has exactly 3 rows
        cursor = in_memory_db.execute("SELECT COUNT(*) FROM expense_types")
        count = cursor.fetchone()[0]
        assert count == 3
