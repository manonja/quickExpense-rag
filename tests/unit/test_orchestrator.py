"""Unit tests for extraction pipeline orchestrator."""

import pytest

from src.qe_tax_rag.extraction.ca.orchestrator import run_extraction


def test_orchestrator_module_imports() -> None:
    """Verify orchestrator module and function can be imported."""
    assert callable(run_extraction)
