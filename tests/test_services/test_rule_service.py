"""Tests for rule service."""

from datetime import date

import pytest

from sankash.core.models import Rule, RuleAction, RuleCondition, Transaction
from sankash.services import rule_service, transaction_service


def test_create_and_get_rule(test_db_path: str) -> None:
    """Test creating and retrieving a rule."""
    rule = Rule(
        name="Grocery Rule",
        priority=10,
        conditions=[
            RuleCondition(field="payee", operator="contains", value="grocery")
        ],
        actions=[
            RuleAction(action_type="set_category", value="Groceries")
        ]
    )

    rule_id = rule_service.create_rule(test_db_path, rule)
    assert rule_id == 1

    # Get rules
    df = rule_service.get_rules(test_db_path)
    assert len(df) == 1
    assert df["name"][0] == "Grocery Rule"


def test_evaluate_rule_contains(test_db_path: str) -> None:
    """Test rule evaluation with contains operator."""
    rule = Rule(
        name="Test",
        conditions=[
            RuleCondition(field="payee", operator="contains", value="amazon")
        ],
        actions=[
            RuleAction(action_type="set_category", value="Shopping")
        ]
    )

    # Should match
    transaction1 = Transaction(
        account_id=1,
        date=date(2024, 1, 1),
        payee="Amazon.com",
        amount=-50.0,
    )
    assert rule_service.evaluate_rule(rule, transaction1) is True

    # Should not match
    transaction2 = Transaction(
        account_id=1,
        date=date(2024, 1, 1),
        payee="Walmart",
        amount=-50.0,
    )
    assert rule_service.evaluate_rule(rule, transaction2) is False


def test_evaluate_rule_amount(test_db_path: str) -> None:
    """Test rule evaluation with amount comparison."""
    rule = Rule(
        name="Large Expense",
        conditions=[
            RuleCondition(field="amount", operator="<", value="-100")
        ],
        actions=[
            RuleAction(action_type="set_category", value="Large Purchase")
        ]
    )

    # Should match (amount is -150, less than -100)
    transaction1 = Transaction(
        account_id=1,
        date=date(2024, 1, 1),
        payee="Store",
        amount=-150.0,
    )
    assert rule_service.evaluate_rule(rule, transaction1) is True

    # Should not match
    transaction2 = Transaction(
        account_id=1,
        date=date(2024, 1, 1),
        payee="Store",
        amount=-50.0,
    )
    assert rule_service.evaluate_rule(rule, transaction2) is False


def test_apply_rules_to_uncategorized(test_db_path: str) -> None:
    """Test applying rules to uncategorized transactions."""
    from sankash.core.database import execute_command

    # Setup account
    execute_command(
        test_db_path,
        "INSERT INTO accounts (name, bank, account_number) VALUES ('Test', 'Bank', '123')"
    )

    # Create rule
    rule = Rule(
        name="Grocery Rule",
        priority=10,
        conditions=[
            RuleCondition(field="payee", operator="contains", value="grocery")
        ],
        actions=[
            RuleAction(action_type="set_category", value="Groceries")
        ]
    )
    rule_service.create_rule(test_db_path, rule)

    # Create matching transaction
    transaction = Transaction(
        account_id=1,
        date=date(2024, 1, 1),
        payee="Whole Foods Grocery",
        amount=-50.0,
    )
    transaction_service.create_transaction(test_db_path, transaction)

    # Apply rules
    categorized = rule_service.apply_rules_to_uncategorized(test_db_path)
    assert categorized == 1

    # Verify transaction was categorized
    df = transaction_service.get_transactions(test_db_path)
    assert df["category"][0] == "Groceries"
    assert df["is_categorized"][0] is True


def test_create_rule_from_transaction(test_db_path: str) -> None:
    """Test creating a rule from a transaction."""
    transaction = Transaction(
        id=1,
        account_id=1,
        date=date(2024, 1, 1),
        payee="Netflix",
        amount=-15.99,
        category="Entertainment",
    )

    rule_id = rule_service.create_rule_from_transaction(
        test_db_path,
        transaction,
        "Netflix Auto-categorize"
    )

    # Verify rule was created
    df = rule_service.get_rules(test_db_path)
    assert len(df) == 1
    assert df["name"][0] == "Netflix Auto-categorize"

    # Parse and verify rule structure
    rule = rule_service.parse_rule_from_row(df.to_dicts()[0])
    assert len(rule.conditions) == 1
    assert rule.conditions[0].field == "payee"
    assert rule.conditions[0].value == "Netflix"
    assert len(rule.actions) == 1
    assert rule.actions[0].action_type == "set_category"
    assert rule.actions[0].value == "Entertainment"
