"""Database connection and operations using functional approach."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import duckdb
import polars as pl


@contextmanager
def get_connection(db_path: str) -> Iterator[duckdb.DuckDBPyConnection]:
    """Context manager for database connection (functional pattern)."""
    con = duckdb.connect(db_path)
    try:
        yield con
    finally:
        con.close()


def execute_query(
    db_path: str,
    query: str,
    params: dict[str, Any] | None = None,
) -> pl.DataFrame:
    """
    Execute a query and return Polars DataFrame (pure function).

    Args:
        db_path: Path to DuckDB database
        query: SQL query string
        params: Optional parameters for parameterized queries

    Returns:
        Polars DataFrame with results
    """
    with get_connection(db_path) as con:
        if params:
            result = con.execute(query, params).pl()
        else:
            result = con.execute(query).pl()
        return result


def execute_command(
    db_path: str,
    command: str,
    params: dict[str, Any] | None = None,
) -> None:
    """
    Execute a command that doesn't return data (INSERT, UPDATE, DELETE).

    Args:
        db_path: Path to DuckDB database
        command: SQL command string
        params: Optional parameters for parameterized queries
    """
    with get_connection(db_path) as con:
        if params:
            con.execute(command, params)
        else:
            con.execute(command)


def init_database(db_path: str) -> None:
    """Initialize database with schema."""
    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, "r") as f:
        schema = f.read()

    with get_connection(db_path) as con:
        con.execute(schema)
