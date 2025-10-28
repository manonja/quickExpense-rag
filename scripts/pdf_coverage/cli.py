"""CLI for PDF coverage validation.

Provides command-line interface for checking PDF coverage against YAML corpus.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

from scripts.pdf_coverage.classifier import classify_pages
from scripts.pdf_coverage.models import CoverageReport
from scripts.pdf_coverage.pdf_extractor import extract_pdf_pages, get_page_count
from scripts.pdf_coverage.report_generator import generate_reports
from scripts.pdf_coverage.yaml_corpus import build_yaml_corpus

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()

# Typer app
app = typer.Typer(
    name="pdf-coverage",
    help="PDF coverage validation - identify pages not covered in YAML extractions",
)


@app.callback(invoke_without_command=True)
def main(
    pdf: Path = typer.Option(
        ...,
        "--pdf",
        "-p",
        help="Path to PDF file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    yaml_dir: Path = typer.Option(
        ...,
        "--yaml-dir",
        "-y",
        help="Directory containing YAML files (rules, principles, tables)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_dir: Path = typer.Option(
        "output/pdf_coverage",
        "--output-dir",
        "-o",
        help="Directory to write reports",
    ),
    threshold: int = typer.Option(
        90,
        "--threshold",
        "-t",
        help="Similarity threshold for 'already covered' (0-100)",
        min=0,
        max=100,
    ),
    blank_threshold: int = typer.Option(
        50,
        "--blank-threshold",
        "-b",
        help="Character count threshold for blank pages",
        min=0,
    ),
    remove_headers: bool = typer.Option(
        True,
        "--remove-headers/--keep-headers",
        help="Remove common PDF header/footer patterns",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Check PDF coverage against YAML corpus.

    Identifies which PDF pages are already covered in YAML extractions
    and which need to be processed.

    Examples:
        # Basic usage
        python -m scripts.pdf_coverage.cli check \\
            --pdf cra_documents/T4002-Business-Expenses-Guide.pdf \\
            --yaml-dir output/

        # Custom threshold and output directory
        python -m scripts.pdf_coverage.cli check \\
            --pdf document.pdf \\
            --yaml-dir output/ \\
            --output-dir reports/ \\
            --threshold 85

    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print("\n[bold blue]PDF Coverage Validation[/bold blue]")
    console.print(f"PDF: {pdf}")
    console.print(f"YAML Directory: {yaml_dir}")
    console.print(f"Threshold: {threshold}%")
    console.print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Step 1: Get PDF page count
            task = progress.add_task("Getting PDF page count...", total=None)
            total_pages = get_page_count(pdf)
            progress.update(task, completed=True)
            console.print(f"✅ PDF has {total_pages} pages\n")

            # Step 2: Build YAML corpus
            task = progress.add_task("Building YAML corpus...", total=None)
            corpus_text, yaml_files, stats = build_yaml_corpus(yaml_dir)
            progress.update(task, completed=True)

            console.print(
                f"✅ Loaded {len(yaml_files)} YAML files: "
                f"{stats['rules']} rules, {stats['principles']} principles, "
                f"{stats['tables']} tables ({stats['table_rows']} rows)"
            )
            console.print(f"   Corpus size: {len(corpus_text):,} characters\n")

            # Step 3: Extract PDF pages
            task = progress.add_task("Extracting PDF pages...", total=None)
            pdf_pages = extract_pdf_pages(pdf, remove_headers=remove_headers)
            progress.update(task, completed=True)
            console.print(f"✅ Extracted {len(pdf_pages)} pages\n")

            # Step 4: Classify pages
            task = progress.add_task("Classifying pages...", total=None)
            keep_pages, discard_pages = classify_pages(
                pdf_pages, corpus_text, threshold, blank_threshold
            )
            progress.update(task, completed=True)

            # Build report
            report = CoverageReport(
                pdf_source=str(pdf),
                yaml_sources=yaml_files,
                total_pdf_pages=total_pages,
                keep_pages=keep_pages,
                discard_pages=discard_pages,
                threshold=threshold,
            )

            stats = report.summary_stats
            console.print(f"✅ Classification complete:")
            console.print(f"   - Already covered: {stats['covered_pages']} pages")
            console.print(f"   - Blank: {stats['blank_pages']} pages")
            console.print(
                f"   - [bold yellow]Needs extraction: {stats['needs_extraction']} pages[/bold yellow]\n"
            )

            # Step 5: Generate reports
            task = progress.add_task("Generating reports...", total=None)
            report_files = generate_reports(report, output_dir)
            progress.update(task, completed=True)

            console.print(f"✅ Reports written to {output_dir}:")
            for report_type, file_path in report_files.items():
                console.print(f"   - {file_path.name}")

        # Summary
        console.print("\n[bold green]✨ Validation complete![/bold green]")
        console.print(
            f"\n[bold]Next steps:[/bold] Process {stats['needs_extraction']} "
            f"pages from [cyan]{output_dir / 'keep_pages.json'}[/cyan]\n"
        )

        # Exit code: 0 if no pages need extraction, 1 if pages need extraction
        if stats["needs_extraction"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {e}")
        logger.exception("Validation failed")
        sys.exit(1)


if __name__ == "__main__":
    app()
