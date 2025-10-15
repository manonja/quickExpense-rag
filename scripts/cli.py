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
from quickexpense_rag.data.builder import IndexBuilder
from quickexpense_rag.data.validator import IndexValidator
from quickexpense_rag.embeddings.encoder import embedding_service
from quickexpense_rag.search.models import SourceFile

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


@app.command()
def build(
    input_file: Path = typer.Option(  # noqa: B008
        Path("data/processed/chunks.jsonl"),
        "--input-file",
        "-i",
        help="Input JSONL file with ParsedDocument objects",
    ),
    manifest_file: Path = typer.Option(  # noqa: B008
        Path("data/raw/manifest.json"),
        "--manifest-file",
        "-m",
        help="Input manifest.json from preprocess step (for source file metadata)",
    ),
    output_db: Path = typer.Option(  # noqa: B008
        Path("data/cra_rules.db"),
        "--output-db",
        "-o",
        help="Output SQLite database path",
    ),
    output_manifest: Path = typer.Option(  # noqa: B008
        Path("data/manifest.json"),
        "--output-manifest",
        help="Output manifest.json path",
    ),
    data_version: str = typer.Option(
        "2024.12",
        "--data-version",
        "-v",
        help="Data version string (YYYY.MM format)",
    ),
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="Skip chunks with embedding errors instead of failing",
    ),
) -> None:
    """
    Build searchable SQLite database from parsed JSONL chunks.

    Loads ParsedDocument chunks from JSONL, generates BGE embeddings,
    and populates SQLite database with FTS5 and vector search indexes.

    Example:
        uv run python scripts/cli.py build --input-file data/processed/chunks.jsonl

    """
    console.print("[bold blue]QuickExpense RAG Index Building[/bold blue]")
    console.print(f"Input: {input_file}")
    console.print(f"Manifest: {manifest_file}")
    console.print(f"Output DB: {output_db}")
    console.print(f"Output Manifest: {output_manifest}")
    console.print(f"Data Version: {data_version}\n")

    # Verify input file exists
    if not input_file.exists():
        console.print(f"[red]Error: Input file not found: {input_file}[/red]")
        raise typer.Exit(code=1)

    # Verify manifest file exists
    if not manifest_file.exists():
        console.print(f"[red]Error: Manifest file not found: {manifest_file}[/red]")
        raise typer.Exit(code=1)

    # Create output directories
    output_db.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Load source files from preprocess manifest
        console.print("[cyan]Loading source file metadata...[/cyan]")
        with manifest_file.open() as f:
            manifest_data = json.load(f)

        # Convert manifest documents to SourceFile models
        source_files = []
        for doc in manifest_data.get("documents", []):
            source_files.append(
                SourceFile(
                    path=doc["filename"],
                    url=doc["source_url"],
                    hash=doc["sha256"],
                )
            )

        if not source_files:
            console.print("[yellow]Warning: No source files found in manifest[/yellow]")

        console.print(f"Loaded {len(source_files)} source file records\n")

        # Initialize IndexBuilder
        console.print("[cyan]Initializing IndexBuilder...[/cyan]")
        builder = IndexBuilder(db_path=str(output_db), encoder=embedding_service)

        # Build index
        console.print("[cyan]Building index (this may take a while)...[/cyan]\n")
        builder.build_from_jsonl(
            jsonl_path=str(input_file),
            manifest_path=str(output_manifest),
            source_files=source_files,
            data_version=data_version,
            continue_on_error=continue_on_error,
        )

        # Success summary
        console.print("\n[bold green]Index Build Complete![/bold green]")
        console.print(f"✅ Database: {output_db}")
        console.print(f"✅ Manifest: {output_manifest}")

        # Show database size
        db_size_mb = output_db.stat().st_size / (1024 * 1024)
        console.print(f"📊 Database size: {db_size_mb:.2f} MB")

    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON in manifest file: {e}[/red]")
        raise typer.Exit(code=1) from e

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from e

    except Exception as e:
        console.print(f"[red]Build failed: {e}[/red]")
        logger.exception("Build failed")
        raise typer.Exit(code=1) from e


@app.command()
def validate(
    db_path: Path = typer.Option(  # noqa: B008
        Path("data/cra_rules.db"),
        "--db-path",
        "-d",
        help="Path to SQLite database to validate",
    ),
) -> None:
    """
    Validate database integrity and perform smoke tests.

    Runs comprehensive validation checks including schema verification,
    row count consistency, embedding dimensions, and live search test.

    Example:
        uv run python scripts/cli.py validate --db-path data/cra_rules.db

    """
    console.print("[bold blue]QuickExpense RAG Database Validation[/bold blue]")
    console.print(f"Database: {db_path}\n")

    # Verify database exists
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/red]")
        raise typer.Exit(code=1)

    try:
        # Initialize validator
        validator = IndexValidator(db_path=db_path)

        # Run validation
        console.print("[cyan]Running validation checks...[/cyan]\n")
        report = validator.validate()

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise

    except Exception as e:
        console.print(f"[red]Validation error: {e}[/red]")
        logger.exception("Validation failed")
        raise typer.Exit(code=1) from e

    # Display results with rich formatting
    from rich.panel import Panel
    from rich.table import Table

    # Overall status
    overall_passed = report["overall_passed"]
    status_color = "green" if overall_passed else "red"
    status_emoji = "✅" if overall_passed else "❌"
    status_text = "PASSED" if overall_passed else "FAILED"

    console.print(
        Panel(
            f"[{status_color}]{status_emoji} Validation {status_text}[/{status_color}]",
            title="Validation Summary",
            border_style=status_color,
        )
    )

    # Detailed checks table
    table = Table(title="Validation Checks", show_header=True)
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Details")

    for check_name, check_result in report.items():
        if check_name == "overall_passed":
            continue

        if isinstance(check_result, dict):
            passed = check_result.get("passed", False)
            message = check_result.get("message", "")
            status = "✅" if passed else "❌"
            table.add_row(check_name, status, message)

    console.print(table)

    # Statistics (if available)
    if "statistics" in report and isinstance(report["statistics"], dict):
        stats = report["statistics"]
        console.print("\n[bold cyan]Database Statistics:[/bold cyan]")
        for key, value in stats.items():
            console.print(f"  {key}: {value}")

    # Exit with appropriate code
    if overall_passed:
        console.print("\n[bold green]All validation checks passed![/bold green]")
        raise typer.Exit(code=0)
    else:
        console.print(
            "\n[bold red]Some validation checks failed. "
            "Please review the details above.[/bold red]"
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
