"""
Integration tests for the extract-rules CLI command.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

# A minimal HTML content that should be parsable by the extraction pipeline.
# NOTE: This may need to be adjusted based on the final implementation of
# the classic and LLM parsers to ensure rules are extracted.
HTML_CONTENT = """
<html>
<body>
    <div id="rule-8523">
        <h1>Chapter 1 - Business Expenses</h1>
        <h2>Line 8523 - Meals and entertainment</h2>
        <p>You can deduct 50% of food, beverage, and entertainment expenses.</p>
    </div>
</body>
</html>
"""


@pytest.fixture
def html_test_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with a minimal HTML file for testing."""
    html_dir = tmp_path / "html_input"
    html_dir.mkdir()
    (html_dir / "test.html").write_text(HTML_CONTENT, encoding="utf-8")
    return html_dir


@pytest.mark.integration
def test_auto_transform_flag_success(html_test_dir: Path, tmp_path: Path) -> None:
    """
    Verify that --auto-transform successfully runs the full pipeline,
    creating both a YAML and a JSONL file.
    """
    # Setup paths
    yml_path = tmp_path / "rules.yml"
    jsonl_path = tmp_path / "chunks.jsonl"

    # Execute the CLI command
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/extract_rules.py",
            "run",
            str(html_test_dir),
            str(yml_path),
            "--auto-transform",
            "--output-jsonl",
            str(jsonl_path),
        ],
        capture_output=True,
        text=True,
        check=False,  # Manually check return code for better error reporting
    )

    # Assert CLI execution
    assert result.returncode == 0, (
        f"CLI command failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Auto-transforming YAML to JSONL" in result.stdout
    assert "Pipeline completed successfully" in result.stdout

    # Assert file creation
    assert yml_path.exists(), "YAML output file was not created."
    assert jsonl_path.exists(), "JSONL output file was not created."

    # Verify YAML content (basic check)
    with yml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "rules" in data
    assert len(data["rules"]) > 0, "No rules were extracted into the YAML file."
    assert data["rules"][0]["rule_number"] == 8523

    # Verify JSONL content (basic check)
    with jsonl_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1, "Expected one document in the JSONL file."
    doc = json.loads(lines[0])
    assert doc["document_id"] == "test"
    assert "Chapter 1" in doc["sections"][0]["section_title"]
    assert len(doc["sections"][0]["content"]) > 0
    assert doc["sections"][0]["content"][0]["citation_id"] == "LINE-8523"


@pytest.mark.integration
def test_auto_transform_without_output_jsonl_fails(
    html_test_dir: Path, tmp_path: Path
) -> None:
    """
    Verify that using --auto-transform without --output-jsonl fails with
    a non-zero exit code and a clear error message.
    """
    # Setup paths
    yml_path = tmp_path / "rules.yml"

    # Execute the CLI command
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/extract_rules.py",
            "run",
            str(html_test_dir),
            str(yml_path),
            "--auto-transform",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    # Assert failure conditions
    assert result.returncode == 1, "CLI should have failed but exited with code 0."
    assert "--output-jsonl is required" in result.stderr, (
        "Error message not found in stderr."
    )

    # Assert that the YAML file was still created before the failure
    assert yml_path.exists(), (
        "YAML file should have been created before the transform step."
    )
