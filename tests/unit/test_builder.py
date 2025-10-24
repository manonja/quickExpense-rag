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
from qe_tax_rag.data.builder import IndexBuilder
from qe_tax_rag.data.models import DatabaseChunk
from qe_tax_rag.exceptions import EmbeddingError, QeTaxRagError
from qe_tax_rag.parser.schema import Metadata, ParsedDocument, Section, TextChunk
from qe_tax_rag.search.models import SourceFile


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
                expense_type=["meals"],
            ),
            sections=[
                Section(
                    section_title="Section 1",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content 1",
                            citation_id="S1-F1-C1-p1.1",
                        )
                    ],
                )
            ],
        )

        doc2 = ParsedDocument(
            title="Test Document 2",
            document_id="S1-F1-C2",
            metadata=Metadata(
                province=["ON"], business_type=["corporation"], expense_type=["travel"]
            ),
            sections=[
                Section(
                    section_title="Section 1",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content 2",
                            citation_id="S1-F1-C2-p1.1",
                        )
                    ],
                )
            ],
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
                            citation_id="S1-F1-C1-p1.1",  # Duplicate
                        )
                    ],
                )
            ],
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
                            citation_id="S1-F1-C1-p1.1",  # Duplicate!
                        )
                    ],
                )
            ],
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


class TestEmbedChunksInBatches:
    """Tests for _embed_chunks_in_batches method."""

    def test_embed_chunks_in_batches_with_mock_encoder(self, tmp_path):
        """
        GIVEN: 100 chunks and mocked encoder
        WHEN: _embed_chunks_in_batches is called
        THEN: Returns list of (chunk, embedding) tuples, processes in batches of 32
        """
        # Create 100 test chunks
        chunks = [
            {"content": f"Test content {i}", "citation_id": f"S1-F1-C1-p{i}"}
            for i in range(100)
        ]

        # Mock encoder that returns fake embeddings
        mock_encoder = Mock()
        mock_encoder.embed_documents.return_value = np.random.rand(32, 384).astype(
            np.float32
        )

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=mock_encoder)
        results = builder._embed_chunks_in_batches(chunks, continue_on_error=False)

        # Verify results
        assert len(results) == 100
        assert all(isinstance(item, tuple) for item in results)
        assert all(len(item) == 2 for item in results)

        # Verify first result structure
        chunk, embedding = results[0]
        assert isinstance(chunk, dict)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32

        # Verify encoder called 4 times (100 chunks / 32 batch_size = 3.125 → 4 batches)
        # Batches: 32, 32, 32, 4
        assert mock_encoder.embed_documents.call_count == 4

    def test_embed_chunks_continue_on_error_true(self, tmp_path):
        """
        GIVEN: Encoder that fails on batch 2
        WHEN: _embed_chunks_in_batches called with continue_on_error=True
        THEN: Logs error, skips failed batch, returns partial results
        """
        # Create 96 chunks (3 batches of 32)
        chunks = [
            {"content": f"Test content {i}", "citation_id": f"S1-F1-C1-p{i}"}
            for i in range(96)
        ]

        # Mock encoder that fails on second call
        mock_encoder = Mock()
        mock_encoder.embed_documents.side_effect = [
            np.random.rand(32, 384).astype(np.float32),  # Batch 1: success
            Exception("Embedding service timeout"),  # Batch 2: failure
            np.random.rand(32, 384).astype(np.float32),  # Batch 3: success
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=mock_encoder)

        # Should not raise exception, returns partial results
        results = builder._embed_chunks_in_batches(chunks, continue_on_error=True)

        # Only batches 1 and 3 succeeded (64 chunks total)
        assert len(results) == 64

        # Verify all results have correct structure
        for chunk, embedding in results:
            assert isinstance(chunk, dict)
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (384,)

    def test_embed_chunks_continue_on_error_false(self, tmp_path):
        """
        GIVEN: Encoder that fails on batch 2
        WHEN: _embed_chunks_in_batches called with continue_on_error=False
        THEN: Raises EmbeddingError
        """
        # Create 96 chunks
        chunks = [
            {"content": f"Test content {i}", "citation_id": f"S1-F1-C1-p{i}"}
            for i in range(96)
        ]

        # Mock encoder that fails on second call
        mock_encoder = Mock()
        mock_encoder.embed_documents.side_effect = [
            np.random.rand(32, 384).astype(np.float32),  # Batch 1: success
            Exception("Embedding service timeout"),  # Batch 2: failure
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=mock_encoder)

        # Should raise EmbeddingError
        with pytest.raises(EmbeddingError) as exc_info:
            builder._embed_chunks_in_batches(chunks, continue_on_error=False)

        assert "Embedding failed" in str(exc_info.value)

    def test_embed_chunks_batch_size_boundary(self, tmp_path):
        """
        GIVEN: Exactly 32 chunks (one batch)
        WHEN: _embed_chunks_in_batches is called
        THEN: Encoder called exactly once
        """
        chunks = [
            {"content": f"Test {i}", "citation_id": f"S1-F1-C1-p{i}"} for i in range(32)
        ]

        mock_encoder = Mock()
        mock_encoder.embed_documents.return_value = np.random.rand(32, 384).astype(
            np.float32
        )

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=mock_encoder)
        results = builder._embed_chunks_in_batches(chunks, continue_on_error=False)

        assert len(results) == 32
        assert mock_encoder.embed_documents.call_count == 1


class TestInsertData:
    """Tests for _insert_data method."""

    @pytest.fixture
    def in_memory_db_with_schema(self):
        """Create in-memory SQLite database with full schema."""
        conn = sqlite3.connect(":memory:")

        # Create all required tables
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                citation_id TEXT UNIQUE NOT NULL,
                source_url TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                province TEXT,
                business_type TEXT,
                metadata_json TEXT,
                retrieved_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
                content,
                content='rules',
                content_rowid='id',
                tokenize='porter unicode61'
            );

            -- Simplified for unit tests (vec0 extension not loaded)
            CREATE TABLE IF NOT EXISTS rules_vec (
                id INTEGER PRIMARY KEY,
                embedding BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS expense_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rule_expense_type_links (
                rule_id INTEGER NOT NULL,
                expense_type_id INTEGER NOT NULL,
                PRIMARY KEY (rule_id, expense_type_id),
                FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE,
                FOREIGN KEY (expense_type_id) REFERENCES expense_types(id) ON DELETE CASCADE
            );

            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS rules_ai AFTER INSERT ON rules BEGIN
                INSERT INTO rules_fts(rowid, content) VALUES (new.id, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS rules_ad AFTER DELETE ON rules BEGIN
                DELETE FROM rules_fts WHERE rowid = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS rules_au AFTER UPDATE ON rules BEGIN
                UPDATE rules_fts SET content = new.content WHERE rowid = new.id;
            END;
        """)

        yield conn
        conn.close()

    def test_insert_data_three_statement_pattern(
        self, in_memory_db_with_schema, tmp_path
    ):
        """
        GIVEN: List of (chunk, embedding) tuples
        WHEN: _insert_data is called
        THEN: rules, rules_vec, rule_expense_type_links all populated correctly
        """
        # Populate expense_types table first
        in_memory_db_with_schema.execute(
            "INSERT INTO expense_types (name) VALUES ('meals')"
        )
        in_memory_db_with_schema.execute(
            "INSERT INTO expense_types (name) VALUES ('travel')"
        )
        expense_type_map = {"meals": 1, "travel": 2}

        # Create embedded chunks
        embedded_chunks = [
            (
                {
                    "content": "Test content 1",
                    "citation_id": "S1-F1-C1-p1.1",
                    "source_url": "https://www.canada.ca/test1",
                    "source_hash": "hash1",
                    "expense_types": ["meals"],
                    "province": ["BC"],
                    "business_type": ["sole_proprietorship"],
                },
                np.random.rand(384).astype(np.float32),
            ),
            (
                {
                    "content": "Test content 2",
                    "citation_id": "S1-F1-C1-p1.2",
                    "source_url": "https://www.canada.ca/test2",
                    "source_hash": "hash2",
                    "expense_types": ["travel"],
                    "province": ["ON"],
                    "business_type": ["corporation"],
                },
                np.random.rand(384).astype(np.float32),
            ),
        ]

        source_files = [
            SourceFile(
                path="test1.html", url="https://www.canada.ca/test1", hash="hash1"
            ),
            SourceFile(
                path="test2.html", url="https://www.canada.ca/test2", hash="hash2"
            ),
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        builder._insert_data(
            in_memory_db_with_schema, embedded_chunks, expense_type_map, source_files
        )

        # Verify rules table
        cursor = in_memory_db_with_schema.execute("SELECT COUNT(*) FROM rules")
        assert cursor.fetchone()[0] == 2

        # Verify rules_vec table
        cursor = in_memory_db_with_schema.execute("SELECT COUNT(*) FROM rules_vec")
        assert cursor.fetchone()[0] == 2

        # Verify rule_expense_type_links table
        cursor = in_memory_db_with_schema.execute(
            "SELECT COUNT(*) FROM rule_expense_type_links"
        )
        assert cursor.fetchone()[0] == 2

    def test_insert_data_multiple_expense_types_creates_multiple_links(
        self, in_memory_db_with_schema, tmp_path
    ):
        """
        GIVEN: Chunk with expense_types=['meals', 'travel']
        WHEN: _insert_data is called
        THEN: Two rows created in rule_expense_type_links
        """
        # Populate expense_types
        in_memory_db_with_schema.execute(
            "INSERT INTO expense_types (name) VALUES ('meals')"
        )
        in_memory_db_with_schema.execute(
            "INSERT INTO expense_types (name) VALUES ('travel')"
        )
        expense_type_map = {"meals": 1, "travel": 2}

        # Chunk with multiple expense types
        embedded_chunks = [
            (
                {
                    "content": "Test content",
                    "citation_id": "S1-F1-C1-p1.1",
                    "source_url": "https://www.canada.ca/test",
                    "source_hash": "hash1",
                    "expense_types": ["meals", "travel"],  # Multiple types
                    "province": ["BC"],
                    "business_type": ["sole_proprietorship"],
                },
                np.random.rand(384).astype(np.float32),
            )
        ]

        source_files = [
            SourceFile(path="test.html", url="https://www.canada.ca/test", hash="hash1")
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        builder._insert_data(
            in_memory_db_with_schema, embedded_chunks, expense_type_map, source_files
        )

        # Verify 2 links created for the single rule
        cursor = in_memory_db_with_schema.execute(
            "SELECT COUNT(*) FROM rule_expense_type_links"
        )
        assert cursor.fetchone()[0] == 2

        # Verify both expense types linked to rule id 1
        cursor = in_memory_db_with_schema.execute(
            "SELECT expense_type_id FROM rule_expense_type_links WHERE rule_id = 1 ORDER BY expense_type_id"
        )
        expense_type_ids = [row[0] for row in cursor.fetchall()]
        assert expense_type_ids == [1, 2]

    def test_fts_triggers_populate_rules_fts(self, in_memory_db_with_schema, tmp_path):
        """
        GIVEN: Rules inserted via _insert_data
        WHEN: Query rules_fts table
        THEN: FTS index contains searchable content (triggers worked)
        """
        # Populate expense_types
        in_memory_db_with_schema.execute(
            "INSERT INTO expense_types (name) VALUES ('meals')"
        )
        expense_type_map = {"meals": 1}

        embedded_chunks = [
            (
                {
                    "content": "Restaurant meal deduction rules",
                    "citation_id": "S1-F1-C1-p1.1",
                    "source_url": "https://www.canada.ca/test",
                    "source_hash": "hash1",
                    "expense_types": ["meals"],
                    "province": ["BC"],
                    "business_type": ["sole_proprietorship"],
                },
                np.random.rand(384).astype(np.float32),
            )
        ]

        source_files = [
            SourceFile(path="test.html", url="https://www.canada.ca/test", hash="hash1")
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        builder._insert_data(
            in_memory_db_with_schema, embedded_chunks, expense_type_map, source_files
        )

        # Search FTS index
        cursor = in_memory_db_with_schema.execute(
            "SELECT content FROM rules_fts WHERE rules_fts MATCH 'restaurant'"
        )
        results = cursor.fetchall()
        assert len(results) == 1
        assert "Restaurant meal" in results[0][0]


class TestIntegrityChecks:
    """Tests for _run_integrity_checks method."""

    @pytest.fixture
    def in_memory_db_with_data(self):
        """Create in-memory database with schema and test data."""
        conn = sqlite3.connect(":memory:")

        # Create schema
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                citation_id TEXT UNIQUE NOT NULL,
                source_url TEXT NOT NULL,
                source_hash TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
                content,
                content='rules',
                content_rowid='id'
            );

            CREATE TABLE IF NOT EXISTS rules_vec (
                id INTEGER PRIMARY KEY,
                embedding BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS expense_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rule_expense_type_links (
                rule_id INTEGER NOT NULL,
                expense_type_id INTEGER NOT NULL,
                PRIMARY KEY (rule_id, expense_type_id),
                FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE,
                FOREIGN KEY (expense_type_id) REFERENCES expense_types(id) ON DELETE CASCADE
            );

            -- FTS trigger
            CREATE TRIGGER rules_ai AFTER INSERT ON rules BEGIN
                INSERT INTO rules_fts(rowid, content) VALUES (new.id, new.content);
            END;
        """)

        # Insert 10 test rules
        for i in range(1, 11):
            conn.execute(
                "INSERT INTO rules (content, citation_id, source_url, source_hash) VALUES (?, ?, ?, ?)",
                (
                    f"Content {i}",
                    f"S1-F1-C1-p{i}",
                    "https://www.canada.ca/test",
                    "hash",
                ),
            )
            conn.execute(
                "INSERT INTO rules_vec (id, embedding) VALUES (?, ?)",
                (i, np.random.rand(384).astype(np.float32).tobytes()),
            )

        # Insert expense types and links
        conn.execute("INSERT INTO expense_types (name) VALUES ('meals')")
        conn.execute("INSERT INTO expense_types (name) VALUES ('travel')")
        for i in range(1, 11):
            conn.execute(
                "INSERT INTO rule_expense_type_links (rule_id, expense_type_id) VALUES (?, ?)",
                (i, 1),  # All rules linked to 'meals'
            )

        yield conn
        conn.close()

    def test_integrity_checks_all_tables_match_count(
        self, in_memory_db_with_data, tmp_path
    ):
        """
        GIVEN: Database with 10 rules inserted
        WHEN: _run_integrity_checks called with expected_count=10
        THEN: Passes without error (all tables have 10 rows)
        """
        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())

        # Should not raise any exception
        builder._run_integrity_checks(in_memory_db_with_data, expected_count=10)

    def test_integrity_checks_fails_on_rules_count_mismatch(
        self, in_memory_db_with_data, tmp_path
    ):
        """
        GIVEN: Database with 10 rules but expected_count=8
        WHEN: _run_integrity_checks called
        THEN: Raises QeTaxRagError with clear message
        """
        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())

        with pytest.raises(QeTaxRagError) as exc_info:
            builder._run_integrity_checks(in_memory_db_with_data, expected_count=8)

        assert "rules" in str(exc_info.value).lower()
        assert "10" in str(exc_info.value)  # Actual count
        assert "8" in str(exc_info.value)  # Expected count

    def test_integrity_checks_fails_on_vec_count_mismatch(
        self, in_memory_db_with_data, tmp_path
    ):
        """
        GIVEN: Database with 10 rules but only 9 vectors
        WHEN: _run_integrity_checks called with expected_count=10
        THEN: Raises QeTaxRagError
        """
        # Delete one vector to create mismatch
        in_memory_db_with_data.execute("DELETE FROM rules_vec WHERE id = 10")

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())

        with pytest.raises(QeTaxRagError) as exc_info:
            builder._run_integrity_checks(in_memory_db_with_data, expected_count=10)

        assert "rules_vec" in str(exc_info.value).lower()
        assert "9" in str(exc_info.value)

    def test_integrity_checks_detects_dangling_foreign_keys(
        self, in_memory_db_with_data, tmp_path
    ):
        """
        GIVEN: Database with dangling rule_id in rule_expense_type_links
        WHEN: _run_integrity_checks called
        THEN: Raises QeTaxRagError about dangling references
        """
        # Insert a link to non-existent rule
        in_memory_db_with_data.execute("PRAGMA foreign_keys = OFF")
        in_memory_db_with_data.execute(
            "INSERT INTO rule_expense_type_links (rule_id, expense_type_id) VALUES (999, 1)"
        )
        in_memory_db_with_data.execute("PRAGMA foreign_keys = ON")

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())

        with pytest.raises(QeTaxRagError) as exc_info:
            builder._run_integrity_checks(in_memory_db_with_data, expected_count=10)

        assert "dangling" in str(exc_info.value).lower()

    def test_integrity_checks_verifies_fts_sync(self, in_memory_db_with_data, tmp_path):
        """
        GIVEN: Database with 10 rules and FTS table
        WHEN: _run_integrity_checks called
        THEN: Verifies FTS table has matching count
        """
        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())

        # Should pass - FTS table auto-synced via triggers
        builder._run_integrity_checks(in_memory_db_with_data, expected_count=10)

        # Verify FTS actually has 10 rows
        cursor = in_memory_db_with_data.execute("SELECT COUNT(*) FROM rules_fts")
        count = cursor.fetchone()[0]
        assert count == 10


class TestYAMLFormatDetection:
    """Tests for YAML format auto-detection in build_index."""

    @pytest.mark.unit
    def test_build_index_detects_yaml_format(self, tmp_path: Path) -> None:
        """Test that .yml files are detected and routed to YAML loader."""
        yaml_file = tmp_path / "rules.yml"
        # Valid RuleSet YAML with minimal rule
        yaml_content = """
rules:
  - rule_number: 8523
    title: "Test Rule"
    content: "Test content for YAML format detection"
    applies_to: [business]
    source_citation: "Line 8523"
    chapter: "Chapter 3"
    section: null
    source_file: "test.html"
    expert_source: classic
    anchor_id: null
    confidence_score: 1.0
schema_version: "1.0"
extraction_timestamp: "2024-12-15T10:30:00Z"
"""
        yaml_file.write_text(yaml_content)

        db_path = tmp_path / "test.db"
        manifest_path = tmp_path / "manifest.json"

        # Mock encoder
        mock_encoder = Mock()
        mock_encoder.embed_documents.return_value = np.random.rand(1, 384).astype(
            np.float32
        )
        mock_encoder.model_name = "BAAI/bge-small-en-v1.5"

        # Source file for the rule
        source_files = [
            SourceFile(path="test.html", url="https://test.ca", hash="abc123")
        ]

        builder = IndexBuilder(db_path=str(db_path), encoder=mock_encoder)

        # Should not raise "Unknown file format" error
        # YAML should be detected and processed successfully
        builder.build_index(
            input_path=yaml_file,
            manifest_path=str(manifest_path),
            source_files=source_files,
            data_version="2024.12",
        )

        # Verify database was created
        assert db_path.exists()

        # Verify manifest was created
        assert manifest_path.exists()

    @pytest.mark.unit
    def test_build_index_detects_jsonl_format(self, tmp_path: Path) -> None:
        """Test that .jsonl files are detected and routed to JSONL loader."""
        # Create minimal valid JSONL with one ParsedDocument
        jsonl_file = tmp_path / "chunks.jsonl"

        doc = ParsedDocument(
            title="Test",
            document_id="S1-F1-C1",
            metadata=Metadata(),
            sections=[
                Section(
                    section_title="Test Section",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content",
                            citation_id="S1-F1-C1-p1.1",
                        )
                    ],
                )
            ],
        )

        jsonl_file.write_text(doc.model_dump_json() + "\n")

        db_path = tmp_path / "test.db"
        manifest_path = tmp_path / "manifest.json"

        # Mock encoder
        mock_encoder = Mock()
        mock_encoder.embed_documents.return_value = np.random.rand(1, 384).astype(
            np.float32
        )
        mock_encoder.model_name = "BAAI/bge-small-en-v1.5"

        source_files = [
            SourceFile(path="S1-F1-C1.html", url="https://test.ca", hash="abc123")
        ]

        builder = IndexBuilder(db_path=str(db_path), encoder=mock_encoder)

        # Should call _load_from_jsonl() internally
        builder.build_index(
            input_path=jsonl_file,
            manifest_path=str(manifest_path),
            source_files=source_files,
            data_version="2024.12",
        )

        # Verify database was created
        assert db_path.exists()

        # Verify one chunk was inserted
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM rules")
        assert cursor.fetchone()[0] == 1
        conn.close()

    @pytest.mark.unit
    def test_build_index_raises_on_unknown_format(self, tmp_path: Path) -> None:
        """Test that unsupported file formats raise clear error."""
        txt_file = tmp_path / "data.txt"
        txt_file.write_text("invalid")

        db_path = tmp_path / "test.db"
        manifest_path = tmp_path / "manifest.json"

        # Mock encoder with model_name
        mock_encoder = Mock()
        mock_encoder.model_name = "BAAI/bge-small-en-v1.5"

        builder = IndexBuilder(db_path=str(db_path), encoder=mock_encoder)

        with pytest.raises(ValueError, match="Unsupported input format"):
            builder.build_index(
                input_path=txt_file,
                manifest_path=str(manifest_path),
                source_files=[],
                data_version="2024.12",
            )


class TestLoadFromYAML:
    """Tests for _load_from_yaml method."""

    @pytest.mark.unit
    def test_load_from_yaml_valid_file(self, tmp_path: Path) -> None:
        """Test loading valid YAML file with RuleSet structure."""
        yaml_content = """
rules:
  - rule_number: 8523
    title: "Test Rule"
    content: "Test content with meal expenses"
    applies_to: [business]
    source_citation: "Line 8523"
    chapter: "Chapter 3"
    section: null
    source_file: "t4002-24e.html"
    expert_source: classic
    anchor_id: null
    confidence_score: 1.0
schema_version: "1.0"
extraction_timestamp: "2024-12-15T10:30:00Z"
"""
        yaml_file = tmp_path / "rules.yml"
        yaml_file.write_text(yaml_content)

        # Source files mapping
        source_files = [
            SourceFile(path="t4002-24e.html", url="https://test.ca", hash="abc123")
        ]

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        chunks = builder._load_from_yaml(yaml_file, source_files)

        assert len(chunks) > 0
        assert all(isinstance(chunk, DatabaseChunk) for chunk in chunks)
        assert chunks[0].citation_id == "LINE-8523"

    @pytest.mark.unit
    def test_load_from_yaml_empty_rules(self, tmp_path: Path) -> None:
        """Test loading YAML with empty rules list."""
        yaml_content = """
rules: []
schema_version: "1.0"
extraction_timestamp: "2024-12-15T10:30:00Z"
"""
        yaml_file = tmp_path / "empty.yml"
        yaml_file.write_text(yaml_content)

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())
        chunks = builder._load_from_yaml(yaml_file, [])

        assert chunks == []

    @pytest.mark.unit
    def test_load_from_yaml_invalid_schema(self, tmp_path: Path) -> None:
        """Test that invalid YAML schema raises validation error."""
        yaml_file = tmp_path / "invalid.yml"
        yaml_file.write_text("invalid: yaml")

        builder = IndexBuilder(db_path=str(tmp_path / "test.db"), encoder=Mock())

        # Should raise validation error (pydantic or KeyError)
        with pytest.raises(Exception):  # ValidationError or KeyError
            builder._load_from_yaml(yaml_file, [])


class TestBuildIndex:
    """
    Tests for build_index orchestration method.

    User Story 2: As a library maintainer, I want to build a searchable database
    from manually downloaded CRA documents so that users can query up-to-date tax rules.

    This method orchestrates the complete build process:
    1. Setup database schema
    2. Load and flatten chunks
    3. Populate expense types
    4. Embed chunks in batches
    5. Insert data
    6. Run integrity checks
    7. Optimize database
    8. Create manifest
    """

    def test_build_index_jsonl_complete_workflow(self, tmp_path):
        """
        GIVEN: Valid JSONL file with ParsedDocuments and source files
        WHEN: build_index is called
        THEN: Creates database, populates tables, validates integrity, creates manifest
        """
        # Create test JSONL with 2 documents
        jsonl_path = tmp_path / "test_chunks.jsonl"

        doc1 = ParsedDocument(
            title="Test Document 1",
            document_id="S1-F1-C1",
            metadata=Metadata(
                province=["BC"],
                business_type=["sole_proprietorship"],
                expense_type=["meals"],
            ),
            sections=[
                Section(
                    section_title="Section 1",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content 1",
                            citation_id="S1-F1-C1-p1.1",
                        )
                    ],
                )
            ],
        )

        doc2 = ParsedDocument(
            title="Test Document 2",
            document_id="S1-F1-C2",
            metadata=Metadata(
                province=["ON"],
                business_type=["corporation"],
                expense_type=["travel"],
            ),
            sections=[
                Section(
                    section_title="Section 2",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content 2",
                            citation_id="S1-F1-C2-p1.1",
                        )
                    ],
                ),
            ],
        )

        with open(jsonl_path, "w") as f:
            f.write(doc1.model_dump_json() + "\n")
            f.write(doc2.model_dump_json() + "\n")

        # Create source files
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

        # Mock encoder
        mock_encoder = Mock()
        mock_encoder.embed_documents.return_value = np.random.rand(2, 384).astype(
            np.float32
        )
        mock_encoder.model_name = "BAAI/bge-small-en-v1.5"

        # Create builder and run build
        db_path = tmp_path / "test.db"
        manifest_path = tmp_path / "manifest.json"

        builder = IndexBuilder(db_path=str(db_path), encoder=mock_encoder)
        builder.build_index(
            input_path=jsonl_path,
            manifest_path=str(manifest_path),
            source_files=source_files,
            data_version="2024.12",
        )

        # Verify database file created
        assert db_path.exists()

        # Verify manifest file created
        assert manifest_path.exists()

        # Verify database contents
        conn = sqlite3.connect(str(db_path))

        # Load sqlite-vec extension for querying vec0 table
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

        # Check rules count
        cursor = conn.execute("SELECT COUNT(*) FROM rules")
        assert cursor.fetchone()[0] == 2

        # Check expense types populated
        cursor = conn.execute("SELECT COUNT(*) FROM expense_types")
        assert cursor.fetchone()[0] == 2

        # Check vectors inserted
        cursor = conn.execute("SELECT COUNT(*) FROM rules_vec")
        assert cursor.fetchone()[0] == 2

        # Check FTS synced
        cursor = conn.execute("SELECT COUNT(*) FROM rules_fts")
        assert cursor.fetchone()[0] == 2

        # Check metadata table (key-value pairs)
        cursor = conn.execute("SELECT value FROM metadata WHERE key = 'data_version'")
        assert cursor.fetchone()[0] == "2024.12"

        conn.close()

        # Verify manifest contents
        with open(manifest_path) as f:
            manifest_data = json.load(f)
            assert manifest_data["version"] == "2024.12"
            assert manifest_data["chunk_count"] == 2
            assert "sha256" in manifest_data
            assert manifest_data["embedding_model"] == "BAAI/bge-small-en-v1.5"

    def test_build_index_atomic_rollback_on_error(self, tmp_path):
        """
        GIVEN: Encoder that fails during embedding
        WHEN: build_index called with JSONL input
        THEN: Transaction rolls back, database file not created or empty
        """
        # Create test JSONL
        jsonl_path = tmp_path / "test_chunks.jsonl"

        doc = ParsedDocument(
            title="Test Document",
            document_id="S1-F1-C1",
            metadata=Metadata(),
            sections=[
                Section(
                    section_title="Section 1",
                    section_level=1,
                    content=[
                        TextChunk(
                            type="paragraph",
                            text="Test content",
                            citation_id="S1-F1-C1-p1.1",
                        )
                    ],
                )
            ],
        )

        with open(jsonl_path, "w") as f:
            f.write(doc.model_dump_json() + "\n")

        source_files = [
            SourceFile(path="test.html", url="https://www.canada.ca/test", hash="hash1")
        ]

        # Mock encoder that fails
        mock_encoder = Mock()
        mock_encoder.embed_documents.side_effect = Exception("Embedding service down")
        mock_encoder.model_name = "BAAI/bge-small-en-v1.5"

        db_path = tmp_path / "test.db"
        manifest_path = tmp_path / "manifest.json"

        builder = IndexBuilder(db_path=str(db_path), encoder=mock_encoder)

        # Should raise EmbeddingError
        with pytest.raises(EmbeddingError):
            builder.build_index(
                input_path=jsonl_path,
                manifest_path=str(manifest_path),
                source_files=source_files,
                data_version="2024.12",
            )

        # Database file may exist (schema created) but no data should be inserted
        # The rollback prevents data from being committed
        if db_path.exists():
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

            # Check that rules table has no rows (rollback worked)
            cursor = conn.execute("SELECT COUNT(*) FROM rules")
            rule_count = cursor.fetchone()[0]
            conn.close()
            assert (
                rule_count == 0
            ), "Transaction should have rolled back, no rules should be inserted"

        # Manifest should not be created
        assert not manifest_path.exists()

    def test_build_index_continue_on_error_creates_partial_database(self, tmp_path):
        """
        GIVEN: Encoder that fails on some batches
        WHEN: build_index called with JSONL input and continue_on_error=True
        THEN: Creates database with successfully embedded chunks only
        """
        # Create test JSONL with 64 chunks (2 batches of 32)
        jsonl_path = tmp_path / "test_chunks.jsonl"

        docs = []
        for i in range(64):
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
            for i in range(64)
        ]

        # Mock encoder that fails on second batch
        mock_encoder = Mock()
        mock_encoder.embed_documents.side_effect = [
            np.random.rand(32, 384).astype(np.float32),  # Batch 1: success
            Exception("Timeout"),  # Batch 2: failure
        ]
        mock_encoder.model_name = "BAAI/bge-small-en-v1.5"

        db_path = tmp_path / "test.db"
        manifest_path = tmp_path / "manifest.json"

        builder = IndexBuilder(db_path=str(db_path), encoder=mock_encoder)
        builder.build_index(
            input_path=jsonl_path,
            manifest_path=str(manifest_path),
            source_files=source_files,
            data_version="2024.12",
            continue_on_error=True,
        )

        # Database created with partial data
        assert db_path.exists()

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

        # Only first batch (32 chunks) should be inserted
        assert count == 32

        # Manifest should reflect partial count
        with open(manifest_path) as f:
            manifest_data = json.load(f)
            assert manifest_data["chunk_count"] == 32
