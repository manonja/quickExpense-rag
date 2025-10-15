"""Maintainer CLI for preprocessing pipeline."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import track

# Add scripts directory and project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.gemini_parser import GeminiParser
from preprocessor.models import DownloadMetadata, PreprocessManifest
from preprocessor.text_extractor import TextExtractor

# Initialize Typer app and Rich console
app = typer.Typer(help="QuickExpense RAG Preprocessing CLI")
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.command()
def preprocess(
    input_dir: Path = typer.Option(  # noqa: B008
        Path("data/raw"),
        "--input-dir",
        "-i",
        help="Directory containing HTML/PDF files to preprocess",
    ),
    output_dir: Path = typer.Option(  # noqa: B008
        Path("data/preprocessed"),
        "--output-dir",
        "-o",
        help="Directory for preprocessed text files",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """
    Convert HTML/PDF files to clean text.

    Processes all HTML and PDF files in input_dir, writes clean text to
    output_dir, and creates manifest.json with document metadata.

    Example:
        uv run python scripts/cli.py preprocess --input-dir data/raw

    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print(f"[bold blue]QuickExpense RAG Preprocessing[/bold blue]")
    console.print(f"Input: {input_dir}")
    console.print(f"Output: {output_dir}\n")

    # Verify input directory exists
    if not input_dir.exists():
        console.print(f"[red]Error: Input directory not found: {input_dir}[/red]")
        raise typer.Exit(code=1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all HTML and PDF files
    html_files = list(input_dir.glob("*.html"))
    pdf_files = list(input_dir.glob("*.pdf"))
    all_files = html_files + pdf_files

    if not all_files:
        console.print(
            f"[yellow]Warning: No HTML or PDF files found in {input_dir}[/yellow]"
        )
        return

    console.print(f"Found {len(html_files)} HTML and {len(pdf_files)} PDF files\n")

    # Initialize extractor
    extractor = TextExtractor()
    manifest_docs: list[DownloadMetadata] = []
    success_count = 0
    error_count = 0

    # Process files with progress bar
    for input_file in track(all_files, description="Preprocessing..."):
        try:
            # Generate output filename (.txt extension)
            output_file = output_dir / f"{input_file.stem}.txt"

            # Preprocess file (computes SHA256)
            sha256 = extractor.preprocess_file(
                input_file,
                output_file,
                compute_hash=True,
            )

            # Add to manifest
            manifest_docs.append(
                DownloadMetadata(
                    filename=input_file.name,
                    source_url=f"https://www.canada.ca/...",  # Placeholder
                    downloaded_at=datetime.now(timezone.utc),
                    sha256=sha256 or "",  # Should always be present
                )
            )

            success_count += 1
            logger.info("Preprocessed: %s → %s", input_file.name, output_file.name)

        except Exception as e:
            error_count += 1
            console.print(f"[red]Error processing {input_file.name}: {e}[/red]")
            logger.exception("Failed to preprocess %s: %s", input_file.name, e)

    # Create manifest
    manifest = PreprocessManifest(documents=manifest_docs)
    manifest_path = input_dir / "manifest.json"

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(mode="json"), f, indent=2, default=str)

    # Summary
    console.print("\n[bold green]Preprocessing Complete![/bold green]")
    console.print(f"✅ Processed: {success_count} files")
    if error_count > 0:
        console.print(f"❌ Errors: {error_count} files")
    console.print(f"📄 Manifest: {manifest_path}")


@app.command()
def parse(
    input_dir: Path = typer.Option(  # noqa: B008
        Path("data/preprocessed"),
        "--input-dir",
        "-i",
        help="Directory containing preprocessed .txt files",
    ),
    output_file: Path = typer.Option(  # noqa: B008
        Path("data/processed/chunks.jsonl"),
        "--output-file",
        "-o",
        help="Output JSONL file for parsed documents",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Continue processing on errors",
    ),
) -> None:
    """
    Parse preprocessed text files using Gemini Flash.

    Processes all .txt files in input_dir using GeminiParser, extracts
    structured data, and writes ParsedDocument objects to JSONL output.

    Requires GEMINI_API_KEY environment variable.

    Example:
        export GEMINI_API_KEY="your-key-here"
        uv run python scripts/cli.py parse --input-dir data/preprocessed

    """
    console.print("[bold blue]QuickExpense RAG Parsing (Gemini Flash)[/bold blue]")
    console.print(f"Input: {input_dir}")
    console.print(f"Output: {output_file}\n")

    # Check for API key (fail fast)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print(
            "[red]Error: GEMINI_API_KEY environment variable not set[/red]\n"
            "Please set your Gemini API key:\n"
            "  export GEMINI_API_KEY='your-key-here'"
        )
        raise typer.Exit(code=1)

    # Verify input directory exists
    if not input_dir.exists():
        console.print(f"[red]Error: Input directory not found: {input_dir}[/red]")
        raise typer.Exit(code=1)

    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Find all .txt files
    txt_files = sorted(input_dir.glob("*.txt"))

    if not txt_files:
        console.print(f"[yellow]Warning: No .txt files found in {input_dir}[/yellow]")
        return

    console.print(f"Found {len(txt_files)} text files to parse\n")

    # Initialize parser
    parser = GeminiParser(api_key=api_key)

    # Track statistics
    success_count = 0
    error_count = 0
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0

    # Open output file for writing (JSONL format)
    with output_file.open("w", encoding="utf-8") as outfile:
        # Process files with progress bar
        for txt_file in track(txt_files, description="Parsing documents..."):
            try:
                # Read preprocessed text
                text_content = txt_file.read_text(encoding="utf-8")

                # Parse with Gemini
                parsed_doc = parser.parse_document(
                    text=text_content, source_filename=txt_file.name
                )

                # Write to JSONL (one JSON object per line)
                json_str = parsed_doc.model_dump_json()
                outfile.write(json_str + "\n")

                # Track token usage
                if parser.last_token_usage:
                    total_prompt_tokens += parser.last_token_usage.get(
                        "prompt_tokens", 0
                    )
                    total_completion_tokens += parser.last_token_usage.get(
                        "completion_tokens", 0
                    )
                    total_tokens += parser.last_token_usage.get("total_tokens", 0)

                success_count += 1
                logger.info("Parsed: %s", txt_file.name)

            except Exception as e:
                error_count += 1
                console.print(f"[red]Error parsing {txt_file.name}: {e}[/red]")
                logger.exception("Failed to parse %s", txt_file.name)

                if not force:
                    console.print(
                        "\n[yellow]Stopping due to error. "
                        "Use --force to continue on errors.[/yellow]"
                    )
                    raise typer.Exit(code=1) from e

    # Display summary
    console.print("\n[bold green]Parsing Complete![/bold green]")
    console.print(f"✅ Parsed: {success_count} files")
    if error_count > 0:
        console.print(f"❌ Errors: {error_count} files")
    console.print(f"📄 Output: {output_file}")

    # Token usage and cost estimation
    if total_tokens > 0:
        console.print(f"\n[bold cyan]Token Usage:[/bold cyan]")
        console.print(f"  Prompt tokens: {total_prompt_tokens:,}")
        console.print(f"  Completion tokens: {total_completion_tokens:,}")
        console.print(f"  Total tokens: {total_tokens:,}")

        # Gemini Flash pricing (as of 2024):
        # $0.075 per 1M input tokens, $0.30 per 1M output tokens
        # https://ai.google.dev/pricing
        input_cost = (total_prompt_tokens / 1_000_000) * 0.075
        output_cost = (total_completion_tokens / 1_000_000) * 0.30
        total_cost = input_cost + output_cost

        console.print(f"\n[bold cyan]Estimated Cost:[/bold cyan]")
        console.print(f"  Input: ${input_cost:.4f}")
        console.print(f"  Output: ${output_cost:.4f}")
        console.print(f"  Total: ${total_cost:.4f}")


if __name__ == "__main__":
    app()
