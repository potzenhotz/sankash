"""Rule service with functional rule engine."""

import json
from typing import Callable

import polars as pl

from sankash.core.database import execute_command, execute_query
from sankash.core.models import Rule, RuleCondition, Transaction


def get_rules(db_path: str, active_only: bool = True) -> pl.DataFrame:
    """Get all rules ordered by priority (pure function)."""
    query = "SELECT * FROM rules"

    if active_only:
        query += " WHERE is_active = TRUE"

    query += " ORDER BY priority DESC, id"

    return execute_query(db_path, query)


def parse_rule_from_row(row: dict) -> Rule:
    """Parse Rule from database row (pure function)."""
    return Rule(
        id=row["id"],
        name=row["name"],
        priority=row["priority"],
        is_active=row["is_active"],
        match_type=row.get("match_type", "any"),  # Default to "any" for backward compatibility
        conditions=json.loads(row["conditions"]) if isinstance(row["conditions"], str) else row["conditions"],
        actions=json.loads(row["actions"]) if isinstance(row["actions"], str) else row["actions"],
    )


def create_condition_evaluator(condition: RuleCondition) -> Callable[[Transaction], bool]:
    """
    Create a condition evaluator function (higher-order function).

    Returns a function that takes a Transaction and returns bool.
    This is a pure function that returns another pure function.
    """
    field = condition.field
    operator = condition.operator
    value = condition.value

    def evaluator(transaction: Transaction) -> bool:
        """Evaluate condition against transaction."""
        if field == "payee":
            field_value = transaction.payee
        elif field == "amount":
            field_value = str(transaction.amount)
        elif field == "notes":
            field_value = transaction.notes or ""
        else:
            return False

        if operator == "contains":
            return value.lower() in field_value.lower()
        elif operator == "equals":
            return value.lower() == field_value.lower()
        elif operator == "<":
            try:
                return float(field_value) < float(value)
            except ValueError:
                return False
        elif operator == ">":
            try:
                return float(field_value) > float(value)
            except ValueError:
                return False
        else:
            return False

    return evaluator


def evaluate_rule(rule: Rule, transaction: Transaction) -> bool:
    """
    Evaluate if transaction matches rule conditions (pure function).

    Supports both AND (all) and OR (any) logic based on rule.match_type.
    """
    if not rule.conditions:
        return False

    evaluators = [create_condition_evaluator(cond) for cond in rule.conditions]

    # Use AND logic if match_type is "all", OR logic if "any"
    if rule.match_type == "any":
        return any(evaluator(transaction) for evaluator in evaluators)
    else:
        return all(evaluator(transaction) for evaluator in evaluators)


def apply_rule_actions(db_path: str, rule: Rule, transaction_id: int) -> None:
    """Apply rule actions to transaction (side effect isolated)."""
    from sankash.services.transaction_service import mark_as_transfer, update_transaction_category

    for action in rule.actions:
        if action.action_type == "set_category":
            update_transaction_category(db_path, transaction_id, action.value)
        elif action.action_type == "mark_transfer":
            # Extract transfer account ID from action value
            transfer_account_id = int(action.value)
            mark_as_transfer(db_path, transaction_id, transfer_account_id)


def apply_rules_to_uncategorized(db_path: str) -> int:
    """
    Apply all active rules to uncategorized transactions.

    Returns count of transactions that were categorized.
    """
    from sankash.services.transaction_service import get_transactions

    # Get active rules sorted by priority
    rules_df = get_rules(db_path, active_only=True)

    if rules_df.is_empty():
        return 0

    rules = [parse_rule_from_row(row) for row in rules_df.to_dicts()]

    # Get all uncategorized transactions (no pagination limit)
    transactions_df, _ = get_transactions(db_path, is_categorized=False, limit=100_000, offset=0)

    if transactions_df.is_empty():
        return 0

    transactions = [Transaction(**row) for row in transactions_df.to_dicts()]

    categorized_count = 0

    for transaction in transactions:
        for rule in rules:
            if evaluate_rule(rule, transaction):
                if transaction.id is not None:
                    apply_rule_actions(db_path, rule, transaction.id)
                    categorized_count += 1
                break  # Stop after first matching rule

    return categorized_count


def test_rule(db_path: str, rule: Rule, limit: int = 100) -> pl.DataFrame:
    """
    Test rule against existing transactions (pure function).

    Returns DataFrame of matching transactions.
    """
    from sankash.services.transaction_service import get_transactions

    # Get all transactions (no pagination limit)
    transactions_df, _ = get_transactions(db_path, limit=100_000, offset=0)

    if transactions_df.is_empty():
        return pl.DataFrame()

    # Limit to recent transactions for testing
    transactions_df = transactions_df.head(limit)
    transactions = [Transaction(**row) for row in transactions_df.to_dicts()]

    # Filter matching transactions
    matching_ids = [
        t.id for t in transactions
        if t.id is not None and evaluate_rule(rule, t)
    ]

    if not matching_ids:
        return pl.DataFrame()

    # Return matching transactions
    return transactions_df.filter(pl.col("id").is_in(matching_ids))


def create_rule(db_path: str, rule: Rule) -> int:
    """Create new rule and return its ID."""
    result = execute_query(
        db_path,
        """INSERT INTO rules (name, priority, is_active, match_type, conditions, actions)
        VALUES ($name, $priority, $is_active, $match_type, $conditions, $actions)
        RETURNING id""",
        {
            "name": rule.name,
            "priority": rule.priority,
            "is_active": rule.is_active,
            "match_type": rule.match_type,
            "conditions": json.dumps([c.model_dump() for c in rule.conditions]),
            "actions": json.dumps([a.model_dump() for a in rule.actions]),
        }
    )
    return int(result["id"][0])


def update_rule(db_path: str, rule_id: int, rule: Rule) -> None:
    """Update existing rule."""
    execute_command(
        db_path,
        """UPDATE rules
        SET name = $name,
            priority = $priority,
            is_active = $is_active,
            match_type = $match_type,
            conditions = $conditions,
            actions = $actions
        WHERE id = $id""",
        {
            "id": rule_id,
            "name": rule.name,
            "priority": rule.priority,
            "is_active": rule.is_active,
            "match_type": rule.match_type,
            "conditions": json.dumps([c.model_dump() for c in rule.conditions]),
            "actions": json.dumps([a.model_dump() for a in rule.actions]),
        }
    )


def delete_rule(db_path: str, rule_id: int) -> None:
    """Delete rule."""
    execute_command(db_path, "DELETE FROM rules WHERE id = $id", {"id": rule_id})


def count_matching_transactions(db_path: str, rule: Rule) -> int:
    """
    Count how many transactions match a rule.

    Returns the count of matching transactions.
    """
    from sankash.services.transaction_service import get_transactions

    # Get all transactions (no pagination limit)
    transactions_df, _ = get_transactions(db_path, limit=100_000, offset=0)

    if transactions_df.is_empty():
        return 0

    transactions = [Transaction(**row) for row in transactions_df.to_dicts()]

    # Count matching transactions
    return sum(1 for t in transactions if evaluate_rule(rule, t))


def create_rule_from_transaction(
    db_path: str,
    transaction: Transaction,
    rule_name: str,
    priority: int = 0,
) -> int:
    """
    Create a rule from a transaction (convenience function).

    Creates a rule that matches the payee and sets the same category.
    """
    if not transaction.category:
        raise ValueError("Transaction must have a category to create rule")

    rule = Rule(
        name=rule_name,
        priority=priority,
        is_active=True,
        conditions=[
            RuleCondition(
                field="payee",
                operator="contains",
                value=transaction.payee
            )
        ],
        actions=[
            RuleAction(
                action_type="set_category",
                value=transaction.category
            )
        ]
    )

    return create_rule(db_path, rule)
