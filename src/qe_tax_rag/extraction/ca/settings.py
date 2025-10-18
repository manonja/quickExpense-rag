"""Configuration settings for the Canadian HTML-to-YAML extraction pipeline."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the data extraction pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QE_TAX_RAG_EXTRACTION_",
        extra="ignore",
    )

    # Gemini API Configuration
    gemini_api_key: str = Field(
        default="",
        description="Gemini API key for HTML-to-YAML extraction (required for operation).",
    )
    llm_model_name: str = "gemini-2.0-flash-exp"
    adjudicator_model_name: str = "gemini-2.0-flash-exp"

    # Caching Configuration
    cache_dir: str | None = Field(
        default=None,
        description="Directory to store cached LLM responses. If not set, caching is disabled.",
    )


# Singleton instance
settings = Settings()
