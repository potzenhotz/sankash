"""Script to reimport CSV by clearing existing transactions first."""

import sys
from pathlib import Path

from sankash.core.database import execute_command
from sankash.services.import_service import import_transactions
from sankash.converters.bank_converters import BankFormat


def reimport_csv(db_path: str, csv_path: str, account_id: int = 1, bank_format: str = "deutsche-bank"):
    """
    Reimport CSV by clearing existing transactions and importing fresh.

    Args:
        db_path: Path to database
        csv_path: Path to CSV file
        account_id: Account ID to import into
        bank_format: Bank format (deutsche-bank, ing, or standard)
    """
    print(f"Reimporting CSV: {csv_path}")
    print(f"Database: {db_path}")
    print(f"Account ID: {account_id}")
    print(f"Bank format: {bank_format}\n")

    # Confirm with user
    response = input("⚠️  This will DELETE all existing transactions. Continue? (yes/no): ")
    if response.lower() != "yes":
        print("Import cancelled.")
        return

    # Clear existing transactions
    print("\n1. Clearing existing transactions...")
    execute_command(db_path, "DELETE FROM transactions")
    print("   ✓ All transactions deleted\n")

    # Import CSV
    print("2. Importing CSV...")
    bank_format_enum = BankFormat(bank_format)
    stats = import_transactions(db_path, csv_path, account_id, bank_format_enum)

    print(f"\n{'='*60}")
    print("IMPORT COMPLETE!")
    print(f"{'='*60}")
    print(f"  Total rows in CSV: {stats['total']}")
    print(f"  Successfully imported: {stats['imported']}")
    print(f"  Duplicates skipped: {stats['duplicates']}")
    print(f"  Auto-categorized: {stats['categorized']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/reimport_csv.py <db_path> <csv_path> [account_id] [bank_format]")
        print("Example: python scripts/reimport_csv.py sankash.duckdb data/transactions.csv 1 deutsche-bank")
        sys.exit(1)

    db_path = sys.argv[1]
    csv_path = sys.argv[2]
    account_id = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    bank_format = sys.argv[4] if len(sys.argv) > 4 else "deutsche-bank"

    reimport_csv(db_path, csv_path, account_id, bank_format)
