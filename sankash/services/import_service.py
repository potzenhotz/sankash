"""Import service for CSV processing using functional approach."""

import hashlib
import os
from datetime import date
from pathlib import Path
from typing import Callable, Optional

import polars as pl

from sankash.converters.bank_converters import BankFormat, get_converter
from sankash.core.models import ImportHistory, Transaction
from sankash.services.transaction_service import create_transaction, get_transactions
from sankash.services.import_history_service import (
    calculate_file_hash,
    check_duplicate_file,
    create_import_history,
)
from sankash.utils.duplicate_detection import find_duplicates


def parse_csv_to_dataframe(
    file_path: str | Path,
    date_column: str = "date",
    payee_column: str = "payee",
    amount_column: str = "amount",
    notes_column: str = "notes",
) -> pl.DataFrame:
    """
    Parse CSV file to Polars DataFrame (pure function).

    Assumes standardized format with date, payee, notes, amount columns.
    """
    # Read CSV with truncate_ragged_lines to handle extra columns
    df = pl.read_csv(file_path, truncate_ragged_lines=True)

    # Check if columns exist
    required_columns = {date_column, payee_column, amount_column}
    if not required_columns.issubset(set(df.columns)):
        raise ValueError(
            f"CSV must contain columns: {required_columns}. "
            f"Found columns: {df.columns}"
        )

    # Rename columns to standard names
    column_mapping = {
        date_column: "date",
        payee_column: "payee",
        amount_column: "amount",
    }

    # Add notes if it exists
    if notes_column in df.columns:
        column_mapping[notes_column] = "notes"

    df = df.rename(column_mapping)

    # Add notes column if it doesn't exist
    if "notes" not in df.columns:
        df = df.with_columns(pl.lit(None).alias("notes"))

    # Ensure correct types
    df = df.with_columns([
        pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"),
        pl.col("amount").cast(pl.Float64),
        pl.col("payee").cast(pl.Utf8),
        pl.col("notes").cast(pl.Utf8),
    ])

    return df


def create_imported_id(
    transaction_date: date, amount: float, payee: str, notes: str = "", occurrence: int = 0
) -> str:
    """
    Create unique imported_id from transaction data (pure function).

    Includes occurrence index to distinguish identical transactions within a file
    while still matching across overlapping CSV exports.
    """
    data = f"{transaction_date}_{amount}_{payee}_{notes}_{occurrence}"
    hash_suffix = hashlib.md5(data.encode()).hexdigest()[:8]

    return f"{transaction_date}_{amount}_{hash_suffix}"


def add_imported_ids(df: pl.DataFrame) -> pl.DataFrame:
    """
    Add imported_id column to DataFrame (pure function).

    Uses an occurrence counter within groups of identical (date, amount, payee, notes)
    so that:
    - Identical rows within the same file get unique IDs (occurrence 0, 1, 2...)
    - The same rows in a different overlapping CSV get the same IDs (same occurrences)
    """
    # Add occurrence counter within each group of identical transactions
    df = df.with_columns(
        pl.cum_count("date").over("date", "amount", "payee", "notes").alias("_occurrence") - 1
    )

    df = df.with_columns(
        pl.struct(["date", "amount", "payee", "notes", "_occurrence"])
        .map_elements(
            lambda row: create_imported_id(
                row["date"],
                row["amount"],
                row["payee"],
                row["notes"] or "",
                row["_occurrence"],
            ),
            return_dtype=pl.Utf8,
        )
        .alias("imported_id")
    )

    df = df.drop("_occurrence")

    return df


def transform_import_dataframe(df: pl.DataFrame, account_id: int) -> pl.DataFrame:
    """
    Transform import DataFrame to transaction format (pure function).

    Adds account_id and imported_id.
    """
    # Add imported_id
    df = add_imported_ids(df)

    # Add account_id
    df = df.with_columns(pl.lit(account_id).alias("account_id"))

    return df


def filter_duplicate_transactions(
    import_df: pl.DataFrame,
    existing_df: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Filter duplicates from import DataFrame (pure function).

    Returns:
        Tuple of (new_transactions, duplicates)
    """
    duplicates = find_duplicates(import_df, existing_df)

    # Filter out duplicates from import
    new_transactions = import_df.filter(~pl.col("imported_id").is_in(duplicates))
    duplicate_transactions = import_df.filter(pl.col("imported_id").is_in(duplicates))

    return new_transactions, duplicate_transactions


def import_transactions(
    db_path: str,
    file_path: str | Path,
    account_id: int,
    bank_format: BankFormat = BankFormat.STANDARD,
    original_filename: str = "",
) -> dict[str, int]:
    """
    Import transactions from CSV file.

    Args:
        db_path: Database path
        file_path: Path to CSV file
        account_id: Account to import into
        bank_format: Bank format for conversion (default: STANDARD)
        original_filename: Original filename before temp storage

    Returns:
        Dictionary with import statistics including import_session_id
    """
    # Calculate file hash for duplicate detection
    file_hash = calculate_file_hash(file_path)
    filename = original_filename or os.path.basename(file_path)

    # Get converter for bank format
    converter = get_converter(bank_format)

    # Parse CSV (use converter if bank-specific format)
    if converter:
        import_df = converter(file_path)
    else:
        import_df = parse_csv_to_dataframe(file_path)

    # Transform to transaction format
    import_df = transform_import_dataframe(import_df, account_id)

    # Get existing transactions for duplicate detection
    existing_df, _ = get_transactions(db_path, account_id=account_id, limit=100_000, offset=0)

    # Filter duplicates
    new_transactions, duplicates = filter_duplicate_transactions(import_df, existing_df)

    # Create import history record
    import_history = ImportHistory(
        filename=filename,
        account_id=account_id,
        bank_format=bank_format.value,
        total_count=len(import_df),
        imported_count=len(new_transactions),
        duplicate_count=len(duplicates),
        categorized_count=0,  # Will be updated after applying rules
        file_hash=file_hash,
    )

    import_session_id = create_import_history(db_path, import_history)

    # Bulk insert all new transactions using a single connection
    import duckdb

    insert_df = new_transactions.select([
        pl.col("account_id"),
        pl.col("date"),
        pl.col("payee"),
        pl.col("notes").fill_null(""),
        pl.col("amount"),
        pl.col("imported_id"),
        pl.lit(import_session_id).alias("import_session_id"),
    ])

    con = duckdb.connect(db_path)
    con.execute(
        """INSERT INTO transactions
        (account_id, date, payee, notes, amount, imported_id, import_session_id)
        SELECT * FROM insert_df""",
    )
    imported_count = len(insert_df)
    con.close()

    # Apply rules to newly imported transactions
    from sankash.services.rule_service import apply_rules_to_uncategorized
    categorized_count = apply_rules_to_uncategorized(db_path)

    # Update import history with categorized count
    con = duckdb.connect(db_path)
    con.execute(
        "UPDATE import_history SET categorized_count = ? WHERE id = ?",
        [categorized_count, import_session_id],
    )
    con.close()

    return {
        "total": len(import_df),
        "imported": imported_count,
        "duplicates": len(duplicates),
        "categorized": categorized_count,
        "import_session_id": import_session_id,
        "filename": filename,
        "file_hash": file_hash,
    }


def preview_import(
    file_path: str | Path,
    account_id: int,
    bank_format: BankFormat = BankFormat.STANDARD,
    limit: int = 10,
) -> pl.DataFrame:
    """
    Preview CSV import without actually importing (pure function).

    Returns DataFrame with first N rows after transformation.
    """
    try:
        # Get converter for bank format
        converter = get_converter(bank_format)

        # Parse CSV with detailed error handling
        if converter:
            try:
                import_df = converter(file_path)
            except Exception as e:
                # Read first few lines for diagnostics
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        first_lines = [f.readline() for _ in range(3)]
                    raise ValueError(
                        f"Failed to parse CSV with bank format '{bank_format.value}'. "
                        f"Error: {str(e)}. "
                        f"First lines of file:\n{''.join(first_lines)}"
                    )
                except Exception:
                    raise ValueError(
                        f"Failed to parse CSV with bank format '{bank_format.value}'. "
                        f"Error: {str(e)}"
                    )
        else:
            try:
                import_df = parse_csv_to_dataframe(file_path)
            except Exception as e:
                # Read first few lines for diagnostics
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        first_lines = [f.readline() for _ in range(3)]
                    raise ValueError(
                        f"Failed to parse standard CSV. "
                        f"Error: {str(e)}. "
                        f"Expected columns: date, payee, amount, notes. "
                        f"First lines of file:\n{''.join(first_lines)}"
                    )
                except Exception:
                    raise ValueError(
                        f"Failed to parse standard CSV. "
                        f"Error: {str(e)}"
                    )

        # Transform
        import_df = transform_import_dataframe(import_df, account_id)

        # Return preview
        return import_df.head(limit)
    except Exception as e:
        # Re-raise with additional context
        raise Exception(f"Preview failed for file {file_path}: {str(e)}")
