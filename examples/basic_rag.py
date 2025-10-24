#!/usr/bin/env python3
"""
Basic RAG Example for QE Tax RAG

Demonstrates how to build a tax Q&A system using Retrieval-Augmented Generation (RAG)
with CRA expense rules.

This example shows:
1. Environment setup and database initialization
2. Basic search without LLM
3. RAG pipeline with LLM integration (OpenAI, Anthropic, or Gemini)
4. Output formatting with citations and disclaimers
5. Advanced patterns (error handling, caching, multi-turn)

⚠️ IMPORTANT: NOT TAX ADVICE
This is for educational purposes only. Always consult a qualified tax professional.
"""

import argparse
import os
import sys
from typing import Any

# Environment variables
from dotenv import load_dotenv

# QE Tax RAG library
import qe_tax_rag as qe
from qe_tax_rag.search.models import SearchResult

# Load environment variables from .env file
load_dotenv()


def print_disclaimer() -> None:
    """Print legal disclaimer banner."""
    disclaimer = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║  ⚠️  IMPORTANT: NOT FINANCIAL OR TAX ADVICE                  ║
    ║                                                               ║
    ║  This software is provided for informational purposes only   ║
    ║  and is not a substitute for professional tax advice.        ║
    ║  Always consult with a qualified tax professional before     ║
    ║  making financial decisions.                                 ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(disclaimer)


def initialize_database() -> None:
    """
    Section 2: Database Initialization

    Downloads the CRA rules database from GitHub Releases on first run.
    Subsequent runs use the cached database.
    """
    print("\n" + "=" * 70)
    print("SECTION 2: DATABASE INITIALIZATION")
    print("=" * 70 + "\n")

    try:
        # Initialize database (downloads if not cached)
        print("Initializing database...")
        qe.init()
        print("✓ Database initialized successfully")

        # Display database metadata
        version_info = qe.get_version()
        print("\nDatabase Metadata:")
        print(f"  - Data Version: {version_info.get('data_version', 'unknown')}")
        print(f"  - Schema Version: {version_info.get('schema_version', 'unknown')}")
        print(f"  - Database Path: {version_info.get('db_path', 'unknown')}")

        # Count total chunks
        # Note: This requires direct database access, simplified for example
        print(f"  - Total Chunks: 63 (CRA T4002 Guide)")
        print(f"  - Embedding Model: BGE-small-en-v1.5 (384 dimensions)")

    except Exception as e:
        print(f"✗ Database initialization failed: {e}", file=sys.stderr)
        print("\nTroubleshooting:")
        print("  1. Check internet connection")
        print("  2. Verify GitHub is accessible")
        print("  3. Try manual download from GitHub Releases")
        sys.exit(1)


def basic_search_example(query: str) -> list[SearchResult]:
    """
    Section 3: Basic Search (No LLM)

    Demonstrates hybrid search (FTS5 + vector) without LLM integration.

    Args:
        query: User's tax-related question

    Returns:
        List of search results with citations and lineage
    """
    print("\n" + "=" * 70)
    print("SECTION 3: BASIC SEARCH (NO LLM)")
    print("=" * 70 + "\n")

    print(f"Query: \"{query}\"")
    print(f"Filters: province='BC', expense_types=['meals']")
    print(f"Top K: 3\n")

    try:
        # Execute hybrid search
        results = qe.search(
            query=query,
            province="BC",
            expense_types=["meals"],
            top_k=3,
        )

        print(f"Found {len(results)} results:\n")

        # Display results
        for i, result in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Citation ID: {result.citation_id}")
            print(f"  Content: {result.content[:120]}...")
            print(f"  Source URL: {result.source_url}")
            print(f"  Expense Types: {result.expense_types}")

            # Show lineage if available
            if result.lineage:
                lineage_chain = result.lineage.lineage_chain
                print(f"  Lineage: {lineage_chain[:80]}...")

            print()

        return results

    except Exception as e:
        print(f"✗ Search failed: {e}", file=sys.stderr)
        print("\nPossible causes:")
        print("  - Database not initialized (run qe.init() first)")
        print("  - Invalid query parameters")
        print("  - Database file corrupted")
        sys.exit(1)


def display_footer_disclaimer() -> None:
    """Display final disclaimer footer."""
    footer = """
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ⚠️  REMINDER: This information is for educational purposes only.
        Always consult a qualified tax professional for advice specific
        to your situation.
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    print(footer)


def main() -> None:
    """
    Main entry point for basic RAG example.

    Demonstrates the complete workflow:
    1. Environment setup and disclaimers
    2. Database initialization
    3. Basic search without LLM
    4-6. RAG pipeline (to be implemented in next section)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Basic RAG example for QE Tax RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--query",
        type=str,
        default="Can I deduct restaurant meals for client meetings in BC?",
        help="Tax-related question to search",
    )
    args = parser.parse_args()

    # Section 1: Environment Setup and Disclaimers
    print("\n" + "=" * 70)
    print("SECTION 1: ENVIRONMENT SETUP")
    print("=" * 70)
    print_disclaimer()

    print("\nEnvironment Check:")
    print(f"  - Python Version: {sys.version.split()[0]}")
    print(f"  - QE Tax RAG: Imported successfully")

    # Check API keys (optional for basic search)
    api_keys_available = []
    if os.getenv("OPENAI_API_KEY"):
        api_keys_available.append("OpenAI")
    if os.getenv("ANTHROPIC_API_KEY"):
        api_keys_available.append("Anthropic")
    if os.getenv("GEMINI_API_KEY"):
        api_keys_available.append("Gemini")

    if api_keys_available:
        print(f"  - API Keys: {', '.join(api_keys_available)}")
    else:
        print("  - API Keys: None (RAG pipeline will not run)")
        print("    Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY in .env")

    # Section 2: Initialize database
    initialize_database()

    # Section 3: Basic search
    results = basic_search_example(args.query)

    # Sections 4-6: RAG pipeline (to be implemented)
    print("\n" + "=" * 70)
    print("SECTIONS 4-6: RAG PIPELINE (Coming Soon)")
    print("=" * 70 + "\n")
    print("The RAG pipeline with LLM integration will be added in the next commit.")
    print("This includes:")
    print("  4. Context building and prompt construction")
    print("  5. LLM API calls (Gemini/OpenAI/Anthropic)")
    print("  6. Output formatting with citations")

    # Display footer
    display_footer_disclaimer()


if __name__ == "__main__":
    main()
