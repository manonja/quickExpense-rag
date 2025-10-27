"""
CLI for table extraction (Phase 3).

Simple command-line interface for extracting TABLE content (structured tabular data)
from CRA HTML documents.
"""

import logging
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.logging import RichHandler

from qe_tax_rag.extraction.ca.table_parser import parse

app = typer.Typer(
    name="extract-tables",
    help="Extract TABLE content (structured data) from CRA HTML documents.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def extract(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Path to HTML file",
            exists=True,
        ),
    ],
    output_yaml: Annotated[
        Path,
        typer.Argument(
            help="Path for output YAML file with extracted tables",
        ),
    ],
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose logging",
        ),
    ] = False,
) -> None:
    """
    Extract TABLE content from HTML file.

    Searches for <table> tags with <thead> and <tbody> structure, extracting
    structured data as list of dictionaries.

    Example:
        uv run extract-tables cra_documents/t4002-10.html output/tables.yml
    """
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    logger = logging.getLogger(__name__)

    try:
        # Validate input
        if not input_path.is_file():
            console.print(f"[red]Error: {input_path} is not a file[/red]")
            raise typer.Exit(code=1)

        # Extract tables
        logger.info(f"Extracting tables from {input_path}")
        tables = parse(str(input_path))

        if not tables:
            logger.warning(f"No tables found in {input_path}")
            console.print("[yellow]No tables found (0 extracted)[/yellow]")

            # Create empty YAML for consistency
            output_yaml.parent.mkdir(parents=True, exist_ok=True)
            output_yaml.write_text("tables: []\n")

            console.print(f"[green]Empty YAML written to {output_yaml}[/green]")
            return

        # Convert to YAML-serializable format
        tables_data = [
            {
                "citation_id": t.citation_id,
                "content_type": t.content_type.value,
                "text": t.text,
                "source_file": t.source_file,
                "anchor_id": t.anchor_id,
                "references": t.references,
                "table_data": t.table_data,
            }
            for t in tables
        ]

        yaml_output = {"tables": tables_data}

        # Write YAML
        output_yaml.parent.mkdir(parents=True, exist_ok=True)
        with output_yaml.open("w") as f:
            yaml.dump(yaml_output, f, default_flow_style=False, sort_keys=False)

        # Success summary
        console.print(f"\n[green]✓ Extraction complete[/green]")
        console.print(f"  Tables extracted: {len(tables)}")
        if tables and tables[0].table_data:
            console.print(f"  First table rows: {len(tables[0].table_data)}")
        console.print(f"  Output: {output_yaml}")

    except Exception as e:
        logger.exception("Extraction failed")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
