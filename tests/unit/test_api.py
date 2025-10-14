"""Unit tests for the public API (src/quickexpense_rag/api.py)."""

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
