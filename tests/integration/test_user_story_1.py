"""
Integration test for User Story 1: ML Engineer API.

This test verifies the complete end-to-end workflow as described in TICKET 8:
1. Call init() to initialize the library
2. Call search() with realistic query and filters
3. Verify results structure and content
4. Validate disclaimer, citation_id, source_url, expense_types
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import quickexpense_rag as qer
from quickexpense_rag.exceptions import DatabaseNotInitializedError


class TestUserStory1:
    """Integration test for User Story 1: ML Engineer API workflow.

    User Story 1: ML engineer imports library, calls init() to download database,
    then uses search() to query CRA expense rules with natural language and filters.
    Returns SearchResult objects with citations, disclaimers, and expense types.

    See plan.md section "User Story 1: ML Engineer API" for full specification.
    """

    @pytest.fixture(autouse=True)
    def setup_fixture_db(self, tmp_path, monkeypatch):
        """Configure library to use fixture database instead of downloading."""
        # Path to fixture database
        fixture_db = Path(__file__).parent.parent / "fixtures" / "test_database.db"
        assert fixture_db.exists(), f"Fixture database not found: {fixture_db}"

        # Copy fixture DB to temp cache directory
        import shutil
        test_db_path = tmp_path / "test_database.db"
        shutil.copy(fixture_db, test_db_path)

        # Mock DataManager.get_database_path to return fixture path
        def mock_get_database_path(self):  # noqa: ARG001
            return test_db_path

        monkeypatch.setattr(
            "quickexpense_rag.data.manager.DataManager.get_database_path",
            mock_get_database_path
        )

        return test_db_path

    def test_complete_user_story_1_workflow(self):
        """
        GIVEN: Fresh library state
        WHEN: User follows User Story 1 workflow (init → search → verify)
        THEN: All assertions pass as per TICKET 8 acceptance criteria
        """
        # Reset module state
        from quickexpense_rag import api
        api._search_engine = None
        api._db_path = None

        # Step 1: Initialize library
        qer.init()

        # Step 2: Search with realistic query and filters
        results = qer.search(
            query="restaurant expense while traveling for training",
            province="BC",
            business_type="sole_proprietorship",
            expense_types=["meals", "travel"],
        )

        # Step 3: Verify results structure (TICKET 8 acceptance criteria)
        assert len(results) > 0, "Expected at least one search result"

        # Step 4: Verify first result properties
        first_result = results[0]

        # Check disclaimer (computed field, always present)
        assert first_result.disclaimer.startswith("⚠️"), \
            "Disclaimer must start with warning emoji"
        assert "NOT TAX ADVICE" in first_result.disclaimer, \
            "Disclaimer must contain 'NOT TAX ADVICE'"

        # Check citation_id (unique CRA reference)
        assert first_result.citation_id is not None, \
            "citation_id must not be None"
        assert len(first_result.citation_id) > 0, \
            "citation_id must not be empty"

        # Check source_url (must be https://canada.ca)
        assert str(first_result.source_url).startswith("https://"), \
            "source_url must use HTTPS"
        assert "canada.ca" in str(first_result.source_url), \
            "source_url must be from canada.ca domain"

        # Check expense_types (many-to-many, list format)
        assert isinstance(first_result.expense_types, list), \
            "expense_types must be a list"
        assert len(first_result.expense_types) > 0, \
            "expense_types must not be empty"

        # Verify all results have required structure
        for result in results:
            assert hasattr(result, "content")
            assert hasattr(result, "score")
            assert hasattr(result, "citation_id")
            assert hasattr(result, "source_url")
            assert hasattr(result, "disclaimer")
            assert hasattr(result, "expense_types")

    def test_search_without_init_raises_error(self):
        """
        GIVEN: Library not initialized
        WHEN: search() is called
        THEN: DatabaseNotInitializedError is raised
        """
        # Reset module state
        from quickexpense_rag import api
        api._search_engine = None

        with pytest.raises(DatabaseNotInitializedError) as exc_info:
            qer.search(query="test query")

        assert "init()" in str(exc_info.value).lower()

    def test_get_version(self):
        """
        GIVEN: Library loaded
        WHEN: get_version() is called
        THEN: Returns valid version information
        """
        version_info = qer.get_version()

        assert isinstance(version_info, dict)
        assert "library_version" in version_info
        assert "data_version" in version_info
        assert "schema_version" in version_info
        assert version_info["library_version"] == qer.__version__
