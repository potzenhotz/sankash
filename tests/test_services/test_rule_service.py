"""Tests for rule service."""

from datetime import date

import pytest

from sankash.core.models import Account, Rule, RuleAction, RuleCondition, Transaction
from sankash.services import account_service, rule_service, transaction_service


def _create_test_account(data_dir: str) -> int:
    """Helper to create a test account."""
    account = Account(name="Test", bank="Bank")
    return account_service.create_account(data_dir, account)


def test_create_and_get_rule(test_data_dir: str) -> None:
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

    rule_id = rule_service.create_rule(test_data_dir, rule)
    assert rule_id == 1

    # Get rules
    df = rule_service.get_rules(test_data_dir)
    assert len(df) == 1
    assert df["name"][0] == "Grocery Rule"


def test_evaluate_rule_contains(test_data_dir: str) -> None:
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


def test_evaluate_rule_amount(test_data_dir: str) -> None:
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


def test_apply_rules_to_uncategorized(test_data_dir: str) -> None:
    """Test applying rules to uncategorized transactions."""
    _create_test_account(test_data_dir)

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
    rule_service.create_rule(test_data_dir, rule)

    # Create matching transaction
    transaction = Transaction(
        account_id=1,
        date=date(2024, 1, 1),
        payee="Whole Foods Grocery",
        amount=-50.0,
    )
    transaction_service.create_transaction(test_data_dir, transaction)

    # Apply rules
    categorized = rule_service.apply_rules_to_uncategorized(test_data_dir)
    assert categorized == 1

    # Verify transaction was categorized
    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] == "Groceries"
    assert df["is_categorized"][0] is True


def test_add_condition_to_category(test_data_dir: str) -> None:
    """Test adding a condition to a category's rule."""
    condition = RuleCondition(field="payee", operator="contains", value="Netflix")
    rule_service.add_condition_to_category(test_data_dir, "Entertainment", condition)

    # Verify rule was created
    df = rule_service.get_rules(test_data_dir)
    assert len(df) == 1

    rule = rule_service.parse_rule_from_row(df.to_dicts()[0])
    assert rule.name == "Entertainment"
    assert len(rule.conditions) == 1
    assert rule.conditions[0].value == "Netflix"
    assert rule.actions[0].value == "Entertainment"

    # Add another condition to the same category
    condition2 = RuleCondition(field="payee", operator="contains", value="Disney")
    rule_service.add_condition_to_category(test_data_dir, "Entertainment", condition2)

    df = rule_service.get_rules(test_data_dir)
    assert len(df) == 1  # Still one rule

    rule = rule_service.parse_rule_from_row(df.to_dicts()[0])
    assert len(rule.conditions) == 2

    # Adding duplicate condition should be a no-op
    rule_service.add_condition_to_category(test_data_dir, "Entertainment", condition)
    df = rule_service.get_rules(test_data_dir)
    rule = rule_service.parse_rule_from_row(df.to_dicts()[0])
    assert len(rule.conditions) == 2
