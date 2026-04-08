"""Transaction service with pure functions for business logic."""

from datetime import date, datetime
from typing import Optional

import polars as pl

from sankash.core.models import Transaction
from sankash.core.storage import (
    append_parquet,
    merge_overrides,
    next_id,
    read_json,
    read_overrides,
    read_parquet,
    write_json,
    write_overrides,
    write_parquet,
)


def _load_transactions(data_dir: str) -> pl.DataFrame:
    """Load transactions with overrides merged."""
    df = read_parquet(data_dir, "transactions")
    if df.is_empty():
        return df
    overrides = read_overrides(data_dir)
    return merge_overrides(df, overrides)


def get_transactions(
    data_dir: str,
    account_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    is_categorized: Optional[bool] = None,
    search_query: Optional[str] = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[pl.DataFrame, int]:
    """Get transactions with optional filters, search, sort, and pagination.

    Returns tuple of (Polars DataFrame, total_count) for paginated results.
    Includes import source information from import_history.
    """
    df = _load_transactions(data_dir)
    if df.is_empty():
        return pl.DataFrame(), 0

    # Apply filters
    if account_id is not None:
        df = df.filter(pl.col("account_id") == account_id)

    if start_date:
        df = df.filter(pl.col("date") >= start_date)

    if end_date:
        df = df.filter(pl.col("date") <= end_date)

    if category:
        df = df.filter(pl.col("category") == category)

    if min_amount is not None:
        df = df.filter(pl.col("amount") >= min_amount)

    if max_amount is not None:
        df = df.filter(pl.col("amount") <= max_amount)

    if is_categorized is not None:
        df = df.filter(pl.col("is_categorized") == is_categorized)

    if search_query:
        query_lower = search_query.lower()
        search_filter = pl.col("payee").str.to_lowercase().str.contains(query_lower, literal=True)
        if "notes" in df.columns:
            search_filter = search_filter | pl.col("notes").fill_null("").str.to_lowercase().str.contains(query_lower, literal=True)
        if "category" in df.columns:
            search_filter = search_filter | pl.col("category").fill_null("").str.to_lowercase().str.contains(query_lower, literal=True)
        df = df.filter(search_filter)

    total_count = len(df)

    # Sort
    sort_col = "amount" if sort_by == "amount" else "date"
    descending = sort_order != "asc"
    df = df.sort([sort_col, "id"], descending=[descending, True])

    # Join import_history for filename/date
    import_history = read_json(data_dir, "import_history")
    if import_history and isinstance(import_history, list) and "import_session_id" in df.columns:
        ih_df = pl.DataFrame(import_history).select(
            pl.col("id").alias("ih_id"),
            pl.col("filename").alias("import_filename"),
            pl.col("import_date"),
        )
        df = df.join(ih_df, left_on="import_session_id", right_on="ih_id", how="left")

    # Paginate
    df = df.slice(offset, limit)

    return df, total_count


def get_uncategorized_count(data_dir: str) -> int:
    """Get count of uncategorized transactions."""
    df = _load_transactions(data_dir)
    if df.is_empty():
        return 0
    return len(df.filter(pl.col("is_categorized") == False))  # noqa: E712


def update_transaction_category(
    data_dir: str, transaction_id: int, category: str, source: str = "manual"
) -> None:
    """Update transaction category via overrides.

    Args:
        source: "manual" for user-set categories, "rule" for rule-applied.
    """
    overrides = read_overrides(data_dir)
    tid = str(transaction_id)
    if tid not in overrides:
        overrides[tid] = {}
    overrides[tid]["category"] = category
    overrides[tid]["is_categorized"] = True
    overrides[tid]["category_source"] = source
    write_overrides(data_dir, overrides)


def bulk_update_categories(
    data_dir: str, transaction_ids: list[int], category: str, source: str = "manual"
) -> None:
    """Bulk update transaction categories via overrides."""
    overrides = read_overrides(data_dir)
    for tid_int in transaction_ids:
        tid = str(tid_int)
        if tid not in overrides:
            overrides[tid] = {}
        overrides[tid]["category"] = category
        overrides[tid]["is_categorized"] = True
        overrides[tid]["category_source"] = source
    write_overrides(data_dir, overrides)


def mark_as_transfer(
    data_dir: str,
    transaction_id: int,
    transfer_account_id: int,
) -> None:
    """Mark transaction as transfer via overrides."""
    overrides = read_overrides(data_dir)
    tid = str(transaction_id)
    if tid not in overrides:
        overrides[tid] = {}
    overrides[tid]["is_transfer"] = True
    overrides[tid]["transfer_account_id"] = transfer_account_id
    write_overrides(data_dir, overrides)


def create_transaction(data_dir: str, transaction: Transaction) -> int:
    """Create new transaction and return its ID."""
    existing = read_parquet(data_dir, "transactions")
    new_id = next_id(existing)

    new_row = pl.DataFrame([{
        "id": new_id,
        "account_id": transaction.account_id,
        "date": transaction.date,
        "payee": transaction.payee,
        "notes": transaction.notes,
        "amount": transaction.amount,
        "category": transaction.category,
        "is_categorized": transaction.is_categorized,
        "is_transfer": transaction.is_transfer,
        "transfer_account_id": transaction.transfer_account_id,
        "imported_id": transaction.imported_id,
        "import_session_id": transaction.import_session_id,
        "created_at": datetime.now().isoformat(),
    }])

    append_parquet(data_dir, "transactions", new_row)
    return new_id


def update_transaction(
    data_dir: str,
    transaction_id: int,
    transaction: Transaction,
) -> None:
    """Update existing transaction. Rewrites parquet for core field changes."""
    df = read_parquet(data_dir, "transactions")
    if df.is_empty():
        return

    # Update the row in parquet for core fields
    mask = pl.col("id") == transaction_id
    df = df.with_columns(
        pl.when(mask).then(pl.lit(transaction.account_id)).otherwise(pl.col("account_id")).alias("account_id"),
        pl.when(mask).then(pl.lit(transaction.date)).otherwise(pl.col("date")).alias("date"),
        pl.when(mask).then(pl.lit(transaction.payee)).otherwise(pl.col("payee")).alias("payee"),
        pl.when(mask).then(pl.lit(transaction.notes)).otherwise(pl.col("notes")).alias("notes"),
        pl.when(mask).then(pl.lit(transaction.amount)).otherwise(pl.col("amount")).alias("amount"),
    )
    write_parquet(data_dir, "transactions", df)

    # Update override fields
    overrides = read_overrides(data_dir)
    tid = str(transaction_id)
    if tid not in overrides:
        overrides[tid] = {}
    overrides[tid]["category"] = transaction.category
    overrides[tid]["is_categorized"] = transaction.is_categorized
    overrides[tid]["is_transfer"] = transaction.is_transfer
    overrides[tid]["transfer_account_id"] = transaction.transfer_account_id
    write_overrides(data_dir, overrides)


def delete_transaction(data_dir: str, transaction_id: int) -> None:
    """Delete transaction."""
    df = read_parquet(data_dir, "transactions")
    if not df.is_empty():
        df = df.filter(pl.col("id") != transaction_id)
        write_parquet(data_dir, "transactions", df)

    # Remove from overrides
    overrides = read_overrides(data_dir)
    tid = str(transaction_id)
    if tid in overrides:
        del overrides[tid]
        write_overrides(data_dir, overrides)


def delete_all_transactions(data_dir: str) -> None:
    """Delete all transactions and their import history."""
    write_parquet(data_dir, "transactions", pl.DataFrame())
    write_overrides(data_dir, {})
    write_json(data_dir, "import_history", [])
