"""
Database schema definition and versioning.

Defines the canonical SQLite schema for rules, FTS5 index, and vector search.
"""

SCHEMA_VERSION = "1.0"

CREATE_TABLES_SQL = """
-- Metadata table for versioning
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Main content table
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    citation_id TEXT UNIQUE NOT NULL,
    source_url TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    province TEXT,
    business_type TEXT,
    expense_type TEXT,
    metadata_json TEXT,
    retrieved_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 virtual table for keyword search
CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
    content,
    content='rules',
    content_rowid='id',
    tokenize='porter unicode61'
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

-- Vector table for semantic search
CREATE VIRTUAL TABLE IF NOT EXISTS rules_vec USING vec0(
    id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);

-- Indexes for metadata filtering
CREATE INDEX IF NOT EXISTS idx_province ON rules(province);
CREATE INDEX IF NOT EXISTS idx_business_type ON rules(business_type);
CREATE INDEX IF NOT EXISTS idx_expense_type ON rules(expense_type);
CREATE INDEX IF NOT EXISTS idx_citation ON rules(citation_id);
"""
