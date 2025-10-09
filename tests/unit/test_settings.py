"""Unit tests for the settings module."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from quickexpense_rag.settings import Settings


def test_settings_load_defaults() -> None:
    """Verify settings load with default values."""
    settings = Settings()
    assert settings.default_top_k == 5
    assert isinstance(settings.cache_dir, Path)
    assert "quickexpense_rag" in settings.cache_dir.parts


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify settings are overridden by environment variables."""
    monkeypatch.setenv("QUICKEXPENSE_RAG_DEFAULT_TOP_K", "20")
    monkeypatch.setenv("QUICKEXPENSE_RAG_CACHE_DIR", "/tmp/custom_cache")

    settings = Settings()

    assert settings.default_top_k == 20
    assert settings.cache_dir == Path("/tmp/custom_cache")


def test_settings_load_from_dotenv_file(tmp_path: Path) -> None:
    """Verify settings are loaded from a .env file."""
    env_content = """
    QUICKEXPENSE_RAG_DB_FILENAME="test.db"
    """
    env_file = tmp_path / ".env"
    env_file.write_text(env_content)

    # Create a temporary Settings class that points to our test .env file
    class TestSettings(Settings):
        model_config = Settings.model_config.copy()
        model_config["env_file"] = str(env_file)

    settings = TestSettings()

    assert settings.db_filename == "test.db"
    # A default value not in the file should still be present
    assert settings.default_top_k == 5


def test_settings_validation_error() -> None:
    """Verify invalid values raise a ValidationError."""
    with pytest.raises(
        ValidationError, match="Input should be greater than or equal to 1"
    ):
        Settings(default_top_k=0)

    with pytest.raises(
        ValidationError, match="Input should be less than or equal to 50"
    ):
        Settings(default_top_k=51)

    with pytest.raises(ValidationError, match="URL must start with"):
        Settings(db_download_url="not-a-valid-url")


def test_settings_forbid_extra_fields() -> None:
    """Verify that extra fields are forbidden."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Settings(some_unsupported_field="some_value")  # type: ignore[call-arg]
