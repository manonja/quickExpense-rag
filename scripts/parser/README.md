# Gemini Flash Parser (TICKET 9B)

Document parser using Gemini 2.0 Flash for structured CRA document extraction.

## Overview

This parser converts preprocessed CRA documents (clean text) into structured JSON chunks compatible with the indexing pipeline (TICKET 9C).

## Components

### 1. **Pydantic Schema** (`schema.py`)
Hierarchical models for structured parsing:
- `ParsedDocument` → `Section` → `ContentItem`
- Content types: `TextChunk`, `ListChunk`, `TableChunk`
- Includes `to_flat_chunks()` for JSONL conversion

### 2. **GeminiParser** (`gemini_parser.py`)
Main parser using Gemini API:
- **Model**: `gemini-2.0-flash-exp`
- **Temperature**: 0.0 (deterministic)
- **Output**: Structured JSON via `response_mime_type="application/json"`
- **Retry Logic**: 3 attempts with exponential backoff (1s, 2s, 4s)

### 3. **Validation** (`validator.py`)
Data integrity checks:
- **Citation Format**: `S\d+-F\d+-C\d+-p\d+(\.\d+)?`
- **Expense Types**: Against canonical list (16 types)
- **ParserValidator**: Comprehensive validation with error collection

### 4. **Retry Logic** (`retry.py`)
Exponential backoff decorator for API resilience

## Usage

### Basic Parsing

```python
from scripts.parser.gemini_parser import GeminiParser

# Initialize parser
parser = GeminiParser(api_key="your-gemini-api-key")

# Parse document
parsed_doc = parser.parse_document(
    text="Clean preprocessed text...",
    source_filename="S3-F2-C1.txt"
)

# Validate
from scripts.parser.validator import ParserValidator
validator = ParserValidator()
report = validator.validate_parsed_document(parsed_doc)

# Flatten for indexing
chunks = parsed_doc.to_flat_chunks(source_url="https://canada.ca/...")
```

### Configuration

Set via environment variables (see `src/quickexpense_rag/settings.py`):

```bash
export QUICKEXPENSE_RAG_GEMINI_API_KEY=your_key_here
export QUICKEXPENSE_RAG_GEMINI_MODEL=gemini-2.0-flash-exp
export QUICKEXPENSE_RAG_GEMINI_TEMPERATURE=0.0
```

## Testing

### Unit Tests (57 tests)
```bash
uv run pytest tests/unit/parser/ -v
```

### Integration Test (requires API key)
```bash
export GEMINI_API_KEY=your_key_here
uv run pytest tests/integration/test_gemini_parser_integration.py -v
```

## Cost Tracking

- **Estimated**: ~$0.03 per document (based on 50-page CRA folio)
- **Tracked**: `parser.last_token_usage` dictionary
- **Budget**: ~$1.59 for 50 documents

## Error Handling

1. **API Failures**: Retry 3x with exponential backoff
2. **Parsing Errors**: Pydantic validation errors
3. **Citation Errors**: Logged, continue processing
4. **Expense Type Warnings**: Unknown types flagged but not fatal

## Key Design Decisions

- **Hierarchical → Flat**: Parse hierarchically for LLM clarity, flatten for DB
- **Structured Output**: JSON mode more reliable than text prompts
- **Verbatim Extraction**: Prompt emphasizes no summarization
- **Error Collection**: Continue on non-critical errors, collect all issues
- **80/20 Approach**: Defer content grounding (complex, low ROI initially)

## Next Steps (TICKET 9C)

Parsed chunks feed into the Index Builder:
1. Load `chunks.jsonl` from parser output
2. Generate embeddings (BGE)
3. Populate SQLite database
4. Create manifest with SHA256
