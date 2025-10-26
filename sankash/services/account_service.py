"""Account service with pure functions."""

import polars as pl

from sankash.core.database import execute_command, execute_query
from sankash.core.models import Account


def get_accounts(db_path: str, include_inactive: bool = False) -> pl.DataFrame:
    """Get all accounts (pure function)."""
    query = "SELECT * FROM accounts"

    if not include_inactive:
        query += " WHERE is_active = TRUE"

    query += " ORDER BY name"

    return execute_query(db_path, query)


def get_account_by_id(db_path: str, account_id: int) -> pl.DataFrame:
    """Get account by ID (pure function)."""
    return execute_query(
        db_path,
        "SELECT * FROM accounts WHERE id = $id",
        {"id": account_id}
    )


def calculate_account_balance(db_path: str, account_id: int) -> float:
    """Calculate account balance from transactions (pure function)."""
    df = execute_query(
        db_path,
        "SELECT COALESCE(SUM(amount), 0) as balance FROM transactions WHERE account_id = $id",
        {"id": account_id}
    )
    return float(df["balance"][0])


def get_accounts_with_balances(db_path: str) -> pl.DataFrame:
    """Get accounts with their calculated balances (pure function)."""
    query = """
    SELECT
        a.*,
        COALESCE(SUM(t.amount), 0) as balance,
        COUNT(t.id) as transaction_count
    FROM accounts a
    LEFT JOIN transactions t ON a.id = t.account_id
    GROUP BY a.id, a.name, a.bank, a.account_number, a.currency, a.is_active, a.created_at
    ORDER BY a.name
    """
    return execute_query(db_path, query)


def create_account(db_path: str, account: Account) -> int:
    """Create new account and return its ID."""
    result = execute_query(
        db_path,
        """INSERT INTO accounts (name, bank, account_number, currency, is_active)
        VALUES ($name, $bank, $account_number, $currency, $is_active)
        RETURNING id""",
        {
            "name": account.name,
            "bank": account.bank,
            "account_number": account.account_number,
            "currency": account.currency,
            "is_active": account.is_active,
        }
    )
    return int(result["id"][0])


def update_account(db_path: str, account_id: int, account: Account) -> None:
    """Update existing account."""
    execute_command(
        db_path,
        """UPDATE accounts
        SET name = $name,
            bank = $bank,
            account_number = $account_number,
            currency = $currency,
            is_active = $is_active
        WHERE id = $id""",
        {
            "id": account_id,
            "name": account.name,
            "bank": account.bank,
            "account_number": account.account_number,
            "currency": account.currency,
            "is_active": account.is_active,
        }
    )


def deactivate_account(db_path: str, account_id: int) -> None:
    """Deactivate account (soft delete)."""
    execute_command(
        db_path,
        "UPDATE accounts SET is_active = FALSE WHERE id = $id",
        {"id": account_id}
    )
