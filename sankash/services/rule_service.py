"""Rule service with functional rule engine."""

from datetime import datetime

import polars as pl
import yaml

from sankash.core.models import Rule, RuleAction, RuleCondition
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


def _condition_expr(condition: RuleCondition) -> pl.Expr:
    """Polars expression that is True where a transaction matches one condition."""
    field = condition.field
    operator = condition.operator
    if field not in ("payee", "notes", "amount"):
        return pl.lit(False)

    if operator in ("<", ">") or (field == "amount" and operator == "equals"):
        try:
            value = float(condition.value.replace(",", "."))
        except ValueError:
            return pl.lit(False)
        number = pl.col(field).cast(pl.Float64, strict=False)
        if operator == "<":
            return number < value
        if operator == ">":
            return number > value
        return number == value

    text = pl.col(field).cast(pl.Utf8).fill_null("").str.to_lowercase()
    if operator == "contains":
        return text.str.contains(condition.value.lower(), literal=True)
    if operator == "equals":
        return text == condition.value.lower()
    return pl.lit(False)


def rule_expr(rule: Rule) -> pl.Expr:
    """Polars expression that is True where a transaction matches the rule."""
    if not rule.conditions:
        return pl.lit(False)
    exprs = [_condition_expr(c) for c in rule.conditions]
    combined = pl.any_horizontal(exprs) if rule.match_type == "any" else pl.all_horizontal(exprs)
    return combined.fill_null(False)


def get_active_rules(data_dir: str) -> list[Rule]:
    """Active rules as models, highest priority first."""
    rules_df = get_rules(data_dir, active_only=True)
    if rules_df.is_empty():
        return []
    return [parse_rule_from_row(row) for row in rules_df.to_dicts()]


def apply_rules(df: pl.DataFrame, rules: list[Rule]) -> pl.DataFrame:
    """Derive category per transaction (pure function).

    A manual assignment (category_source == "manual") always wins; otherwise the
    first matching rule in priority order sets the category. Nothing is stored, so
    rule edits take effect immediately on all transactions.
    """
    if df.is_empty():
        return df

    # shortcut: only set_category actions are derived; mark_transfer is not, no rule uses it yet
    rule_category = pl.lit(None, dtype=pl.Utf8)
    for rule in reversed(rules):
        category = next((a.value for a in rule.actions if a.action_type == "set_category"), None)
        if category:
            rule_category = pl.when(rule_expr(rule)).then(pl.lit(category)).otherwise(rule_category)

    if "category_source" in df.columns:
        is_manual = (pl.col("category_source") == "manual").fill_null(False)
    else:
        is_manual = pl.lit(False)

    return df.with_columns(
        pl.when(is_manual).then(pl.col("category").cast(pl.Utf8)).otherwise(rule_category).alias("category")
    ).with_columns(pl.col("category").is_not_null().alias("is_categorized"))


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


def rename_category_in_rules(data_dir: str, old_name: str, new_name: str) -> None:
    """Point rules that target old_name at new_name (category rename cascade)."""
    records = read_yaml(data_dir, "rules")
    changed = False
    for rec in records:
        for action in rec.get("actions", []):
            if action.get("action_type") == "set_category" and action.get("value") == old_name:
                action["value"] = new_name
                changed = True
                if rec.get("name") == old_name:
                    rec["name"] = new_name
    if changed:
        write_yaml(data_dir, "rules", records)
