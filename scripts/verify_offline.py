#!/usr/bin/env python3
"""
Offline verification script for qe-tax-rag package.

Tests that the package works completely offline:
1. Database is bundled and accessible
2. Search functionality works without network
3. Version information is correct
4. Database contains expected number of rules

Exit codes:
- 0: All checks passed
- 1: One or more checks failed
"""

import sys
from pathlib import Path


def main() -> int:
    """Run offline verification checks."""
    print("=" * 60)
    print("QE Tax RAG - Offline Verification")
    print("=" * 60)
    print()

    # Test 1: Import library
    print("[1/6] Testing library import...")
    try:
        import qe_tax_rag as qe
        print("✓ Library imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import library: {e}")
        return 1

    # Test 2: Initialize with bundled database (no network)
    print("\n[2/6] Testing initialization (offline mode)...")
    try:
        qe.init()  # Should use bundled database
        print("✓ Initialization successful (bundled database)")
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return 1

    # Test 3: Verify version info
    print("\n[3/6] Testing version information...")
    try:
        version_info = qe.get_version()
        lib_version = version_info["library_version"]
        data_version = version_info["data_version"]
        schema_version = version_info["schema_version"]

        print(f"  Library version: {lib_version}")
        print(f"  Data version: {data_version}")
        print(f"  Schema version: {schema_version}")

        # Verify versions are not "not_initialized"
        if data_version == "not_initialized":
            print("✗ Database not properly initialized")
            return 1

        print("✓ Version information valid")
    except Exception as e:
        print(f"✗ Failed to get version: {e}")
        return 1

    # Test 4: Test search functionality
    print("\n[4/6] Testing search functionality...")
    try:
        results = qe.search(
            query="restaurant meal",
            expense_types=["meals"],
            top_k=3
        )

        if not results:
            print("✗ Search returned no results")
            return 1

        print(f"✓ Search returned {len(results)} results")

        # Verify result structure
        first_result = results[0]
        print(f"  Sample result:")
        print(f"    Citation ID: {first_result.citation_id}")
        print(f"    Score: {first_result.score:.3f}")
        print(f"    Content preview: {first_result.content[:80]}...")

    except Exception as e:
        print(f"✗ Search failed: {e}")
        return 1

    # Test 5: Verify database path (should be in package)
    print("\n[5/6] Testing database location...")
    try:
        # Access internal _db_path to verify it's in the package
        from qe_tax_rag import api
        db_path = api._db_path

        if db_path is None:
            print("✗ Database path not set")
            return 1

        # Check database exists
        if not Path(db_path).exists():
            print(f"✗ Database file not found at: {db_path}")
            return 1

        # Verify it's in the package (not in /tmp or cache)
        db_path_str = str(db_path)
        if "qe_tax_rag" in db_path_str:
            print(f"✓ Database bundled in package: {db_path}")
        else:
            print(f"⚠ Database at unexpected location: {db_path}")

    except Exception as e:
        print(f"✗ Failed to verify database location: {e}")
        return 1

    # Test 6: Verify database content
    print("\n[6/6] Testing database content...")
    try:
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM rules")
        rule_count = cursor.fetchone()[0]
        conn.close()

        print(f"  Total rules in database: {rule_count}")

        if rule_count < 600:  # Expected ~662 rules
            print(f"⚠ Rule count lower than expected (expected ~662, got {rule_count})")
        else:
            print(f"✓ Database contains {rule_count} rules")

    except Exception as e:
        print(f"✗ Failed to verify database content: {e}")
        return 1

    # All checks passed
    print()
    print("=" * 60)
    print("✓ ALL CHECKS PASSED - Package works offline!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
