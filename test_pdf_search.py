"""Quick test script for PDF-extracted content search."""

from pathlib import Path

from qe_tax_rag.embeddings.encoder import _EmbeddingService
from qe_tax_rag.search.hybrid import HybridSearchEngine
from qe_tax_rag.search.models import ExpenseQuery

# Initialize embedding service
embedding_service = _EmbeddingService()

# Initialize search engine with PDF-based test database
db_path = Path("output/pdf_test/chapter1_test.db")
search_engine = HybridSearchEngine(db_path=db_path, encoder=embedding_service)

# Test search query
query_text = "business income"
query = ExpenseQuery(query=query_text, top_k=3)
print(f"Searching for: '{query_text}'")
print("=" * 60)

results = search_engine.search(query)

for i, result in enumerate(results, 1):
    print(f"\nResult {i}:")
    print(f"  Citation: {result.citation_id}")
    print(f"  Score: {result.score:.4f}")
    print(f"  Content: {result.content[:200]}...")
    if result.metadata:
        print(f"  Income Type: {result.metadata.income_type}")
        print(f"  Section: {result.metadata.section_title}")

print("\n" + "=" * 60)
print(f"Found {len(results)} results")
