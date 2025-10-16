"""Configuration settings for the Canadian HTML-to-YAML extraction pipeline."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the data extraction pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QE_TAX_RAG_EXTRACTION_",
    )

    # Gemini API Configuration
    gemini_api_key: str = Field(
        default="",
        description="Gemini API key for HTML-to-YAML extraction (required for operation).",
    )
    llm_model_name: str = "gemini-1.5-flash-latest"
    adjudicator_model_name: str = "gemini-1.5-pro-latest"


# Singleton instance
settings = Settings()
