"""Integration tests for extraction pipeline with transformer (T4.2)."""

import sqlite3
import subprocess
import time
from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_full_document_set_performance_baseline(tmp_path: Path) -> None:
    """
    Establish performance baseline with full document set.

    Uses realistic full T4002 document set (~247 rules) to:
    - Record baseline timing for regression detection
    - Verify database quality (rule count, structure)
    - Test full pipeline under realistic load

    This test is marked 'slow' and should be run periodically,
    not on every commit.
    """
    # Use full T4002 document set
    html_dir = Path("cra_documents/cra_t4002e_rev24_dump/")

    if not html_dir.exists():
        pytest.skip(f"Test data not found: {html_dir}")

    db_path = tmp_path / "baseline.db"

    # Measure pipeline performance
    start_time = time.time()

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/cli.py",
            "pipeline-extraction",
            "--input-dir",
            str(html_dir),
            "--output-db",
            str(db_path),
        ],
        capture_output=True,
        text=True,
        timeout=600,  # 10 min timeout
    )

    elapsed = time.time() - start_time

    # Verify pipeline succeeded
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
    assert db_path.exists(), "Database was not created"

    # Record baseline for future regression detection
    print(f"\n⏱️  Performance Baseline: {elapsed:.2f}s for full T4002 extraction")
    print(f"   Expected range: 30-120s (depends on hardware)")

    # Verify database quality
    conn = sqlite3.connect(db_path)

    # Check rule count (T4002 has ~247 line items)
    rule_count = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
    assert rule_count > 200, f"Expected >200 rules, got {rule_count}"
    print(f"   ✅ Database contains {rule_count} rules")

    # Check LINE-{number} citation format
    cursor = conn.execute("SELECT citation_id FROM rules LIMIT 5")
    citations = [row[0] for row in cursor.fetchall()]
    assert all(
        c.startswith("LINE-") for c in citations
    ), f"Expected LINE-* citations, got: {citations}"
    print(f"   ✅ Citation format correct: {citations[0]}")

    # Check extraction metadata present
    cursor = conn.execute(
        "SELECT metadata_json FROM rules WHERE citation_id LIKE 'LINE-%' LIMIT 1"
    )
    metadata_json = cursor.fetchone()
    assert metadata_json is not None, "No metadata found"
    print(f"   ✅ Extraction metadata present")

    # Check FTS5 index populated
    fts_count = conn.execute("SELECT COUNT(*) FROM rules_fts").fetchone()[0]
    assert fts_count == rule_count, f"FTS index mismatch: {fts_count} != {rule_count}"
    print(f"   ✅ FTS5 index synced ({fts_count} entries)")

    # Check vector embeddings generated
    vec_count = conn.execute("SELECT COUNT(*) FROM rules_vec").fetchone()[0]
    assert (
        vec_count == rule_count
    ), f"Vector count mismatch: {vec_count} != {rule_count}"
    print(f"   ✅ Vector embeddings generated ({vec_count} vectors)")

    conn.close()

    # Performance guidance
    if elapsed > 120:
        print(f"   ⚠️  Pipeline took {elapsed:.2f}s (>2min) - consider investigating")
    elif elapsed < 30:
        print(f"   🚀 Pipeline very fast ({elapsed:.2f}s) - excellent!")
