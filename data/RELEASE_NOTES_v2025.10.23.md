# CRA Tax Rules Database - October 2025

## Release Information

**Tag:** `data-v2025.10.23`
**Title:** CRA Tax Rules Database - October 2025
**Database File:** `cra_rules.db` (1.7 MB)

## Database Statistics

- **Total Chunks:** 63 searchable expense rules
- **Schema Version:** 1.0
- **Data Version:** 2025.10.23
- **Embedding Model:** BGE-small-en-v1.5 (384 dimensions)
- **Source Documents:** CRA T4002 Business and Professional Income Guide
- **Source Files:** t4002-5.html
- **Lineage Coverage:** 100% (classic parser + adjudicator)
- **Expense Types:** 16 unique categories
- **Search Indices:** FTS5 full-text + sqlite-vec semantic search

## File Verification

**SHA256 Checksum:**
```
c8f7a98c418b9c82d22653c6f74ac3a9677c3679ee7dd80e924270fe84bdfef5
```

**Verify download:**
```bash
shasum -a 256 cra_rules.db
# Should match: c8f7a98c418b9c82d22653c6f74ac3a9677c3679ee7dd80e924270fe84bdfef5
```

## Usage

Install the library:
```bash
pip install qe-tax-rag
```

The database will be downloaded automatically on first use:
```python
import qe_tax_rag as qe

# Downloads database from this GitHub Release
qe.init()

# Search expense rules
results = qe.search(
    query="restaurant meals for client meetings",
    province="BC",
    expense_types=["meals"]
)
```

## Quality Validation

This database has been validated through comprehensive testing:

- **Search Success Rate:** 10/10 queries (100% - exceeds 70% threshold)
- **Lineage Traceability:** 100% coverage with source document tracking
- **Integrity Checks:** All database constraints verified
- **Embedding Quality:** All 63 chunks have valid 384-dim vectors

See [PR #44](https://github.com/manonja/quickExpense-rag/pull/44) and [PR #45](https://github.com/manonja/quickExpense-rag/pull/45) for full validation reports.

## Technical Details

### Database Schema

- **metadata** - Schema version, data version, build timestamp
- **rules** - Main content table (citation_id, content, metadata_json)
- **rules_fts** - FTS5 virtual table for keyword search
- **rules_vec** - Vector table for semantic search (sqlite-vec)
- **expense_types** - Taxonomy of expense categories
- **rule_expense_type_links** - Many-to-many relationships

### Lineage Metadata

Every chunk includes complete lineage traceability in `metadata_json`:

```json
{
  "lineage": {
    "source_document": "t4002-5.html",
    "expert_source": "classic" | "adjudicated",
    "extraction_timestamp": "2025-10-24T06:55:39Z",
    "pipeline_stages": [
      {"stage": "classic_parser", "timestamp": "2025-10-24T06:55:39Z"},
      {"stage": "adjudicator", "timestamp": "2025-10-24T06:56:10Z"}
    ],
    "lineage_chain": "t4002-5.html | classic_parser[...] -> adjudicator[...]"
  }
}
```

## Distribution Model

- **Code:** Distributed via PyPI (`pip install qe-tax-rag`)
- **Database:** Downloaded from GitHub Releases on first use
- **Versioning:** Schema version + data version stored in database metadata
- **Integrity:** SHA256 checksums verified on download
- **Compatibility:** Version compatibility checked on `qe.init()`

## License

This database contains excerpts from CRA publications, which are © Crown Copyright.
Distributed under MIT License for research and educational purposes.

## Disclaimer

⚠️ **IMPORTANT: NOT FINANCIAL OR TAX ADVICE**

This software is provided for informational purposes only and is not a substitute for
professional financial or tax advice. Always consult with a qualified tax professional
before making financial decisions. CRA rules are complex, change frequently, and require
professional interpretation.

## Support

- Documentation: https://github.com/manonja/quickExpense-rag
- Issues: https://github.com/manonja/quickExpense-rag/issues
- Examples: See `examples/` directory in repository
