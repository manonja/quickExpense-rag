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

# QE Tax RAG library
import qe_tax_rag as qe

# Environment variables
from dotenv import load_dotenv
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

    print(f'Query: "{query}"')
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


def build_context_from_results(results: list[SearchResult]) -> str:
    """
    Section 4a: Build Context from Search Results

    Formats search results into a context string for LLM prompts.

    Args:
        results: List of search results from qe.search()

    Returns:
        Formatted context string with citations and source URLs

    """
    if not results:
        return "No relevant CRA rules found for this query."

    context_parts = []
    for i, result in enumerate(results, 1):
        context_parts.append(f"[{i}] Citation ID: {result.citation_id}")
        context_parts.append(f"    Content: {result.content}")
        context_parts.append(f"    Source: {result.source_url}")
        context_parts.append("")  # Blank line

    return "\n".join(context_parts)


def call_gemini_api(query: str, context: str) -> dict[str, Any]:
    """
    Section 4c: Gemini API Call

    Makes API call to Google Gemini for RAG response.

    Args:
        query: User's tax question
        context: Formatted context from search results

    Returns:
        Dictionary with 'response' and 'citations' keys

    """
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError:
        raise ImportError(
            "google-generativeai not installed. "
            "Install with: pip install google-generativeai"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    # Construct prompt
    system_prompt = """You are a tax information assistant specializing in Canadian Revenue Agency (CRA) expense rules.

IMPORTANT INSTRUCTIONS:
1. Use ONLY the provided CRA excerpts to answer questions
2. Include citation IDs in your response (e.g., [Citation ID: LINE-8523])
3. If the excerpts don't contain relevant information, say so clearly
4. Remind users to consult a qualified tax professional for advice
5. Keep responses concise and focused on the user's question

DO NOT make up information. If unsure, say "The provided excerpts don't cover this topic."
"""

    user_prompt = f"""Question: {query}

CRA Excerpts:
{context}

Based ONLY on the CRA excerpts above, please answer the user's question. Include citation IDs and remind the user to consult a tax professional.
"""

    # Make API call
    response = model.generate_content(user_prompt)

    return {"response": response.text, "model": "gemini-2.0-flash-exp"}


def show_alternative_providers() -> None:
    """
    Section 4d: Alternative LLM Providers

    Shows code snippets for OpenAI and Anthropic as alternatives to Gemini.
    """
    print("\n" + "-" * 70)
    print("Alternative LLM Providers (Code Snippets)")
    print("-" * 70 + "\n")

    openai_snippet = """
# OpenAI GPT Example
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.1
)
answer = response.choices[0].message.content
"""

    anthropic_snippet = """
# Anthropic Claude Example
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system=system_prompt,
    messages=[
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.1
)
answer = response.content[0].text
"""

    print("OpenAI GPT-4:")
    print(openai_snippet)
    print("\nAnthropic Claude:")
    print(anthropic_snippet)


def rag_pipeline_example(query: str, results: list[SearchResult]) -> None:
    """
    Section 4: RAG Pipeline with LLM

    Demonstrates complete RAG workflow:
    - Build context from search results
    - Construct prompts
    - Call LLM API
    - Display results with citations

    Args:
        query: User's tax question
        results: Search results from basic_search_example()

    """
    print("\n" + "=" * 70)
    print("SECTION 4: RAG PIPELINE WITH LLM")
    print("=" * 70 + "\n")

    # Section 4a: Build context
    print("4a. Building context from search results...\n")
    context = build_context_from_results(results)

    # Display token count estimate
    token_estimate = len(context.split()) * 1.3  # Rough estimate
    print(f"Context length: ~{int(token_estimate)} tokens\n")

    # Section 4b: Prompt construction
    print("4b. Constructing RAG prompt...")
    print("   System prompt: Tax information assistant")
    print(f"   User query: {query}")
    print(f"   Context: {len(results)} CRA excerpts\n")

    # Section 4c: LLM API call
    print("4c. Calling Gemini API...\n")

    # Check if API key is available
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not found. Skipping LLM integration.")
        print("   Set GEMINI_API_KEY in .env to run RAG pipeline.")
        print("   You can also use OPENAI_API_KEY or ANTHROPIC_API_KEY.\n")
        show_alternative_providers()
        return

    try:
        result = call_gemini_api(query, context)

        # Section 5: Output formatting
        print("\n" + "=" * 70)
        print("SECTION 5: OUTPUT FORMATTING")
        print("=" * 70 + "\n")

        print(f"Model: {result['model']}")
        print(f"\nAI Response:\n")
        print("-" * 70)
        print(result["response"])
        print("-" * 70)

        # Extract and display citations
        print("\n📚 Citations:")
        for i, search_result in enumerate(results, 1):
            print(f"  [{i}] {search_result.citation_id} - {search_result.source_url}")

        # Legal disclaimer
        print("\n⚠️  IMPORTANT DISCLAIMER:")
        print("    This AI-generated response is for informational purposes only.")
        print("    It is NOT professional tax advice. Consult a qualified tax")
        print("    professional for advice specific to your situation.")

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("\nInstall required package:")
        print("  pip install google-generativeai")
        show_alternative_providers()

    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        print("\nSet your API key in .env:")
        print("  GEMINI_API_KEY=your_key_here")
        show_alternative_providers()

    except Exception as e:
        print(f"✗ API call failed: {e}")
        print("\nPossible causes:")
        print("  - Rate limit exceeded (wait and retry)")
        print("  - Invalid API key (check your key)")
        print("  - Network connectivity issues")
        print("  - API service temporarily unavailable")
        show_alternative_providers()

    # Section 4d: Show alternative providers
    if os.getenv("GEMINI_API_KEY"):
        show_alternative_providers()


def show_advanced_patterns() -> None:
    """
    Section 6: Advanced Usage Patterns

    Demonstrates:
    - Multi-turn conversations
    - Error handling strategies
    - Caching search results
    """
    print("\n" + "=" * 70)
    print("SECTION 6: ADVANCED PATTERNS")
    print("=" * 70 + "\n")

    multi_turn_example = """
# Multi-Turn Conversation Example
conversation_history = []

# First question
results1 = qe.search("vehicle expenses", top_k=5)
context1 = build_context_from_results(results1)
conversation_history.append({"role": "user", "content": "What are vehicle expense rules?"})
# ... get LLM response ...
conversation_history.append({"role": "assistant", "content": response1})

# Follow-up question (maintains context)
results2 = qe.search("electric vehicle", top_k=3)
context2 = build_context_from_results(results2)
conversation_history.append({"role": "user", "content": "What about electric vehicles?"})
# ... pass conversation_history to LLM for context ...
"""

    caching_example = """
# Caching Search Results Example
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query: str, province: str | None = None):
    return qe.search(query, province=province, top_k=5)

# First call: queries database
results1 = cached_search("meal expenses", province="BC")

# Second call: returns cached results (instant)
results2 = cached_search("meal expenses", province="BC")
"""

    error_handling_example = """
# Robust Error Handling Example
def safe_rag_query(query: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            # Search with timeout
            results = qe.search(query, top_k=5)

            if not results:
                return "No relevant rules found. Try broader search terms."

            # LLM call with retry logic
            context = build_context_from_results(results)
            response = call_gemini_api(query, context)
            return response

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                return f"Failed after {max_retries} attempts: {e}"
"""

    print("6a. Multi-Turn Conversations:")
    print(multi_turn_example)

    print("\n6b. Caching Search Results:")
    print(caching_example)

    print("\n6c. Error Handling with Retry Logic:")
    print(error_handling_example)


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

    # Sections 4-5: RAG pipeline with LLM
    rag_pipeline_example(args.query, results)

    # Section 6: Advanced patterns
    show_advanced_patterns()

    # Display footer
    display_footer_disclaimer()


if __name__ == "__main__":
    main()
