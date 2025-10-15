# Coverage Audit - TICKET 10 Baseline

**Date**: 2025-10-15
**Before TICKET 10 Implementation**: Phase 1 complete (pytest config + fixtures)

## Overall Coverage: 93%

**Status**: ✅ Already exceeds target of ≥85%

## Module-by-Module Coverage

| Module | Coverage | Target | Status |
|--------|----------|--------|--------|
| `api.py` | 100% | ≥95% | ✅ Exceeds |
| `search/hybrid.py` | 94% | ≥95% | ⚠️ **1% short** |
| `data/manager.py` | 99% | ≥90% | ✅ Exceeds |
| `embeddings/encoder.py` | 90% | - | ✅ Good |
| `data/builder.py` | 94% | - | ✅ Good |
| `data/validator.py` | 88% | - | ✅ Good |
| `search/models.py` | 98% | - | ✅ Excellent |

## Detailed Coverage Report

```
Name                                          Stmts   Miss  Cover
-----------------------------------------------------------------
src/quickexpense_rag/__init__.py                  9      0   100%
src/quickexpense_rag/api.py                      28      0   100%
src/quickexpense_rag/data/__init__.py             3      0   100%
src/quickexpense_rag/data/builder.py            178     10    94%
src/quickexpense_rag/data/connection.py          11     11     0%
src/quickexpense_rag/data/manager.py             68      1    99%
src/quickexpense_rag/data/migrations.py           0      0   100%
src/quickexpense_rag/data/schema.py               9      0   100%
src/quickexpense_rag/data/validator.py           84     10    88%
src/quickexpense_rag/embeddings/__init__.py       2      0   100%
src/quickexpense_rag/embeddings/encoder.py       30      3    90%
src/quickexpense_rag/exceptions.py                8      0   100%
src/quickexpense_rag/search/__init__.py           3      0   100%
src/quickexpense_rag/search/enums.py             19      0   100%
src/quickexpense_rag/search/hybrid.py           117      7    94%
src/quickexpense_rag/search/models.py            53      1    98%
src/quickexpense_rag/settings.py                 27      0   100%
-----------------------------------------------------------------
TOTAL                                           649     43    93%
```

## Test Suite Status

**Total Tests**: 311 (excluding 10 slow tests)
- ✅ Passed: 295
- ❌ Failed: 10 (pre-existing failures in test_models.py - not TICKET 10)
- ⏭️ Skipped: 6

### Pre-existing Failures (Not TICKET 10)

10 failures in `tests/unit/test_models.py` related to SourceFile model:
- `url` field now required but tests use `path` parameter
- These failures existed before TICKET 10 work
- Not blocking TICKET 10 implementation

## Gaps to Address in Phase 2

### hybrid.py (94% → 95% target)

**Missing**: 7 statements (1% short of target)

Likely uncovered areas:
- Edge cases in RRF fusion
- Error handling in metadata filtering
- Some conditional branches

**Action**: Phase 2 will add targeted tests for these gaps.

### Modules Already Meeting Targets

- ✅ `api.py`: 100% (target: ≥95%)
- ✅ `manager.py`: 99% (target: ≥90%)

**Action**: Maintain current coverage, add integration tests.

## Conclusion

**Current state is excellent**:
- Overall coverage: 93% (target: ≥85%) ✅
- api.py: 100% (target: ≥95%) ✅
- manager.py: 99% (target: ≥90%) ✅
- hybrid.py: 94% (target: ≥95%) ⚠️ **Needs 1% improvement**

**Phase 2 focus**: Add 3-5 tests to hybrid.py to close the 1% gap.

**TICKET 10 is on track**: Minimal additional testing needed to meet all targets.
