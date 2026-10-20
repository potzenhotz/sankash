"""Tests for rule service."""

from datetime import date

import polars as pl

from sankash.core.models import Account, Category, Rule, RuleAction, RuleCondition, Transaction
from sankash.core.storage import write_overrides
from sankash.services import account_service, category_service, rule_service, transaction_service


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


def _matches(rule: Rule, **row: object) -> bool:
    """Evaluate a rule against a single transaction row."""
    df = pl.DataFrame([{"payee": "", "notes": None, "amount": 0.0, **row}])
    return df.select(rule_service.rule_expr(rule)).item()


def test_rule_expr_contains() -> None:
    """Contains is case-insensitive and matches substrings."""
    rule = Rule(
        name="Test",
        conditions=[RuleCondition(field="payee", operator="contains", value="amazon")],
        actions=[RuleAction(action_type="set_category", value="Shopping")],
    )
    assert _matches(rule, payee="Amazon.com") is True
    assert _matches(rule, payee="Walmart") is False


def test_rule_expr_amount() -> None:
    """Amount comparisons are numeric, including equals."""
    less = Rule(
        name="Large Expense",
        conditions=[RuleCondition(field="amount", operator="<", value="-100")],
    )
    assert _matches(less, amount=-150.0) is True
    assert _matches(less, amount=-50.0) is False

    equals = Rule(name="Exact", conditions=[RuleCondition(field="amount", operator="equals", value="-12,50")])
    assert _matches(equals, amount=-12.5) is True


def test_rule_expr_match_type_and_null_notes() -> None:
    """'all' needs every condition; null notes never crash a contains check."""
    rule = Rule(
        name="Both",
        match_type="all",
        conditions=[
            RuleCondition(field="payee", operator="contains", value="paypal"),
            RuleCondition(field="notes", operator="contains", value="spotify"),
        ],
    )
    assert _matches(rule, payee="PayPal", notes="Spotify AB") is True
    assert _matches(rule, payee="PayPal", notes=None) is False


def _grocery_rule() -> Rule:
    return Rule(
        name="Grocery Rule",
        priority=10,
        conditions=[RuleCondition(field="payee", operator="contains", value="grocery")],
        actions=[RuleAction(action_type="set_category", value="Groceries")],
    )


def _create_grocery_transaction(data_dir: str) -> int:
    return transaction_service.create_transaction(
        data_dir,
        Transaction(account_id=1, date=date(2024, 1, 1), payee="Whole Foods Grocery", amount=-50.0),
    )


def test_rules_categorize_at_read_time(test_data_dir: str) -> None:
    """Rules apply without an explicit apply step, also to existing transactions."""
    _create_test_account(test_data_dir)
    _create_grocery_transaction(test_data_dir)
    rule_service.create_rule(test_data_dir, _grocery_rule())

    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] == "Groceries"
    assert df["is_categorized"][0] is True


def test_priority_and_manual_override(test_data_dir: str) -> None:
    """Higher priority rule wins; manual wins over any rule until it is cleared."""
    _create_test_account(test_data_dir)
    tid = _create_grocery_transaction(test_data_dir)
    rule_service.create_rule(test_data_dir, _grocery_rule())
    rule_service.create_rule(test_data_dir, Rule(
        name="Food",
        priority=20,
        conditions=[RuleCondition(field="payee", operator="contains", value="foods")],
        actions=[RuleAction(action_type="set_category", value="Food")],
    ))

    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] == "Food"

    transaction_service.update_transaction_category(test_data_dir, tid, "Gifts")
    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] == "Gifts"

    transaction_service.clear_manual_category(test_data_dir, tid)
    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] == "Food"


def test_legacy_rule_overrides_are_ignored(test_data_dir: str) -> None:
    """Old stored rule results must not freeze a category after the rule changes."""
    _create_test_account(test_data_dir)
    tid = _create_grocery_transaction(test_data_dir)
    write_overrides(test_data_dir, {
        str(tid): {"category": "Stale", "is_categorized": True, "category_source": "rule"},
    })

    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] is None
    assert df["is_categorized"][0] is False


def test_category_rename_and_delete_cascade_to_rules(test_data_dir: str) -> None:
    """Renaming a category retargets its rule; deleting it removes the rule."""
    _create_test_account(test_data_dir)
    _create_grocery_transaction(test_data_dir)
    cat_id = category_service.create_category(test_data_dir, Category(name="Groceries"))
    rule_service.create_rule(test_data_dir, _grocery_rule())

    category_service.update_category(test_data_dir, cat_id, Category(name="Supermarket"))
    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] == "Supermarket"
    assert rule_service.get_rule_for_category(test_data_dir, "Supermarket") is not None

    category_service.delete_category(test_data_dir, cat_id)
    df, _ = transaction_service.get_transactions(test_data_dir)
    assert df["category"][0] is None
    assert rule_service.get_rules(test_data_dir).is_empty()


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
