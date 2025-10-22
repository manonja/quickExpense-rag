"""
Index builder for QuickExpense RAG.

Implements User Story 2: Maintainer Indexing Workflow

This module provides the IndexBuilder class that orchestrates building a searchable
index from document chunks:
1. Loads chunks from YAML (extraction pipeline) or JSONL (Gemini parser)
2. Generates BGE embeddings in batches
3. Populates SQLite with rules, FTS index, vector embeddings, expense type links
4. Validates integrity and generates manifest with SHA256 hash

The build process is transactional (atomic) - either fully succeeds or rolls back.
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import numpy.typing as npt
from tqdm import tqdm

from qe_tax_rag.data.models import DatabaseChunk
from qe_tax_rag.data.schema import CREATE_TABLES_SQL, init_metadata, optimize_database
from qe_tax_rag.embeddings.encoder import _EmbeddingService
from qe_tax_rag.exceptions import EmbeddingError, QeTaxRagError
from qe_tax_rag.parser.schema import ParsedDocument
from qe_tax_rag.search.models import IndexManifest, SourceFile

logger = logging.getLogger(__name__)


class IndexBuilder:
    """
    Builds searchable SQLite index from CRA document chunks.

    Implements User Story 2: Maintainer Indexing Workflow

    This class orchestrates building a searchable index from document chunks:
    1. Loads chunks from YAML (extraction pipeline) or JSONL (Gemini parser)
    2. Generates BGE embeddings in batches
    3. Populates SQLite with rules, FTS index, vector embeddings, expense type links
    4. Validates integrity and generates manifest with SHA256 hash

    The build process is transactional (atomic) - either fully succeeds or rolls back.
    Supports graceful error handling for embedding failures via continue_on_error flag.

    Example:
        >>> from qe_tax_rag.embeddings.encoder import embedding_service
        >>> builder = IndexBuilder(db_path="cra_rules.db", encoder=embedding_service)
        >>> builder.build_index(
        ...     input_path="rules.yml",
        ...     manifest_path="manifest.json",
        ...     source_files=[SourceFile(...)],
        ...     data_version="2024.12",
        ... )

    """

    def __init__(self, db_path: str, encoder: _EmbeddingService):
        """
        Initialize IndexBuilder.

        Args:
            db_path: Path to the SQLite database file to be created
            encoder: An instance of _EmbeddingService for generating embeddings

        """
        self.db_path = Path(db_path)
        self.encoder = encoder

    def build_index(
        self,
        input_path: str | Path,
        manifest_path: str,
        source_files: list[SourceFile],
        data_version: str,
        continue_on_error: bool = False,
    ) -> None:
        """
        Build searchable index from YAML or JSONL chunks file.

        Auto-detects format based on file extension (.yml, .yaml, .jsonl).

        Args:
            input_path: Path to YAML or JSONL file with rules/documents
            manifest_path: Where to write manifest.json
            source_files: List of SourceFile models with hash/URL metadata
            data_version: Version string (YYYY.MM format)
            continue_on_error: If True, skip chunks with embedding errors

        Raises:
            ValueError: Duplicate citation_id found or unsupported format
            EmbeddingError: Embedding generation failed (if continue_on_error=False)
            sqlite3.IntegrityError: Database constraint violation

        """
        input_path = Path(input_path)
        logger.info(f"Starting index build: {input_path} → {self.db_path}")
        logger.info(
            f"Data version: {data_version}, continue_on_error: {continue_on_error}"
        )

        # Create database connection
        conn = sqlite3.connect(str(self.db_path))

        try:
            # Phase 1: Setup database schema and metadata
            logger.info("Phase 1: Setting up database schema...")
            self._setup_database(conn, data_version)

            # Phase 2: Load and flatten chunks (auto-detects YAML vs JSONL)
            logger.info("Phase 2: Loading and flattening chunks...")
            chunks = self._load_and_flatten_chunks(input_path, source_files)

            # Phase 3: Populate expense types table
            logger.info("Phase 3: Populating expense types...")
            expense_type_map = self._populate_expense_types(conn, chunks)

            # Phase 4: Generate embeddings in batches
            logger.info("Phase 4: Generating embeddings...")
            embedded_chunks = self._embed_chunks_in_batches(chunks, continue_on_error)

            # Phase 5: Insert data into database (within transaction)
            logger.info("Phase 5: Inserting data...")
            self._insert_data(conn, embedded_chunks, expense_type_map, source_files)

            # Phase 6: Run integrity checks
            logger.info("Phase 6: Running integrity checks...")
            self._run_integrity_checks(conn, expected_count=len(embedded_chunks))

            # Phase 7: Optimize database
            logger.info("Phase 7: Optimizing database...")
            optimize_database(conn)

            # Commit transaction
            conn.commit()
            logger.info("Database build complete, transaction committed")

        except Exception as e:
            # Rollback on any error
            conn.rollback()
            logger.error(f"Build failed, rolling back: {e}")
            raise

        finally:
            conn.close()

        # Phase 8: Calculate database hash and create manifest
        logger.info("Phase 8: Creating manifest...")
        db_hash = self._calculate_file_hash(self.db_path)
        self._create_manifest(
            manifest_path=manifest_path,
            db_hash=db_hash,
            chunk_count=len(embedded_chunks),
            source_files=tuple(source_files),
            data_version=data_version,
        )

        logger.info(f"Index build complete: {len(embedded_chunks)} chunks indexed")

    def _setup_database(self, conn: sqlite3.Connection, data_version: str) -> None:
        """
        Initialize database schema and metadata.

        Args:
            conn: SQLite connection
            data_version: Version string to store in metadata table

        """
        # Load sqlite-vec extension before creating tables
        try:
            conn.enable_load_extension(True)
        except AttributeError:
            # Extension loading not supported in this build
            pass

        import sqlite_vec

        sqlite_vec.load(conn)

        try:
            conn.enable_load_extension(False)
        except AttributeError:
            pass

        # Create all tables, indexes, and triggers
        conn.executescript(CREATE_TABLES_SQL)

        # Initialize metadata table with version info
        init_metadata(conn, data_version, self.encoder.model_name)

        logger.info("Database schema initialized")

    def _load_and_flatten_chunks(
        self, input_path: Path, source_files: list[SourceFile]
    ) -> list[DatabaseChunk]:
        """
        Load chunks from YAML (extraction pipeline) or JSONL (Gemini parser).

        Auto-detects format and returns unified DatabaseChunk list.

        Args:
            input_path: Path to YAML or JSONL file
            source_files: List of SourceFile metadata

        Returns:
            List of DatabaseChunk objects ready for embedding and insertion

        Raises:
            ValueError: If duplicate citation_id detected or unsupported format

        """
        if input_path.suffix in [".yml", ".yaml"]:
            # Extraction pipeline: YAML → DatabaseChunk
            chunks = self._load_from_yaml(input_path, source_files)
        elif input_path.suffix == ".jsonl":
            # Gemini parser: JSONL → DatabaseChunk
            chunks = self._load_from_jsonl(input_path, source_files)
        else:
            raise ValueError(
                f"Unsupported input format: {input_path.suffix}. "
                f"Expected .yml, .yaml, or .jsonl"
            )

        # Check for duplicate citation_ids across all chunks
        seen_citations: set[str] = set()
        for chunk in chunks:
            if chunk.citation_id in seen_citations:
                raise ValueError(
                    f"Duplicate citation_id found: {chunk.citation_id}. "
                    "Each citation_id must be unique across all documents."
                )
            seen_citations.add(chunk.citation_id)

        logger.info(f"Loaded {len(chunks)} chunks from {input_path}")
        return chunks

    def _load_from_yaml(
        self, yaml_path: Path, source_files: list[SourceFile]
    ) -> list[DatabaseChunk]:
        """
        Load extraction pipeline YAML and convert to DatabaseChunk.

        Args:
            yaml_path: Path to YAML file with RuleSet
            source_files: List of SourceFile metadata

        Returns:
            List of DatabaseChunk objects

        """
        import yaml

        from qe_tax_rag.extraction.ca.schema import RuleSet

        logger.info(f"Loading extraction YAML: {yaml_path}")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        ruleset = RuleSet.model_validate(data)

        # Create filename stem → SourceFile mapping
        source_map = {Path(sf.path).stem: sf for sf in source_files}

        return ruleset.to_database_chunks(source_map)

    def _load_from_jsonl(
        self, jsonl_path: Path, source_files: list[SourceFile]
    ) -> list[DatabaseChunk]:
        """
        Load Gemini parser JSONL and convert to DatabaseChunk.

        Args:
            jsonl_path: Path to JSONL file with ParsedDocument objects
            source_files: List of SourceFile metadata

        Returns:
            List of DatabaseChunk objects

        """
        logger.info(f"Loading JSONL: {jsonl_path}")

        chunks: list[DatabaseChunk] = []

        with open(jsonl_path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    doc = ParsedDocument.model_validate_json(line)
                    chunks.extend(doc.to_database_chunks(source_files))
                except Exception as e:
                    logger.error(f"Failed to parse line {line_num}: {e}")
                    raise

        return chunks

    def _populate_expense_types(
        self, conn: sqlite3.Connection, chunks: list[DatabaseChunk]
    ) -> dict[str, int]:
        """
        Identify unique expense types, populate table, return name-to-ID map.

        Extracts all unique expense types from chunks, inserts them into the
        expense_types table, and returns a mapping of expense type names to
        their auto-incremented database IDs for use in junction table inserts.

        Args:
            conn: SQLite connection
            chunks: List of DatabaseChunk objects

        Returns:
            Dictionary mapping expense type name (str) to database ID (int)

        """
        # Collect unique expense types from all chunks
        expense_types: set[str] = set()
        for chunk in chunks:
            if chunk.expense_types:
                expense_types.update(chunk.expense_types)

        # If no expense types found, return empty dict
        if not expense_types:
            logger.info("No expense types found in chunks")
            return {}

        # Insert expense types into table (sorted for deterministic order)
        for expense_type in sorted(expense_types):
            conn.execute("INSERT INTO expense_types (name) VALUES (?)", (expense_type,))

        # Query back to get name→id mapping
        cursor = conn.execute("SELECT id, name FROM expense_types")
        expense_type_map = {name: id for id, name in cursor.fetchall()}

        logger.info(f"Populated {len(expense_type_map)} unique expense types")
        return expense_type_map

    def _embed_chunks_in_batches(
        self, chunks: list[DatabaseChunk], continue_on_error: bool
    ) -> list[tuple[DatabaseChunk, npt.NDArray[np.float32]]]:
        """
        Generate embeddings for all chunks in batches with progress bar.

        Processes chunks in batches of 32, calling encoder.embed_documents() for
        each batch. Shows progress bar with tqdm. Handles errors according to
        continue_on_error flag.

        Args:
            chunks: List of DatabaseChunk objects
            continue_on_error: If True, log errors and skip failed batches;
                             if False, raise EmbeddingError on first failure

        Returns:
            List of (DatabaseChunk, embedding_vector) tuples for successfully
            embedded chunks

        Raises:
            EmbeddingError: If embedding fails and continue_on_error=False

        """
        if not chunks:
            return []

        # Extract content texts for embedding
        texts = [chunk.content for chunk in chunks]
        results: list[tuple[DatabaseChunk, npt.NDArray[np.float32]]] = []

        # Process in batches of 32
        batch_size = 32
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for i in tqdm(
            range(0, len(texts), batch_size),
            desc="Embedding chunks",
            total=total_batches,
            unit="batch",
        ):
            batch_texts = texts[i : i + batch_size]
            batch_chunks = chunks[i : i + batch_size]

            try:
                # Generate embeddings for this batch
                embeddings = self.encoder.embed_documents(batch_texts)

                # Pair chunks with their embeddings
                for chunk, embedding in zip(batch_chunks, embeddings, strict=False):
                    results.append((chunk, embedding))

            except Exception as e:
                if continue_on_error:
                    logger.error(
                        f"Embedding failed for batch {i // batch_size + 1}/{total_batches}: {e}"
                    )
                    logger.info(f"Skipping {len(batch_texts)} chunks due to error")
                    continue
                else:
                    raise EmbeddingError(
                        f"Embedding failed for batch {i // batch_size + 1}: {e}"
                    ) from e

        logger.info(f"Successfully embedded {len(results)}/{len(chunks)} chunks")
        return results

    def _insert_data(
        self,
        conn: sqlite3.Connection,
        embedded_chunks: list[tuple[DatabaseChunk, npt.NDArray[np.float32]]],
        expense_type_map: dict[str, int],
        source_files: list[SourceFile],
    ) -> None:
        """
        Insert all rules, vectors, and links within a single transaction.

        For each embedded chunk, performs three inserts:
        1. INSERT INTO rules (get lastrowid)
        2. INSERT INTO rules_vec using lastrowid
        3. For each expense type: INSERT INTO rule_expense_type_links

        FTS index (rules_fts) is auto-populated via database triggers.

        Args:
            conn: SQLite connection (within transaction)
            embedded_chunks: List of (DatabaseChunk, embedding_vector) tuples
            expense_type_map: Mapping of expense type name to database ID
            source_files: List of SourceFile models for source_hash lookup

        """
        for chunk, embedding in embedded_chunks:
            # 1. Insert into rules table
            cursor = conn.execute(
                """
                INSERT INTO rules (
                    content, citation_id, source_url, source_hash,
                    province, business_type, metadata_json, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.content,
                    chunk.citation_id,
                    chunk.source_url,
                    chunk.source_hash,
                    json.dumps(chunk.province),
                    json.dumps(chunk.business_type),
                    json.dumps(chunk.metadata.model_dump()),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            rule_id = cursor.lastrowid

            # 2. Insert into rules_vec table (vec0 uses implicit rowid, not explicit id)
            conn.execute(
                "INSERT INTO rules_vec (rowid, embedding) VALUES (?, ?)",
                (rule_id, embedding.tobytes()),
            )

            # 3. Insert into rule_expense_type_links (many-to-many)
            for expense_type in chunk.expense_types:
                type_id = expense_type_map.get(expense_type)
                if type_id:
                    conn.execute(
                        "INSERT INTO rule_expense_type_links (rule_id, expense_type_id) VALUES (?, ?)",
                        (rule_id, type_id),
                    )

        logger.info(
            f"Inserted {len(embedded_chunks)} rules with embeddings and expense type links"
        )

    def _run_integrity_checks(
        self, conn: sqlite3.Connection, expected_count: int
    ) -> None:
        """
        Verify the integrity of the database post-build.

        Checks that:
        - rules, rules_vec, rules_fts all have expected_count rows
        - No dangling foreign keys in rule_expense_type_links

        Args:
            conn: SQLite connection
            expected_count: Number of chunks that should be in each table

        Raises:
            QeTaxRagError: If any integrity check fails

        """
        # Check row counts for core tables
        tables = ["rules", "rules_vec", "rules_fts"]
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            if count != expected_count:
                raise QeTaxRagError(
                    f"Integrity check failed: {table} has {count} rows, expected {expected_count}"
                )

        # Check for dangling foreign keys in junction table
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM rule_expense_type_links l
            LEFT JOIN rules r ON l.rule_id = r.id
            WHERE r.id IS NULL
            """
        )
        dangling_rules = cursor.fetchone()[0]
        if dangling_rules > 0:
            raise QeTaxRagError(
                f"Integrity check failed: Found {dangling_rules} dangling rule_id references "
                "in rule_expense_type_links"
            )

        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM rule_expense_type_links l
            LEFT JOIN expense_types e ON l.expense_type_id = e.id
            WHERE e.id IS NULL
            """
        )
        dangling_types = cursor.fetchone()[0]
        if dangling_types > 0:
            raise QeTaxRagError(
                f"Integrity check failed: Found {dangling_types} dangling expense_type_id references "
                "in rule_expense_type_links"
            )

        logger.info(
            f"Integrity checks passed: {expected_count} rows in all tables, "
            "no dangling foreign keys"
        )

    def _create_manifest(
        self,
        manifest_path: str,
        db_hash: str,
        chunk_count: int,
        source_files: tuple[SourceFile, ...],
        data_version: str,
    ) -> None:
        """
        Create the index manifest file.

        Instantiates IndexManifest Pydantic model and writes JSON to manifest_path.

        Args:
            manifest_path: Where to write manifest.json
            db_hash: SHA256 hash of database file
            chunk_count: Number of chunks in database
            source_files: Tuple of SourceFile models
            data_version: Version string (YYYY.MM format)

        """
        from qe_tax_rag.data.schema import SCHEMA_VERSION

        manifest = IndexManifest(
            version=data_version,
            schema_version=SCHEMA_VERSION,
            source_files=source_files,
            embedding_model=self.encoder.model_name,
            chunk_count=chunk_count,
            created_at=datetime.now(timezone.utc),
            sha256=db_hash,
        )

        # Write manifest to file
        with open(manifest_path, "w") as f:
            f.write(manifest.model_dump_json(indent=2))

        logger.info(f"Manifest created: {manifest_path}")

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """
        Compute the SHA256 hash of a file.

        Args:
            file_path: Path to file to hash

        Returns:
            Hexadecimal SHA256 hash string

        """
        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        return sha256.hexdigest()
