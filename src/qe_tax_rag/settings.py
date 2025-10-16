"""Application settings using pydantic-settings."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration for the QuickExpense RAG library.

    Settings are loaded from environment variables with the prefix 'QUICKEXPENSE_RAG_'.
    An optional .env file can also be used.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="QUICKEXPENSE_RAG_",
        case_sensitive=False,
        extra="forbid",
        frozen=True,
    )

    # Data settings
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "quickexpense_rag",
        description="Directory to cache the downloaded database.",
    )
    db_download_url: str = Field(
        # Placeholder URL, should be updated when a release exists
        default="https://github.com/manonja/quickExpense-rag/releases/download/data-v2025.10/cra_rules.db",
        description="URL to download the SQLite database from.",
    )
    db_filename: str = Field(
        default="cra_rules.db",
        description="Default filename for the downloaded database.",
    )

    # Embedding settings
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="SentenceTransformer model for embeddings.",
    )
    embedding_device: str = Field(
        default="cpu", description="Device to run embedding model on ('cpu', 'cuda')."
    )
    embedding_batch_size: int = Field(
        default=32, ge=1, description="Batch size for embedding generation."
    )

    # Search settings
    default_top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Default number of search results to return.",
    )
    rrf_k: int = Field(
        default=60,
        description="Reciprocal Rank Fusion constant 'k' to balance result sets.",
    )

    # Network settings
    request_timeout: int = Field(
        default=30, description="Timeout in seconds for network requests."
    )

    # Gemini settings (for indexing pipeline only, not runtime)
    gemini_api_key: str = Field(
        default="", description="Gemini API key for document parsing (indexing only)."
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini model for document parsing.",
    )
    gemini_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Gemini temperature for parsing (0.0 = deterministic).",
    )

    # Database verification settings (bundled with library)
    database_sha256: str = Field(
        default="",  # Will be updated when production database is built
        description="Expected SHA256 checksum of the database file.",
    )
    database_version: str = Field(
        default="2025.10",
        description="Expected data version in YYYY.MM format.",
    )
    schema_version: str = Field(
        default="1.0",
        description="Expected schema version (major.minor).",
    )

    @field_validator("db_download_url", mode="after")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        """Ensure URL is valid and uses https scheme."""
        if not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


# Single, reusable settings instance for the library
settings = Settings()
