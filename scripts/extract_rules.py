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
from rich.progress import track

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Import pipeline modules (from TICKETS 1-5)
# These will be implemented in previous tickets
try:
    from qe_tax_rag.extraction.ca.transformer import (
        CriticalTransformationError,
        TransformationReport,
        YAMLTransformer,
    )

    from parser.adjudicator import adjudicate
    from parser.classic_parser import parse as classic_parse
    from parser.exceptions import PipelineError
    from parser.generate_yaml import generate as generate_yaml
    from parser.llm_parser import parse as llm_parse
except ImportError as e:
    # Graceful degradation for development
    print(f"Warning: Pipeline modules not yet implemented: {e}", file=sys.stderr)
    classic_parse = None  # type: ignore
    llm_parse = None  # type: ignore
    adjudicate = None  # type: ignore
    generate_yaml = None  # type: ignore
    PipelineError = Exception  # type: ignore
    YAMLTransformer = None  # type: ignore
    CriticalTransformationError = Exception  # type: ignore
    TransformationReport = None  # type: ignore

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

    # Check if pipeline modules are available
    if classic_parse is None or YAMLTransformer is None:
        console.print(
            "[red]Error: Pipeline modules not implemented yet.[/red]\n"
            "Please implement TICKETS 1-5 and T2.1-2.3 first."
        )
        raise typer.Exit(code=1)

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
    # Phase 3: Main Processing Loop
    # -------------------------------------------------------------------------
    console.print(f"[cyan]Processing {len(html_files)} file(s)...[/cyan]\n")

    # Initialize collectors
    all_resolved_rules = []
    all_manual_review_items = []
    failed_files = []

    # Statistics tracking
    stats = {
        "total_rules": 0,
        "perfect_matches": 0,
        "auto_corrected": 0,
        "manual_review": 0,
    }

    # Process files with progress bar
    for html_file in track(html_files, description="Extracting rules..."):
        try:
            logger.info(f"Processing: {html_file.name}")

            # Read HTML content
            html_content = html_file.read_text(encoding="utf-8")

            # Run classic parser (TICKET 2)
            logger.debug(f"Running classic parser on {html_file.name}")
            classic_rules = classic_parse(str(html_file))

            # Run LLM parser (TICKET 3)
            logger.debug(f"Running LLM parser on {html_file.name}")
            llm_rules = llm_parse(str(html_file))

            # Adjudicate conflicts (TICKET 4)
            logger.debug(f"Adjudicating {html_file.name}")
            resolved_rules, manual_items, file_stats = adjudicate(
                classic_rules=classic_rules,
                llm_rules=llm_rules,
                source_html_content=html_content,
            )

            # Accumulate results
            all_resolved_rules.extend(resolved_rules)
            all_manual_review_items.extend(manual_items)

            # Update statistics
            stats["total_rules"] += file_stats.get("total", 0)
            stats["perfect_matches"] += file_stats.get("perfect_matches", 0)
            stats["auto_corrected"] += file_stats.get("auto_corrected", 0)
            stats["manual_review"] += file_stats.get("manual_review", 0)

            logger.info(
                f"Completed {html_file.name}: "
                f"{file_stats.get('total', 0)} rules extracted"
            )

        except PipelineError as e:
            # Expected pipeline errors (parser failures, validation errors)
            failed_files.append((html_file.name, str(e)))
            logger.error(f"Pipeline error processing {html_file.name}: {e}")
            if verbose:
                console.print(
                    f"\n[yellow]⚠️  Warning: Failed to process {html_file.name}[/yellow]"
                )
                console.print(f"[yellow]   Error: {e}[/yellow]\n")

        except Exception as e:
            # Unexpected errors
            failed_files.append((html_file.name, f"Unexpected error: {e}"))
            logger.exception(f"Unexpected error processing {html_file.name}: {e}")
            if verbose:
                console.print(
                    f"\n[red]❌ Error: Failed to process {html_file.name}[/red]"
                )
                console.print(f"[red]   {e}[/red]\n")

    # -------------------------------------------------------------------------
    # Phase 4: Output Generation
    # -------------------------------------------------------------------------
    console.print("\n[cyan]Generating YAML outputs...[/cyan]")

    try:
        # Generate main ruleset YAML (TICKET 5)
        logger.info(f"Writing main ruleset to {output_yaml}")
        generate_yaml(rules=all_resolved_rules, output_path=str(output_yaml))
        console.print(f"[green]✓[/green] Generated: {output_yaml}")

        # Generate manual review YAML if needed (TICKET 5)
        if all_manual_review_items:
            logger.info(
                f"Writing {len(all_manual_review_items)} manual review items "
                f"to {manual_review_yaml}"
            )
            generate_yaml(
                rules=all_manual_review_items,
                output_path=str(manual_review_yaml),
            )
            console.print(
                f"[yellow]⚠️[/yellow]  Manual review: {manual_review_yaml} "
                f"({len(all_manual_review_items)} items)"
            )
        else:
            logger.info("No manual review items, skipping manual review file")
            console.print("[green]✓[/green] No items require manual review")

    except PipelineError as e:
        console.print(f"\n[red]❌ Error: Failed to generate YAML output[/red]")
        console.print(f"[red]   {e}[/red]")
        logger.exception("YAML generation failed")
        raise typer.Exit(code=1) from e

    except Exception as e:
        console.print(f"\n[red]❌ Error: Unexpected failure during output[/red]")
        console.print(f"[red]   {e}[/red]")
        logger.exception("Unexpected error during YAML generation")
        raise typer.Exit(code=1) from e

    # -------------------------------------------------------------------------
    # Phase 4.5: Auto-Transformation (Optional)
    # -------------------------------------------------------------------------
    transformation_report: TransformationReport | None = None
    if auto_transform:
        console.print("\n[cyan]Auto-transforming YAML to JSONL...[/cyan]")
        if not output_jsonl:
            typer.echo(
                "❌ Error: --output-jsonl is required when using --auto-transform",
                err=True,
            )
            raise typer.Exit(code=1)

        try:
            transformer = YAMLTransformer()
            report = transformer.transform_yaml_to_jsonl(
                yaml_path=output_yaml,
                jsonl_path=output_jsonl,
                continue_on_error=True,
            )
            transformation_report = report

            console.print(f"[green]✓[/green] Transformation complete!")
            console.print(f"  📄 JSONL written to: {output_jsonl}")
            console.print(
                f"  - Rules processed: {report.successful}/{report.total_rules}"
            )
            if report.errors:
                console.print(
                    f"  [yellow]⚠️[/yellow]  Encountered {len(report.errors)} skippable errors."
                )

        except CriticalTransformationError as e:
            console.print(
                f"\n[red]❌ Error: Auto-transformation failed critically[/red]"
            )
            console.print(f"[red]   {e}[/red]")
            raise typer.Exit(code=1) from e
        except Exception as e:
            console.print(
                f"\n[red]❌ Error: Unexpected failure during auto-transformation[/red]"
            )
            console.print(f"[red]   {e}[/red]")
            raise typer.Exit(code=1) from e

    # -------------------------------------------------------------------------
    # Phase 5: Summary Report
    # -------------------------------------------------------------------------
    console.print("\n" + "━" * 60)
    console.print("[bold green]  CRA Rule Extraction Complete[/bold green]")
    console.print("━" * 60 + "\n")

    # Files processed
    files_processed = len(html_files) - len(failed_files)
    console.print(
        f"Files Processed: [bold]{files_processed}[/bold] / {len(html_files)}"
    )

    if failed_files:
        console.print(f"[red]Failed Files: {len(failed_files)}[/red]")
        if verbose:
            for filename, error in failed_files:
                console.print(f"  [red]• {filename}:[/red] {error}")

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
    if all_manual_review_items:
        console.print(
            f"  ⚠️  Manual Review: {manual_review_yaml} "
            f"({len(all_manual_review_items)} items)"
        )
    if transformation_report:
        console.print(f"  📄 Transformed JSONL: {output_jsonl}")

    # Final status
    final_exit_code = 0
    if failed_files:
        final_exit_code = 1

    if transformation_report and transformation_report.errors:
        final_exit_code = 1

    if final_exit_code == 0:
        console.print("\n[green]✅ Pipeline completed successfully![/green]")
    else:
        console.print(
            "\n[yellow]⚠️  Pipeline completed with warnings or errors.[/yellow]"
        )

    raise typer.Exit(code=final_exit_code)


if __name__ == "__main__":
    app()
