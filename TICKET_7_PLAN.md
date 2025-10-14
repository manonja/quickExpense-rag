# TICKET 7: Hybrid Search Engine Implementation Plan

## Overview
Build a hybrid search engine combining FTS5 keyword search, vector semantic search, and Reciprocal Rank Fusion (RRF) with metadata filtering for many-to-many expense types.

## Implementation Strategy (80/20 Approach + TDD)

### Phase 1: Foundation & Basic Filtering
**Goal**: Prove database connectivity and simple metadata filtering work

#### Step 1.1: Create HybridSearchEngine Skeleton
- [ ] Create `src/quickexpense_rag/search/hybrid.py`
- [ ] Define `HybridSearchEngine` class
- [ ] Implement `__init__(db_path: Path, encoder: BGEEncoder)`
- [ ] Create empty `search(query: ExpenseQuery) -> list[SearchResult]` method stub
- [ ] **Commit**: "feat: add HybridSearchEngine skeleton"

#### Step 1.2: Implement Basic Filter Clause Builder (TDD)
- [ ] Write test: `test_build_filter_clauses_no_filters()` - empty query returns empty clauses
- [ ] Write test: `test_build_filter_clauses_province_only()` - correct SQL for province filter
- [ ] Write test: `test_build_filter_clauses_business_type_only()` - correct SQL for business type
- [ ] Write test: `test_build_filter_clauses_both_simple_filters()` - combines province + business_type
- [ ] Implement `_build_filter_clauses(query: ExpenseQuery) -> tuple[str, str, list[Any]]`
- [ ] Returns: `(join_clause, where_clause, params)`
- [ ] Handle `province` and `business_type` filters only (simple WHERE clauses)
- [ ] **Commit**: "feat: add basic metadata filter builder with tests"

#### Step 1.3: Implement Simple Search (No FTS/Vector Yet)
- [ ] Write integration test: `test_search_with_province_filter()` using fixture DB
- [ ] Write integration test: `test_search_with_business_type_filter()` using fixture DB
- [ ] Implement basic `search()` method:
  - Build filter clauses
  - Execute `SELECT * FROM rules r [WHERE ...]`
  - Hydrate `SearchResult` objects (basic version without expense_types list)
  - Return results
- [ ] **Commit**: "feat: implement basic search with simple metadata filtering"

### Phase 2: Many-to-Many Expense Types
**Goal**: Handle expense_types filtering with JOINs and deduplication

#### Step 2.1: Extend Filter Builder for expense_types (TDD)
- [ ] Write test: `test_build_filter_clauses_expense_types_single()` - one expense type
- [ ] Write test: `test_build_filter_clauses_expense_types_multiple()` - multiple expense types
- [ ] Write test: `test_build_filter_clauses_all_filters()` - province + business_type + expense_types
- [ ] Extend `_build_filter_clauses()`:
  - Add JOIN clauses for `rule_expense_type_links` and `expense_types`
  - Generate `WHERE et.name IN (?, ?, ...)` clause
  - Return proper SQL with parameters
- [ ] **Commit**: "feat: add expense_types filtering with JOIN clauses"

#### Step 2.2: Implement Candidate ID Fetching (TDD)
- [ ] Write test: `test_get_candidate_ids_no_filters()` - returns all rule IDs
- [ ] Write test: `test_get_candidate_ids_with_expense_types()` - filters by expense types
- [ ] Write test: `test_get_candidate_ids_deduplication()` - rule with multiple types appears once
- [ ] Implement `_get_candidate_ids(query: ExpenseQuery) -> list[int]`:
  - Build filter clauses
  - Execute: `SELECT DISTINCT r.id FROM rules r [JOINS] [WHERE]`
  - Return list of rule IDs
- [ ] **Commit**: "feat: add candidate ID fetching with deduplication"

#### Step 2.3: Update Search to Use Candidates
- [ ] Write integration test: `test_search_expense_types_or_logic()` - matches ANY type
- [ ] Write integration test: `test_search_expense_types_no_duplicates()` - rule appears once
- [ ] Update `search()` to use `_get_candidate_ids()`
- [ ] Add short-circuit: if no candidates, return `[]`
- [ ] **Commit**: "feat: integrate candidate filtering into search"

### Phase 3: FTS5 Keyword Search
**Goal**: Add keyword search on filtered candidates

#### Step 3.1: Implement FTS5 Search (TDD)
- [ ] Write test: `test_keyword_search_empty_candidates()` - returns empty list
- [ ] Write test: `test_keyword_search_with_match()` - finds matching documents
- [ ] Write test: `test_keyword_search_exact_term()` - "T2125 form" matches exactly
- [ ] Write test: `test_keyword_search_no_match()` - returns empty if no matches
- [ ] Implement `_keyword_search(query_text: str, candidate_ids: list[int], k: int) -> list[tuple[int, float]]`:
  - Handle empty candidates (return `[]`)
  - Build SQL: `SELECT rowid, rank FROM rules_fts WHERE rowid IN (...) AND content MATCH ?`
  - Execute with parameters
  - Return `[(id, score), ...]`
- [ ] **Commit**: "feat: add FTS5 keyword search on candidates"

#### Step 3.2: Integrate FTS5 into Search (Temporary)
- [ ] Write integration test: `test_search_keyword_only()` - uses FTS5 ranking
- [ ] Update `search()` to call `_keyword_search()`
- [ ] Return results ranked by FTS5 score (temporary - will be replaced by RRF)
- [ ] **Commit**: "feat: integrate FTS5 search into main search method"

### Phase 4: Vector Semantic Search
**Goal**: Add semantic search on filtered candidates

#### Step 4.1: Implement Vector Search (TDD)
- [ ] Write test: `test_vector_search_empty_candidates()` - returns empty list
- [ ] Write test: `test_vector_search_with_match()` - finds semantically similar docs
- [ ] Write test: `test_vector_search_semantic_similarity()` - "restaurant meal" → "dining expense"
- [ ] Implement `_vector_search(query_text: str, candidate_ids: list[int], k: int) -> list[tuple[int, float]]`:
  - Handle empty candidates (return `[]`)
  - Embed query using `self.encoder.embed_query()`
  - Build SQL for sqlite-vec: `SELECT rowid, distance FROM rules_vec WHERE rowid IN (...) AND embedding MATCH ?`
  - Format vector properly for sqlite-vec
  - Return `[(id, distance), ...]`
- [ ] **Commit**: "feat: add vector semantic search on candidates"

#### Step 4.2: Test Vector Search Integration
- [ ] Write integration test: `test_search_vector_only()` - uses vector ranking
- [ ] Temporarily update `search()` to use vector search instead of FTS5 (for testing)
- [ ] Verify semantic search works end-to-end
- [ ] **Commit**: "test: verify vector search integration"

### Phase 5: RRF Fusion & Final Assembly
**Goal**: Merge rankings and hydrate results

#### Step 5.1: Implement RRF Fusion (TDD)
- [ ] Write test: `test_rrf_both_empty()` - returns empty list
- [ ] Write test: `test_rrf_one_empty()` - uses non-empty list
- [ ] Write test: `test_rrf_no_overlap()` - merges disjoint results
- [ ] Write test: `test_rrf_with_overlap()` - item in both lists ranked higher
- [ ] Write test: `test_rrf_scoring_formula()` - verifies score = 1/(k + rank + 1)
- [ ] Implement `reciprocal_rank_fusion(fts_results: list[tuple[int, float]], vec_results: list[tuple[int, float]], k: int = 60) -> list[tuple[int, float]]`:
  - Standalone function (not class method)
  - Implement RRF algorithm as specified in plan.md
  - Return sorted by combined score
- [ ] **Commit**: "feat: add RRF fusion algorithm with comprehensive tests"

#### Step 5.2: Implement Result Hydration (TDD)
- [ ] Write test: `test_hydrate_results_empty()` - returns empty list
- [ ] Write test: `test_hydrate_results_single()` - constructs SearchResult correctly
- [ ] Write test: `test_hydrate_results_with_expense_types()` - properly splits expense_types
- [ ] Write test: `test_hydrate_results_preserves_order()` - maintains RRF ranking
- [ ] Implement `_hydrate_results(rule_ids: list[int]) -> list[SearchResult]`:
  - Query: `SELECT r.*, GROUP_CONCAT(et.name) FROM rules r LEFT JOIN rule_expense_type_links ... WHERE r.id IN (...) GROUP BY r.id`
  - Split expense type names (comma-separated string → list)
  - Construct `SearchResult` objects
  - Preserve order from input `rule_ids`
  - Return `list[SearchResult]`
- [ ] **Commit**: "feat: add result hydration with expense_types aggregation"

#### Step 5.3: Complete Search Implementation
- [ ] Update `search()` method to use all components:
  1. Get candidate IDs from metadata filtering
  2. Short-circuit if empty
  3. Run `_keyword_search()` and `_vector_search()` in parallel on candidates
  4. Apply `reciprocal_rank_fusion()`
  5. Take top `query.top_k` fused IDs
  6. Hydrate results
  7. Return `list[SearchResult]`
- [ ] **Commit**: "feat: complete hybrid search with RRF fusion"

### Phase 6: Comprehensive Testing & Edge Cases
**Goal**: Ensure robustness and meet all acceptance criteria

#### Step 6.1: End-to-End Integration Tests
- [ ] Write test: `test_search_full_hybrid()` - FTS5 + vector + RRF working together
- [ ] Write test: `test_search_keyword_results_only()` - vector returns nothing
- [ ] Write test: `test_search_vector_results_only()` - FTS5 returns nothing
- [ ] Write test: `test_search_overlap_ranked_higher()` - item in both lists ranked first
- [ ] Write test: `test_search_all_filters_combined()` - province + business_type + expense_types + hybrid search
- [ ] **Commit**: "test: add comprehensive end-to-end search tests"

#### Step 6.2: Edge Case Tests
- [ ] Write test: `test_search_no_results()` - filters match zero rows
- [ ] Write test: `test_search_empty_query_text()` - handles empty/whitespace query
- [ ] Write test: `test_search_single_result()` - returns one result correctly
- [ ] Write test: `test_search_large_result_set()` - handles 100+ results, respects top_k
- [ ] Write test: `test_search_special_characters()` - handles quotes, apostrophes in query
- [ ] **Commit**: "test: add edge case coverage for search"

#### Step 6.3: Performance Validation
- [ ] Write benchmark: `test_search_performance()` - 100 searches on fixture DB
- [ ] Verify p99 latency < 250ms (will need larger DB for realistic test)
- [ ] Add performance notes to documentation
- [ ] **Commit**: "test: add performance benchmark for search"

### Phase 7: Documentation & Cleanup
**Goal**: Finalize implementation

#### Step 7.1: Code Documentation
- [ ] Add comprehensive docstrings to all methods
- [ ] Document SQL query patterns
- [ ] Add inline comments for complex logic (RRF, deduplication)
- [ ] **Commit**: "docs: add comprehensive docstrings to HybridSearchEngine"

#### Step 7.2: Integration with Settings
- [ ] Verify `settings.rrf_k` is used (default: 60)
- [ ] Verify `settings.default_top_k` is used
- [ ] **Commit**: "feat: integrate settings for RRF and top_k defaults"

#### Step 7.3: Final Review
- [ ] Run all tests: `uv run pytest tests/ -v`
- [ ] Run type checking: `uv run mypy src/`
- [ ] Run linting: `uvx ruff check`
- [ ] Run formatting: `uvx ruff format`
- [ ] Verify all acceptance criteria met
- [ ] **Commit**: "chore: final cleanup and validation for TICKET 7"

## Key Implementation Details

### SQL Query Patterns

#### Candidate ID Fetching
```sql
SELECT DISTINCT r.id
FROM rules r
[JOIN rule_expense_type_links retl ON r.id = retl.rule_id]
[JOIN expense_types et ON retl.expense_type_id = et.id]
WHERE [conditions]
```

#### FTS5 Keyword Search
```sql
SELECT rowid, rank
FROM rules_fts
WHERE rowid IN (?, ?, ...)
  AND content MATCH ?
ORDER BY rank
LIMIT ?
```

#### Vector Search
```sql
SELECT rowid, distance
FROM rules_vec
WHERE rowid IN (?, ?, ...)
  AND embedding MATCH ?
LIMIT ?
```

#### Result Hydration
```sql
SELECT
    r.id,
    r.content,
    r.citation_id,
    r.source_url,
    r.province,
    r.business_type,
    r.retrieved_at,
    GROUP_CONCAT(et.name) as expense_type_names
FROM rules r
LEFT JOIN rule_expense_type_links retl ON r.id = retl.rule_id
LEFT JOIN expense_types et ON retl.expense_type_id = et.id
WHERE r.id IN (?, ?, ...)
GROUP BY r.id
```

### RRF Algorithm
```python
def reciprocal_rank_fusion(
    fts_results: list[tuple[int, float]],
    vec_results: list[tuple[int, float]],
    k: int = 60
) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}

    for rank, (id, _) in enumerate(fts_results):
        scores[id] = scores.get(id, 0) + 1 / (k + rank + 1)

    for rank, (id, _) in enumerate(vec_results):
        scores[id] = scores.get(id, 0) + 1 / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### sqlite-vec Vector Format
```python
# Query vector must be L2-normalized (BGEEncoder handles this)
query_vec = self.encoder.embed_query(query_text)

# Convert to bytes for sqlite-vec
query_vec_bytes = query_vec.tobytes()

# Use in SQL query
cursor.execute(
    "SELECT rowid, distance FROM rules_vec WHERE embedding MATCH ?",
    (query_vec_bytes,)
)
```

## Testing Strategy

### Test File Structure
```
tests/
  unit/
    test_hybrid_search.py          # Unit tests for HybridSearchEngine methods
    test_rrf_fusion.py             # Unit tests for RRF algorithm
  integration/
    test_search_integration.py     # End-to-end search tests with fixture DB
```

### Test Data Requirements
- Fixture database must have:
  - Rules from multiple provinces (BC, AB, ON, QC)
  - Rules with different business types
  - Rules with multiple expense types (many-to-many)
  - Rules with overlapping keywords and semantic content

## Success Criteria Checklist

- [ ] All 20+ unit tests passing
- [ ] All integration tests passing with fixture database
- [ ] Province filtering works correctly
- [ ] Business type filtering works correctly
- [ ] Expense types OR logic works (matches ANY type)
- [ ] Deduplication works (rule appears once even with multiple types)
- [ ] FTS5 keyword search finds exact matches
- [ ] Vector search finds semantic matches
- [ ] RRF fusion merges rankings correctly
- [ ] Items in both result sets ranked higher
- [ ] Empty result cases handled gracefully
- [ ] Performance: p99 latency < 250ms
- [ ] Type checking passes (mypy strict mode)
- [ ] Linting passes (ruff)
- [ ] Code formatted (ruff format)
- [ ] Comprehensive docstrings added
- [ ] All acceptance criteria from TICKET 7 met

## Estimated Timeline

- Phase 1 (Foundation): 1-2 hours
- Phase 2 (Many-to-Many): 1-2 hours
- Phase 3 (FTS5): 1 hour
- Phase 4 (Vector): 1-2 hours
- Phase 5 (RRF & Assembly): 2-3 hours
- Phase 6 (Testing): 1-2 hours
- Phase 7 (Documentation): 30 minutes

**Total: 7-12 hours** (1-1.5 days of focused work)

## Dependencies

- ✅ TICKET 2: Database Schema (completed)
- ✅ TICKET 3: Configuration (completed)
- ✅ TICKET 4: Pydantic Models (completed)
- ✅ TICKET 4.6: Many-to-Many Schema (completed)
- ✅ TICKET 4.7: Multi-Type Models (completed)
- ✅ TICKET 5: BGE Embeddings (completed)

## Next Steps After Completion

- TICKET 8: Public API (will use HybridSearchEngine)
- TICKET 6: Complete Data Manager (download/cache logic)
