"""Tests for transaction service."""

from datetime import date

import pytest

from sankash.core.models import Account, Transaction
from sankash.services import account_service, transaction_service


def _create_test_account(data_dir: str) -> int:
    """Helper to create a test account."""
    account = Account(name="Test", bank="Bank")
    return account_service.create_account(data_dir, account)


def test_create_and_get_transaction(test_data_dir: str) -> None:
    """Test creating and retrieving a transaction."""
    _create_test_account(test_data_dir)

    transaction = Transaction(
        account_id=1,
        date=date(2024, 1, 15),
        payee="Test Store",
        notes="Test purchase",
        amount=-50.0,
    )

    tx_id = transaction_service.create_transaction(test_data_dir, transaction)
    assert tx_id == 1

    # Get transactions
    df, count = transaction_service.get_transactions(test_data_dir)
    assert count == 1
    assert df["payee"][0] == "Test Store"
    assert float(df["amount"][0]) == -50.0


def test_update_transaction_category(test_data_dir: str) -> None:
    """Test updating transaction category."""
    _create_test_account(test_data_dir)

    transaction = Transaction(
        account_id=1,
        date=date(2024, 1, 15),
        payee="Grocery Store",
        amount=-25.0,
    )

    tx_id = transaction_service.create_transaction(test_data_dir, transaction)

    # Update category
    transaction_service.update_transaction_category(test_data_dir, tx_id, "Groceries")

    # Verify
    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] == "Groceries"
    assert df["is_categorized"][0] is True


def test_get_uncategorized_count(test_data_dir: str) -> None:
    """Test getting uncategorized transaction count."""
    _create_test_account(test_data_dir)

    # Create 3 transactions, categorize 1
    for i in range(3):
        transaction = Transaction(
            account_id=1,
            date=date(2024, 1, i + 1),
            payee=f"Store {i}",
            amount=-10.0,
        )
        transaction_service.create_transaction(test_data_dir, transaction)

    # Categorize one
    transaction_service.update_transaction_category(test_data_dir, 1, "Test")

    # Check count
    count = transaction_service.get_uncategorized_count(test_data_dir)
    assert count == 2


def test_filter_transactions_by_date(test_data_dir: str) -> None:
    """Test filtering transactions by date range."""
    _create_test_account(test_data_dir)

    # Create transactions on different dates
    dates = [date(2024, 1, 1), date(2024, 1, 15), date(2024, 2, 1)]
    for d in dates:
        transaction = Transaction(
            account_id=1,
            date=d,
            payee="Store",
            amount=-10.0,
        )
        transaction_service.create_transaction(test_data_dir, transaction)

    # Filter by date range
    df, count = transaction_service.get_transactions(
        test_data_dir,
        start_date=date(2024, 1, 10),
        end_date=date(2024, 1, 20)
    )

    assert count == 1
    assert df["date"][0] == date(2024, 1, 15)
