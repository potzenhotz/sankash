"""Duplicate detection utilities using pure functions."""

import polars as pl


def find_duplicates(
    import_df: pl.DataFrame,
    existing_df: pl.DataFrame,
) -> pl.Series:
    """
    Find duplicate transactions using imported_id (pure function).

    Returns Series of imported_ids that already exist.
    """
    if existing_df.is_empty():
        return pl.Series("imported_id", [], dtype=pl.Utf8)

    # Check for imported_id matches
    existing_ids = existing_df["imported_id"].drop_nulls()
    import_ids = import_df["imported_id"]

    # Find intersection
    duplicates = import_ids.filter(import_ids.is_in(existing_ids))

    return duplicates


def find_similar_transactions(
    transaction_date: str,
    transaction_amount: float,
    transaction_payee: str,
    existing_df: pl.DataFrame,
    days_threshold: int = 3,
) -> pl.DataFrame:
    """
    Find similar transactions by date, amount, and payee (pure function).

    Used for manual duplicate checking.
    """
    # Filter by amount (exact match)
    similar = existing_df.filter(pl.col("amount") == transaction_amount)

    # Filter by payee (case-insensitive contains)
    similar = similar.filter(
        pl.col("payee").str.to_lowercase().str.contains(transaction_payee.lower())
    )

    # Filter by date within threshold
    # Note: This is simplified, proper date range filtering would need date parsing
    similar = similar.filter(pl.col("date") == transaction_date)

    return similar
