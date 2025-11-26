"""Diagnostic script to analyze CSV import and show what would be filtered out."""

import sys
from pathlib import Path

import polars as pl

from sankash.converters.bank_converters import BankFormat, convert_deutsche_bank_csv


def diagnose_csv(csv_path: str, bank_format: str = "deutsche-bank"):
    """
    Diagnose CSV file to see what rows would be imported vs filtered out.

    Args:
        csv_path: Path to CSV file
        bank_format: Bank format (deutsche-bank, ing, or standard)
    """
    print(f"Diagnosing CSV file: {csv_path}")
    print(f"Bank format: {bank_format}\n")

    # Read raw CSV
    if bank_format == "deutsche-bank":
        print("Step 1: Reading raw CSV (skipping 7 metadata rows)...")
        df_raw = pl.read_csv(
            csv_path,
            separator=";",
            skip_rows=7,
            encoding="utf-8",
            truncate_ragged_lines=True,
        )
        print(f"  Total rows after skipping metadata: {len(df_raw)}")
        print(f"  Columns: {df_raw.columns}\n")

        # Check date format
        print("Step 2: Checking date format (DD.MM.YYYY)...")
        if "Buchungstag" in df_raw.columns:
            valid_dates = df_raw.filter(
                pl.col("Buchungstag").str.contains(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
            )
            invalid_dates = df_raw.filter(
                ~pl.col("Buchungstag").str.contains(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
            )
            print(f"  Valid date format: {len(valid_dates)} rows")
            print(f"  Invalid date format: {len(invalid_dates)} rows")

            if len(invalid_dates) > 0:
                print("\n  Sample of invalid date rows:")
                print(invalid_dates.select(["Buchungstag"]).head(5))

        # Check for nulls
        print("\nStep 3: Checking for null values...")
        if "Buchungstag" in df_raw.columns and "Betrag" in df_raw.columns:
            non_null = df_raw.filter(
                pl.col("Buchungstag").is_not_null() & pl.col("Betrag").is_not_null()
            )
            has_nulls = df_raw.filter(
                pl.col("Buchungstag").is_null() | pl.col("Betrag").is_null()
            )
            print(f"  Non-null rows: {len(non_null)}")
            print(f"  Rows with null date/amount: {len(has_nulls)}")

        # Run converter
        print("\nStep 4: Running full converter...")
        df_converted = convert_deutsche_bank_csv(csv_path)
        print(f"  Final imported rows: {len(df_converted)}")
        print(f"\n  Date range: {df_converted['date'].min()} to {df_converted['date'].max()}")
        print(f"\n  First 5 rows:")
        print(df_converted.head(5))

        # Summary
        print("\n" + "="*60)
        print("SUMMARY:")
        print(f"  Raw CSV rows (after skipping metadata): {len(df_raw)}")
        print(f"  Rows after all filters: {len(df_converted)}")
        print(f"  Rows filtered out: {len(df_raw) - len(df_converted)}")
        print("="*60)

    else:
        print(f"Bank format '{bank_format}' not supported in this diagnostic script yet.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/diagnose_csv_import.py <csv_file_path> [bank_format]")
        print("Example: python scripts/diagnose_csv_import.py data/transactions.csv deutsche-bank")
        sys.exit(1)

    csv_path = sys.argv[1]
    bank_format = sys.argv[2] if len(sys.argv) > 2 else "deutsche-bank"

    diagnose_csv(csv_path, bank_format)
