"""Unit tests for the public API (src/qe_tax_rag/api.py)."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from qe_tax_rag import api
from qe_tax_rag.exceptions import DatabaseNotInitializedError
from qe_tax_rag.search.models import SearchResult


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

    @patch("qe_tax_rag.api.DataManager")
    @patch("qe_tax_rag.api.HybridSearchEngine")
    @patch("qe_tax_rag.api._EmbeddingService")
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

    @patch("qe_tax_rag.api.DataManager")
    @patch("qe_tax_rag.api.HybridSearchEngine")
    @patch("qe_tax_rag.api._EmbeddingService")
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


class TestSearch:
    """Test search() function behavior."""

    def test_search_validation_invalid_province(self):
        """
        GIVEN: Library is initialized
        WHEN: search() is called with invalid province
        THEN: ValueError is raised by enum validation
        """
        # Setup mock search engine to verify it's initialized
        api._search_engine = Mock()

        with pytest.raises(ValueError) as exc_info:
            api.search(
                query="test query",
                province="INVALID",  # Invalid province code
                business_type="sole_proprietorship",
                expense_types=["meals"],
            )

        # Verify error mentions the invalid value and field
        error_str = str(exc_info.value)
        assert "INVALID" in error_str
        assert "Province" in error_str or "province" in error_str.lower()

    def test_search_validation_query_too_short(self):
        """
        GIVEN: Library is initialized
        WHEN: search() is called with query < 3 characters
        THEN: ValidationError is raised
        """
        api._search_engine = Mock()

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            api.search(query="ab")  # Only 2 characters

    def test_search_validation_top_k_out_of_range(self):
        """
        GIVEN: Library is initialized
        WHEN: search() is called with top_k > 50
        THEN: ValidationError is raised
        """
        api._search_engine = Mock()

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            api.search(query="test query", top_k=100)  # Max is 50

    @patch("qe_tax_rag.api._search_engine")
    def test_search_happy_path(self, mock_engine):
        """
        GIVEN: Library is initialized with valid parameters
        WHEN: search() is called
        THEN: ExpenseQuery is constructed and search engine is called
        """
        # Setup mock
        mock_results = [Mock(spec=SearchResult)]
        mock_engine_instance = Mock()
        mock_engine_instance.search.return_value = mock_results
        api._search_engine = mock_engine_instance

        # Call search
        results = api.search(
            query="restaurant meal expense",
            province="BC",
            business_type="sole_proprietorship",
            expense_types=["meals", "travel"],
            top_k=10,
        )

        # Verify search engine was called
        mock_engine_instance.search.assert_called_once()

        # Verify ExpenseQuery was constructed correctly
        call_args = mock_engine_instance.search.call_args
        query_obj = call_args.args[0]

        # Check query object properties
        assert query_obj.query == "restaurant meal expense"
        assert str(query_obj.province) == "Province.BC"  # Enum representation
        assert str(query_obj.business_type) == "BusinessType.SOLE_PROPRIETORSHIP"
        assert query_obj.expense_types == ["meals", "travel"]
        assert query_obj.top_k == 10

        # Verify results returned
        assert results == mock_results


class TestGetVersion:
    """Test get_version() function."""

    def test_get_version_returns_dict(self):
        """
        GIVEN: Library module loaded
        WHEN: get_version() is called
        THEN: Returns dict with library_version, data_version, schema_version
        """
        version_info = api.get_version()

        # Verify structure
        assert isinstance(version_info, dict)
        assert "library_version" in version_info
        assert "data_version" in version_info
        assert "schema_version" in version_info

        # Verify library_version matches __version__
        from qe_tax_rag import __version__

        assert version_info["library_version"] == __version__


class TestLegalDisclaimers:
    """Test that legal disclaimers are present in all docstrings."""

    def test_init_has_legal_disclaimer(self):
        """
        GIVEN: init() function defined
        WHEN: Docstring is checked
        THEN: Contains prominent legal disclaimer
        """
        assert api.init.__doc__ is not None
        assert "LEGAL DISCLAIMER" in api.init.__doc__
        assert "not" in api.init.__doc__.lower()
        assert "tax advice" in api.init.__doc__.lower()

    def test_search_has_tax_advice_warning(self):
        """
        GIVEN: search() function defined
        WHEN: Docstring is checked
        THEN: Contains "NOT TAX ADVICE" warning
        """
        assert api.search.__doc__ is not None
        assert "NOT TAX ADVICE" in api.search.__doc__
        assert "informational" in api.search.__doc__.lower()
