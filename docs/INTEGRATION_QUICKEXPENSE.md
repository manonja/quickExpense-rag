# Integration Guide: qe-tax-rag for quickExpense Multi-Agent Workflow

**Last Updated:** 2025-10-29
**Target Application:** [quickExpense](https://github.com/manonja/quickExpense)
**Integration Type:** RAG Knowledge Base for CRArulesAgent
**Package Version:** v0.2.4 (bundled database - no network required)

---

## 🚀 Quick Start for Demo (2-Day Timeline)

**Situation:** Demo in 2 days - need RAG integrated with accurate CRA rule citations

**Strategy:** Install from TestPyPI first → validate → migrate to production PyPI after demo success

### Timeline Overview

| Day | Focus | Tasks |
|-----|-------|-------|
| **Day 1** | Integration & Testing | Install package, update CRArulesAgent, test 5 sample queries |
| **Day 2** | Validation & Rehearsal | End-to-end workflow test, demo dry run, confidence check |
| **Post-Demo** | Production Migration | Switch to production PyPI (simple pip reinstall) |

### Fastest Path to Working Demo

```bash
# Step 1: Install from TestPyPI (5 minutes)
cd ~/quickExpense  # Your quickExpense repository
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ qe-tax-rag==0.2.4

# Step 2: Verify installation (1 minute)
python -c "import qe_tax_rag as qe; qe.init(); print('✅ Ready for integration')"

# Step 3: Update CRArulesAgent (see detailed steps below)
# Step 4: Test with sample expenses (see validation checklist)
# Step 5: Demo rehearsal
```

**Expected Result:** Working RAG integration in < 2 hours of focused work

### Key Changes from Previous Versions

**v0.2.4 Changes:**
- ✅ **No network download required** - database bundled in package (1.2MB wheel)
- ✅ **No httpx dependency** - works offline immediately after install
- ✅ **Lazy loading** - faster import times
- ✅ **Cache-based extraction** - database extracts to `~/.qe_tax_rag/t4002.db` on first init

**Migration Note:** If you previously used v0.1.0 with GitHub Releases download, v0.2.4 simplifies setup significantly.

---

## Overview

This guide shows how to integrate the `qe-tax-rag` library into the quickExpense AutoGen multi-agent workflow to ground the CRArulesAgent's tax compliance decisions in authoritative CRA documentation.

### Problem Statement

**Before Integration:**
- CRArulesAgent relies purely on LLM reasoning (TogetherAI Llama 3.1 70B)
- Risk of hallucinations and outdated tax rules
- No source citations or audit trail
- Rules limited to LLM's training data cutoff

**After Integration:**
- Retrieval-grounded compliance analysis using 662 authoritative CRA rules
- Every decision backed by citation IDs (e.g., `LINE-8523`)
- Source URLs link to official CRA publications
- Database updated independently from application code
- Hybrid approach: Retrieval (factual) + LLM (interpretation)

---

## Architecture & Data Flow

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    quickExpense Application                     │
│                       (FastAPI Backend)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ DataExtract  │────▶│  CRArules    │────▶│ TaxCalc      │
│   Agent      │     │   Agent      │     │  Agent       │
│              │     │  [WITH RAG]  │     │              │
│ Gemini 2.0   │     │ Llama 3.1    │     │  Validator   │
└──────────────┘     └──────────────┘     └──────────────┘
                              │
                              │ qe.search()
                              ▼
                     ┌──────────────┐
                     │  qe-tax-rag  │
                     │   Library    │
                     │              │
                     │ SQLite + FTS5│
                     │ + Vector DB  │
                     └──────────────┘
```

### Data Flow Sequence

```
1. User Uploads Receipt
       ↓
2. DataExtractionAgent (Gemini)
   → Extracts: {vendor: "Tim Hortons", amount: 15.50, category: "meals"}
       ↓
3. CRArulesAgent (Enhanced with RAG)

   Step 3a: Query RAG Database
   ┌──────────────────────────────────────────────────────────┐
   │ qe.search("meals restaurant business deduction")         │
   │   → Returns top 5 relevant CRA rules                     │
   │   → Result: LINE-8523 (50% deduction rule for meals)     │
   └──────────────────────────────────────────────────────────┘
       ↓
   Step 3b: Build LLM Context
   ┌──────────────────────────────────────────────────────────┐
   │ Context = format_search_results([                        │
   │   {citation: "LINE-8523",                                │
   │    content: "You can deduct 50% of meal costs...",       │
   │    source: "https://canada.ca/..."}                      │
   │ ])                                                       │
   └──────────────────────────────────────────────────────────┘
       ↓
   Step 3c: LLM Reasoning with Grounded Context
   ┌──────────────────────────────────────────────────────────┐
   │ Prompt:                                                  │
   │ "Analyze this $15.50 Tim Hortons expense.               │
   │  Use ONLY these CRA rules:                              │
   │  [LINE-8523] You can deduct 50%..."                     │
   │                                                          │
   │ LLM Response:                                            │
   │ {deductible_pct: 0.5,                                    │
   │  category: "meals_and_entertainment",                    │
   │  citations: ["LINE-8523"],                               │
   │  reasoning: "Based on LINE-8523...",                     │
   │  confidence: 0.95}                                       │
   └──────────────────────────────────────────────────────────┘
       ↓
4. TaxCalculatorAgent
   → Validates: $15.50 × 50% = $7.75 deductible
       ↓
5. QuickBooks Integration
   → Posts entry with memo: "50% deductible per CRA LINE-8523"
```

---

## Quick Start (5-Minute Integration)

### Minimal Working Example

```python
# In your CRArulesAgent initialization
import qe_tax_rag as qe

class CRArulesAgent:
    def __init__(self):
        # Initialize RAG database (extracts bundled database on first run)
        qe.init()

        self.llm = TogetherAI(model="llama-3.1-70b")

    def analyze_expense(self, expense_data: dict) -> dict:
        # Step 1: Retrieve relevant CRA rules
        query = f"{expense_data['category']} {expense_data['vendor']} deduction"
        rules = qe.search(query, expense_types=[expense_data['category']], top_k=5)

        # Step 2: Format context for LLM
        context = "\n\n".join([
            f"[{r.citation_id}] {r.content}\nSource: {r.source_url}"
            for r in rules
        ])

        # Step 3: LLM reasoning with grounded context
        prompt = f"""
        Expense: {expense_data}

        CRA Rules (use ONLY these):
        {context}

        Return JSON: {{deductible_percentage, category, citations, reasoning}}
        """

        response = self.llm.generate(prompt)
        return parse_json(response)
```

**Expected Behavior:**
- First run: Extracts bundled database to `~/.qe_tax_rag/t4002.db` (instant, no network)
- Subsequent runs: Uses cached database (instant startup)
- Query latency: \<250ms for hybrid search (FTS5 + vector)
- Returns: 1-5 relevant CRA rules with citations and source URLs

---

## Step-by-Step Integration Checklist

### Phase 1: Installation & Setup (10 minutes)

#### Step 1: Install Library

**Option A: TestPyPI (Recommended for Demo)**
```bash
# In quickExpense repository
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    qe-tax-rag==0.2.4

# Or add to requirements.txt
echo "qe-tax-rag==0.2.4" >> requirements.txt
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    -r requirements.txt
```

**Option B: Production PyPI (After Demo Success)**
```bash
# Production install (when available)
pip install qe-tax-rag

# Or add to requirements.txt
echo "qe-tax-rag>=0.2.4" >> requirements.txt
pip install -r requirements.txt
```

**Acceptance Criteria:**
- ✅ `pip install qe-tax-rag==0.2.4` completes without errors
- ✅ `python -c "import qe_tax_rag as qe; print(qe.__version__)"` prints `0.2.4`
- ✅ No httpx dependency error

#### Step 2: Initialize Database (One-Time)
```bash
# Test database initialization
python -c "
import qe_tax_rag as qe
qe.init()
print('✅ Database initialized')
print('Version:', qe.get_version())
"
```

**Acceptance Criteria:**
- ✅ Database extracts successfully to `~/.qe_tax_rag/t4002.db` (instant, no network)
- ✅ Cache created at `~/.qe_tax_rag/` with version tracking
- ✅ No network calls during init
- ✅ `get_version()` returns `{'library_version': '0.2.4', 'data_version': '2024.12', 'schema_version': '1.0'}`

#### Step 3: Verify Search Works
```bash
python -c "
import qe_tax_rag as qe
qe.init()

results = qe.search('meals restaurant', expense_types=['meals'], top_k=3)
print(f'Found {len(results)} results')
print(f'Top result: {results[0].citation_id}')
print(f'Content: {results[0].content[:100]}...')
"
```

**Acceptance Criteria:**
- ✅ Returns 3 results for "meals restaurant" query
- ✅ Results include `citation_id`, `content`, `source_url`, `expense_types`
- ✅ Search completes in \<250ms
- ✅ No network activity during search

---

## Integration Validation Checklist

Use this checklist to validate your integration before the demo:

### Pre-Demo Validation (Day 1 & 2)

#### ✅ Installation Verification
- [ ] Package installed from TestPyPI without errors
- [ ] Version check returns `0.2.4`
- [ ] Database extracts to `~/.qe_tax_rag/t4002.db`
- [ ] No httpx dependency warnings

#### ✅ CRArulesAgent Integration
- [ ] `qe.init()` called in agent `__init__` or FastAPI lifespan
- [ ] Search query construction combines category, vendor, description
- [ ] RAG context formatted with citation IDs and source URLs
- [ ] LLM prompt includes explicit instruction to use ONLY provided rules
- [ ] Response parsing extracts `citations` field correctly

#### ✅ Sample Query Testing

Test with these 5 representative expense queries:

**Query 1: Meals (50% deduction)**
```python
results = qe.search("restaurant meal client meeting", expense_types=["meals"], top_k=3)
assert len(results) >= 1
assert any("50%" in r.content for r in results)
```

**Query 2: Vehicle (Per-km allowance)**
```python
results = qe.search("vehicle mileage reimbursement", expense_types=["vehicle"], top_k=3)
assert len(results) >= 1
```

**Query 3: Home Office**
```python
results = qe.search("home office workspace deduction", expense_types=["home_office"], top_k=3)
assert len(results) >= 1
```

**Query 4: Travel**
```python
results = qe.search("business travel accommodation", expense_types=["travel"], top_k=3)
assert len(results) >= 1
```

**Query 5: Office Supplies**
```python
results = qe.search("office supplies equipment", expense_types=["supplies"], top_k=3)
assert len(results) >= 1
```

**Acceptance Criteria:**
- [ ] All 5 queries return relevant results
- [ ] Citation IDs present in all results (format: `LINE-####`)
- [ ] Source URLs link to CRA documentation
- [ ] Query latency \<250ms for all queries

#### ✅ End-to-End Workflow Test

**Test Full Receipt → QuickBooks Flow:**
```python
# 1. Mock or real receipt data
expense_data = {
    "vendor": "Tim Hortons",
    "amount": 15.50,
    "category": "meals",
    "description": "Client lunch meeting",
    "date": "2025-10-29"
}

# 2. Analyze with CRArulesAgent
compliance = cra_rules_agent.analyze_expense(expense_data)

# 3. Validate response structure
assert "deductible_percentage" in compliance
assert "citations" in compliance
assert len(compliance["citations"]) > 0
assert "cra_sources" in compliance

# 4. Check citations in QuickBooks entry
quickbooks_entry = quickbooks_client.post_expense(validated)
assert any(citation in quickbooks_entry["memo"] for citation in compliance["citations"])
```

**Acceptance Criteria:**
- [ ] Full workflow completes without errors
- [ ] Deductible percentage matches CRA rules (e.g., 0.5 for meals)
- [ ] Citations appear in QuickBooks memo field
- [ ] End-to-end latency \<2 seconds

#### ✅ Error Handling & Edge Cases
- [ ] Empty query returns graceful fallback (no crash)
- [ ] Unknown expense category returns 0 results (not error)
- [ ] Missing vendor/description doesn't break search
- [ ] LLM handles "no relevant rules" case (conservative fallback)

#### ✅ Demo Rehearsal
- [ ] Practice full demo flow 2-3 times
- [ ] Prepare 3-5 sample receipts with known outcomes
- [ ] Verify citations visible in QuickBooks UI
- [ ] Test with audience-facing laptop/screen

---

## Migration to Production PyPI

**After successful demo**, migrate from TestPyPI to production PyPI with these steps:

### Step 1: Verify TestPyPI Installation Still Works
```bash
# Ensure current setup is working
python -c "import qe_tax_rag as qe; qe.init(); print(qe.get_version())"
```

### Step 2: Uninstall TestPyPI Version
```bash
pip uninstall qe-tax-rag -y
```

### Step 3: Install from Production PyPI
```bash
# Once available on production PyPI
pip install qe-tax-rag==0.2.4

# Or update requirements.txt
# Remove TestPyPI install flag
echo "qe-tax-rag==0.2.4" > requirements.txt
pip install -r requirements.txt
```

### Step 4: Verify Production Installation
```bash
python -c "
import qe_tax_rag as qe
qe.init()
version = qe.get_version()
assert version['library_version'] == '0.2.4'
print('✅ Production PyPI migration successful')
"
```

### Step 5: Update Deployment Configuration

**Docker:**
```dockerfile
# Update Dockerfile to remove TestPyPI flags
RUN pip install qe-tax-rag==0.2.4
```

**requirements.txt:**
```
# Production PyPI (no --index-url needed)
qe-tax-rag==0.2.4
```

**Acceptance Criteria:**
- ✅ Production PyPI installation works identically to TestPyPI
- ✅ No code changes required (API identical)
- ✅ Database cache reused (no re-download)
- ✅ All tests pass with production package

---

## Troubleshooting TestPyPI Installation

### Issue 1: TestPyPI Package Not Found

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement qe-tax-rag==0.2.4
```

**Solutions:**
1. **Verify TestPyPI URL:**
   ```bash
   # Check package exists on TestPyPI
   curl https://test.pypi.org/pypi/qe-tax-rag/json | grep version
   ```

2. **Use Correct Install Command:**
   ```bash
   # MUST include --extra-index-url for dependencies
   pip install --index-url https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ \
       qe-tax-rag==0.2.4
   ```

3. **Wait for Indexing:**
   - TestPyPI can take 30-60 seconds to index new uploads
   - Try again after 1 minute

---

### Issue 2: Dependency Resolution Errors

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement pydantic>=2.0
```

**Root Cause:**
- TestPyPI doesn't host all dependencies
- Missing `--extra-index-url` flag

**Solution:**
```bash
# Always include --extra-index-url for production PyPI dependencies
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    qe-tax-rag==0.2.4
```

---

### Issue 3: httpx Import Error (v0.2.2 or earlier)

**Symptoms:**
```
ModuleNotFoundError: No module named 'httpx'
```

**Root Cause:**
- Installing v0.2.2 or earlier (eager import bug)

**Solution:**
```bash
# Uninstall and reinstall v0.2.4
pip uninstall qe-tax-rag -y
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    qe-tax-rag==0.2.4

# Verify version
python -c "import qe_tax_rag; assert qe_tax_rag.__version__ == '0.2.4'"
```

---

### Issue 4: Database Not Extracting

**Symptoms:**
```python
qe.init()
# FileNotFoundError: Database not found
```

**Root Cause:**
- Bundled database missing from wheel
- Cache directory not writable

**Solutions:**
1. **Verify Wheel Contents:**
   ```bash
   unzip -l $(pip show qe-tax-rag | grep Location)/qe_tax_rag-*.whl | grep t4002.db
   ```

2. **Check Cache Permissions:**
   ```bash
   ls -ld ~/.qe_tax_rag
   # Should be writable by current user
   ```

3. **Manual Cache Creation:**
   ```bash
   mkdir -p ~/.qe_tax_rag
   chmod 755 ~/.qe_tax_rag
   ```

---

### Issue 5: Version Mismatch After Update

**Symptoms:**
```python
print(qe.__version__)  # Shows 0.2.3 instead of 0.2.4
```

**Root Cause:**
- Old version cached in pip

**Solution:**
```bash
# Force reinstall
pip uninstall qe-tax-rag -y
pip cache purge
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    qe-tax-rag==0.2.4
```

---

### Phase 2: Agent Integration (15 minutes)

#### Step 4: Add RAG to CRArulesAgent Class

**Conceptual Interface:**
```python
class CRArulesAgent:
    """Enhanced CRA compliance agent with RAG retrieval"""

    def __init__(self):
        # Initialize RAG database once at agent startup
        qe.init()

        # Existing LLM initialization
        self.llm = TogetherAI(model="llama-3.1-70b")

    def analyze_expense(self, expense_data: dict) -> dict:
        """
        Analyzes expense for CRA compliance using RAG + LLM

        Args:
            expense_data: {
                "vendor": str,          # e.g., "Tim Hortons"
                "amount": float,        # e.g., 15.50
                "category": str,        # e.g., "meals"
                "description": str,     # e.g., "Client lunch meeting"
                "date": str            # e.g., "2025-01-15"
            }

        Returns:
            {
                "deductible_percentage": float,  # 0.0 - 1.0
                "category": str,                 # "meals_and_entertainment"
                "citations": list[str],          # ["LINE-8523"]
                "reasoning": str,                # "Based on LINE-8523..."
                "confidence": float,             # 0.0 - 1.0
                "cra_sources": list[str]         # [source URLs]
            }
        """

        # STEP 1: Retrieve relevant CRA rules
        query = self._build_search_query(expense_data)
        cra_rules = qe.search(
            query=query,
            expense_types=[expense_data.get("category")],
            top_k=5
        )

        # STEP 2: Build context from retrieved rules
        context = self._format_context_for_llm(cra_rules)

        # STEP 3: LLM reasoning with grounded context
        prompt = self._build_compliance_prompt(expense_data, context)
        llm_response = self.llm.generate(prompt)

        # STEP 4: Parse and validate response
        result = self._parse_llm_response(llm_response)
        result["cra_sources"] = [r.source_url for r in cra_rules]

        return result
```

**Acceptance Criteria:**
- ✅ `qe.init()` called once in `__init__` (not per expense)
- ✅ `analyze_expense()` calls `qe.search()` for each expense
- ✅ Returns dict with required fields: `deductible_percentage`, `category`, `citations`
- ✅ `cra_sources` contains URLs to official CRA documentation

#### Step 5: Implement Helper Methods

**Search Query Builder:**
```python
def _build_search_query(self, expense_data: dict) -> str:
    """
    Constructs semantic search query from expense metadata

    Args:
        expense_data: Expense dict with vendor, category, description

    Returns:
        Query string optimized for hybrid search
    """
    parts = [
        expense_data.get("category", ""),
        expense_data.get("vendor", ""),
        expense_data.get("description", ""),
        "deduction rules"
    ]

    return " ".join(filter(None, parts))
```

**Context Formatter:**
```python
def _format_context_for_llm(self, results: list) -> str:
    """
    Formats search results into LLM-ready context string

    Args:
        results: List of SearchResult objects from qe.search()

    Returns:
        Formatted string with citations and content
    """
    if not results:
        return "No specific CRA rules found. Use general tax principles."

    context_parts = []
    for i, result in enumerate(results, 1):
        context_parts.append(
            f"[{i}] Citation: {result.citation_id}\n"
            f"    Rule: {result.content}\n"
            f"    Source: {result.source_url}\n"
        )

    return "\n".join(context_parts)
```

**Acceptance Criteria:**
- ✅ `_build_search_query()` combines category, vendor, description into query
- ✅ `_format_context_for_llm()` includes citation IDs and source URLs
- ✅ Context string is LLM-readable (numbered list format)
- ✅ Handles empty results gracefully

#### Step 6: Update LLM Prompt Template

**Compliance Prompt:**
```python
def _build_compliance_prompt(self, expense_data: dict, context: str) -> str:
    """
    Constructs LLM prompt with grounded CRA context

    Args:
        expense_data: Expense metadata
        context: Formatted CRA rules from RAG

    Returns:
        Complete prompt for LLM
    """
    return f"""
You are a CRA tax compliance assistant. Analyze this expense using ONLY the provided CRA rules.

Expense Details:
- Vendor: {expense_data['vendor']}
- Amount: ${expense_data['amount']:.2f}
- Category: {expense_data['category']}
- Description: {expense_data.get('description', 'N/A')}
- Date: {expense_data.get('date', 'N/A')}

CRA Rules (use ONLY these - do not rely on training data):
{context}

Determine:
1. Deductible percentage (0.0 - 1.0)
2. Expense category classification
3. Citations from above rules (use citation IDs)
4. Reasoning based ONLY on provided CRA rules
5. Confidence score (0.0 - 1.0)

CRITICAL: If the provided rules don't cover this expense type, set deductible_percentage to 0.0 and explain in reasoning.

Response format (JSON):
{{
    "deductible_percentage": 0.5,
    "category": "meals_and_entertainment",
    "citations": ["LINE-8523"],
    "reasoning": "Based on LINE-8523...",
    "confidence": 0.95
}}
"""
```

**Acceptance Criteria:**
- ✅ Prompt explicitly instructs LLM to use ONLY provided rules
- ✅ Includes all expense metadata (vendor, amount, category, description, date)
- ✅ Specifies JSON output format with required fields
- ✅ Handles cases where rules don't cover expense type (conservative fallback)

---

### Phase 3: FastAPI Lifespan Integration (5 minutes)

#### Step 7: Initialize on Application Startup

**FastAPI Lifespan Pattern:**
```python
# In your FastAPI app's main file (e.g., main.py or app.py)
from contextlib import asynccontextmanager
from fastapi import FastAPI
import qe_tax_rag as qe
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Initializes qe-tax-rag database on startup before handling requests.
    Ensures database is ready for all agents.
    """
    # Startup: Initialize RAG database
    db_path = os.environ.get("QE_TAX_RAG_DB_PATH", "/data/qe_tax_rag")
    qe.init(path=db_path)
    print(f"✅ qe-tax-rag initialized: {qe.get_version()}")

    yield  # Application runs here

    # Shutdown: Cleanup if needed
    print("✅ qe-tax-rag shutdown")

app = FastAPI(lifespan=lifespan)
```

**Acceptance Criteria:**
- ✅ `qe.init()` called once on FastAPI startup (before first request)
- ✅ Database path configurable via `QE_TAX_RAG_DB_PATH` environment variable
- ✅ Version info logged on successful initialization
- ✅ Application fails loudly if database initialization fails

#### Step 8: Configure Environment Variables

**Docker Compose Example:**
```yaml
# docker-compose.yml
services:
  quickexpense-api:
    build: .
    environment:
      - QE_TAX_RAG_DB_PATH=/data/qe_tax_rag
    volumes:
      - qe-rag-cache:/data/qe_tax_rag  # Persistent cache

volumes:
  qe-rag-cache:
```

**Kubernetes ConfigMap Example:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: quickexpense-config
data:
  QE_TAX_RAG_DB_PATH: "/mnt/shared/qe_tax_rag"
```

**Acceptance Criteria:**
- ✅ `QE_TAX_RAG_DB_PATH` points to writable directory
- ✅ Volume persists across container restarts (avoid re-download)
- ✅ Multi-instance deployments can share read-only database file

---

### Phase 4: Testing & Validation (10 minutes)

#### Step 9: Unit Tests with Mocked RAG

**Test Pattern:**
```python
# tests/unit/test_cra_agent.py
from unittest.mock import patch, MagicMock
import pytest

def test_analyze_expense_with_mocked_rag():
    """Unit test: CRArulesAgent with mocked qe.search()"""

    # Mock search results
    mock_result = MagicMock()
    mock_result.citation_id = "LINE-8523"
    mock_result.content = "You can deduct 50% of meal costs..."
    mock_result.source_url = "https://canada.ca/..."

    with patch('qe_tax_rag.search', return_value=[mock_result]):
        agent = CRArulesAgent()

        result = agent.analyze_expense({
            "vendor": "Tim Hortons",
            "amount": 15.50,
            "category": "meals"
        })

        assert result["deductible_percentage"] == 0.5
        assert "LINE-8523" in result["citations"]
```

**Acceptance Criteria:**
- ✅ Unit tests don't require actual database download
- ✅ `qe.search()` mocked to return known results
- ✅ Tests verify agent correctly uses RAG output
- ✅ Tests cover empty results, missing fields, invalid data

#### Step 10: Integration Tests with Fixture Database

**Test Pattern (using future `qe_tax_rag.testing` module):**
```python
# tests/integration/test_cra_agent_integration.py
from qe_tax_rag.testing import qe_test_db  # Provided by library
import pytest

def test_analyze_expense_real_rag(qe_test_db):
    """Integration test: CRArulesAgent with real test database"""

    agent = CRArulesAgent()

    # Test with known expense in fixture database
    result = agent.analyze_expense({
        "vendor": "Restaurant ABC",
        "amount": 100.00,
        "category": "meals",
        "description": "Client dinner meeting"
    })

    # Assertions based on known test data
    assert result["deductible_percentage"] == 0.5
    assert "LINE-8523" in result["citations"]
    assert len(result["cra_sources"]) > 0
```

**Acceptance Criteria:**
- ✅ Uses `qe_test_db` fixture for deterministic testing
- ✅ Test database contains 5-10 known rules with expected queries
- ✅ Tests verify end-to-end RAG → LLM → response flow
- ✅ Tests check citation IDs are properly propagated

#### Step 11: End-to-End Test with Production Database

**Test Pattern:**
```python
# tests/e2e/test_full_workflow.py
import pytest

@pytest.mark.e2e
@pytest.mark.slow
def test_full_receipt_processing_workflow():
    """E2E test: Full receipt → QuickBooks flow with RAG"""

    # Step 1: Upload receipt (DataExtractionAgent)
    receipt = upload_receipt("tests/fixtures/tim_hortons_receipt.pdf")

    # Step 2: Extract data (Gemini)
    extracted = data_extraction_agent.process(receipt)
    assert extracted["vendor"] == "Tim Hortons"

    # Step 3: Analyze with CRArulesAgent (with RAG)
    compliance = cra_rules_agent.analyze_expense(extracted)
    assert compliance["deductible_percentage"] == 0.5
    assert len(compliance["citations"]) > 0

    # Step 4: Validate (TaxCalculatorAgent)
    validated = tax_calculator_agent.validate(extracted, compliance)
    assert validated["deductible_amount"] == 7.75  # $15.50 × 50%

    # Step 5: Post to QuickBooks
    entry = quickbooks_client.post_expense(validated)
    assert "LINE-8523" in entry["memo"]
```

**Acceptance Criteria:**
- ✅ Full workflow from receipt upload to QuickBooks posting works
- ✅ CRA citations appear in QuickBooks memo field
- ✅ Deductible percentages match CRA rules from database
- ✅ Test uses production database (not fixture)

---

## API Usage Patterns

### Pattern 1: Simple Expense Analysis

**Use Case:** Single expense needs CRA rule lookup

```python
# Input
expense = {
    "vendor": "Staples",
    "amount": 45.99,
    "category": "office_equipment"
}

# RAG Query
results = qe.search(
    query="office supplies equipment deduction",
    expense_types=["office_equipment"],
    top_k=3
)

# Output
for r in results:
    print(f"{r.citation_id}: {r.content[:100]}...")
    # LINE-9234: Office supplies and equipment are...
```

**When to Use:**
- Single expense from user upload
- Interactive expense review
- User asks "Is this deductible?"

**Expected Performance:**
- Query latency: \<250ms
- Results: 1-5 relevant rules
- Relevance: Hybrid FTS5 + semantic search (BGE embeddings)

---

### Pattern 2: Batch Expense Processing

**Use Case:** Nightly batch processing of 100+ expenses

```python
# Future API (not yet implemented - see roadmap)
expenses = [
    {"vendor": "Tim Hortons", "amount": 15.50, "category": "meals"},
    {"vendor": "Shell Gas", "amount": 65.00, "category": "vehicle"},
    {"vendor": "Office Depot", "amount": 89.99, "category": "supplies"},
    # ... 97 more
]

# Batch search (conceptual)
queries = [f"{e['category']} {e['vendor']} deduction" for e in expenses]
results_batch = qe.search_batch(queries, top_k=3)

# Process results
for expense, rules in zip(expenses, results_batch):
    context = format_context(rules)
    compliance = llm_analyze(expense, context)
```

**When to Use:**
- Nightly batch expense processing
- Bulk import from accounting software
- Historical data re-analysis

**Expected Performance:**
- Batch latency: \<5 seconds for 100 queries
- Throughput: ~20 queries/second
- Memory: \<500MB for full batch

---

### Pattern 3: Multi-Turn Conversation

**Use Case:** User asks follow-up questions about specific expense

```python
# Turn 1: Initial expense analysis
query1 = "restaurant meals client meeting deduction"
rules1 = qe.search(query1, expense_types=["meals"], top_k=5)
llm_response1 = llm.generate(context=format_context(rules1))
# Response: "50% deductible based on LINE-8523"

# Turn 2: User asks clarification
query2 = "what about meals with employees instead of clients"
rules2 = qe.search(query2, expense_types=["meals"], top_k=5)
llm_response2 = llm.generate(
    context=format_context(rules2),
    conversation_history=[
        {"role": "user", "content": query1},
        {"role": "assistant", "content": llm_response1},
        {"role": "user", "content": query2}
    ]
)
# Response: "Employee meals are 100% deductible based on LINE-9456"
```

**When to Use:**
- Interactive chat interface
- User requests clarification on specific rules
- Complex multi-part questions

**Optimization:**
- Cache search results per session (avoid redundant queries)
- Use conversation history for LLM context, not RAG context

---

### Pattern 4: Filtering by Expense Type

**Use Case:** Pre-filter RAG search by known expense category

```python
# Scenario: User categorized expense as "vehicle"
results_vehicle = qe.search(
    query="mileage reimbursement",
    expense_types=["vehicle", "travel"],  # OR filter
    top_k=5
)

# Only returns rules tagged with vehicle OR travel expense types
# Filters out: meals, home_office, supplies, etc.
```

**Supported Expense Types:**
- `meals`, `travel`, `vehicle`, `home_office`
- `advertising`, `supplies`, `professional_fees`
- `utilities`, `insurance`, `capital`
- `maintenance`, `salaries`, `office_equipment`
- `interest`, `bad_debts`

**When to Use:**
- Known expense category from DataExtractionAgent
- User explicitly selects category
- Narrow search space for faster results

---

### Pattern 5: Citation Formatting for QuickBooks

**Use Case:** Format citations for QuickBooks memo field

```python
# RAG results
rules = qe.search("meals", expense_types=["meals"], top_k=3)

# Format citations for QuickBooks memo (max 4000 chars)
citations = [f"{r.citation_id}" for r in rules]
memo = f"50% deductible per CRA {', '.join(citations)}"
# Output: "50% deductible per CRA LINE-8523, LINE-9234"

# Post to QuickBooks
quickbooks_client.create_expense({
    "account": "Meals and Entertainment",
    "amount": 15.50,
    "deductible_amount": 7.75,
    "memo": memo  # Includes CRA citations
})
```

**When to Use:**
- Every QuickBooks posting
- Audit trail for CRA compliance
- User wants to see which rules were applied

**Memo Field Best Practices:**
- Keep citations concise (LINE-XXX format)
- Limit to 3-5 citations max
- Include deductible percentage + citation IDs

---

## Testing Strategy

### Testing Pyramid

```
                    ┌──────────┐
                    │   E2E    │  ← 5% (Full workflow, production DB)
                    │  Tests   │
                   ┌┴──────────┴┐
                   │ Integration │ ← 20% (Real RAG, fixture DB)
                   │    Tests    │
                  ┌┴─────────────┴┐
                  │  Unit Tests    │ ← 75% (Mocked qe.search())
                  │  (Fast)        │
                  └────────────────┘
```

### Unit Tests (Fast, No Database)

**Scope:**
- Agent logic with mocked `qe.search()`
- Helper methods (`_build_query`, `_format_context`)
- Error handling and edge cases

**Example:**
```python
def test_build_search_query():
    agent = CRArulesAgent()

    query = agent._build_search_query({
        "vendor": "Tim Hortons",
        "category": "meals",
        "description": "Client lunch"
    })

    assert "meals" in query
    assert "Tim Hortons" in query
    assert "Client lunch" in query
```

**Run Command:**
```bash
pytest tests/unit -v -m "not slow"
```

**Acceptance Criteria:**
- ✅ All unit tests run in \<10 seconds total
- ✅ No network calls or file I/O
- ✅ Code coverage \>80% for CRArulesAgent class

---

### Integration Tests (Medium, Fixture Database)

**Scope:**
- End-to-end RAG flow with known test data
- Verify search results match expected citations
- Test error handling with real database

**Example:**
```python
from qe_tax_rag.testing import qe_test_db

def test_meals_expense_analysis(qe_test_db):
    """Test RAG returns LINE-8523 for meals query"""

    results = qe.search("restaurant meals", expense_types=["meals"], top_k=3)

    assert len(results) >= 1
    assert any("LINE-8523" in r.citation_id for r in results)
    assert any("50%" in r.content for r in results)
```

**Run Command:**
```bash
pytest tests/integration -v
```

**Acceptance Criteria:**
- ✅ All integration tests run in \<30 seconds total
- ✅ Uses deterministic fixture database (5-10 rules)
- ✅ Tests cover all major expense types (meals, travel, vehicle, home_office)

---

### End-to-End Tests (Slow, Production Database)

**Scope:**
- Full receipt → QuickBooks workflow
- Real production database (662 rules)
- Performance benchmarks

**Example:**
```python
@pytest.mark.e2e
@pytest.mark.slow
def test_full_receipt_workflow():
    """E2E: Receipt upload → QuickBooks posting with CRA citations"""

    # Upload receipt
    receipt = upload_receipt("tests/fixtures/restaurant_receipt.pdf")

    # Process through all agents
    extracted = data_extraction_agent.process(receipt)
    compliance = cra_rules_agent.analyze_expense(extracted)
    validated = tax_calculator_agent.validate(extracted, compliance)

    # Verify citations in final output
    assert len(compliance["citations"]) > 0
    assert compliance["deductible_percentage"] > 0

    # Verify QuickBooks posting
    entry = quickbooks_client.post_expense(validated)
    assert any(cit in entry["memo"] for cit in compliance["citations"])
```

**Run Command:**
```bash
pytest tests/e2e -v -m e2e --slow
```

**Acceptance Criteria:**
- ✅ E2E tests run in \<5 minutes total
- ✅ Uses production database (662 rules)
- ✅ Tests cover at least 5 different expense categories
- ✅ Performance benchmarks: query latency \<250ms, end-to-end \<2 seconds

---

## Deployment Considerations

### Environment Configuration

**Environment Variables:**
```bash
# Required
export QE_TAX_RAG_DB_PATH="/data/qe_tax_rag"  # Database cache location

# Optional
export QE_TAX_RAG_DEFAULT_TOP_K=5             # Default search results
export QE_TAX_RAG_EMBEDDING_DEVICE="cpu"      # or "cuda" for GPU
```

**Docker Deployment:**
```dockerfile
# Dockerfile
FROM python:3.12-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Configure RAG cache
ENV QE_TAX_RAG_DB_PATH=/data/qe_tax_rag
RUN mkdir -p /data/qe_tax_rag && chmod 777 /data/qe_tax_rag

# Copy application
COPY . /app
WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker Compose:**
```yaml
version: '3.8'

services:
  quickexpense-api:
    build: .
    environment:
      - QE_TAX_RAG_DB_PATH=/data/qe_tax_rag
    volumes:
      - qe-rag-cache:/data/qe_tax_rag  # Persistent volume
    ports:
      - "8000:8000"

volumes:
  qe-rag-cache:
    driver: local
```

**Acceptance Criteria:**
- ✅ Database persists across container restarts
- ✅ Cache directory is writable by application user
- ✅ Volume size sufficient for 10MB database (future growth)

---

### Multi-Instance Deployments

**Scenario:** Multiple FastAPI workers or Kubernetes pods

**Pattern: Shared Read-Only Database**
```yaml
# Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quickexpense-api
spec:
  replicas: 3  # Multiple pods
  template:
    spec:
      containers:
      - name: api
        image: quickexpense:latest
        env:
        - name: QE_TAX_RAG_DB_PATH
          value: "/mnt/shared/qe_tax_rag"
        volumeMounts:
        - name: shared-db
          mountPath: /mnt/shared/qe_tax_rag
          readOnly: true  # Read-only for all pods
      volumes:
      - name: shared-db
        persistentVolumeClaim:
          claimName: qe-rag-pvc
```

**Why Read-Only is Safe:**
- SQLite handles concurrent reads gracefully
- No write operations during request processing
- Only startup `init()` writes to cache (one-time per deployment)

**Acceptance Criteria:**
- ✅ Multiple pods/workers share same database file
- ✅ No file locking issues or race conditions
- ✅ All instances use same database version (atomic deployment)

---

### Performance Optimization

**Caching Strategy:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_search(query: str, category: str | None = None) -> list:
    """Cache search results to avoid redundant RAG queries"""
    return qe.search(query, expense_types=[category] if category else None, top_k=5)
```

**Why Cache:**
- Same queries repeat (e.g., "meals" appears in 30% of expenses)
- Cached queries return instantly (no DB access)
- LRU eviction ensures memory usage stays bounded

**Benchmark Results:**
- Uncached query: 150-250ms (hybrid FTS5 + vector search)
- Cached query: \<1ms (memory lookup)
- Memory overhead: \~10KB per cached query × 1000 = 10MB

**Acceptance Criteria:**
- ✅ Cache hit rate \>60% in production workloads
- ✅ Memory usage \<50MB for cache (monitor with `@lru_cache` stats)
- ✅ Cache invalidation on library version upgrade

---

### Monitoring & Observability

**Metrics to Track:**
```python
# Query latency
histogram("qe_rag_query_duration_ms", value=latency_ms, tags={"category": category})

# Cache hit rate
counter("qe_rag_cache_hit", tags={"hit": True/False})

# Search result counts
gauge("qe_rag_results_returned", value=len(results), tags={"query_type": query_type})

# Error rates
counter("qe_rag_errors", tags={"error_type": error.__class__.__name__})
```

**Logging Best Practices:**
```python
import logging

logger = logging.getLogger(__name__)

def analyze_expense(self, expense_data: dict) -> dict:
    logger.info(f"Analyzing expense: {expense_data['vendor']} (${expense_data['amount']})")

    results = qe.search(query, expense_types=[category], top_k=5)
    logger.info(f"RAG returned {len(results)} results for category '{category}'")

    if len(results) == 0:
        logger.warning(f"No CRA rules found for query: '{query}'")

    return compliance_result
```

**Acceptance Criteria:**
- ✅ Query latency p50 \<200ms, p99 \<500ms
- ✅ Cache hit rate \>60% after 1 hour of production traffic
- ✅ Error rate \<0.1% (database read errors, cache failures)
- ✅ Logs include expense metadata for debugging (vendor, category, amount)

---

## Troubleshooting

### Issue 1: No Search Results for Valid Queries

**Symptoms:**
```python
results = qe.search("meals restaurant", expense_types=["meals"], top_k=5)
print(len(results))  # 0
```

**Root Causes:**
- Query too specific (no exact matches in 662 rules)
- Wrong expense type filter (database uses different category names)
- Typos in query

**Solutions:**
1. **Broaden Query:**
   ```python
   # Too specific
   results = qe.search("Tim Hortons client lunch meeting deduction")  # 0 results

   # Better: Use general terms
   results = qe.search("meals restaurant", expense_types=["meals"])  # 5+ results
   ```

2. **Remove Filters:**
   ```python
   # Without filter (searches all expense types)
   results = qe.search("meals", top_k=5)
   ```

3. **Verify Expense Types:**
   ```python
   # Check supported expense types
   from qe_tax_rag.search.enums import ExpenseType
   print(list(ExpenseType))
   # ['meals', 'travel', 'vehicle', 'home_office', ...]
   ```

**Prevention:**
- Use general CRA terminology (not vendor names)
- Start with broad queries, then narrow with filters
- Log queries and result counts for debugging

---

### Issue 2: High Query Latency (\>500ms)

**Symptoms:**
- Search queries taking \>500ms
- Slow receipt processing workflow

**Root Causes:**
- Cold start (first query after app restart)
- Large result sets (`top_k=100`)
- No caching enabled

**Solutions:**
1. **Enable Query Caching:**
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def cached_search(query: str, category: str = None):
       return qe.search(query, expense_types=[category] if category else None, top_k=5)
   ```

2. **Reduce `top_k`:**
   ```python
   # Only need top 3-5 results for LLM context
   results = qe.search(query, top_k=3)  # Faster than top_k=10
   ```

3. **Warm Up Cache on Startup:**
   ```python
   # In FastAPI lifespan
   async def lifespan(app: FastAPI):
       qe.init()

       # Warm up common queries
       qe.search("meals", top_k=3)
       qe.search("travel", top_k=3)
       qe.search("vehicle", top_k=3)

       yield
   ```

**Benchmarks:**
- Cold start (first query): 200-300ms
- Warm cache (subsequent): 150-200ms
- With LRU cache: \<1ms (cache hit)

---

### Issue 3: Version Compatibility Errors

**Symptoms:**
```
DataVersionMismatchError: Database version 2024.12 incompatible with library version 0.2.4
```

**Root Causes:**
- Library updated but database not refreshed
- Cached old database version from different package version
- Schema breaking changes

**Solutions:**
1. **Clear Cache and Reinstall:**
   ```bash
   rm -rf ~/.qe_tax_rag/
   pip uninstall qe-tax-rag -y
   pip install --index-url https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ \
       qe-tax-rag==0.2.4
   ```

2. **Verify Version Match:**
   ```python
   import qe_tax_rag as qe
   qe.init()
   version = qe.get_version()
   print(version)  # library_version should match package version
   ```

**Prevention:**
- Pin exact library versions in `requirements.txt`: `qe-tax-rag==0.2.4`
- Monitor library release notes for breaking changes
- Use version pinning in production: avoid auto-upgrades
- Database version automatically updates with package (bundled)

---

## Acceptance Criteria Summary

### Installation & Setup
- ✅ Library installs via `pip install qe-tax-rag==0.2.4` without errors (TestPyPI or production)
- ✅ Database extracts successfully on first `init()` (instant, no network)
- ✅ `get_version()` returns expected version metadata
- ✅ Search returns 1-5 results for "meals restaurant" query
- ✅ No httpx dependency required

### Agent Integration
- ✅ `qe.init()` called once on FastAPI startup (lifespan event)
- ✅ `analyze_expense()` calls `qe.search()` for each expense
- ✅ Returns dict with `deductible_percentage`, `category`, `citations`, `cra_sources`
- ✅ LLM prompt includes RAG context with citation IDs

### Testing
- ✅ Unit tests run in \<10 seconds (mocked RAG)
- ✅ Integration tests run in \<30 seconds (fixture DB)
- ✅ E2E tests run in \<5 minutes (production DB)
- ✅ Code coverage \>80% for CRArulesAgent class

### Deployment
- ✅ Works in Docker with persistent volume
- ✅ Multi-instance deployments share read-only database
- ✅ Query latency p50 \<200ms, p99 \<500ms
- ✅ Cache hit rate \>60% after 1 hour of production traffic
- ✅ Offline operation (no network dependency after install)

### Production Readiness
- ✅ No external network dependencies (bundled database)
- ✅ Logs include expense metadata for debugging
- ✅ Metrics track query latency, cache hit rate, error rate
- ✅ QuickBooks entries include CRA citation IDs in memo field

---

## Next Steps

### Immediate (This Week)
1. Install `qe-tax-rag` in quickExpense repository
2. Add FastAPI lifespan initialization
3. Update CRArulesAgent to call `qe.search()`
4. Write unit tests with mocked RAG

### Short Term (This Month)
1. Deploy to staging environment with Docker
2. Run integration tests with fixture database
3. Benchmark query performance and optimize
4. Add logging and metrics

### Long Term (Next Quarter)
1. Monitor production metrics (latency, cache hit rate)
2. Collect user feedback on citation quality
3. Expand database to additional CRA documents
4. Implement batch search API for nightly processing

---

## Resources

- **Library Documentation:** [README.md](../README.md)
- **API Reference:** [API.md](./API.md)
- **TestPyPI Package:** [test.pypi.org/project/qe-tax-rag/0.2.4](https://test.pypi.org/project/qe-tax-rag/0.2.4/)
- **quickExpense Repository:** [github.com/manonja/quickExpense](https://github.com/manonja/quickExpense)
- **CRA T4002 Guide:** [canada.ca/t4002](https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4002.html)

---

## Support

For integration questions or issues:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review [examples/basic_rag.py](../examples/basic_rag.py) for reference implementation
3. Open issue: [github.com/manonja/quickExpense-rag/issues](https://github.com/manonja/quickExpense-rag/issues)
4. Email: support@quickexpense.example.com

**Legal Disclaimer:** This integration guide and the qe-tax-rag library are for informational purposes only and do not constitute tax advice. Always consult a qualified tax professional for advice specific to your situation.
