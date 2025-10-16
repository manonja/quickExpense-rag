"""Unit tests for Gemini configuration in Settings."""

import os

import pytest


def test_gemini_settings_defaults():
    """Test Gemini settings have sensible defaults."""
    from src.qe_tax_rag.settings import Settings

    settings = Settings()

    assert settings.gemini_model == "gemini-2.0-flash-exp"
    assert settings.gemini_temperature == 0.0  # Deterministic
    assert settings.gemini_api_key == ""  # Empty by default (loaded from env)


def test_gemini_settings_from_env(monkeypatch):
    """Test Gemini settings load from environment variables."""
    from src.qe_tax_rag.settings import Settings

    monkeypatch.setenv("QE_TAX_RAG_GEMINI_API_KEY", "test-key-123")
    monkeypatch.setenv("QE_TAX_RAG_GEMINI_MODEL", "gemini-custom-model")
    monkeypatch.setenv("QE_TAX_RAG_GEMINI_TEMPERATURE", "0.5")

    settings = Settings()

    assert settings.gemini_api_key == "test-key-123"
    assert settings.gemini_model == "gemini-custom-model"
    assert settings.gemini_temperature == 0.5


def test_gemini_temperature_validation():
    """Test Gemini temperature is validated (0.0 to 1.0)."""
    from pydantic import ValidationError
    from src.qe_tax_rag.settings import Settings

    # Valid temperatures
    Settings(gemini_temperature=0.0)
    Settings(gemini_temperature=0.5)
    Settings(gemini_temperature=1.0)

    # Invalid temperatures
    with pytest.raises(ValidationError):
        Settings(gemini_temperature=-0.1)

    with pytest.raises(ValidationError):
        Settings(gemini_temperature=1.1)
