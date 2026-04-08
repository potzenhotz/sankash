"""Account service with pure functions."""

from datetime import datetime

import polars as pl

from sankash.core.models import Account
from sankash.core.storage import (
    merge_overrides,
    next_id,
    read_overrides,
    read_parquet,
    read_yaml,
    write_yaml,
)


def _accounts_path() -> str:
    return "accounts"


def get_accounts(data_dir: str, include_inactive: bool = False) -> pl.DataFrame:
    """Get all accounts."""
    records = read_yaml(data_dir, "accounts")
    if not records:
        return pl.DataFrame()
    df = pl.DataFrame(records)
    if not include_inactive and "is_active" in df.columns:
        df = df.filter(pl.col("is_active") == True)  # noqa: E712
    if "name" in df.columns:
        df = df.sort("name")
    return df


def get_account_by_id(data_dir: str, account_id: int) -> pl.DataFrame:
    """Get account by ID."""
    records = read_yaml(data_dir, "accounts")
    if not records:
        return pl.DataFrame()
    df = pl.DataFrame(records)
    return df.filter(pl.col("id") == account_id)


def calculate_account_balance(data_dir: str, account_id: int) -> float:
    """Calculate account balance from transactions."""
    txns = read_parquet(data_dir, "transactions")
    if txns.is_empty():
        return 0.0
    overrides = read_overrides(data_dir)
    txns = merge_overrides(txns, overrides)
    filtered = txns.filter(pl.col("account_id") == account_id)
    if filtered.is_empty():
        return 0.0
    return float(filtered["amount"].sum())


def get_accounts_with_balances(data_dir: str) -> pl.DataFrame:
    """Get accounts with their calculated balances."""
    accounts = read_yaml(data_dir, "accounts")
    if not accounts:
        return pl.DataFrame()

    accounts_df = pl.DataFrame(accounts)
    txns = read_parquet(data_dir, "transactions")

    if txns.is_empty():
        return accounts_df.with_columns(
            pl.lit(0.0).alias("balance"),
            pl.lit(0).cast(pl.Int64).alias("transaction_count"),
        ).sort("name")

    overrides = read_overrides(data_dir)
    txns = merge_overrides(txns, overrides)

    balances = txns.group_by("account_id").agg(
        pl.col("amount").sum().alias("balance"),
        pl.col("id").count().alias("transaction_count"),
    )

    result = accounts_df.join(
        balances, left_on="id", right_on="account_id", how="left"
    ).with_columns(
        pl.col("balance").fill_null(0.0),
        pl.col("transaction_count").fill_null(0).cast(pl.Int64),
    )

    return result.sort("name")


def create_account(data_dir: str, account: Account) -> int:
    """Create new account and return its ID."""
    records = read_yaml(data_dir, "accounts")
    new_id = next_id(records)
    record = {
        "id": new_id,
        "name": account.name,
        "bank": account.bank,
        "currency": account.currency,
        "is_active": account.is_active,
        "created_at": datetime.now().isoformat(),
    }
    records.append(record)
    write_yaml(data_dir, "accounts", records)
    return new_id


def update_account(data_dir: str, account_id: int, account: Account) -> None:
    """Update existing account."""
    records = read_yaml(data_dir, "accounts")
    for rec in records:
        if rec["id"] == account_id:
            rec["name"] = account.name
            rec["bank"] = account.bank
            rec["currency"] = account.currency
            rec["is_active"] = account.is_active
            break
    write_yaml(data_dir, "accounts", records)


def deactivate_account(data_dir: str, account_id: int) -> None:
    """Deactivate account (soft delete)."""
    records = read_yaml(data_dir, "accounts")
    for rec in records:
        if rec["id"] == account_id:
            rec["is_active"] = False
            break
    write_yaml(data_dir, "accounts", records)
