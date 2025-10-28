"""Quick test script for PDF-extracted content search.

Tests search functionality against the production database v3 with 60% PDF coverage.
"""

from pathlib import Path

from qe_tax_rag.embeddings.encoder import _EmbeddingService
from qe_tax_rag.search.hybrid import HybridSearchEngine
from qe_tax_rag.search.models import ExpenseQuery

# Initialize embedding service
embedding_service = _EmbeddingService()

# Initialize search engine with production database v3 (60% coverage)
db_path = Path("output/pdf_full/t4002_pdf_v3.db")
search_engine = HybridSearchEngine(db_path=db_path, encoder=embedding_service)

# Test search query
query_text = "business income"
query = ExpenseQuery(query=query_text, top_k=3)
print(f"\nSearching database: {db_path}")
print(f"Query: '{query_text}'")
print("=" * 60)

results = search_engine.search(query)

for i, result in enumerate(results, 1):
    print(f"\nResult {i}:")
    print(f"  Citation: {result.citation_id}")
    print(f"  Score: {result.score:.4f}")
    print(f"  Content ({len(result.content)} chars): {result.content}")
    if result.expense_types:
        print(f"  Expense Types: {', '.join(result.expense_types)}")

print("\n" + "=" * 60)
print(f"Found {len(results)} results")
print(f"Database: {db_path}")
