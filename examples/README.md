# QE Tax RAG Examples

This directory contains working examples demonstrating how to use QE Tax RAG for
building tax Q&A systems with Retrieval-Augmented Generation (RAG).

## ⚠️ IMPORTANT: NOT TAX ADVICE

**These examples are for educational purposes only and do not constitute tax advice.**
Always consult with a qualified tax professional before making financial decisions.

## Available Examples

### 1. Basic RAG Example

Two formats demonstrating the same workflow:

- **`basic_rag.py`** - Standalone Python script (run from command line)
- **`basic_rag.ipynb`** - Jupyter notebook (interactive exploration)

Both examples demonstrate:

1. **Environment Setup** - Loading API keys and configuring the library
1. **Database Initialization** - Downloading and verifying the CRA rules database
1. **Basic Search** - Querying expense rules without LLM integration
1. **RAG Pipeline** - Building context and generating AI responses with citations
1. **Output Formatting** - Displaying results with proper disclaimers
1. **Advanced Patterns** - Error handling, caching, multi-turn conversations

## Prerequisites

### Required

- Python 3.12 or higher
- QE Tax RAG library: `pip install qe-tax-rag`

### Optional (for RAG examples)

At least one LLM API key:

- **OpenAI** - Get key from [platform.openai.com](https://platform.openai.com)
- **Anthropic Claude** - Get key from
  [console.anthropic.com](https://console.anthropic.com)
- **Google Gemini** - Get key from [ai.google.dev](https://ai.google.dev)

## Setup Instructions

### 1. Install Dependencies

Install the QE Tax RAG library:

```bash
pip install qe-tax-rag
```

For RAG examples, install optional dependencies:

```bash
pip install -r examples/requirements.txt
```

Or with uv:

```bash
uv pip install qe-tax-rag
uv pip install -r examples/requirements.txt
```

### 2. Configure API Keys

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API key(s):

```bash
# For OpenAI
OPENAI_API_KEY=sk-...

# For Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# For Google Gemini
GEMINI_API_KEY=...
```

**Note:** You only need ONE API key to run the examples. The code includes examples for
all three providers.

### 3. Run the Examples

#### Option A: Python Script

```bash
python examples/basic_rag.py
```

With custom query:

```bash
python examples/basic_rag.py --query "Can I deduct home office expenses for my sole proprietorship?"
```

#### Option B: Jupyter Notebook

```bash
# Install Jupyter if you don't have it
pip install jupyter

# Start Jupyter and open the notebook
jupyter notebook examples/basic_rag.ipynb
```

Then run cells sequentially or use "Run All".

## What to Expect

### First Run

On first run, the library will:

1. Download the CRA rules database (~1.7 MB) from GitHub Releases
1. Verify SHA256 checksum
1. Cache the database locally (`~/.cache/qe_tax_rag/`)
1. Display database metadata (version, schema, chunk count)

Subsequent runs use the cached database.

### Search Results

Basic search (no LLM) returns:

- **Citation ID** - Unique identifier for verification (e.g., `LINE-8523`)
- **Content** - Text excerpt from CRA documents
- **Source URL** - Link to original CRA publication
- **Expense Types** - Classified categories (meals, travel, vehicle, etc.)
- **Lineage** - Extraction source and timestamp

### RAG Pipeline Output

RAG examples with LLM integration show:

- AI-generated answer based on CRA excerpts
- Citations linking answer to source documents
- Legal disclaimers reminding users to consult professionals
- Token usage and API call metrics

## Example Query Results

**Query:** "Can I deduct restaurant meals for client meetings in BC?"

**Search Results** (without LLM):

```
Citation ID: LINE-8523
Content: You can deduct 50% of the cost of food, beverages, and
         entertainment when they are consumed...
Source: https://www.canada.ca/en/revenue-agency/...
Expense Types: ['meals', 'entertainment']
```

**RAG Response** (with LLM):

```
Based on CRA guidelines, you can deduct 50% of restaurant meal costs
for client meetings. This applies when meals are consumed during
business activities [LINE-8523].

However, the 50% limit applies to both the meal cost and any
associated entertainment expenses [LINE-8523].

⚠️ This is informational only - consult a tax professional for
advice specific to your situation.
```

## Troubleshooting

### Database Download Fails

**Error:** "Failed to download database from GitHub Releases"

**Solutions:**

- Check internet connection
- Verify GitHub is accessible (not blocked by firewall)
- Try manual download:
  [Release URL](https://github.com/manonja/qe-tax-rag/releases/download/data-v2025.10.23/cra_rules.db)
- Place downloaded file in: `~/.cache/qe_tax_rag/cra_rules.db`

### Missing API Key

**Error:** "No API key found for [provider]"

**Solutions:**

- Ensure `.env` file exists in project root
- Check API key is not empty: `OPENAI_API_KEY=sk-...`
- Verify environment variable is loaded:
  `python -c "import os; print(os.getenv('OPENAI_API_KEY'))"`
- Restart terminal/IDE after editing `.env`

### Import Errors

**Error:** "ModuleNotFoundError: No module named 'qe_tax_rag'"

**Solutions:**

- Install library: `pip install qe-tax-rag`
- Check Python version: `python --version` (must be 3.12+)
- Use virtual environment: `python -m venv venv && source venv/bin/activate`

### LLM API Errors

**Error:** "Rate limit exceeded" or "Invalid API key"

**Solutions:**

- **Rate limits:** Add retry logic or wait before retrying
- **Invalid key:** Verify key is correct and active
- **Billing:** Ensure API account has credits/billing enabled
- **Try alternative provider:** Examples support OpenAI, Anthropic, and Gemini

### Empty Search Results

**Behavior:** Query returns no results

**Solutions:**

- Try broader query terms: "meals" instead of "restaurant dining"
- Remove filters: Don't specify province/business_type if unsure
- Check query spelling and terminology
- Use semantic search by avoiding overly specific keywords

## Advanced Usage

### Multi-Turn Conversations

Build context across multiple queries:

```python
import qe_tax_rag as qe

qe.init()

# First question
results1 = qe.search("vehicle expenses", top_k=5)
# ... build context and get LLM response ...

# Follow-up question (maintain conversation context)
results2 = qe.search("what about electric vehicles?", top_k=3)
# ... combine with previous context for multi-turn conversation ...
```

### Custom Filtering

Filter by province and business type:

```python
results = qe.search(
    query="home office deduction",
    province="BC",
    business_type="sole_proprietorship",
    expense_types=["home_office"],
    top_k=10
)
```

### Caching Search Results

Avoid redundant searches and API calls:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query: str, province: str | None = None):
    import qe_tax_rag as qe
    return qe.search(query, province=province)

# First call: queries database
results1 = cached_search("meal expenses", province="BC")

# Second call: returns cached results (no database query)
results2 = cached_search("meal expenses", province="BC")
```

## Additional Resources

- **Main Documentation:** [README.md](../README.md)
- **API Reference:** See docstrings in library code
- **GitHub Issues:**
  [Report bugs or request features](https://github.com/manonja/quickExpense-rag/issues)
- **CRA Source:**
  [T4002 Guide](https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4002.html)

## License

Examples are provided under MIT License. See [LICENSE](../LICENSE) for details.

CRA content excerpts are © Crown Copyright. Used for educational purposes.
