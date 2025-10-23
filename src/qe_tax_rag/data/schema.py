"""
Database schema definition for QuickExpense RAG.

This module defines the canonical SQLite schema including:
- Main content table (rules)
- FTS5 virtual table for keyword search (rules_fts)
- sqlite-vec virtual table for semantic search (rules_vec)
- Metadata table for versioning and provenance

Schema follows SQLite best practices:
- WITHOUT ROWID for metadata table (non-integer PK optimization)
- External content FTS5 to minimize storage
- Indexes on frequently filtered columns
- ISO 8601 TEXT dates for human readability
"""

import sqlite3

SCHEMA_VERSION = "1.0"

CREATE_TABLES_SQL = """
-- Metadata table for database versioning and provenance.
-- WITHOUT ROWID optimization for non-integer PK tables.
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

-- Main content table storing processed chunks of CRA rules.
/*
 * The metadata_json column stores flexible, non-indexed metadata from the
 * extraction pipeline. Expected fields include:
 * - income_type: list[str]
 * - extraction_source: str
 * - extraction_confidence: float
 * - source_anchor: str
 * - section_title: str
 * - document_id: str
 */
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    citation_id TEXT UNIQUE NOT NULL,
    source_url TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    province TEXT,
    business_type TEXT,
    metadata_json TEXT,
    retrieved_at TEXT NOT NULL,  -- ISO 8601
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP  -- ISO 8601
);

-- FTS5 virtual table for fast keyword search.
-- Uses external content table to save space.
CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
    content,
    content='rules',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- Triggers to automatically update the FTS table on changes to 'rules'.
CREATE TRIGGER IF NOT EXISTS rules_ai AFTER INSERT ON rules BEGIN
    INSERT INTO rules_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS rules_ad AFTER DELETE ON rules BEGIN
    DELETE FROM rules_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS rules_au AFTER UPDATE ON rules BEGIN
    UPDATE rules_fts SET content = new.content WHERE rowid = new.id;
END;

-- Vector search virtual table powered by sqlite-vec.
-- The implicit 'rowid' of this table corresponds to 'rules.id'.
-- No auxiliary columns needed - always hydrate from rules table.
CREATE VIRTUAL TABLE IF NOT EXISTS rules_vec USING vec0(
    embedding FLOAT[384]  -- BGE-small-en-v1.5
);

-- Indexes for efficient filtering on common metadata fields.
-- Justified for read-heavy workload despite write-time overhead.
CREATE INDEX IF NOT EXISTS idx_province ON rules(province);
CREATE INDEX IF NOT EXISTS idx_business_type ON rules(business_type);
CREATE INDEX IF NOT EXISTS idx_citation ON rules(citation_id);

-- Controlled vocabulary table for expense types.
-- Enforces consistency and enables efficient many-to-many relationships.
CREATE TABLE IF NOT EXISTS expense_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Many-to-many junction table linking rules to expense types.
-- A single rule can apply to multiple expense categories.
CREATE TABLE IF NOT EXISTS rule_expense_type_links (
    rule_id INTEGER NOT NULL,
    expense_type_id INTEGER NOT NULL,
    PRIMARY KEY (rule_id, expense_type_id),
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE,
    FOREIGN KEY (expense_type_id) REFERENCES expense_types(id) ON DELETE CASCADE
);

-- Indexes for efficient many-to-many joins.
CREATE INDEX IF NOT EXISTS idx_link_rule ON rule_expense_type_links(rule_id);
CREATE INDEX IF NOT EXISTS idx_link_type ON rule_expense_type_links(expense_type_id);
"""


def init_metadata(
    conn: sqlite3.Connection, data_version: str, embedding_model: str
) -> None:
    """
    Initialize metadata table with version info.

    Args:
        conn: SQLite connection
        data_version: Data version (YYYY.MM format)
        embedding_model: Name of embedding model used

    """
    conn.execute(
        "INSERT OR REPLACE INTO metadata VALUES (?, ?)",
        ("schema_version", SCHEMA_VERSION),
    )
    conn.execute(
        "INSERT OR REPLACE INTO metadata VALUES (?, ?)",
        ("data_version", data_version),
    )
    conn.execute(
        "INSERT OR REPLACE INTO metadata VALUES (?, ?)",
        ("embedding_model", embedding_model),
    )


def optimize_database(conn: sqlite3.Connection) -> None:
    """
    Run post-build optimizations.

    Call this after all data is inserted. ANALYZE updates query planner
    statistics for optimal read performance.

    Args:
        conn: SQLite connection

    """
    conn.execute("ANALYZE")
