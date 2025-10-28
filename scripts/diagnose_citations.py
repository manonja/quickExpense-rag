"""Diagnostic script to analyze citation_id patterns in the database.

This script connects to a SQLite database and categorizes all citation_ids
to understand the full scope of format variations, including any anomalies.
"""

import re
import sqlite3
from collections import defaultdict
from pathlib import Path

# --- CONFIGURATION ---
DEFAULT_DB_PATH = "output/pdf_full/t4002_pdf_v3.db"
# --- END CONFIGURATION ---

# Known and suspected patterns
PATTERNS = {
    "legacy_gemini": re.compile(r"^S\d+-F\d+-C\d+-p\d+\.?\d*$"),
    "html_line": re.compile(r"^LINE-\d+$"),
    "pdf_hash_ok": re.compile(r"^T4002-P\d+-[a-f0-9]{8}(?:-DUP\d+)?$"),
    "pdf_item_anomaly": re.compile(r"^T4002-P\d+-ITEM\d+(?:-DUP\d+)?$"),
}


def analyze_citation_ids(db_path: str | Path) -> None:
    """Connects to the DB, fetches all citation_ids, and categorizes them."""
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        print(f"   Please provide a valid database path as argument.")
        return

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        print(f"❌ Error connecting to database at {db_path}: {e}")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT citation_id FROM rules")
    except sqlite3.OperationalError:
        print("❌ Error: 'rules' table not found. Is the database path correct?")
        conn.close()
        return

    all_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    categorized = defaultdict(list)
    unmatched = []

    for cid in all_ids:
        matched = False
        for name, pattern in PATTERNS.items():
            if pattern.match(cid):
                categorized[name].append(cid)
                matched = True
                break
        if not matched:
            unmatched.append(cid)

    print(f"\n{'='*70}")
    print(f"Citation ID Analysis for {db_path}")
    print(f"Total IDs: {len(all_ids)}")
    print(f"{'='*70}\n")

    for name, ids in categorized.items():
        if ids:
            status = "✅" if "anomaly" not in name else "⚠️ "
            print(f"{status} Found {len(ids):>5} IDs matching pattern '{name}'")
            print(f"   Example: {ids[0]}")

            # Show more examples for anomalies
            if "anomaly" in name and len(ids) > 1:
                print(f"   More examples: {', '.join(ids[1:min(6, len(ids))])}")
                if len(ids) > 5:
                    print(f"   ... and {len(ids) - 5} more")
            print()

    if unmatched:
        unique_unmatched = sorted(list(set(unmatched)))
        print(f"\n❌ Found {len(unmatched)} UNMATCHED IDs ({len(unique_unmatched)} unique)")
        print(f"   These require investigation:\n")
        # Print up to 20 unique unmatched examples
        for cid in unique_unmatched[:20]:
            print(f"   - {cid}")
        if len(unique_unmatched) > 20:
            print(f"   ... and {len(unique_unmatched) - 20} more\n")
    else:
        print("✅ All citation IDs match known patterns.\n")

    # Summary recommendations
    print(f"{'='*70}")
    print("RECOMMENDATIONS:")
    print(f"{'='*70}")

    if categorized["pdf_item_anomaly"]:
        item_count = len(categorized["pdf_item_anomaly"])
        print(f"\n⚠️  Found {item_count} citation(s) with ITEM format (legacy extraction)")
        print(f"   These should be regenerated with hash-based IDs for data consistency.")
        print(f"   Current pattern in search/models.py allows these temporarily.")

    if unmatched:
        print(f"\n❌ Found {len(unmatched)} unmatched citation(s)")
        print(f"   These need pattern updates in search/models.py")

    if not categorized["pdf_item_anomaly"] and not unmatched:
        print(f"\n✅ Database is clean! All citations use correct hash-based format.")
        print(f"   Consider removing ITEM\\d+ support from CITATION_ID_PATTERN.")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    analyze_citation_ids(db_path)
