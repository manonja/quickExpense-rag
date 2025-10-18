"""Gemini Flash parser for CRA documents."""

import json
from typing import Any

import google.generativeai as genai
from qe_tax_rag.parser.schema import ParsedDocument

from scripts.parser.retry import retry_with_backoff
from scripts.parser.validator import CANONICAL_EXPENSE_TYPES


class GeminiParser:
    """Parser using Gemini Flash for structured document extraction."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.0,
    ):
        """
        Initialize Gemini parser.

        Args:
            api_key: Gemini API key
            model: Gemini model name
            temperature: Temperature for generation (0.0 = deterministic)

        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.last_token_usage: dict[str, int] = {}

        # Configure Gemini client
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model_name=model)

    def _build_prompt(self, text: str, document_id: str) -> str:
        """
        Build parsing prompt with instructions and schema.

        Args:
            text: Clean text to parse
            document_id: Document identifier (e.g., "S3-F2-C1")

        Returns:
            Complete prompt for Gemini

        """
        expense_types_str = ", ".join(f'"{et}"' for et in CANONICAL_EXPENSE_TYPES)

        prompt = f"""You are an expert legal analyst specializing in Canadian Revenue Agency (CRA) tax documents.

Your task is to meticulously extract information from the provided legal text into a structured JSON format.

**CRITICAL INSTRUCTIONS:**
1. Extract text VERBATIM - do not summarize, paraphrase, or interpret
2. Preserve the exact wording and structure from the source document
3. Extract ALL applicable expense types from the canonical list (not just one)
4. All citations must follow the S#-F#-C#-p#.# pattern (e.g., "S3-F2-C1-p1.25")
5. Maintain hierarchical structure (sections, lists, tables)

**Document ID:** {document_id}

**Canonical Expense Types:**
{expense_types_str}

**Example Citation Formats:**
- S1-F1-C1-p1.1 (section 1, folio 1, chapter 1, paragraph 1.1)
- S3-F2-C1-p2.5 (section 3, folio 2, chapter 1, paragraph 2.5)

**Expected JSON Structure:**
- title: Document title
- document_id: "{document_id}"
- metadata: {{province: [], business_type: [], expense_type: []}}
- sections: [{{section_title, section_level, content: [...]}}]

Content items can be:
- TextChunk: {{"type": "paragraph"|"footnote", "text": "...", "citation_id": "..."}}
- ListChunk: {{"type": "list", "items": [...]}}
- TableChunk: {{"type": "table", "data": [[...]], "citation_id": "..."}}

**Source Text to Parse:**

{text}

**Output valid JSON matching the ParsedDocument schema.**"""

        return prompt

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def _call_gemini_api(self, prompt: str) -> Any:
        """
        Call Gemini API with the prompt (with retry logic).

        Args:
            prompt: Prompt to send to Gemini

        Returns:
            Gemini response object

        Note:
            Retries up to 3 times with exponential backoff (1s, 2s, 4s)

        """
        response = self.client.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=self.temperature,
                response_mime_type="application/json",
            ),
        )
        return response

    def parse_document(self, text: str, source_filename: str) -> ParsedDocument:
        """
        Parse clean text using Gemini Flash with structured output.

        Args:
            text: Preprocessed clean text
            source_filename: Source filename for document_id extraction

        Returns:
            ParsedDocument instance

        Raises:
            Exception: If API call fails or parsing fails

        """
        # Extract document_id from filename (e.g., "S3-F2-C1.txt" -> "S3-F2-C1")
        document_id = (
            source_filename.replace(".txt", "").replace(".html", "").replace(".pdf", "")
        )

        # Build prompt
        prompt = self._build_prompt(text, document_id)

        # Call Gemini API
        response = self._call_gemini_api(prompt)

        # Extract token usage if available
        if hasattr(response, "usage_metadata"):
            self.last_token_usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }

        # Parse JSON response
        parsed_json = json.loads(response.text)

        # Validate with Pydantic
        parsed_doc = ParsedDocument.model_validate(parsed_json)

        return parsed_doc
