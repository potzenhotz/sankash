"""Transaction service with pure functions for business logic."""

from datetime import date
from typing import Optional

import polars as pl

from sankash.core.database import execute_command, execute_query
from sankash.core.models import Transaction


def get_transactions(
    db_path: str,
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
    """
    Get transactions with optional filters, search, sort, and pagination.

    Returns tuple of (Polars DataFrame, total_count) for paginated results.
    Includes import source information from import_history table.
    """
    where_clause = " WHERE 1=1"
    params: dict = {}

    if account_id is not None:
        where_clause += " AND t.account_id = $account_id"
        params["account_id"] = account_id

    if start_date:
        where_clause += " AND t.date >= $start_date"
        params["start_date"] = start_date

    if end_date:
        where_clause += " AND t.date <= $end_date"
        params["end_date"] = end_date

    if category:
        where_clause += " AND t.category = $category"
        params["category"] = category

    if min_amount is not None:
        where_clause += " AND t.amount >= $min_amount"
        params["min_amount"] = min_amount

    if max_amount is not None:
        where_clause += " AND t.amount <= $max_amount"
        params["max_amount"] = max_amount

    if is_categorized is not None:
        where_clause += " AND t.is_categorized = $is_categorized"
        params["is_categorized"] = is_categorized

    if search_query:
        where_clause += (
            " AND (t.payee ILIKE $search OR t.notes ILIKE $search"
            " OR t.category ILIKE $search)"
        )
        params["search"] = f"%{search_query}%"

    # Build ORDER BY
    sort_col = "t.amount" if sort_by == "amount" else "t.date"
    sort_dir = "ASC" if sort_order == "asc" else "DESC"
    order_clause = f" ORDER BY {sort_col} {sort_dir}, t.id DESC"

    # Count query (same filters, no pagination)
    count_query = (
        "SELECT COUNT(*) as count FROM transactions t"
        f" LEFT JOIN import_history ih ON t.import_session_id = ih.id"
        f"{where_clause}"
    )
    count_df = execute_query(db_path, count_query, params if params else None)
    total_count = int(count_df["count"][0])

    # Data query with pagination
    data_query = (
        "SELECT t.*, ih.filename as import_filename,"
        " ih.import_date as import_date"
        " FROM transactions t"
        " LEFT JOIN import_history ih ON t.import_session_id = ih.id"
        f"{where_clause}{order_clause}"
        f" LIMIT {limit} OFFSET {offset}"
    )
    df = execute_query(db_path, data_query, params if params else None)

    return df, total_count


def get_uncategorized_count(db_path: str) -> int:
    """Get count of uncategorized transactions (pure function)."""
    df = execute_query(
        db_path,
        "SELECT COUNT(*) as count FROM transactions WHERE is_categorized = FALSE"
    )
    return int(df["count"][0])


def update_transaction_category(db_path: str, transaction_id: int, category: str) -> None:
    """Update transaction category (side effect isolated)."""
    execute_command(
        db_path,
        "UPDATE transactions SET category = $category, is_categorized = TRUE WHERE id = $id",
        {"id": transaction_id, "category": category}
    )


def bulk_update_categories(db_path: str, transaction_ids: list[int], category: str) -> None:
    """Bulk update transaction categories (side effect isolated)."""
    execute_command(
        db_path,
        "UPDATE transactions SET category = $category, is_categorized = TRUE WHERE id = ANY($ids)",
        {"ids": transaction_ids, "category": category}
    )


def mark_as_transfer(
    db_path: str,
    transaction_id: int,
    transfer_account_id: int,
) -> None:
    """Mark transaction as transfer (side effect isolated)."""
    execute_command(
        db_path,
        """UPDATE transactions
        SET is_transfer = TRUE,
            transfer_account_id = $transfer_account_id
        WHERE id = $id""",
        {"id": transaction_id, "transfer_account_id": transfer_account_id}
    )


def create_transaction(db_path: str, transaction: Transaction) -> int:
    """Create new transaction and return its ID."""
    result = execute_query(
        db_path,
        """INSERT INTO transactions
        (account_id, date, payee, notes, amount, category, is_categorized, is_transfer, transfer_account_id, imported_id, import_session_id)
        VALUES ($account_id, $date, $payee, $notes, $amount, $category, $is_categorized, $is_transfer, $transfer_account_id, $imported_id, $import_session_id)
        RETURNING id""",
        {
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
        }
    )
    return int(result["id"][0])


def update_transaction(
    db_path: str,
    transaction_id: int,
    transaction: Transaction,
) -> None:
    """Update existing transaction (side effect isolated)."""
    execute_command(
        db_path,
        """UPDATE transactions
        SET account_id = $account_id,
            date = $date,
            payee = $payee,
            notes = $notes,
            amount = $amount,
            category = $category,
            is_categorized = $is_categorized,
            is_transfer = $is_transfer,
            transfer_account_id = $transfer_account_id
        WHERE id = $id""",
        {
            "id": transaction_id,
            "account_id": transaction.account_id,
            "date": transaction.date,
            "payee": transaction.payee,
            "notes": transaction.notes,
            "amount": transaction.amount,
            "category": transaction.category,
            "is_categorized": transaction.is_categorized,
            "is_transfer": transaction.is_transfer,
            "transfer_account_id": transaction.transfer_account_id,
        }
    )


def delete_transaction(db_path: str, transaction_id: int) -> None:
    """Delete transaction (side effect isolated)."""
    execute_command(
        db_path,
        "DELETE FROM transactions WHERE id = $id",
        {"id": transaction_id}
    )


def delete_all_transactions(db_path: str) -> None:
    """Delete all transactions and their import history."""
    execute_command(db_path, "DELETE FROM transactions")
    execute_command(db_path, "DELETE FROM import_history")
