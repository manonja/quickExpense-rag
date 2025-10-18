"""
HTML-to-YAML Rule Extraction Pipeline Orchestrator.

This script orchestrates the complete extraction pipeline:
1. Parse HTML files using classic (BeautifulSoup) and LLM (Gemini) parsers
2. Adjudicate conflicts between parsers with grounded self-correction
3. Generate validated YAML output with schema verification

Implements TICKET 6 from html-to-yaml-plan.md
"""

import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

# Add src directory to path for imports
# NOTE: sys.path needed because src/ is not in standard Python path for scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import canonical orchestrator and transformer from src package
from qe_tax_rag.extraction.ca.orchestrator import run_extraction
from qe_tax_rag.extraction.ca.transformer import (
    TransformationReport,
    YAMLTransformer,
)

# Initialize Typer app and Rich console
app = typer.Typer(
    help="HTML-to-YAML rule extraction pipeline for CRA T4002 documents.",
    add_completion=False,
)
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.command()
def run(
    input_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Path to HTML file or directory of HTML files",
        ),
    ],
    output_yaml: Annotated[
        Path,
        typer.Argument(
            resolve_path=True,
            help="Path for output YAML file with extracted rules",
        ),
    ],
    manual_review_yaml: Annotated[
        Path,
        typer.Option(
            "--manual-review-file",
            "-m",
            resolve_path=True,
            help="Path for YAML file with items requiring manual review",
        ),
    ] = Path("manual_review.yml"),
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose logging for debugging",
        ),
    ] = False,
    auto_transform: Annotated[
        bool,
        typer.Option(
            "--auto-transform",
            help="Automatically transform YAML to JSONL after extraction.",
        ),
    ] = False,
    output_jsonl: Annotated[
        Path | None,
        typer.Option(
            "--output-jsonl",
            help="JSONL output path (required if --auto-transform is set).",
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """
    Extract structured rules from CRA HTML documents into YAML format.

    Uses a Mixture-of-Experts approach with two parsers (classic BeautifulSoup
    + LLM semantic) and grounded adjudication to resolve conflicts.

    Examples:
        # Process directory of HTML files
        uv run extract-rules cra_documents/cra_t4002e_rev24_dump/ output/rules.yml

        # Process single file
        uv run extract-rules input.html output.yml

        # With custom manual review file
        uv run extract-rules input/ output.yml --manual-review-file review.yml

        # Extract and auto-transform to JSONL
        uv run extract-rules input/ rules.yml --auto-transform --output-jsonl chunks.jsonl

    """
    # Enable verbose logging if requested
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Display header
    console.print("\n[bold blue]CRA Rule Extraction Pipeline[/bold blue]")
    console.print(f"Input: {input_path}")
    console.print(f"Output: {output_yaml}\n")

    # -------------------------------------------------------------------------
    # Phase 1: Input Resolution
    # -------------------------------------------------------------------------
    logger.info("Resolving input files...")

    if input_path.is_dir():
        html_files = sorted(input_path.glob("*.html"))
        if not html_files:
            console.print(
                f"[red]Error: No HTML files found in directory: {input_path}[/red]"
            )
            raise typer.Exit(code=1)
        logger.info(f"Found {len(html_files)} HTML files in directory")
    else:
        html_files = [input_path]
        logger.info("Processing single HTML file")

    # -------------------------------------------------------------------------
    # Phase 2: Pre-flight Checks
    # -------------------------------------------------------------------------
    logger.info("Running pre-flight checks...")

    # Create output directory if needed
    try:
        output_yaml.parent.mkdir(parents=True, exist_ok=True)
        manual_review_yaml.parent.mkdir(parents=True, exist_ok=True)
        if output_jsonl:
            output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        console.print(
            f"[red]Error: Cannot create output directory: {e}[/red]\n"
            "Check file permissions and try again."
        )
        raise typer.Exit(code=1) from e

    # Test write permissions
    try:
        test_file = output_yaml.parent / ".write_test"
        test_file.touch()
        test_file.unlink()
    except (PermissionError, OSError) as e:
        console.print(
            f"[red]Error: Output directory not writable: {output_yaml.parent}[/red]\n"
            f"Permission error: {e}"
        )
        raise typer.Exit(code=1) from e

    logger.info("Pre-flight checks passed")

    # -------------------------------------------------------------------------
    # Phase 3: Main Processing - Call helper function
    # -------------------------------------------------------------------------
    console.print(f"[cyan]Processing {len(html_files)} file(s)...[/cyan]\n")

    # Call the extracted pipeline logic
    stats, transformation_report = _run_extraction_pipeline(
        html_files=html_files,
        output_yaml=output_yaml,
        manual_review_yaml=manual_review_yaml,
        output_jsonl=output_jsonl if auto_transform else None,
        verbose=verbose,
    )

    # -------------------------------------------------------------------------
    # Phase 5: Summary Report
    # -------------------------------------------------------------------------
    console.print("\n" + "━" * 60)
    console.print("[bold green]  CRA Rule Extraction Complete[/bold green]")
    console.print("━" * 60 + "\n")

    # Files processed (simplified - just show total)
    console.print(f"Files Processed: [bold]{len(html_files)}[/bold] HTML file(s)")

    # Rules extracted
    console.print(f"Total Rules Extracted: [bold]{stats['total_rules']}[/bold]\n")

    # Adjudication breakdown
    console.print("[bold]Adjudication Breakdown:[/bold]")

    if stats["total_rules"] > 0:
        perfect_pct = (stats["perfect_matches"] / stats["total_rules"]) * 100
        corrected_pct = (stats["auto_corrected"] / stats["total_rules"]) * 100
        manual_pct = (stats["manual_review"] / stats["total_rules"]) * 100

        console.print(
            f"  [green]✓[/green] Perfect Matches:  {stats['perfect_matches']:4} "
            f"({perfect_pct:5.1f}%)"
        )
        console.print(
            f"  [yellow]⚡[/yellow] Auto-corrected:   {stats['auto_corrected']:4} "
            f"({corrected_pct:5.1f}%)"
        )
        console.print(
            f"  [yellow]⚠️[/yellow]  Manual Review:    {stats['manual_review']:4} "
            f"({manual_pct:5.1f}%)"
        )
    else:
        console.print("  [yellow]No rules extracted[/yellow]")

    # Transformation breakdown
    if transformation_report:
        console.print("\n[bold]Transformation Breakdown:[/bold]")
        console.print(f"  - Total Rules: {transformation_report.total_rules}")
        console.print(f"  - [green]Successful:[/] {transformation_report.successful}")
        console.print(f"  - [yellow]Skipped:[/]   {transformation_report.skipped}")
        console.print(f"  - [red]Errors:[/]    {len(transformation_report.errors)}")

    # Output files
    console.print("\n[bold]Outputs:[/bold]")
    console.print(f"  📄 Ruleset: {output_yaml}")
    # Check if manual review file exists and has content
    if manual_review_yaml.exists() and stats["manual_review"] > 0:
        console.print(
            f"  ⚠️  Manual Review: {manual_review_yaml} ({stats['manual_review']} items)"
        )
    if transformation_report:
        console.print(f"  📄 Transformed JSONL: {output_jsonl}")

    # Final status
    final_exit_code = 0
    if transformation_report and transformation_report.errors:
        final_exit_code = 1

    if final_exit_code == 0:
        console.print("\n[green]✅ Pipeline completed successfully![/green]")
    else:
        console.print(
            "\n[yellow]⚠️  Pipeline completed with warnings or errors.[/yellow]"
        )

    raise typer.Exit(code=final_exit_code)


def _run_extraction_pipeline(
    html_files: list[Path],
    output_yaml: Path,
    manual_review_yaml: Path,
    output_jsonl: Path | None,
    verbose: bool = False,
) -> tuple[dict, "TransformationReport | None"]:
    """
    Adapter for core extraction pipeline.

    Calls the canonical orchestrator from src/qe_tax_rag/extraction/ca/orchestrator.py
    and adapts its output to the legacy format expected by callers.

    This function bridges the gap between the old script-level interface and the
    new canonical orchestrator, ensuring backward compatibility.

    Args:
        html_files: List of HTML files to process
        output_yaml: Path for main ruleset YAML
        manual_review_yaml: Path for manual review YAML
        output_jsonl: Path for JSONL output (enables auto-transform if set)
        verbose: Enable debug logging

    Returns:
        Tuple of (stats dict, transformation report or None)
        - stats: Flat dict with total_rules, perfect_matches, auto_corrected, manual_review
        - report: TransformationReport if output_jsonl is set, None otherwise

    Raises:
        PipelineError: On extraction/parsing failures
        CriticalTransformationError: On transformation failures

    """
    # Configure logging
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Orchestrator expects a path (file or directory), not a list of files
    # Use the parent directory of the first file
    if not html_files:
        logger.warning("No HTML files provided to extraction pipeline")
        return {
            "total_rules": 0,
            "perfect_matches": 0,
            "auto_corrected": 0,
            "manual_review": 0,
        }, None

    input_dir = html_files[0].parent

    # === Step 1: Call canonical orchestrator (HTML → YAML) ===
    logger.info(
        f"Calling canonical orchestrator for {len(html_files)} files in {input_dir}"
    )
    result = run_extraction(
        input_path=input_dir,
        output_yaml=output_yaml,
        manual_review_yaml=manual_review_yaml,
    )

    # === Step 2: Adapt orchestrator output to legacy flat stats structure ===
    # Orchestrator returns nested structure: {"total_rules": X, "stats": {...}}
    # Legacy callers expect flat structure: {"total_rules": X, "perfect_matches": Y, ...}
    stats = {
        "total_rules": result["total_rules"],
        **result[
            "stats"
        ],  # Unpack nested stats dict (perfect_matches, auto_corrected, manual_review)
    }

    logger.info(f"Extraction complete: {stats['total_rules']} rules extracted")

    # === Step 3: Handle transformation (YAML → JSONL) ===
    # The orchestrator doesn't do transformation, so we handle it separately
    transformation_report = None
    if output_jsonl is not None:
        logger.info(f"Transforming YAML to JSONL: {output_yaml} → {output_jsonl}")
        transformer = YAMLTransformer()
        transformation_report = transformer.transform_yaml_to_jsonl(
            yaml_path=output_yaml,
            jsonl_path=output_jsonl,
            continue_on_error=True,
        )
        logger.info(
            f"Transformation complete: {transformation_report.successful}/{transformation_report.total_rules} rules"
        )

    return stats, transformation_report


if __name__ == "__main__":
    app()
