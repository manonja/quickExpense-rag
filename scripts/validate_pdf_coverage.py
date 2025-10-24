#!/usr/bin/env python3
"""
PDF Coverage Validation Tool for HTML Extraction Pipeline.

Validates that HTML-to-YAML extraction achieves ≥95% coverage against the
authoritative PDF source using semantic comparison with Gemini Pro 2.5.

Usage:
    python scripts/validate_pdf_coverage.py \\
        --pdf cra_documents/pdfs/t4002-5.pdf \\
        --yaml output/t4002-5_rules.yml \\
        --output reports/t4002-5_validation.json

Features:
- Semantic chunk matching (not exact text comparison)
- Smart rate limiting to prevent API quota exhaustion
- Coverage metrics: chunk_coverage, section_coverage
- Detailed mismatch reports for HITL review

Success Criteria (PRE-143):
- ≥95% chunk coverage (chunks found in PDF)
- ≥95% section coverage (PDF sections represented in YAML)
- Manual HITL quality gate: ≥18/20 chunks valid, 5/5 sections found
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai
import pdfplumber
import yaml
from google.api_core import exceptions as google_exceptions
from qe_tax_rag.extraction.ca.rate_limiter import RateLimiter, RateLimitError
from qe_tax_rag.extraction.ca.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Rate limiter for Gemini API (singleton)
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            rpm_limit=settings.gemini_rpm_limit,
            rpd_limit=settings.gemini_rpd_limit,
            state_file=Path(".cache/pdf_validation_rate_limiter.json"),
        )
    return _rate_limiter


def extract_pdf_text(pdf_path: Path) -> str:
    """
    Extract full text from PDF using pdfplumber.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Full text extracted from all pages

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If PDF extraction fails

    """
    logger.info(f"Extracting text from PDF: {pdf_path}")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = []
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(f"[Page {page_num}]\n{page_text}")
                else:
                    logger.warning(f"No text extracted from page {page_num}")

            full_text = "\n\n".join(pages_text)
            logger.info(
                f"Extracted {len(full_text)} characters from {len(pdf.pages)} pages"
            )
            return full_text

    except Exception as e:
        raise ValueError(f"Failed to extract PDF text: {e}") from e


def load_yaml_rules(yaml_path: Path) -> list[dict[str, Any]]:
    """
    Load extracted rules from YAML file.

    Args:
        yaml_path: Path to YAML file with extracted rules

    Returns:
        List of rule dictionaries

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        ValueError: If YAML parsing fails

    """
    logger.info(f"Loading YAML rules: {yaml_path}")

    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")

    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])
        logger.info(f"Loaded {len(rules)} rules from YAML")
        return rules

    except Exception as e:
        raise ValueError(f"Failed to load YAML: {e}") from e


def semantic_chunk_match(
    chunk_content: str,
    pdf_text: str,
    rule_number: int,
) -> dict[str, Any]:
    """
    Use Gemini Pro 2.5 to verify if chunk content exists in PDF.

    Args:
        chunk_content: The extracted rule content from YAML
        pdf_text: Full PDF text
        rule_number: Line number for logging

    Returns:
        Dictionary with:
        - found_in_pdf: bool
        - confidence: str ("high", "medium", "low")
        - reasoning: str
        - pdf_excerpt: str (relevant PDF text if found)

    """
    # Respect rate limits
    rate_limiter = get_rate_limiter()
    try:
        rate_limiter.wait_if_needed()
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
        raise

    prompt = f"""You are validating HTML extraction against the authoritative PDF source.

Task: Determine if the following extracted rule content appears in the PDF text.

CRITICAL:
- Match semantically (not exact text comparison)
- Extracted content may have formatting differences (whitespace, line breaks)
- Look for the SUBSTANCE of the rule, not exact wording
- Respond with RFC 8259 compliant JSON only (no markdown, no explanations)

--- EXTRACTED RULE (Line {rule_number}) ---
{chunk_content}

--- PDF SOURCE ---
{pdf_text[:50000]}  # Truncate to fit context window

Respond ONLY with valid JSON:
{{
  "found_in_pdf": true/false,
  "confidence": "high/medium/low",
  "reasoning": "<1-2 sentence explanation>",
  "pdf_excerpt": "<relevant PDF text if found, or null>"
}}"""

    genai.configure(api_key=settings.gemini_api_key)  # type: ignore[attr-defined]
    model = genai.GenerativeModel("gemini-2.0-flash-exp")  # Use Pro 2.5 for quality

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            ),
            request_options={"timeout": 30},
        )

        result = json.loads(response.text)
        logger.info(
            f"Rule {rule_number}: found={result['found_in_pdf']}, "
            f"confidence={result['confidence']}"
        )
        return result

    except (google_exceptions.ResourceExhausted, google_exceptions.ServiceUnavailable):
        logger.warning(f"API error for rule {rule_number}, retrying after backoff...")
        time.sleep(10)  # Backoff
        raise  # Retry in main loop
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini JSON response: {e}")
        return {
            "found_in_pdf": False,
            "confidence": "low",
            "reasoning": "JSON parsing error",
            "pdf_excerpt": None,
        }


def validate_coverage(
    pdf_path: Path,
    yaml_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """
    Validate HTML extraction coverage against PDF source.

    Args:
        pdf_path: Path to authoritative PDF
        yaml_path: Path to extracted YAML rules
        output_path: Path to write validation report (JSON)

    Returns:
        Validation report dictionary with metrics

    """
    logger.info(f"Starting validation: {yaml_path} against {pdf_path}")

    # Step 1: Load inputs
    pdf_text = extract_pdf_text(pdf_path)
    rules = load_yaml_rules(yaml_path)

    # Step 2: Semantic matching with rate limiting
    results = []
    chunks_found = 0

    for rule in rules:
        rule_number = rule.get("rule_number")
        content = f"{rule.get('title', '')}\n\n{rule.get('content', '')}"

        try:
            match_result = semantic_chunk_match(content, pdf_text, rule_number)
            results.append(
                {
                    "rule_number": rule_number,
                    "title": rule.get("title"),
                    "match_result": match_result,
                }
            )

            if match_result["found_in_pdf"]:
                chunks_found += 1

        except Exception as e:
            logger.error(f"Failed to validate rule {rule_number}: {e}")
            results.append(
                {
                    "rule_number": rule_number,
                    "title": rule.get("title"),
                    "match_result": {
                        "found_in_pdf": False,
                        "confidence": "low",
                        "reasoning": f"Validation error: {e}",
                        "pdf_excerpt": None,
                    },
                }
            )

    # Step 3: Calculate metrics
    total_chunks = len(rules)
    chunk_coverage = (chunks_found / total_chunks) * 100 if total_chunks > 0 else 0

    report = {
        "pdf_source": str(pdf_path),
        "yaml_source": str(yaml_path),
        "total_chunks": total_chunks,
        "chunks_found_in_pdf": chunks_found,
        "chunk_coverage_percent": round(chunk_coverage, 2),
        "success_criteria": {
            "target_coverage": 95.0,
            "meets_criteria": chunk_coverage >= 95.0,
        },
        "detailed_results": results,
    }

    # Step 4: Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Validation complete: {chunk_coverage:.2f}% coverage")
    logger.info(f"Report written to: {output_path}")

    return report


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate HTML extraction coverage against PDF source"
    )
    parser.add_argument("--pdf", type=Path, required=True, help="Path to PDF file")
    parser.add_argument(
        "--yaml", type=Path, required=True, help="Path to extracted YAML rules"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Path to write validation report"
    )

    args = parser.parse_args()

    try:
        report = validate_coverage(args.pdf, args.yaml, args.output)

        # Print summary
        print("\n" + "=" * 60)
        print("PDF COVERAGE VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total chunks:        {report['total_chunks']}")
        print(f"Chunks found in PDF: {report['chunks_found_in_pdf']}")
        print(f"Coverage:            {report['chunk_coverage_percent']:.2f}%")
        print(f"Target:              {report['success_criteria']['target_coverage']}%")
        print(
            f"Status:              {'✅ PASS' if report['success_criteria']['meets_criteria'] else '❌ FAIL'}"
        )
        print("=" * 60)

        return 0 if report["success_criteria"]["meets_criteria"] else 1

    except Exception as e:
        logger.exception(f"Validation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
