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

from preprocessor.models import DownloadMetadata, PreprocessManifest
from preprocessor.text_extractor import TextExtractor
from qe_tax_rag.data.builder import IndexBuilder
from qe_tax_rag.data.validator import IndexValidator
from qe_tax_rag.embeddings.encoder import embedding_service
from qe_tax_rag.extraction.ca.orchestrator import run_extraction
from qe_tax_rag.search.models import SourceFile

from parser.gemini_parser import GeminiParser

# Initialize Typer app and Rich console
app = typer.Typer(help="QE Tax RAG Preprocessing CLI")
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

    console.print(f"[bold blue]QE Tax RAG Preprocessing[/bold blue]")
    console.print(f"Input: {input_dir}")
    console.print(f"Output: {output_dir}\n")

    # Run preprocessing logic via shared helper
    file_count, _manifest_path = _run_preprocess_logic(
        input_dir=input_dir,
        output_dir=output_dir,
        console=console,
    )

    # Early exit if no files found
    if file_count == 0:
        return


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
    console.print("[bold blue]QE Tax RAG Parsing (Gemini Flash)[/bold blue]")
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
        help="Input YAML or JSONL file with rules/documents",
    ),
    manifest_file: Path | None = typer.Option(  # noqa: B008
        None,
        "--manifest-file",
        "-m",
        help="Optional manifest.json with source file metadata (auto-generated if missing)",
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
    Build searchable SQLite database from YAML or JSONL files.

    Loads rules from YAML (extraction pipeline) or JSONL (Gemini parser),
    generates BGE embeddings, and populates SQLite database with FTS5 and
    vector search indexes.

    The manifest file is optional - if not provided, source file metadata
    will be auto-generated from the input file.

    Example:
        uv run python scripts/cli.py build --input-file output/rules.yml

    """
    console.print("[bold blue]QE Tax RAG Index Building[/bold blue]")
    console.print(f"Input: {input_file}")
    console.print(f"Manifest: {manifest_file if manifest_file else '(auto-generated)'}")
    console.print(f"Output DB: {output_db}")
    console.print(f"Output Manifest: {output_manifest}")
    console.print(f"Data Version: {data_version}\n")

    # Run build logic via shared helper
    _run_build_logic(
        input_file=input_file,
        manifest_file=manifest_file,
        output_db=output_db,
        output_manifest=output_manifest,
        data_version=data_version,
        continue_on_error=continue_on_error,
        console=console,
    )


def _run_preprocess_logic(
    input_dir: Path,
    output_dir: Path,
    console: Console,
) -> tuple[int, Path]:
    """
    Run preprocessing logic (HTML/PDF → clean text).

    Shared by both preprocess() command and pipeline() command.

    Args:
        input_dir: Directory containing HTML/PDF files
        output_dir: Directory for preprocessed text files
        console: Rich console for output

    Returns:
        Tuple of (file_count, manifest_path)

    Raises:
        typer.Exit: If input directory not found or no files to process

    """
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
        # Return 0 count for preprocess() to handle gracefully
        # But raise for pipeline() to fail-fast
        return (0, input_dir / "manifest.json")

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

    return (len(all_files), manifest_path)


def _extract_source_files_from_input(input_path: Path) -> list[SourceFile]:
    """
    Extract unique source file names from YAML or JSONL input.

    For YAML: reads ExtractedRule.source_file field (HTML pipeline)
              or ExtractedContent.source_file field (PDF pipeline)
    For JSONL: reads ParsedDocument.source_filename field

    Args:
        input_path: Path to YAML or JSONL file

    Returns:
        List of SourceFile objects with auto-generated metadata

    """
    source_filenames: set[str] = set()

    if input_path.suffix in [".yml", ".yaml"]:
        # Parse YAML and extract source_file from each rule
        import yaml

        with open(input_path) as f:
            data = yaml.safe_load(f)

        # Handle HTML extraction format (rules field)
        for rule in data.get("rules", []):
            if source_file := rule.get("source_file"):
                source_filenames.add(source_file)

        # Handle PDF extraction format (content field)
        for content_item in data.get("content", []):
            if source_file := content_item.get("source_file"):
                source_filenames.add(source_file)

    elif input_path.suffix == ".jsonl":
        # Parse JSONL and extract source_filename from each document
        with open(input_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                doc = json.loads(line)
                if source_filename := doc.get("source_filename"):
                    source_filenames.add(source_filename)

    # Convert to SourceFile objects with placeholder metadata
    return [
        SourceFile(
            path=filename,
            url=f"file://{filename}",  # Placeholder URL
            hash="",  # Hash not critical for manual workflows
        )
        for filename in sorted(source_filenames)
    ]


def _run_build_logic(
    input_file: Path,
    manifest_file: Path | None,
    output_db: Path,
    output_manifest: Path,
    data_version: str,
    continue_on_error: bool,
    console: Console,
) -> None:
    """
    Run database build logic (JSONL/YAML → SQLite + embeddings).

    Shared by both build() command and pipeline() command.

    Args:
        input_file: Input YAML or JSONL file with rules/documents
        manifest_file: Optional input manifest.json from preprocess step.
            If None, source file metadata is auto-generated from input_file.
        output_db: Output SQLite database path
        output_manifest: Output manifest.json path
        data_version: Data version string (YYYY.MM format)
        continue_on_error: Skip chunks with embedding errors instead of failing
        console: Rich console for output

    Raises:
        typer.Exit: If input file not found or build fails

    """
    # Verify input file exists
    if not input_file.exists():
        console.print(f"[red]Error: Input file not found: {input_file}[/red]")
        raise typer.Exit(code=1)

    # Create output directories
    output_db.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Load or auto-generate source files
        if manifest_file and manifest_file.exists():
            # Load source files from existing manifest
            console.print("[cyan]Loading source file metadata from manifest...[/cyan]")
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
                console.print(
                    "[yellow]Warning: No source files found in manifest[/yellow]"
                )

            console.print(f"Loaded {len(source_files)} source file records\n")

        else:
            # Auto-generate source file metadata from input file
            console.print(
                "[cyan]Auto-generating source file metadata from input...[/cyan]"
            )

            # Extract unique source files from input
            source_files = _extract_source_files_from_input(input_file)

            console.print(f"Auto-generated {len(source_files)} source file record(s)\n")

        # Initialize IndexBuilder
        console.print("[cyan]Initializing IndexBuilder...[/cyan]")
        builder = IndexBuilder(db_path=str(output_db), encoder=embedding_service)

        # Build index
        console.print("[cyan]Building index (this may take a while)...[/cyan]\n")
        builder.build_index(
            input_path=input_file,
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


@app.command()
def pipeline(
    input_dir: Path = typer.Option(  # noqa: B008
        Path("data/raw"),
        "--input-dir",
        "-i",
        help="Directory containing HTML/PDF files",
    ),
    preprocessed_dir: Path = typer.Option(  # noqa: B008
        Path("data/preprocessed"),
        "--preprocessed-dir",
        help="Directory for preprocessed text files",
    ),
    processed_dir: Path = typer.Option(  # noqa: B008
        Path("data/processed"),
        "--processed-dir",
        help="Directory for processed JSONL files",
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
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompts and continue on non-critical errors",
    ),
) -> None:
    """
    Run full indexing pipeline: preprocess → parse → build → validate.

    Orchestrates the complete workflow from raw HTML/PDF files to
    validated searchable database. Stateless execution - always
    runs from beginning and overwrites existing artifacts.

    Stages:
    1. Preprocess: HTML/PDF → clean text
    2. Parse: Text → structured JSONL (requires GEMINI_API_KEY)
    3. Build: JSONL → SQLite database with embeddings
    4. Validate: Smoke tests for database integrity

    Example:
        export GEMINI_API_KEY="your-key-here"
        uv run python scripts/cli.py pipeline --input-dir data/raw

    """
    console.print("[bold blue]QE Tax RAG Full Pipeline[/bold blue]")
    console.print(f"Input: {input_dir}")
    console.print(f"Output DB: {output_db}\n")

    # Check for existing artifacts
    existing_artifacts = []
    if preprocessed_dir.exists() and any(preprocessed_dir.iterdir()):
        existing_artifacts.append(f"Preprocessed directory: {preprocessed_dir}")
    if processed_dir.exists() and any(processed_dir.iterdir()):
        existing_artifacts.append(f"Processed directory: {processed_dir}")
    if output_db.exists():
        existing_artifacts.append(f"Database: {output_db}")
    if output_manifest.exists():
        existing_artifacts.append(f"Manifest: {output_manifest}")

    # Prompt for confirmation if artifacts exist (unless --force)
    if existing_artifacts and not force:
        console.print(
            "[yellow]Warning: The following artifacts will be overwritten:[/yellow]"
        )
        for artifact in existing_artifacts:
            console.print(f"  - {artifact}")

        if not typer.confirm("\nContinue and overwrite?"):
            console.print("[yellow]Pipeline cancelled by user.[/yellow]")
            raise typer.Exit(code=0)

    # Stage 1: Preprocess
    console.print("\n[bold cyan]Stage 1/4: Preprocessing HTML/PDF files[/bold cyan]")
    try:
        # Run preprocessing via shared helper function
        file_count, _manifest_path = _run_preprocess_logic(
            input_dir=input_dir,
            output_dir=preprocessed_dir,
            console=console,
        )

        # Fail-fast if no files found (pipeline requires files)
        if file_count == 0:
            console.print(
                f"[red]Error: No HTML or PDF files found in {input_dir}[/red]"
            )
            raise typer.Exit(code=1)

    except typer.Exit:
        raise

    # Stage 2: Parse
    console.print("[bold cyan]Stage 2/4: Parsing with Gemini Flash[/bold cyan]")

    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print(
            "[red]Error: GEMINI_API_KEY environment variable not set[/red]\n"
            "Please set your Gemini API key:\n"
            "  export GEMINI_API_KEY='your-key-here'"
        )
        raise typer.Exit(code=1)

    try:
        processed_dir.mkdir(parents=True, exist_ok=True)
        chunks_file = processed_dir / "chunks.jsonl"

        txt_files = sorted(preprocessed_dir.glob("*.txt"))
        console.print(f"Found {len(txt_files)} text files to parse")

        parser = GeminiParser(api_key=api_key)
        success_count = 0

        with chunks_file.open("w", encoding="utf-8") as outfile:
            for txt_file in track(txt_files, description="Parsing documents..."):
                text_content = txt_file.read_text(encoding="utf-8")
                parsed_doc = parser.parse_document(
                    text=text_content, source_filename=txt_file.name
                )
                json_str = parsed_doc.model_dump_json()
                outfile.write(json_str + "\n")
                success_count += 1

        console.print(f"✅ Parsed {success_count} files\n")

    except typer.Exit:
        raise

    # Stage 3: Build
    console.print("[bold cyan]Stage 3/4: Building searchable database[/bold cyan]")
    try:
        # Run build logic via shared helper function
        manifest_file = input_dir / "manifest.json"
        _run_build_logic(
            input_file=chunks_file,
            manifest_file=manifest_file,
            output_db=output_db,
            output_manifest=output_manifest,
            data_version=data_version,
            continue_on_error=force,
            console=console,
        )

    except typer.Exit:
        raise

    # Stage 4: Validate
    console.print("[bold cyan]Stage 4/4: Validating database[/bold cyan]")
    try:
        validator = IndexValidator(db_path=output_db)
        report = validator.validate()

        if report["overall_passed"]:
            console.print("✅ Validation passed\n")
        else:
            console.print("[yellow]⚠️  Some validation checks failed[/yellow]\n")

    except typer.Exit:
        raise
    except Exception:
        # Don't fail the pipeline if validation fails - just log the exception
        console.print(
            "[yellow]Warning: Validation failed (see logs for details)[/yellow]"
        )
        logger.exception("Validation failed")

    # Success summary
    console.print("[bold green]Pipeline Complete![/bold green]")
    console.print(f"✅ Database: {output_db}")
    console.print(f"✅ Manifest: {output_manifest}")

    # Show database size
    db_size_mb = output_db.stat().st_size / (1024 * 1024)
    console.print(f"📊 Database size: {db_size_mb:.2f} MB")


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
    console.print("[bold blue]QE Tax RAG Database Validation[/bold blue]")
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


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query text"),
    db_path: Path = typer.Option(  # noqa: B008
        Path("output/PRE-144/mvp_rules.db"),
        "--db-path",
        "-d",
        help="Path to SQLite database",
    ),
    province: str | None = typer.Option(
        None, "--province", "-p", help="Filter by province (BC, AB, ON, etc.)"
    ),
    business_type: str | None = typer.Option(
        None, "--business-type", "-b", help="Filter by business type"
    ),
    expense_types: list[str] | None = typer.Option(  # noqa: B008
        None,
        "--expense-type",
        "-e",
        help="Filter by expense types (can repeat: -e meals -e vehicle)",
    ),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
) -> None:
    """
    Search CRA tax rules database with lineage tracing.

    Examples:
        uv run python scripts/cli.py search "meal expenses"
        uv run python scripts/cli.py search "LINE-8523" --top-k 1
        uv run python scripts/cli.py search "vehicle" --province BC --top-k 3

    """
    from qe_tax_rag.search.enums import BusinessType, Province
    from qe_tax_rag.search.hybrid import HybridSearchEngine
    from qe_tax_rag.search.models import ExpenseQuery
    from rich.table import Table

    console.print("[bold blue]QE Tax RAG Search[/bold blue]")
    console.print(f"Query: {query}")
    console.print(f"Database: {db_path}\n")

    # Verify database exists
    if not db_path.exists():
        console.print(f"[red]Error: Database not found: {db_path}[/red]")
        raise typer.Exit(code=1)

    try:
        # Parse enum filters if provided
        province_enum = Province(province) if province else None
        business_type_enum = BusinessType(business_type) if business_type else None

        # Build search query
        search_query = ExpenseQuery(
            query=query,
            province=province_enum,
            business_type=business_type_enum,
            expense_types=expense_types if expense_types else None,
            top_k=top_k,
        )

        # Initialize search engine
        engine = HybridSearchEngine(db_path=db_path, encoder=embedding_service)

        # Execute search
        console.print("[cyan]Searching...[/cyan]\n")
        results = engine.search(search_query)

        # Display results
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        console.print(f"[green]Found {len(results)} results:[/green]\n")

        # Create Rich table
        table = Table(
            title="Search Results", show_header=True, header_style="bold cyan"
        )
        table.add_column("Citation ID", style="cyan", no_wrap=True)
        table.add_column("Content Preview", style="white", max_width=60)
        table.add_column("Lineage Chain", style="yellow", max_width=40)
        table.add_column("Source", style="green", max_width=20)

        for result in results:
            # Truncate content for preview
            content_preview = (
                result.content[:150] + "..."
                if len(result.content) > 150
                else result.content
            )

            # Extract lineage info
            lineage_chain = result.lineage.lineage_chain if result.lineage else "N/A"
            source_doc = result.lineage.source_document if result.lineage else "N/A"

            table.add_row(
                result.citation_id,
                content_preview,
                lineage_chain,
                source_doc,
            )

        console.print(table)

        # Display legal disclaimer
        console.print("\n[bold yellow]⚠️  DISCLAIMER[/bold yellow]")
        console.print(results[0].disclaimer)

    except ValueError as e:
        console.print(f"[red]Error: Invalid filter value: {e}[/red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Search failed")
        raise typer.Exit(code=1) from e


@app.command(name="pipeline-extraction")
def pipeline_extraction(
    input_dir: Path = typer.Option(  # noqa: B008
        ...,
        "--input-dir",
        "-i",
        help="Directory containing HTML files",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_db: Path = typer.Option(  # noqa: B008
        ...,
        "--output-db",
        "-o",
        help="Output SQLite database path",
    ),
    intermediate_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--intermediate-dir",
        help="Directory for intermediate files (YAML, JSONL). Default: temp dir",
    ),
    keep_intermediate: bool = typer.Option(
        False,
        "--keep-intermediate",
        help="Keep intermediate YAML and JSONL files after completion",
    ),
) -> None:
    r"""
    Run complete extraction-to-database pipeline.

    This command orchestrates:
    1. Extract rules from HTML → YAML (canonical orchestrator)
    2. Build RAG database directly from YAML (IndexBuilder with auto-detection)
    3. Validate database integrity

    Note: This pipeline now skips the intermediate JSONL transformation step,
    going directly from YAML to SQLite for improved performance.

    Example:
        uv run python scripts/cli.py pipeline-extraction \
          --input-dir cra_documents/cra_t4002e_rev24_dump/ \
          --output-db data/cra_rules.db

    """
    import shutil
    import tempfile

    console.print("[bold blue]QE Tax RAG Extraction Pipeline[/bold blue]")
    console.print(f"Input: {input_dir}")
    console.print(f"Output DB: {output_db}\n")

    # Setup intermediate directory
    temp_dir_created = False
    if intermediate_dir:
        work_dir = intermediate_dir
        work_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"Using intermediate directory: {work_dir}")
    else:
        temp_dir = tempfile.mkdtemp(prefix="qetax_extract_")
        work_dir = Path(temp_dir)
        temp_dir_created = True
        console.print(f"Using temporary directory: {work_dir}")

    # Define intermediate file paths
    yml_path = work_dir / "rules.yml"
    manual_path = work_dir / "manual_review.yml"

    pipeline_success = False
    try:
        # =====================================================================
        # Stage 1/3: Extract rules
        # =====================================================================
        try:
            console.print(
                "\n[bold cyan]Stage 1/3: Extracting rules from HTML[/bold cyan]"
            )

            # Find HTML files
            html_files = sorted(input_dir.glob("*.html"))
            if not html_files:
                console.print(f"[red]Error: No HTML files found in {input_dir}[/red]")
                raise typer.Exit(code=1)

            console.print(f"Found {len(html_files)} HTML files to process")

            # Run extraction (HTML → YAML) via canonical orchestrator
            logger.info("Calling canonical orchestrator for extraction")
            extraction_result = run_extraction(
                input_path=input_dir,
                output_yaml=yml_path,
                manual_review_yaml=manual_path,
            )

            console.print(
                f"✅ Extracted {extraction_result['total_rules']} rules to YAML"
            )

        except typer.Exit:
            raise
        except Exception:
            console.print("\n[red]❌ Stage 1/3 (Extraction) failed[/red]")
            logger.exception("Stage 1 (Extraction) failed")
            raise

        # =====================================================================
        # Stage 2/3: Build database
        # =====================================================================
        try:
            console.print(
                "\n[bold cyan]Stage 2/3: Building searchable database[/bold cyan]"
            )

            # Create manifest for extraction pipeline
            manifest_path = work_dir / "manifest.json"
            source_files = [
                SourceFile(
                    path=f.name,
                    url=f"file://{f.absolute()}",
                    hash="",  # Hash not critical for extraction pipeline
                )
                for f in html_files
            ]

            # Build index (directly from YAML, bypassing transformer)
            output_db.parent.mkdir(parents=True, exist_ok=True)
            builder = IndexBuilder(db_path=str(output_db), encoder=embedding_service)
            builder.build_index(
                input_path=yml_path,  # Use YAML directly
                manifest_path=str(manifest_path),
                source_files=source_files,
                data_version="2024.12",
                continue_on_error=False,
            )

            console.print(f"✅ Database built: {output_db}")

            # Show database size
            db_size_mb = output_db.stat().st_size / (1024 * 1024)
            console.print(f"   Database size: {db_size_mb:.2f} MB")

        except typer.Exit:
            raise
        except Exception:
            console.print("\n[red]❌ Stage 2/3 (Build) failed[/red]")
            logger.exception("Stage 2 (Build) failed")
            raise

        # =====================================================================
        # Stage 3/3: Validate database
        # =====================================================================
        try:
            console.print("\n[bold cyan]Stage 3/3: Validating database[/bold cyan]")

            validator = IndexValidator(db_path=output_db)
            validation_report = validator.validate()

            if validation_report["overall_passed"]:
                console.print("✅ Validation passed")
            else:
                console.print("[yellow]⚠️  Some validation checks failed[/yellow]")

        except typer.Exit:
            raise
        except Exception:
            console.print("\n[red]❌ Stage 3/3 (Validation) failed[/red]")
            logger.exception("Stage 3 (Validation) failed")
            raise

        pipeline_success = True

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise

    finally:
        # Cleanup intermediate files if applicable
        if temp_dir_created:
            if not pipeline_success:
                console.print(
                    f"\n[yellow]⚠️  Pipeline failed. "
                    f"Intermediate files kept for debugging:[/yellow]"
                )
                console.print(f"   {work_dir}")
            elif not keep_intermediate:
                console.print("\n🧹 Cleaning up intermediate files")
                shutil.rmtree(work_dir, ignore_errors=True)
            else:
                console.print(f"\nIntermediate files kept at: {work_dir}")

    # Success summary
    console.print("\n[bold green]🎉 Pipeline complete![/bold green]")
    console.print(f"✅ Database: {output_db}")


if __name__ == "__main__":
    app()
