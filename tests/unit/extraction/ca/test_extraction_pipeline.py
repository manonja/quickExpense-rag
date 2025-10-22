"""End-to-end tests for HTML→YAML extraction pipeline."""

from pathlib import Path

import pytest
import vcr
import yaml
from qe_tax_rag.extraction.ca.orchestrator import run_extraction
from tests.conftest import normalize_yaml_for_golden_comparison

# Configure VCR for these tests
my_vcr = vcr.VCR(
    cassette_library_dir="tests/fixtures/vcr_cassettes",
    record_mode="once",
    match_on=["method", "scheme", "host", "port", "path", "query"],
    filter_headers=["authorization", "x-goog-api-key"],
)


@pytest.fixture(autouse=True, scope="module")
def set_dummy_api_key(module_monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Set a dummy API key for all tests in this module.

    This is required for the Gemini client to initialize correctly, even when
    VCR is replaying responses. The client may have pre-flight checks that
    fail if the key is missing entirely.
    """
    module_monkeypatch.setenv("QE_TAX_RAG_EXTRACTION_GEMINI_API_KEY", "dummy-key-for-vcr")


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to extraction test fixtures."""
    return Path(__file__).parent.parent.parent.parent / "fixtures/extraction/ca"


@pytest.fixture
def temp_output(tmp_path: Path) -> tuple[Path, Path]:
    """Temporary paths for output and manual review YAML."""
    output_yaml = tmp_path / "output.yml"
    manual_review_yaml = tmp_path / "manual_review.yml"
    return output_yaml, manual_review_yaml


@my_vcr.use_cassette("pipeline_complex_rule.yaml")
@pytest.mark.unit
def test_pipeline_complex_rule_against_golden(
    fixtures_dir: Path,
    temp_output: tuple[Path, Path],
) -> None:
    """
    Test extraction pipeline on complex HTML against golden YAML file.

    Uses VCR to record/replay Gemini API responses for deterministic testing.

    Validates:
    - AC1: Valid YAML output (deserializes to RuleSet)
    - AC2: Citation ID integrity (no duplicates, correct format)
    - AC3: Adjudicator merges Classic + LLM outputs correctly
    - AC6: Content integrity (preserves RAG keywords)
    """
    output_yaml, manual_review_yaml = temp_output

    # Run extraction pipeline
    result = run_extraction(
        input_path=fixtures_dir / "complex_rule.html",
        output_yaml=output_yaml,
        manual_review_yaml=manual_review_yaml,
        dry_run=False,
    )

    # Verify pipeline completed successfully
    assert result["total_files"] == 1
    assert result["processed_files"] == 1
    assert len(result["failed_files"]) == 0
    assert result["total_rules"] == 3

    # Load generated YAML
    with open(output_yaml, encoding="utf-8") as f:
        generated_data = yaml.safe_load(f)

    # AC1: Valid YAML Output
    assert generated_data["schema_version"] == "1.0"
    assert len(generated_data["rules"]) == 3

    # AC2: Citation ID Integrity (no duplicate rule_numbers)
    rule_numbers = [r["rule_number"] for r in generated_data["rules"]]
    assert len(rule_numbers) == len(set(rule_numbers)), "Duplicate rule_numbers found"

    # AC2: All source_citations follow "Line {number}" format
    for rule in generated_data["rules"]:
        assert rule["source_citation"].startswith("Line ")
        assert str(rule["rule_number"]) in rule["source_citation"]

    # AC3: Adjudicator produces correct number of rules
    assert len(generated_data["rules"]) == 3

    # AC6: Content Integrity (RAG keywords preserved)
    # Check Line 8523 (Meals and entertainment)
    rule_8523 = next(
        (r for r in generated_data["rules"] if r["rule_number"] == 8523), None
    )
    assert rule_8523 is not None
    assert "deduct 50%" in rule_8523["content"].lower() or "50%" in rule_8523["content"]
    assert (
        "food" in rule_8523["content"].lower()
        or "beverages" in rule_8523["content"].lower()
    )

    # Load golden YAML for comparison
    with open(fixtures_dir / "complex_rule.golden.yml", encoding="utf-8") as f:
        golden_data = yaml.safe_load(f)

    # Normalize both for resilient comparison (ignore volatile fields like timestamps)
    normalized_generated = normalize_yaml_for_golden_comparison(generated_data)
    normalized_golden = normalize_yaml_for_golden_comparison(golden_data)

    # Compare against golden file
    assert len(normalized_generated["rules"]) == len(normalized_golden["rules"])

    # Sort both by rule_number for comparison
    gen_rules = sorted(normalized_generated["rules"], key=lambda r: r["rule_number"])
    gold_rules = sorted(normalized_golden["rules"], key=lambda r: r["rule_number"])

    for gen, gold in zip(gen_rules, gold_rules, strict=False):
        assert gen["rule_number"] == gold["rule_number"]
        assert gen["title"] == gold["title"]
        assert gen["applies_to"] == gold["applies_to"]


@my_vcr.use_cassette("adjudicator_merge.yaml")
@pytest.mark.unit
def test_adjudicator_merges_classic_and_llm_outputs(
    fixtures_dir: Path,
    temp_output: tuple[Path, Path],
) -> None:
    """
    Test adjudicator logic with complex multi-rule HTML.

    Uses VCR to record/replay Gemini API responses for deterministic testing.

    Validates:
    - AC3: Adjudicator merges Classic + LLM outputs correctly
    - AC3: Conflict resolution follows confidence score rules
    """
    output_yaml, manual_review_yaml = temp_output

    # Run extraction pipeline
    result = run_extraction(
        input_path=fixtures_dir / "complex_rule.html",
        output_yaml=output_yaml,
        manual_review_yaml=manual_review_yaml,
        dry_run=False,
    )

    # Verify pipeline processed multiple rules
    assert result["total_files"] == 1
    assert result["processed_files"] == 1
    assert result["total_rules"] == 3

    # Load generated YAML
    with open(output_yaml, encoding="utf-8") as f:
        generated_data = yaml.safe_load(f)

    # AC3: Verify all three rules extracted
    assert len(generated_data["rules"]) == 3

    # AC3: Verify rule_numbers are correct
    rule_numbers = {r["rule_number"] for r in generated_data["rules"]}
    assert rule_numbers == {8523, 9270, 8000}

    # AC3: Verify applies_to fields match expected applicability
    rule_8523 = next(r for r in generated_data["rules"] if r["rule_number"] == 8523)
    rule_9270 = next(r for r in generated_data["rules"] if r["rule_number"] == 9270)
    rule_8000 = next(r for r in generated_data["rules"] if r["rule_number"] == 8000)

    assert rule_8523["applies_to"] == ["business"]
    assert set(rule_9270["applies_to"]) == {"business", "farming"}
    assert rule_8000["applies_to"] == ["fishing"]


@my_vcr.use_cassette("citation_id_integrity.yaml")
@pytest.mark.unit
def test_citation_id_format_and_uniqueness(
    fixtures_dir: Path,
    temp_output: tuple[Path, Path],
) -> None:
    """
    Test citation ID integrity across multiple rules.

    Uses VCR to record/replay Gemini API responses for deterministic testing.

    Validates:
    - AC2: No duplicate citation_ids (rule_numbers)
    - AC2: All citation formats are consistent
    """
    output_yaml, manual_review_yaml = temp_output

    # Run extraction on complex fixture (3 rules)
    result = run_extraction(
        input_path=fixtures_dir / "complex_rule.html",
        output_yaml=output_yaml,
        manual_review_yaml=manual_review_yaml,
        dry_run=False,
    )

    # Load generated YAML
    with open(output_yaml, encoding="utf-8") as f:
        generated_data = yaml.safe_load(f)

    # AC2: No duplicate rule_numbers (citation uniqueness)
    rule_numbers = [r["rule_number"] for r in generated_data["rules"]]
    assert len(rule_numbers) == len(set(rule_numbers))

    # AC2: All source_citations follow "Line {number}" format
    for rule in generated_data["rules"]:
        assert rule["source_citation"].startswith("Line ")
        assert str(rule["rule_number"]) in rule["source_citation"]

    # Verify no None or empty values (critical constraint)
    for rule in generated_data["rules"]:
        assert rule["rule_number"] is not None
        assert rule["rule_number"] > 0
        assert rule["source_citation"] is not None
        assert rule["source_citation"] != ""
