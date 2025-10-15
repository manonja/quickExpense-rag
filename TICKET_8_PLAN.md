# TICKET 8: Public API Implementation Plan

## Architecture Decisions

### 1. State Management: Simple Module-Level Variable
- Use `_search_engine: Optional[HybridSearchEngine] = None` in `app/api.py`
- Store initialized components once during `init()`, reuse in `search()`
- Rationale: Simple, Pythonic, fits single-init-then-search workflow
- Thread safety: Defer until needed (add `threading.Lock` if required later)

### 2. Validation Strategy: Leverage Pydantic
- Accept raw Python types in `search()` signature
- Construct `ExpenseQuery` model inside `try...except` block
- Let Pydantic handle all validation logic
- Catch `ValidationError` and re-raise with helpful context

### 3. Error Handling: Clear & Actionable
- `DatabaseNotInitializedError`: Check `_search_engine is None` at start of `search()`
- `ValidationError`: Wrap Pydantic errors with guidance on valid options
- `NetworkError/DataVersionMismatchError`: Propagate directly from `DataManager`

### 4. Component Integration: Cache & Reuse
- `init()` orchestrates: DataManager → get DB path → HybridSearchEngine → store in module state
- `search()` uses cached `_search_engine` instance (no re-initialization per search)

## Implementation Steps (Priority Order)

### Step 1: Create `src/quickexpense_rag/api.py` skeleton
```python
# Imports: HybridSearchEngine, DataManager, Config, ExpenseQuery, SearchResult, exceptions
# Module state: _search_engine = None
```

### Step 2: Implement `get_version()` (simplest, no dependencies)
- Return dict with library_version, data_version, schema_version
- Include legal disclaimer in docstring
- Lazy-load metadata from database

### Step 3: Implement `init(force_update: bool = False)`
- Instantiate DataManager
- Call `data_manager.get_database_path(force_update)`
- Instantiate HybridSearchEngine with db_path
- Store in `_search_engine` global
- Full legal disclaimer in docstring

### Step 4: Implement `search(...)`
- Check `_search_engine is None` → raise `DatabaseNotInitializedError`
- Construct `ExpenseQuery` from params in try/except
- Catch Pydantic `ValidationError`, re-raise with context
- Call `_search_engine.search(query_model, top_k)`
- "NOT TAX ADVICE" warning in docstring

### Step 5: Update `src/quickexpense_rag/__init__.py`
- Export: init, search, get_version, SearchResult, ExpenseQuery
- Define `__version__ = "0.1.0"`
- Define `__all__` list

## Testing Strategy (TDD)

### Unit Tests (`tests/unit/test_api.py`)
1. **test_search_raises_error_if_not_initialized**: Verify `DatabaseNotInitializedError`
2. **test_init_calls_data_manager**: Mock DataManager, verify get_database_path called
3. **test_init_creates_search_engine**: Mock components, verify HybridSearchEngine created
4. **test_search_validation_invalid_province**: Invalid params → `ValidationError`
5. **test_search_validation_invalid_top_k**: Out of range → `ValidationError`
6. **test_search_happy_path**: Mock engine, verify `ExpenseQuery` construction and search call
7. **test_get_version**: Verify dict structure
8. **test_legal_disclaimers_in_docstrings**: Verify "LEGAL DISCLAIMER" and "NOT TAX ADVICE"

### Integration Test (`tests/integration/test_user_story_1.py`)
- Use fixture database (`tests/fixtures/test_database.db`)
- **User Story 1 complete workflow**:
  1. Call `init()`
  2. Call `search()` with realistic query
  3. Assert results structure and content
  4. Verify disclaimer, citation_id, source_url, expense_types

## TDD Workflow

1. Write failing test
2. Implement minimal code to pass
3. Refactor
4. Commit
5. Repeat

## 80/20 Priorities

✅ **Focus on**: Happy path, clear error messages, legal disclaimers
⏸️ **Defer**: Thread safety, retry logic, comprehensive edge cases
🎯 **Goal**: User Story 1 integration test passing
