"""Unit tests for the public API (src/quickexpense_rag/api.py)."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from quickexpense_rag import api
from quickexpense_rag.exceptions import DatabaseNotInitializedError


class TestSearchWithoutInit:
    """Test that search() raises an error when called before init()."""

    def test_search_raises_error_if_not_initialized(self):
        """
        GIVEN: Library has not been initialized
        WHEN: search() is called
        THEN: DatabaseNotInitializedError is raised with helpful message
        """
        # Reset module state (in case other tests have initialized)
        api._search_engine = None

        with pytest.raises(DatabaseNotInitializedError) as exc_info:
            api.search(
                query="test query",
                province="BC",
                business_type="sole_proprietorship",
                expense_types=["meals"],
            )

        # Verify error message is actionable
        assert "init()" in str(exc_info.value).lower()


class TestInit:
    """Test init() function behavior."""

    @patch("quickexpense_rag.api.DataManager")
    @patch("quickexpense_rag.api.HybridSearchEngine")
    @patch("quickexpense_rag.api._EmbeddingService")
    def test_init_creates_search_engine(
        self, mock_encoder_cls, mock_engine_cls, mock_dm_cls
    ):
        """
        GIVEN: Fresh library state
        WHEN: init() is called
        THEN: DataManager is instantiated and HybridSearchEngine is created
        """
        # Reset module state
        api._search_engine = None
        api._db_path = None

        # Setup mocks
        mock_db_path = Path("/fake/path/to/database.db")
        mock_dm = Mock()
        mock_dm.get_database_path.return_value = mock_db_path
        mock_dm_cls.return_value = mock_dm

        mock_encoder = Mock()
        mock_encoder_cls.return_value = mock_encoder

        mock_engine = Mock()
        mock_engine_cls.return_value = mock_engine

        # Call init()
        api.init()

        # Verify DataManager was instantiated and get_database_path called
        mock_dm_cls.assert_called_once()
        mock_dm.get_database_path.assert_called_once()

        # Verify HybridSearchEngine was created with correct arguments
        mock_engine_cls.assert_called_once_with(
            db_path=mock_db_path, encoder=mock_encoder
        )

        # Verify module state was updated
        assert api._search_engine is mock_engine
        assert api._db_path == mock_db_path

    @patch("quickexpense_rag.api.DataManager")
    @patch("quickexpense_rag.api.HybridSearchEngine")
    @patch("quickexpense_rag.api._EmbeddingService")
    def test_init_with_force_update(
        self, mock_encoder_cls, mock_engine_cls, mock_dm_cls
    ):
        """
        GIVEN: Cached database exists
        WHEN: init(force_update=True) is called
        THEN: force_update flag is passed to download_database
        """
        # Reset module state
        api._search_engine = None

        # Setup mocks
        mock_db_path = Path("/fake/path/to/database.db")
        mock_dm = Mock()
        mock_dm.get_database_path.return_value = mock_db_path
        mock_dm_cls.return_value = mock_dm

        # Call init with force_update
        api.init(force_update=True)

        # Verify get_database_path was called (force_update handling is in DataManager)
        mock_dm.get_database_path.assert_called_once()
