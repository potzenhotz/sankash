"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from sankash.core.database import init_database


@pytest.fixture
def test_db_path(tmp_path: Path) -> str:
    """Create a temporary test database."""
    db_path = str(tmp_path / "test.duckdb")
    init_database(db_path)
    return db_path
