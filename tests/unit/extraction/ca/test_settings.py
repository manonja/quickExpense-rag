"""Tests for extraction pipeline settings management."""

import pytest
from pydantic import ValidationError
from qe_tax_rag.extraction.ca.settings import Settings, settings


def test_settings_has_empty_default_for_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify gemini_api_key defaults to empty string when not provided."""
    # Clear any existing API key from environment
    monkeypatch.delenv("QE_TAX_RAG_EXTRACTION_GEMINI_API_KEY", raising=False)

    config = Settings()
    assert config.gemini_api_key == ""


def test_settings_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify settings loads from environment variables with QE_TAX_RAG_EXTRACTION_ prefix."""
    test_api_key = "test-gemini-key-12345"

    monkeypatch.setenv("QE_TAX_RAG_EXTRACTION_GEMINI_API_KEY", test_api_key)

    config = Settings()
    assert config.gemini_api_key == test_api_key


def test_settings_has_default_model_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify default model names for Flash (parsing) and Pro (adjudication)."""
    monkeypatch.setenv("QE_TAX_RAG_EXTRACTION_GEMINI_API_KEY", "test-key")

    config = Settings()
    assert config.llm_model_name == "gemini-1.5-flash-latest"
    assert config.adjudicator_model_name == "gemini-1.5-pro-latest"


def test_settings_can_override_model_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify model names can be overridden via environment variables."""
    monkeypatch.setenv("QE_TAX_RAG_EXTRACTION_GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("QE_TAX_RAG_EXTRACTION_LLM_MODEL_NAME", "custom-flash-model")
    monkeypatch.setenv(
        "QE_TAX_RAG_EXTRACTION_ADJUDICATOR_MODEL_NAME", "custom-pro-model"
    )

    config = Settings()
    assert config.llm_model_name == "custom-flash-model"
    assert config.adjudicator_model_name == "custom-pro-model"


def test_settings_singleton_pattern() -> None:
    """Verify singleton instance works and is accessible."""
    # The singleton is created with environment variables already set
    # We just verify it's accessible and has the expected type
    assert isinstance(settings, Settings)
    assert hasattr(settings, "gemini_api_key")
    assert hasattr(settings, "llm_model_name")
    assert hasattr(settings, "adjudicator_model_name")
