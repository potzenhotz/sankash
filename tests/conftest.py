"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from sankash.core.storage import init_data_dir


@pytest.fixture
def test_data_dir(tmp_path: Path) -> str:
    """Create a temporary data directory for testing."""
    data_dir = str(tmp_path / "data")
    init_data_dir(data_dir)
    return data_dir
