"""Import history service for tracking CSV imports."""

import hashlib
from pathlib import Path
from typing import Optional

import duckdb
import polars as pl

from sankash.core.models import ImportHistory


def calculate_file_hash(file_path: str | Path) -> str:
    """
    Calculate SHA256 hash of a file (pure function).

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_import_history(
    db_path: str,
    import_history: ImportHistory,
) -> int:
    """
    Create a new import history record.

    Args:
        db_path: Database path
        import_history: ImportHistory object

    Returns:
        ID of the created import history record
    """
    con = duckdb.connect(db_path)

    result = con.execute(
        """
        INSERT INTO import_history (
            filename, account_id, bank_format, total_count,
            imported_count, duplicate_count, categorized_count, file_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [
            import_history.filename,
            import_history.account_id,
            import_history.bank_format,
            import_history.total_count,
            import_history.imported_count,
            import_history.duplicate_count,
            import_history.categorized_count,
            import_history.file_hash,
        ],
    ).fetchone()

    con.close()

    return result[0] if result else 0


def get_import_history(
    db_path: str,
    account_id: Optional[int] = None,
    limit: int = 50,
) -> pl.DataFrame:
    """
    Get import history records.

    Args:
        db_path: Database path
        account_id: Optional account ID to filter by
        limit: Maximum number of records to return

    Returns:
        Polars DataFrame with import history records
    """
    con = duckdb.connect(db_path)

    if account_id:
        query = """
        SELECT
            ih.*,
            a.name as account_name,
            a.bank as account_bank
        FROM import_history ih
        JOIN accounts a ON ih.account_id = a.id
        WHERE ih.account_id = ?
        ORDER BY ih.import_date DESC
        LIMIT ?
        """
        df = con.execute(query, [account_id, limit]).pl()
    else:
        query = """
        SELECT
            ih.*,
            a.name as account_name,
            a.bank as account_bank
        FROM import_history ih
        JOIN accounts a ON ih.account_id = a.id
        ORDER BY ih.import_date DESC
        LIMIT ?
        """
        df = con.execute(query, [limit]).pl()

    con.close()

    return df


def get_import_by_id(db_path: str, import_id: int) -> Optional[pl.DataFrame]:
    """
    Get a specific import history record by ID.

    Args:
        db_path: Database path
        import_id: Import history ID

    Returns:
        Polars DataFrame with single record or None
    """
    con = duckdb.connect(db_path)

    query = """
    SELECT
        ih.*,
        a.name as account_name,
        a.bank as account_bank
    FROM import_history ih
    JOIN accounts a ON ih.account_id = a.id
    WHERE ih.id = ?
    """

    df = con.execute(query, [import_id]).pl()
    con.close()

    return df if len(df) > 0 else None


def check_duplicate_file(db_path: str, file_hash: str) -> Optional[pl.DataFrame]:
    """
    Check if a file with the same hash has been imported before.

    Args:
        db_path: Database path
        file_hash: File hash to check

    Returns:
        Polars DataFrame with matching import record(s) or None
    """
    con = duckdb.connect(db_path)

    query = """
    SELECT
        ih.*,
        a.name as account_name,
        a.bank as account_bank
    FROM import_history ih
    JOIN accounts a ON ih.account_id = a.id
    WHERE ih.file_hash = ?
    ORDER BY ih.import_date DESC
    """

    df = con.execute(query, [file_hash]).pl()
    con.close()

    return df if len(df) > 0 else None


def delete_import_history(db_path: str, import_id: int) -> bool:
    """
    Delete an import history record.

    Note: This does NOT delete the associated transactions.
    It only removes the import history metadata.

    Args:
        db_path: Database path
        import_id: Import history ID to delete

    Returns:
        True if deleted successfully
    """
    con = duckdb.connect(db_path)

    # First, set import_session_id to NULL for associated transactions
    con.execute(
        "UPDATE transactions SET import_session_id = NULL WHERE import_session_id = ?",
        [import_id],
    )

    # Then delete the import history record
    con.execute("DELETE FROM import_history WHERE id = ?", [import_id])

    con.close()

    return True


def get_transactions_by_import(db_path: str, import_id: int) -> pl.DataFrame:
    """
    Get all transactions from a specific import session.

    Args:
        db_path: Database path
        import_id: Import history ID

    Returns:
        Polars DataFrame with transactions
    """
    con = duckdb.connect(db_path)

    query = """
    SELECT
        t.*,
        a.name as account_name,
        ih.filename as import_filename
    FROM transactions t
    JOIN accounts a ON t.account_id = a.id
    LEFT JOIN import_history ih ON t.import_session_id = ih.id
    WHERE t.import_session_id = ?
    ORDER BY t.date DESC
    """

    df = con.execute(query, [import_id]).pl()
    con.close()

    return df
