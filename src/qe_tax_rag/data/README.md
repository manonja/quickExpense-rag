# Data Layer

This module handles database schema, connection management, and data operations for the
QuickExpense RAG library.

## Architecture

The data layer follows SQLite best practices for a read-optimized, distributable
database:

- **Schema**: Defined in `schema.py` with hybrid search support (FTS5 + sqlite-vec)
- **Connections**: Configured in `connection.py` with optimized PRAGMAs
- **Migrations**: Placeholder in `migrations.py` (uses "rebuild and replace" model)
- **Management**: Data download and caching in `manager.py`

## SQLite Best Practices Applied

### Schema Design

- **WITHOUT ROWID on metadata**: Optimized for non-integer primary key
- **External content FTS5**: Saves space by referencing rules table via
  `content='rules'`
- **No auxiliary columns in vec0**: Avoids duplication; always hydrate full data from
  rules table
- **ISO 8601 TEXT dates**: Human-readable, SQLite date functions compatible

### Connection Configuration

**Build time** (via `configure_build_connection()`):

- `PRAGMA journal_mode = WAL`: Write-Ahead Logging for better concurrency
- `PRAGMA synchronous = NORMAL`: Faster writes, safe for non-critical data

**Runtime** (via `configure_runtime_connection()`):

- Read-only mode (`file:path?mode=ro`): Safety for distributed databases
- `PRAGMA journal_mode = WAL`: Concurrent reads without locking

**Post-build optimization**:

- Run `ANALYZE` via `optimize_database()` to update query planner statistics

### Index Strategy

The schema includes 4 indexes on the `rules` table:

- `idx_province`: Filter by province (BC, AB, ON, QC)
- `idx_business_type`: Filter by business type (sole_proprietorship, corporation,
  partnership)
- `idx_expense_type`: Filter by expense category (meals, travel, vehicle, home_office)
- `idx_citation`: Lookup by citation ID (S#-F#-C#-p#.#)

**Rationale**: Read-heavy workload justifies write-time overhead. Database is built once
offline, then becomes read-only for all users.

### Type Choices

- **TEXT for dates**: ISO 8601 format provides readability over minor storage savings
  from INTEGER timestamps
- **No STRICT tables**: Compatibility with older SQLite versions; Pydantic validation
  handles type safety
- **Dynamic typing**: Leverage SQLite's flexibility while enforcing types at application
  layer

## Database Structure

### Tables

#### `metadata` (WITHOUT ROWID)

Stores versioning and provenance information:

- `schema_version`: Database structure version (e.g., "1.0")
- `data_version`: Content freshness (e.g., "2024.12")
- `embedding_model`: Model used for vector generation (e.g., "BAAI/bge-small-en-v1.5")

#### `rules`

Main content table with CRA rule chunks:

- `id`: Primary key (corresponds to FTS/vector rowid)
- `content`: Rule text content
- `citation_id`: Unique identifier (e.g., "S3-F2-C1-p1.25")
- `source_url`: CRA source document URL
- `source_hash`: SHA256 of source document
- `province`, `business_type`, `expense_type`: Metadata for filtering
- `metadata_json`: Flexible JSON for additional metadata
- `retrieved_at`, `created_at`: ISO 8601 timestamps

#### `rules_fts`

FTS5 virtual table for keyword search:

- Uses `porter` tokenizer with `unicode61` for Canadian English
- External content table (no data duplication)
- Automatically synced via triggers

#### `rules_vec`

sqlite-vec virtual table for semantic search:

- 384-dimensional embeddings (BGE-small-en-v1.5)
- Implicit `rowid` corresponds to `rules.id`
- Chunked storage for fast KNN queries

## Version Compatibility

The library enforces compatibility on `init()`:

- **schema_version**: Major version must match (e.g., library v1.x requires schema v1.x)
- **data_version**: Informational only; newer data is always compatible
- **package_version**: Library code version (independent of data versions)

## Query Pattern

Hybrid search follows this pattern:

1. **Filter metadata**: `WHERE province = ? AND business_type = ?` on `rules` table
1. **Keyword search**: FTS5 `MATCH` on filtered candidates → ranked by BM25
1. **Semantic search**: sqlite-vec KNN on filtered candidates → ranked by cosine
   distance
1. **Fusion**: Reciprocal Rank Fusion (RRF) merges rankings
1. **Hydrate**: Join back to `rules` table for full data

This pattern justifies:

- Indexes on metadata columns (fast filtering)
- External content FTS5 (no duplication)
- No auxiliary columns in vec0 (always return to rules table)

## Migration Strategy

This project uses **"rebuild and replace"** for database updates:

1. Maintainer rebuilds database with updated CRA data
1. New database published to GitHub Releases with incremented `data_version`
1. Users run `init(force_update=True)` to download new version
1. Library checks `schema_version` compatibility and raises error if incompatible

**No client-side migrations needed** - the database is a distributable artifact.

## Performance Considerations

### Build Time

- Use `configure_build_connection()` for optimized write performance
- WAL mode enables concurrent access during build
- NORMAL synchronous mode balances speed and safety
- Run `optimize_database()` as final step

### Runtime

- Use `configure_runtime_connection()` for read-only safety
- WAL mode allows concurrent reads without locking
- Query planner uses ANALYZE statistics for optimal execution plans
- Small database size (~10-50 MB) fits in OS page cache

### Scalability

- Current design tested up to ~5000 chunks (~50 CRA documents)
- FTS5 and sqlite-vec scale well to 10-100K chunks
- Metadata indexes prevent full table scans
- Read-only distribution enables CDN caching

## Usage Examples

### Creating Database (Build Pipeline)

```python
from pathlib import Path
from qe_tax_rag.data.schema import CREATE_TABLES_SQL, init_metadata, optimize_database
from qe_tax_rag.data.connection import configure_build_connection

db_path = Path("cra_rules.db")
conn = configure_build_connection(db_path)

# Create schema
conn.executescript(CREATE_TABLES_SQL)

# Initialize metadata
init_metadata(conn, data_version="2024.12", embedding_model="BAAI/bge-small-en-v1.5")

# ... insert data into rules, rules_fts, rules_vec ...

# Optimize for read performance
optimize_database(conn)
conn.commit()
conn.close()
```

### Querying Database (Runtime)

```python
from pathlib import Path
from qe_tax_rag.data.connection import configure_runtime_connection

db_path = Path.home() / ".cache" / "quickexpense_rag" / "cra_rules.db"
conn = configure_runtime_connection(db_path)

# Check versions
cursor = conn.execute("SELECT key, value FROM metadata")
metadata = dict(cursor.fetchall())
print(f"Schema: {metadata['schema_version']}, Data: {metadata['data_version']}")

# Query with filters
cursor = conn.execute("""
    SELECT id, content, citation_id, source_url
    FROM rules
    WHERE province = ? AND business_type = ?
    LIMIT 10
""", ("BC", "sole_proprietorship"))

results = cursor.fetchall()
conn.close()
```

## References

- [SQLite FTS5 Extension](https://www.sqlite.org/fts5.html)
- [sqlite-vec Documentation](https://github.com/asg017/sqlite-vec)
- [SQLite Performance Best Practices](https://www.sqlite.org/optoverview.html)
- [Schema Migrations in Python/SQLite](https://eskerda.com/sqlite-schema-migrations-python/)
