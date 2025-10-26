"""Tests for transaction service."""

from datetime import date

import pytest

from sankash.core.models import Transaction
from sankash.services import transaction_service


def test_create_and_get_transaction(test_db_path: str) -> None:
    """Test creating and retrieving a transaction."""
    # Create account first (manually insert)
    from sankash.core.database import execute_command
    execute_command(
        test_db_path,
        "INSERT INTO accounts (name, bank, account_number) VALUES ('Test', 'Bank', '123')"
    )

    # Create transaction
    transaction = Transaction(
        account_id=1,
        date=date(2024, 1, 15),
        payee="Test Store",
        notes="Test purchase",
        amount=-50.0,
    )

    tx_id = transaction_service.create_transaction(test_db_path, transaction)
    assert tx_id == 1

    # Get transactions
    df = transaction_service.get_transactions(test_db_path)
    assert len(df) == 1
    assert df["payee"][0] == "Test Store"
    assert float(df["amount"][0]) == -50.0


def test_update_transaction_category(test_db_path: str) -> None:
    """Test updating transaction category."""
    from sankash.core.database import execute_command

    # Setup
    execute_command(
        test_db_path,
        "INSERT INTO accounts (name, bank, account_number) VALUES ('Test', 'Bank', '123')"
    )

    transaction = Transaction(
        account_id=1,
        date=date(2024, 1, 15),
        payee="Grocery Store",
        amount=-25.0,
    )

    tx_id = transaction_service.create_transaction(test_db_path, transaction)

    # Update category
    transaction_service.update_transaction_category(test_db_path, tx_id, "Groceries")

    # Verify
    df = transaction_service.get_transactions(test_db_path)
    assert df["category"][0] == "Groceries"
    assert df["is_categorized"][0] is True


def test_get_uncategorized_count(test_db_path: str) -> None:
    """Test getting uncategorized transaction count."""
    from sankash.core.database import execute_command

    execute_command(
        test_db_path,
        "INSERT INTO accounts (name, bank, account_number) VALUES ('Test', 'Bank', '123')"
    )

    # Create 3 transactions, categorize 1
    for i in range(3):
        transaction = Transaction(
            account_id=1,
            date=date(2024, 1, i + 1),
            payee=f"Store {i}",
            amount=-10.0,
        )
        transaction_service.create_transaction(test_db_path, transaction)

    # Categorize one
    transaction_service.update_transaction_category(test_db_path, 1, "Test")

    # Check count
    count = transaction_service.get_uncategorized_count(test_db_path)
    assert count == 2


def test_filter_transactions_by_date(test_db_path: str) -> None:
    """Test filtering transactions by date range."""
    from sankash.core.database import execute_command

    execute_command(
        test_db_path,
        "INSERT INTO accounts (name, bank, account_number) VALUES ('Test', 'Bank', '123')"
    )

    # Create transactions on different dates
    dates = [date(2024, 1, 1), date(2024, 1, 15), date(2024, 2, 1)]
    for d in dates:
        transaction = Transaction(
            account_id=1,
            date=d,
            payee="Store",
            amount=-10.0,
        )
        transaction_service.create_transaction(test_db_path, transaction)

    # Filter by date range
    df = transaction_service.get_transactions(
        test_db_path,
        start_date=date(2024, 1, 10),
        end_date=date(2024, 1, 20)
    )

    assert len(df) == 1
    assert df["date"][0] == date(2024, 1, 15)
