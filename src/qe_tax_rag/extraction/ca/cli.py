"""
CLI for HTML-to-YAML extraction pipeline.

Provides a user-friendly command-line interface for extracting CRA tax rules
from HTML documents using the Mixture-of-Experts pipeline.
"""

import logging
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.logging import RichHandler

from qe_tax_rag.extraction.ca.orchestrator import run_extraction

app = typer.Typer(
    name="extract-rules",
    help="HTML-to-YAML rule extraction pipeline for CRA T4002 documents.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def extract(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Path to HTML file or directory of HTML files",
            exists=True,
        ),
    ],
    output_yaml: Annotated[
        Path,
        typer.Argument(
            help="Path for output YAML file with extracted rules",
        ),
    ],
    manual_review_file: Annotated[
        Path,
        typer.Option(
            "--manual-review-file",
            "-m",
            help="Path for YAML file with items requiring manual review",
        ),
    ] = Path("manual_review.yml"),
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Run pipeline without generating output files"),
    ] = False,
    cache_dir: Annotated[
        Path | None,
        typer.Option(
            "--cache-dir",
            help="Directory to cache LLM responses (improves performance and reduces API costs)",
        ),
    ] = None,
) -> None:
    """
    Extract tax rules from CRA HTML documents to structured YAML.

    Uses a Mixture-of-Experts approach:
    1. Classic HTML parser (rule-based, fast)
    2. LLM parser (semantic, resilient to changes)
    3. Grounded adjudicator (resolves conflicts with evidence)

    Examples:
        # Process single file
        $ extract-rules cra_documents/t4002-5.html output/rules.yml

        # Process entire directory
        $ extract-rules cra_documents/cra_t4002e_rev24_dump/ output/rules.yml

        # Dry run (validate without writing files)
        $ extract-rules cra_documents/ output.yml --dry-run

        # Verbose logging for debugging
        $ extract-rules cra_documents/ output.yml --verbose

    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    try:
        # Run extraction
        result = run_extraction(
            input_path, output_yaml, manual_review_file, dry_run, cache_dir
        )

        # Render summary report
        _render_summary_report(result, output_yaml, manual_review_file, dry_run)

        # Exit with appropriate code
        if result["failed_files"]:
            raise typer.Exit(code=1)
        else:
            raise typer.Exit(code=0)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e


def _render_summary_report(
    result: dict[str, Any],
    output_yaml: Path,
    manual_review_yaml: Path,
    dry_run: bool,
) -> None:
    """Render rich-formatted summary report."""
    console.print()
    console.rule("[bold]CRA Rule Extraction Complete[/bold]")
    console.print()

    # Files processed
    console.print(
        f"Files Processed: [green]{result['processed_files']}[/green] / {result['total_files']}"
    )
    console.print(f"Total Rules Extracted: [cyan]{result['total_rules']}[/cyan]")
    console.print()

    # Adjudication breakdown
    stats = result["stats"]
    total = sum(stats.values())
    if total > 0:
        console.print("[bold]Adjudication Breakdown:[/bold]")
        console.print(
            f"  ✓ Perfect Matches:    {stats['perfect_matches']:>3} "
            f"({stats['perfect_matches'] / total * 100:.0f}%)"
        )
        console.print(
            f"  ⚡ Auto-corrected:     {stats['auto_corrected']:>3} "
            f"({stats['auto_corrected'] / total * 100:.0f}%)"
        )
        console.print(
            f"  ⚠️  Manual Review:      {stats['manual_review']:>3} "
            f"({stats['manual_review'] / total * 100:.0f}%)"
        )
        console.print()

    # Outputs
    if not dry_run:
        console.print("[bold]Outputs:[/bold]")
        console.print(f"  📄 Ruleset: {output_yaml}")
        if result["manual_review_count"] > 0:
            console.print(
                f"  ⚠️  Manual Review: {manual_review_yaml} ({result['manual_review_count']} items)"
            )
        console.print()
    else:
        console.print("[yellow]Dry run - no files generated[/yellow]")
        console.print()

    # Errors
    if result["failed_files"]:
        console.print(f"[red]Errors: {len(result['failed_files'])} files failed[/red]")
        for filename, error in result["failed_files"]:
            console.print(f"  - {filename}: {error}")
    else:
        console.print("[green]Errors: 0 files failed[/green]")

    console.print()
