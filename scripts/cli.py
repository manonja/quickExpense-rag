"""Maintainer CLI for preprocessing pipeline."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import track

# Add scripts directory and project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

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


if __name__ == "__main__":
    app()
