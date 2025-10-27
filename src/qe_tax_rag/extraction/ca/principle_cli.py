"""
CLI for principle extraction (Phase 2).

Simple command-line interface for extracting PRINCIPLE content (rule references)
from CRA HTML documents.
"""

import logging
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.logging import RichHandler

from qe_tax_rag.extraction.ca.principle_parser import parse

app = typer.Typer(
    name="extract-principles",
    help="Extract PRINCIPLE content (rule references) from CRA HTML documents.",
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
            help="Path for output YAML file with extracted principles",
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
    Extract PRINCIPLE content from HTML file.

    Searches for text containing line number references (e.g., "Enter on line 9925...")
    and outputs as YAML.

    Example:
        uv run extract-principles cra_documents/t4002-6.html output/principles.yml
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

        # Extract principles
        logger.info(f"Extracting principles from {input_path}")
        principles = parse(str(input_path))

        if not principles:
            logger.warning(f"No principles found in {input_path}")
            console.print("[yellow]No principles found (0 extracted)[/yellow]")

            # Create empty YAML for consistency
            output_yaml.parent.mkdir(parents=True, exist_ok=True)
            output_yaml.write_text("principles: []\n")

            console.print(f"[green]Empty YAML written to {output_yaml}[/green]")
            return

        # Convert to YAML-serializable format
        principles_data = [
            {
                "citation_id": p.citation_id,
                "content_type": p.content_type.value,
                "text": p.text,
                "source_file": p.source_file,
                "anchor_id": p.anchor_id,
                "references": p.references,
            }
            for p in principles
        ]

        yaml_output = {"principles": principles_data}

        # Write YAML
        output_yaml.parent.mkdir(parents=True, exist_ok=True)
        with output_yaml.open("w") as f:
            yaml.dump(yaml_output, f, default_flow_style=False, sort_keys=False)

        # Success summary
        console.print(f"\n[green]✓ Extraction complete[/green]")
        console.print(f"  Principles extracted: {len(principles)}")
        console.print(f"  Output: {output_yaml}")

    except Exception as e:
        logger.exception("Extraction failed")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
