"""Bank-specific CSV converters for transforming raw bank exports to standard format.

All converters are pure functions that take a file path and return a Polars DataFrame
with standardized columns: date, payee, notes, amount.
"""

from enum import Enum
from pathlib import Path
from typing import Callable

import polars as pl


class BankFormat(str, Enum):
    """Supported bank CSV formats."""

    STANDARD = "standard"
    DEUTSCHE_BANK = "deutsche-bank"
    ING = "ing"


def convert_deutsche_bank_csv(file_path: str | Path) -> pl.DataFrame:
    """
    Convert Deutsche Bank CSV export to standard format (pure function).

    Deutsche Bank format characteristics:
    - Semicolon separator
    - Decimal comma (German format)
    - Date format: DD.MM.YYYY
    - 7 metadata rows at top (must skip)
    - Columns: Buchungstag, Begünstigter / Auftraggeber, Verwendungszweck, Betrag

    Args:
        file_path: Path to Deutsche Bank CSV file

    Returns:
        DataFrame with columns: date, payee, notes, amount
    """
    # Read CSV with Deutsche Bank settings, skipping 7 metadata rows
    df = pl.read_csv(
        file_path,
        separator=";",
        skip_rows=7,
        encoding="utf-8",
        truncate_ragged_lines=True,
    )

    # Select and rename columns to standard format
    df_standard = df.select([
        pl.col("Buchungstag").alias("date"),
        pl.col("Begünstigter / Auftraggeber").alias("payee"),
        pl.col("Verwendungszweck").alias("notes"),
        pl.col("Betrag").alias("amount"),
    ])

    # Filter valid date rows (DD.MM.YYYY format)
    df_standard = df_standard.filter(
        pl.col("date").str.contains(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
    )

    # Remove null rows
    df_standard = df_standard.filter(
        pl.col("date").is_not_null() & pl.col("amount").is_not_null()
    )

    # Convert date to ISO format (YYYY-MM-DD)
    df_standard = df_standard.with_columns([
        pl.col("date")
        .str.strptime(pl.Date, "%d.%m.%Y")
        .dt.strftime("%Y-%m-%d")
    ])

    # Convert German number format to float
    # German format: 1.234,56 (dot as thousands, comma as decimal)
    # Target format: 1234.56
    df_standard = df_standard.with_columns([
        pl.col("amount")
        .cast(pl.Utf8)  # Ensure it's string first
        .str.replace_all(r"\.", "")  # Remove thousands separator (dots)
        .str.replace(",", ".")  # Replace decimal comma with dot
        .cast(pl.Float64)
    ])

    # Handle empty payees
    df_standard = df_standard.with_columns([
        pl.when(pl.col("payee").is_null() | (pl.col("payee") == ""))
        .then(pl.lit("Unknown"))
        .otherwise(pl.col("payee"))
        .alias("payee")
    ])

    # Handle null notes
    df_standard = df_standard.with_columns([
        pl.col("notes").fill_null("")
    ])

    # Sort by date (oldest first)
    df_standard = df_standard.sort("date")

    return df_standard


def convert_ing_csv(file_path: str | Path) -> pl.DataFrame:
    """
    Convert ING CSV export to standard format (pure function).

    ING format characteristics:
    - Semicolon separator
    - 13 metadata rows at top (must skip)
    - ISO-8859-1 (Latin-1) encoding
    - Date format: DD.MM.YYYY
    - German number format with thousands separator (1.234,56)
    - Columns: Buchung, Auftraggeber/Empfänger, Buchungstext, Verwendungszweck, Betrag

    Args:
        file_path: Path to ING CSV file

    Returns:
        DataFrame with columns: date, payee, notes, amount
    """
    # Read CSV with ING settings
    df = pl.read_csv(
        file_path,
        separator=";",
        skip_rows=13,
        encoding="iso-8859-1",
        truncate_ragged_lines=True,
    )

    # Select and rename columns, combine text fields for notes
    df_standard = df.select([
        pl.col("Buchung").alias("date"),
        pl.col("Auftraggeber/Empfänger").alias("payee"),
        (pl.col("Buchungstext") + " - " + pl.col("Verwendungszweck")).alias("notes"),
        pl.col("Betrag").alias("amount"),
    ])

    # Filter valid date rows (DD.MM.YYYY format)
    df_standard = df_standard.filter(
        pl.col("date").str.contains(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
    )

    # Remove null rows
    df_standard = df_standard.filter(
        pl.col("date").is_not_null() & pl.col("amount").is_not_null()
    )

    # Convert date to ISO format (YYYY-MM-DD)
    df_standard = df_standard.with_columns([
        pl.col("date")
        .str.strptime(pl.Date, "%d.%m.%Y")
        .dt.strftime("%Y-%m-%d")
    ])

    # Convert German number format to float
    # Remove thousands separator (dots), replace decimal comma with dot
    df_standard = df_standard.with_columns([
        pl.col("amount")
        .str.replace_all(r"\.", "")  # Remove thousands separator
        .str.replace(",", ".")  # Replace decimal comma
        .cast(pl.Float64)
    ])

    # Handle empty payees
    df_standard = df_standard.with_columns([
        pl.when(pl.col("payee").is_null() | (pl.col("payee") == ""))
        .then(pl.lit("Unknown"))
        .otherwise(pl.col("payee"))
        .alias("payee")
    ])

    # Handle null notes
    df_standard = df_standard.with_columns([
        pl.col("notes").fill_null("")
    ])

    # Sort by date (oldest first)
    df_standard = df_standard.sort("date")

    return df_standard


def get_converter(bank_format: BankFormat) -> Callable[[str | Path], pl.DataFrame] | None:
    """
    Get converter function for specific bank format (pure function).

    Args:
        bank_format: Bank format enum value

    Returns:
        Converter function or None for standard format
    """
    converters = {
        BankFormat.DEUTSCHE_BANK: convert_deutsche_bank_csv,
        BankFormat.ING: convert_ing_csv,
        BankFormat.STANDARD: None,  # No conversion needed
    }

    return converters.get(bank_format)
