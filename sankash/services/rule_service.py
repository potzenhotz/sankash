"""Rule service with functional rule engine."""

from datetime import datetime
from typing import Any, Callable

import polars as pl
import yaml

from sankash.core.models import Rule, RuleAction, RuleCondition, Transaction
from sankash.core.storage import next_id, read_yaml, write_yaml


def get_rules(data_dir: str, active_only: bool = True) -> pl.DataFrame:
    """Get all rules ordered by priority."""
    records = read_yaml(data_dir, "rules")
    if not records:
        return pl.DataFrame()
    df = pl.DataFrame(records)
    if active_only and "is_active" in df.columns:
        df = df.filter(pl.col("is_active") == True)  # noqa: E712
    if "priority" in df.columns:
        df = df.sort(["priority", "id"], descending=[True, False])
    return df


def parse_rule_from_row(row: dict) -> Rule:
    """Parse Rule from a record (pure function)."""
    conditions = row.get("conditions", [])
    actions = row.get("actions", [])

    # Handle both serialized JSON strings and native dicts/lists
    if isinstance(conditions, str):
        import json
        conditions = json.loads(conditions)
    if isinstance(actions, str):
        import json
        actions = json.loads(actions)

    return Rule(
        id=row["id"],
        name=row["name"],
        priority=row["priority"],
        is_active=row["is_active"],
        match_type=row.get("match_type", "any"),
        conditions=conditions,
        actions=actions,
    )


def create_condition_evaluator(condition: RuleCondition) -> Callable[[Transaction], bool]:
    """Create a condition evaluator function (higher-order function)."""
    field = condition.field
    operator = condition.operator
    value = condition.value

    def evaluator(transaction: Transaction) -> bool:
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
    """Evaluate if transaction matches rule conditions (pure function)."""
    if not rule.conditions:
        return False

    evaluators = [create_condition_evaluator(cond) for cond in rule.conditions]

    if rule.match_type == "any":
        return any(evaluator(transaction) for evaluator in evaluators)
    else:
        return all(evaluator(transaction) for evaluator in evaluators)


def apply_rule_actions(data_dir: str, rule: Rule, transaction_id: int) -> None:
    """Apply rule actions to transaction (side effect isolated)."""
    from sankash.services.transaction_service import mark_as_transfer, update_transaction_category

    for action in rule.actions:
        if action.action_type == "set_category":
            update_transaction_category(data_dir, transaction_id, action.value, source="rule")
        elif action.action_type == "mark_transfer":
            transfer_account_id = int(action.value)
            mark_as_transfer(data_dir, transaction_id, transfer_account_id)


def apply_rules_to_uncategorized(data_dir: str) -> int:
    """Apply all active rules to uncategorized transactions.

    Returns count of transactions that were categorized.
    """
    from sankash.services.transaction_service import get_transactions

    rules_df = get_rules(data_dir, active_only=True)
    if rules_df.is_empty():
        return 0

    rules = [parse_rule_from_row(row) for row in rules_df.to_dicts()]

    transactions_df, _ = get_transactions(data_dir, is_categorized=False, limit=100_000, offset=0)
    if transactions_df.is_empty():
        return 0

    transactions = [Transaction(**row) for row in transactions_df.to_dicts()]

    categorized_count = 0
    for transaction in transactions:
        for rule in rules:
            if evaluate_rule(rule, transaction):
                if transaction.id is not None:
                    apply_rule_actions(data_dir, rule, transaction.id)
                    categorized_count += 1
                break
    return categorized_count


def apply_rules_to_all(data_dir: str) -> int:
    """Clear ALL categories, re-apply rules. Manual categorizations are restored
    only for transactions that no rule matches.

    Returns count of transactions that were categorized by rules.
    """
    from sankash.core.storage import read_overrides, write_overrides
    from sankash.services.transaction_service import get_transactions

    overrides = read_overrides(data_dir)

    # Remember manual categorizations so we can restore unmatched ones
    manual_categories = {}
    for tid, data in overrides.items():
        if data.get("category_source") == "manual" and "category" in data:
            manual_categories[tid] = data["category"]

    # Clear all category overrides
    for tid in list(overrides.keys()):
        overrides[tid].pop("category", None)
        overrides[tid].pop("is_categorized", None)
        overrides[tid].pop("category_source", None)
    overrides = {tid: v for tid, v in overrides.items() if v}
    write_overrides(data_dir, overrides)

    # Apply rules (they dominate)
    rule_count = apply_rules_to_uncategorized(data_dir)

    # Restore manual categorizations for transactions that rules didn't match
    overrides = read_overrides(data_dir)
    restored = 0
    for tid, category in manual_categories.items():
        if tid not in overrides or not overrides[tid].get("is_categorized"):
            if tid not in overrides:
                overrides[tid] = {}
            overrides[tid]["category"] = category
            overrides[tid]["is_categorized"] = True
            overrides[tid]["category_source"] = "manual"
            restored += 1
    if restored:
        write_overrides(data_dir, overrides)

    return rule_count


def test_rule(data_dir: str, rule: Rule, limit: int = 100) -> pl.DataFrame:
    """Test rule against existing transactions. Returns matching transactions."""
    from sankash.services.transaction_service import get_transactions

    transactions_df, _ = get_transactions(data_dir, limit=100_000, offset=0)
    if transactions_df.is_empty():
        return pl.DataFrame()

    transactions_df = transactions_df.head(limit)
    transactions = [Transaction(**row) for row in transactions_df.to_dicts()]

    matching_ids = [
        t.id for t in transactions
        if t.id is not None and evaluate_rule(rule, t)
    ]

    if not matching_ids:
        return pl.DataFrame()

    return transactions_df.filter(pl.col("id").is_in(matching_ids))


def create_rule(data_dir: str, rule: Rule) -> int:
    """Create new rule and return its ID."""
    records = read_yaml(data_dir, "rules")
    new_id = next_id(records)
    record = {
        "id": new_id,
        "name": rule.name,
        "priority": rule.priority,
        "is_active": rule.is_active,
        "match_type": rule.match_type,
        "conditions": [c.model_dump() for c in rule.conditions],
        "actions": [a.model_dump() for a in rule.actions],
        "created_at": datetime.now().isoformat(),
    }
    records.append(record)
    write_yaml(data_dir, "rules", records)
    return new_id


def update_rule(data_dir: str, rule_id: int, rule: Rule) -> None:
    """Update existing rule."""
    records = read_yaml(data_dir, "rules")
    for rec in records:
        if rec["id"] == rule_id:
            rec["name"] = rule.name
            rec["priority"] = rule.priority
            rec["is_active"] = rule.is_active
            rec["match_type"] = rule.match_type
            rec["conditions"] = [c.model_dump() for c in rule.conditions]
            rec["actions"] = [a.model_dump() for a in rule.actions]
            break
    write_yaml(data_dir, "rules", records)


def delete_rule(data_dir: str, rule_id: int) -> None:
    """Delete rule."""
    records = read_yaml(data_dir, "rules")
    records = [r for r in records if r["id"] != rule_id]
    write_yaml(data_dir, "rules", records)


def count_matching_transactions(data_dir: str, rule: Rule) -> int:
    """Count how many transactions match a rule."""
    from sankash.services.transaction_service import get_transactions

    transactions_df, _ = get_transactions(data_dir, limit=100_000, offset=0)
    if transactions_df.is_empty():
        return 0

    transactions = [Transaction(**row) for row in transactions_df.to_dicts()]
    return sum(1 for t in transactions if evaluate_rule(rule, t))


def get_rule_for_category(data_dir: str, category: str) -> dict | None:
    """Find the rule that targets a specific category."""
    records = read_yaml(data_dir, "rules")
    for rec in records:
        actions = rec.get("actions", [])
        if actions and actions[0].get("value") == category:
            return rec
    return None


def add_condition_to_category(
    data_dir: str, category: str, condition: RuleCondition
) -> None:
    """Add a condition to the rule for a category. Creates the rule if needed."""
    existing = get_rule_for_category(data_dir, category)

    if existing:
        # Append condition to existing rule
        rule = parse_rule_from_row(existing)
        # Avoid duplicate conditions
        for c in rule.conditions:
            if c.field == condition.field and c.operator == condition.operator and c.value == condition.value:
                return
        rule.conditions.append(condition)
        update_rule(data_dir, existing["id"], rule)
    else:
        # Create new rule for this category
        rule = Rule(
            name=category,
            priority=0,
            is_active=True,
            match_type="any",
            conditions=[condition],
            actions=[RuleAction(action_type="set_category", value=category)],
        )
        create_rule(data_dir, rule)


def remove_condition_from_category(
    data_dir: str, category: str, condition_index: int
) -> None:
    """Remove a condition by index from the rule for a category."""
    existing = get_rule_for_category(data_dir, category)
    if not existing:
        return
    rule = parse_rule_from_row(existing)
    if 0 <= condition_index < len(rule.conditions):
        rule.conditions.pop(condition_index)
        if rule.conditions:
            update_rule(data_dir, existing["id"], rule)
        else:
            delete_rule(data_dir, existing["id"])


def migrate_rules_to_category_based(data_dir: str) -> int:
    """Merge old-style rules into one rule per category.

    Rules with the same target category are merged — conditions combined with
    match_type "any". Highest priority is kept. Returns number of merges performed.
    """
    records = read_yaml(data_dir, "rules")
    if not records:
        return 0

    # Group by target category
    by_category: dict[str, list[dict]] = {}
    for rec in records:
        actions = rec.get("actions", [])
        if not actions:
            continue
        category = actions[0].get("value", "")
        if not category:
            continue
        by_category.setdefault(category, []).append(rec)

    # Check if migration is needed (any category has multiple rules)
    needs_migration = any(len(rules) > 1 for rules in by_category.values())
    if not needs_migration:
        return 0

    # Build merged rules
    merged = []
    merges = 0
    for category, rules in by_category.items():
        # Combine all conditions
        all_conditions = []
        for r in rules:
            conditions = r.get("conditions", [])
            if isinstance(conditions, str):
                import json
                conditions = json.loads(conditions)
            all_conditions.extend(conditions)

        # Deduplicate conditions
        seen = set()
        unique_conditions = []
        for c in all_conditions:
            key = (c.get("field"), c.get("operator"), c.get("value"))
            if key not in seen:
                seen.add(key)
                unique_conditions.append(c)

        merged.append({
            "id": rules[0]["id"],
            "name": category,
            "priority": max(r.get("priority", 0) for r in rules),
            "is_active": any(r.get("is_active", True) for r in rules),
            "match_type": "any",
            "conditions": unique_conditions,
            "actions": [{"action_type": "set_category", "value": category}],
            "created_at": rules[0].get("created_at", datetime.now().isoformat()),
        })

        if len(rules) > 1:
            merges += len(rules) - 1

    write_yaml(data_dir, "rules", merged)
    return merges


def export_rules(data_dir: str) -> str:
    """Export all rules as YAML string.

    Strips internal fields (id, created_at) so the export is portable.
    """
    records = read_yaml(data_dir, "rules")
    export_records = []
    for rec in records:
        export_records.append({
            "name": rec["name"],
            "priority": rec.get("priority", 0),
            "is_active": rec.get("is_active", True),
            "match_type": rec.get("match_type", "any"),
            "conditions": rec.get("conditions", []),
            "actions": rec.get("actions", []),
        })
    return yaml.dump(export_records, default_flow_style=False, allow_unicode=True, sort_keys=False)


def import_rules(data_dir: str, yaml_content: str) -> tuple[int, int]:
    """Import rules from YAML string, updating existing rules by name.

    Returns (added_count, updated_count).
    """
    imported_data = yaml.safe_load(yaml_content)
    if not isinstance(imported_data, list):
        raise ValueError("Invalid rules file: expected a list of rules")

    existing_records = read_yaml(data_dir, "rules")
    existing_by_name = {r["name"]: r for r in existing_records}

    added = 0
    updated = 0

    for rule_data in imported_data:
        if not isinstance(rule_data, dict) or "name" not in rule_data:
            continue

        rule = Rule(
            name=rule_data["name"],
            priority=rule_data.get("priority", 0),
            is_active=rule_data.get("is_active", True),
            match_type=rule_data.get("match_type", "any"),
            conditions=[
                RuleCondition(**c) for c in rule_data.get("conditions", [])
            ],
            actions=[
                RuleAction(**a) for a in rule_data.get("actions", [])
            ],
        )

        if rule_data["name"] in existing_by_name:
            rule_id = existing_by_name[rule_data["name"]]["id"]
            update_rule(data_dir, rule_id, rule)
            updated += 1
        else:
            create_rule(data_dir, rule)
            added += 1

    return added, updated
