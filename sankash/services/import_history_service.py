"""Import history service for tracking CSV imports."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import polars as pl

from sankash.core.models import ImportHistory
from sankash.core.storage import (
    merge_overrides,
    next_id,
    read_json,
    read_overrides,
    read_parquet,
    read_yaml,
    write_json,
    write_parquet,
)


def calculate_file_hash(file_path: str | Path) -> str:
    """Calculate SHA256 hash of a file (pure function)."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_import_history(data_dir: str, import_history: ImportHistory) -> int:
    """Create a new import history record. Returns the new record ID."""
    records = read_json(data_dir, "import_history")
    if not isinstance(records, list):
        records = []

    new_id = next_id(records)
    record = {
        "id": new_id,
        "filename": import_history.filename,
        "account_id": import_history.account_id,
        "bank_format": import_history.bank_format,
        "import_date": datetime.now().isoformat(),
        "total_count": import_history.total_count,
        "imported_count": import_history.imported_count,
        "duplicate_count": import_history.duplicate_count,
        "categorized_count": import_history.categorized_count,
        "file_hash": import_history.file_hash,
    }
    records.append(record)
    write_json(data_dir, "import_history", records)
    return new_id


def _join_account_info(df: pl.DataFrame, data_dir: str) -> pl.DataFrame:
    """Join account name/bank onto a DataFrame that has account_id."""
    accounts = read_yaml(data_dir, "accounts")
    if not accounts:
        return df.with_columns(
            pl.lit(None).alias("account_name"),
            pl.lit(None).alias("account_bank"),
        )
    accounts_df = pl.DataFrame(accounts).select(
        pl.col("id").alias("acc_id"),
        pl.col("name").alias("account_name"),
        pl.col("bank").alias("account_bank"),
    )
    return df.join(accounts_df, left_on="account_id", right_on="acc_id", how="left")


def get_import_history(
    data_dir: str,
    account_id: Optional[int] = None,
    limit: int = 50,
) -> pl.DataFrame:
    """Get import history records with account info and remaining transaction count."""
    records = read_json(data_dir, "import_history")
    if not isinstance(records, list) or not records:
        return pl.DataFrame()

    df = pl.DataFrame(records)

    if account_id is not None and "account_id" in df.columns:
        df = df.filter(pl.col("account_id") == account_id)

    # Join account info
    df = _join_account_info(df, data_dir)

    # Add remaining_count (transactions still linked to this import)
    txns = read_parquet(data_dir, "transactions")
    if not txns.is_empty() and "import_session_id" in txns.columns:
        remaining = txns.group_by("import_session_id").agg(
            pl.col("id").count().alias("remaining_count")
        )
        df = df.join(
            remaining, left_on="id", right_on="import_session_id", how="left"
        ).with_columns(pl.col("remaining_count").fill_null(0))
    else:
        df = df.with_columns(pl.lit(0).alias("remaining_count"))

    # Sort and limit
    if "import_date" in df.columns:
        df = df.sort("import_date", descending=True)
    df = df.head(limit)

    return df


def get_import_by_id(data_dir: str, import_id: int) -> Optional[pl.DataFrame]:
    """Get a specific import history record by ID."""
    records = read_json(data_dir, "import_history")
    if not isinstance(records, list) or not records:
        return None

    df = pl.DataFrame(records)
    df = df.filter(pl.col("id") == import_id)
    if df.is_empty():
        return None

    return _join_account_info(df, data_dir)


def check_duplicate_file(data_dir: str, file_hash: str) -> Optional[pl.DataFrame]:
    """Check if a file with the same hash has been imported before."""
    records = read_json(data_dir, "import_history")
    if not isinstance(records, list) or not records:
        return None

    df = pl.DataFrame(records)
    if "file_hash" not in df.columns:
        return None

    df = df.filter(pl.col("file_hash") == file_hash)
    if df.is_empty():
        return None

    df = _join_account_info(df, data_dir)
    if "import_date" in df.columns:
        df = df.sort("import_date", descending=True)
    return df


def delete_import_history(data_dir: str, import_id: int) -> bool:
    """Delete an import history record. Does NOT delete associated transactions."""
    # Unlink transactions from this import
    txns = read_parquet(data_dir, "transactions")
    if not txns.is_empty() and "import_session_id" in txns.columns:
        txns = txns.with_columns(
            pl.when(pl.col("import_session_id") == import_id)
            .then(pl.lit(None))
            .otherwise(pl.col("import_session_id"))
            .alias("import_session_id")
        )
        write_parquet(data_dir, "transactions", txns)

    # Remove from history
    records = read_json(data_dir, "import_history")
    if isinstance(records, list):
        records = [r for r in records if r.get("id") != import_id]
        write_json(data_dir, "import_history", records)

    return True


def get_transactions_by_import(data_dir: str, import_id: int) -> pl.DataFrame:
    """Get all transactions from a specific import session."""
    txns = read_parquet(data_dir, "transactions")
    if txns.is_empty() or "import_session_id" not in txns.columns:
        return pl.DataFrame()

    overrides = read_overrides(data_dir)
    txns = merge_overrides(txns, overrides)

    df = txns.filter(pl.col("import_session_id") == import_id)

    # Join account info
    accounts = read_yaml(data_dir, "accounts")
    if accounts:
        accounts_df = pl.DataFrame(accounts).select(
            pl.col("id").alias("acc_id"),
            pl.col("name").alias("account_name"),
        )
        df = df.join(accounts_df, left_on="account_id", right_on="acc_id", how="left")

    # Join import filename
    records = read_json(data_dir, "import_history")
    if isinstance(records, list) and records:
        ih_df = pl.DataFrame(records).select(
            pl.col("id").alias("ih_id"),
            pl.col("filename").alias("import_filename"),
        )
        df = df.join(ih_df, left_on="import_session_id", right_on="ih_id", how="left")

    if "date" in df.columns:
        df = df.sort("date", descending=True)

    return df
