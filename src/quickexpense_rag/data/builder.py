"""
Index builder for QuickExpense RAG.

Implements User Story 2: Maintainer Indexing Workflow

This module provides the IndexBuilder class that orchestrates the final stage
of the data pipeline:
1. Loads flattened chunks from JSONL (Gemini parser output)
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
from typing import Any

import numpy as np
import numpy.typing as npt
from tqdm import tqdm

from quickexpense_rag.data.schema import CREATE_TABLES_SQL, init_metadata, optimize_database
from quickexpense_rag.embeddings.encoder import _EmbeddingService
from quickexpense_rag.exceptions import EmbeddingError, QuickExpenseError
from quickexpense_rag.search.models import IndexManifest, SourceFile
from scripts.parser.schema import ParsedDocument

logger = logging.getLogger(__name__)


class IndexBuilder:
    """
    Builds searchable SQLite database from Gemini-parsed CRA document chunks.

    Implements User Story 2: Maintainer Indexing Workflow

    This class orchestrates the final stage of the data pipeline:
    1. Loads flattened chunks from JSONL (Gemini parser output)
    2. Generates BGE embeddings in batches
    3. Populates SQLite with rules, FTS index, vector embeddings, expense type links
    4. Validates integrity and generates manifest with SHA256 hash

    The build process is transactional (atomic) - either fully succeeds or rolls back.
    Supports graceful error handling for embedding failures via continue_on_error flag.

    Example:
        >>> from quickexpense_rag.embeddings.encoder import embedding_service
        >>> builder = IndexBuilder(db_path="cra_rules.db", encoder=embedding_service)
        >>> builder.build_from_jsonl(
        ...     jsonl_path="chunks.jsonl",
        ...     manifest_path="manifest.json",
        ...     source_files=[SourceFile(...)],
        ...     data_version="2024.12"
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

    def build_from_jsonl(
        self,
        jsonl_path: str,
        manifest_path: str,
        source_files: list[SourceFile],
        data_version: str,
        continue_on_error: bool = False,
    ) -> None:
        """
        Main entry point to build index from JSONL file.

        Args:
            jsonl_path: Path to JSONL file with ParsedDocument objects
            manifest_path: Where to write manifest.json
            source_files: List of SourceFile models with hash/URL metadata
            data_version: Version string (YYYY.MM format)
            continue_on_error: If True, skip chunks with embedding errors

        Raises:
            ValueError: Duplicate citation_id found
            EmbeddingError: Embedding generation failed (if continue_on_error=False)
            sqlite3.IntegrityError: Database constraint violation
        """
        raise NotImplementedError("Phase 6: Orchestration")

    def _setup_database(self, conn: sqlite3.Connection, data_version: str) -> None:
        """
        Initialize database schema and metadata.

        Args:
            conn: SQLite connection
            data_version: Version string to store in metadata table
        """
        raise NotImplementedError("Phase 6: Orchestration")

    def _load_and_flatten_chunks(
        self, jsonl_path: str, source_files: list[SourceFile]
    ) -> list[dict[str, Any]]:
        """
        Load documents from JSONL and flatten into chunks.

        Reads JSONL file line by line, parses each line into a ParsedDocument,
        calls to_flat_chunks() to flatten hierarchical structure, and accumulates
        all chunks. Detects duplicate citation_ids early (fail fast).

        Args:
            jsonl_path: Path to JSONL file with ParsedDocument objects
            source_files: List of SourceFile models to lookup source_url and source_hash

        Returns:
            List of chunk dictionaries with keys: citation_id, content, expense_types,
            source_url, source_hash, province, business_type, metadata

        Raises:
            ValueError: If duplicate citation_id detected
        """
        # Create document_id -> SourceFile mapping for fast lookup
        source_map = {Path(sf.path).stem: sf for sf in source_files}

        all_chunks = []
        seen_citations: set[str] = set()

        with open(jsonl_path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                # Parse document
                try:
                    doc = ParsedDocument.model_validate_json(line)
                except Exception as e:
                    logger.error(f"Failed to parse line {line_num}: {e}")
                    raise

                # Get source file for this document
                source_file = source_map.get(doc.document_id)
                if not source_file:
                    logger.warning(
                        f"No source file found for document_id: {doc.document_id}"
                    )
                    # Use first source file as fallback
                    source_file = source_files[0] if source_files else None
                    if not source_file:
                        raise ValueError("No source files provided")

                # Flatten document to chunks
                chunks = doc.to_flat_chunks(source_url=str(source_file.url))

                # Add source_hash to each chunk and check for duplicates
                for chunk in chunks:
                    citation_id = chunk.get("citation_id")
                    if not citation_id:
                        logger.warning(f"Chunk missing citation_id in document {doc.document_id}")
                        continue

                    # Duplicate detection
                    if citation_id in seen_citations:
                        raise ValueError(
                            f"Duplicate citation_id found: {citation_id}. "
                            "Each citation_id must be unique across all documents."
                        )
                    seen_citations.add(citation_id)

                    # Add source_hash
                    chunk["source_hash"] = source_file.hash

                    # Extract expense_types from nested metadata to top level (for easier access)
                    metadata = chunk.get("metadata", {})
                    chunk["expense_types"] = metadata.get("expense_type", [])
                    chunk["province"] = metadata.get("province")
                    chunk["business_type"] = metadata.get("business_type")

                    all_chunks.append(chunk)

        logger.info(f"Loaded {len(all_chunks)} chunks from {jsonl_path}")
        return all_chunks

    def _populate_expense_types(
        self, conn: sqlite3.Connection, chunks: list[dict[str, Any]]
    ) -> dict[str, int]:
        """
        Identify unique expense types, populate table, return name-to-ID map.

        Extracts all unique expense types from chunks, inserts them into the
        expense_types table, and returns a mapping of expense type names to
        their auto-incremented database IDs for use in junction table inserts.

        Args:
            conn: SQLite connection
            chunks: List of chunk dictionaries

        Returns:
            Dictionary mapping expense type name (str) to database ID (int)
        """
        # Collect unique expense types from all chunks
        expense_types: set[str] = set()
        for chunk in chunks:
            chunk_types = chunk.get("expense_types", [])
            if chunk_types:
                expense_types.update(chunk_types)

        # If no expense types found, return empty dict
        if not expense_types:
            logger.info("No expense types found in chunks")
            return {}

        # Insert expense types into table (sorted for deterministic order)
        for expense_type in sorted(expense_types):
            conn.execute(
                "INSERT INTO expense_types (name) VALUES (?)", (expense_type,)
            )

        # Query back to get name→id mapping
        cursor = conn.execute("SELECT id, name FROM expense_types")
        expense_type_map = {name: id for id, name in cursor.fetchall()}

        logger.info(f"Populated {len(expense_type_map)} unique expense types")
        return expense_type_map

    def _embed_chunks_in_batches(
        self, chunks: list[dict[str, Any]], continue_on_error: bool
    ) -> list[tuple[dict[str, Any], npt.NDArray[np.float32]]]:
        """
        Generate embeddings for all chunks in batches with progress bar.

        Processes chunks in batches of 32, calling encoder.embed_documents() for
        each batch. Shows progress bar with tqdm. Handles errors according to
        continue_on_error flag.

        Args:
            chunks: List of chunk dictionaries
            continue_on_error: If True, log errors and skip failed batches;
                             if False, raise EmbeddingError on first failure

        Returns:
            List of (chunk_dict, embedding_vector) tuples for successfully
            embedded chunks

        Raises:
            EmbeddingError: If embedding fails and continue_on_error=False
        """
        if not chunks:
            return []

        # Extract content texts for embedding
        texts = [chunk["content"] for chunk in chunks]
        results: list[tuple[dict[str, Any], npt.NDArray[np.float32]]] = []

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
                for chunk, embedding in zip(batch_chunks, embeddings):
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
        embedded_chunks: list[tuple[dict[str, Any], npt.NDArray[np.float32]]],
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
            embedded_chunks: List of (chunk_dict, embedding_vector) tuples
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
                    chunk["content"],
                    chunk["citation_id"],
                    chunk["source_url"],
                    chunk["source_hash"],
                    json.dumps(chunk.get("province")),
                    json.dumps(chunk.get("business_type")),
                    json.dumps(chunk.get("metadata", {})),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            rule_id = cursor.lastrowid

            # 2. Insert into rules_vec table
            conn.execute(
                "INSERT INTO rules_vec (id, embedding) VALUES (?, ?)",
                (rule_id, embedding.tobytes()),
            )

            # 3. Insert into rule_expense_type_links (many-to-many)
            expense_types = chunk.get("expense_types", [])
            for expense_type in expense_types:
                type_id = expense_type_map.get(expense_type)
                if type_id:
                    conn.execute(
                        "INSERT INTO rule_expense_type_links (rule_id, expense_type_id) VALUES (?, ?)",
                        (rule_id, type_id),
                    )

        logger.info(f"Inserted {len(embedded_chunks)} rules with embeddings and expense type links")

    def _run_integrity_checks(self, conn: sqlite3.Connection, expected_count: int) -> None:
        """
        Verify the integrity of the database post-build.

        Checks that:
        - rules, rules_vec, rules_fts all have expected_count rows
        - No dangling foreign keys in rule_expense_type_links

        Args:
            conn: SQLite connection
            expected_count: Number of chunks that should be in each table

        Raises:
            QuickExpenseError: If any integrity check fails
        """
        raise NotImplementedError("Phase 5: Integrity Checks")

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
        raise NotImplementedError("Phase 6: Orchestration")

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """
        Compute the SHA256 hash of a file.

        Args:
            file_path: Path to file to hash

        Returns:
            Hexadecimal SHA256 hash string
        """
        raise NotImplementedError("Phase 6: Orchestration")
