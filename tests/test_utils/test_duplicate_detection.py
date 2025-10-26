"""Tests for duplicate detection utilities."""

import polars as pl
import pytest

from sankash.utils.duplicate_detection import find_duplicates


def test_find_duplicates_empty_existing() -> None:
    """Test duplicate detection with empty existing DataFrame."""
    import_df = pl.DataFrame({
        "imported_id": ["id1", "id2", "id3"],
        "amount": [10.0, 20.0, 30.0],
    })

    existing_df = pl.DataFrame()

    duplicates = find_duplicates(import_df, existing_df)
    assert len(duplicates) == 0


def test_find_duplicates_no_matches() -> None:
    """Test duplicate detection with no matching IDs."""
    import_df = pl.DataFrame({
        "imported_id": ["id1", "id2", "id3"],
        "amount": [10.0, 20.0, 30.0],
    })

    existing_df = pl.DataFrame({
        "imported_id": ["id4", "id5", "id6"],
        "amount": [40.0, 50.0, 60.0],
    })

    duplicates = find_duplicates(import_df, existing_df)
    assert len(duplicates) == 0


def test_find_duplicates_with_matches() -> None:
    """Test duplicate detection with matching IDs."""
    import_df = pl.DataFrame({
        "imported_id": ["id1", "id2", "id3"],
        "amount": [10.0, 20.0, 30.0],
    })

    existing_df = pl.DataFrame({
        "imported_id": ["id2", "id5", "id6"],
        "amount": [20.0, 50.0, 60.0],
    })

    duplicates = find_duplicates(import_df, existing_df)
    assert len(duplicates) == 1
    assert duplicates[0] == "id2"


def test_find_duplicates_all_match() -> None:
    """Test duplicate detection where all imports are duplicates."""
    import_df = pl.DataFrame({
        "imported_id": ["id1", "id2", "id3"],
        "amount": [10.0, 20.0, 30.0],
    })

    existing_df = pl.DataFrame({
        "imported_id": ["id1", "id2", "id3", "id4"],
        "amount": [10.0, 20.0, 30.0, 40.0],
    })

    duplicates = find_duplicates(import_df, existing_df)
    assert len(duplicates) == 3
    assert set(duplicates.to_list()) == {"id1", "id2", "id3"}
