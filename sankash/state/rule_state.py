"""Rules page state management."""

import json

import reflex as rx

from sankash.core.models import RuleCondition
from sankash.services import rule_service, category_service, transaction_service
from sankash.state.base import BaseState


class RuleState(BaseState):
    """State for rules management — one rule per category, no create/delete."""

    state_auto_setters = True

    # All categories with their rule info (one row per category)
    category_rules: list[dict] = []
    loading: bool = False
    error: str = ""
    success: str = ""

    # Inline editing: which category is currently being edited
    editing_category: str = ""
    conditions: list[dict] = []  # Current conditions being edited

    # Category display mapping
    categories: list[str] = []
    category_display_map: dict[str, str] = {}

    # Uncategorized transactions
    uncategorized_transactions: list[dict] = []
    uncategorized_count: int = 0

    # Quick-assign
    assigning_tx_payee: str = ""

    def load_rules(self) -> None:
        """Load all categories with their rule info."""
        self.loading = True
        self.error = ""

        try:
            # Run migration on first load
            merges = rule_service.migrate_rules_to_category_based(self.data_dir)
            if merges:
                self.success = f"Migrated rules: merged {merges} duplicate(s)"

            # Get all categories
            cat_df = category_service.get_categories(self.data_dir)
            all_cats = cat_df.to_dicts() if not cat_df.is_empty() else []

            # Get all rules indexed by target category
            rules_df = rule_service.get_rules(self.data_dir, active_only=False)
            rules_by_category: dict[str, dict] = {}
            if not rules_df.is_empty():
                for rule in rules_df.to_dicts():
                    conditions = json.loads(rule["conditions"]) if isinstance(rule["conditions"], str) else rule["conditions"]
                    actions = json.loads(rule["actions"]) if isinstance(rule["actions"], str) else rule["actions"]
                    target_cat = actions[0]["value"] if actions else ""
                    if target_cat:
                        rules_by_category[target_cat] = {
                            "rule_id": rule["id"],
                            "conditions": conditions,
                            "is_active": rule.get("is_active", True),
                            "priority": rule.get("priority", 0),
                        }

            # Build one row per category
            category_rules = []
            for cat in all_cats:
                cat_name = cat["name"]
                display_name = category_service.get_category_display_name(
                    self.data_dir, cat_name
                )
                rule_info = rules_by_category.get(cat_name, {})
                conditions = rule_info.get("conditions", [])

                # Count matches
                match_count = 0
                if conditions:
                    try:
                        from sankash.core.models import Rule, RuleAction
                        parsed = Rule(
                            name=cat_name,
                            priority=rule_info.get("priority", 0),
                            is_active=rule_info.get("is_active", True),
                            match_type="any",
                            conditions=[RuleCondition(**c) for c in conditions],
                            actions=[RuleAction(action_type="set_category", value=cat_name)],
                        )
                        match_count = rule_service.count_matching_transactions(self.data_dir, parsed)
                    except Exception:
                        pass

                # Format conditions for display
                if conditions:
                    parts = [f"{c['field']} {c['operator']} '{c['value']}'" for c in conditions]
                    condition_text = " OR ".join(parts)
                else:
                    condition_text = ""

                category_rules.append({
                    "category": cat_name,
                    "display_name": display_name,
                    "rule_id": rule_info.get("rule_id", 0),
                    "has_conditions": len(conditions) > 0,
                    "conditions": conditions,
                    "condition_text": condition_text,
                    "condition_count": len(conditions),
                    "match_count": match_count,
                    "is_active": rule_info.get("is_active", True),
                    "priority": rule_info.get("priority", 0),
                })

            # Sort: categories with conditions first (by match count desc), then without (alphabetically)
            category_rules.sort(
                key=lambda r: (not r["has_conditions"], -r["match_count"], r["display_name"])
            )
            self.category_rules = category_rules
        except Exception as e:
            self.error = f"Failed to load rules: {str(e)}"
        finally:
            self.loading = False

    def load_categories(self) -> None:
        """Load category display names for quick-assign."""
        try:
            df = category_service.get_categories(self.data_dir)
            categories = df.to_dicts()

            display_names = []
            display_map = {}

            for cat in categories:
                display_name = category_service.get_category_display_name(
                    self.data_dir, cat["name"]
                )
                display_names.append(display_name)
                display_map[display_name] = cat["name"]

            display_names.sort()
            self.categories = display_names
            self.category_display_map = display_map
        except Exception as e:
            self.error = f"Failed to load categories: {str(e)}"

    def load_uncategorized(self) -> None:
        """Load uncategorized transactions for the side panel."""
        try:
            df, total = transaction_service.get_transactions(
                self.data_dir,
                is_categorized=False,
                sort_by="date",
                sort_order="desc",
                limit=100,
            )
            self.uncategorized_transactions = df.to_dicts() if not df.is_empty() else []
            self.uncategorized_count = total
        except Exception:
            self.uncategorized_transactions = []
            self.uncategorized_count = 0

    # --- Inline editing ---

    def start_editing(self, category: str) -> None:
        """Open inline editor for a category's conditions."""
        self.editing_category = category
        self.error = ""
        self.success = ""

        # Load existing conditions for this category
        existing = rule_service.get_rule_for_category(self.data_dir, category)
        if existing:
            conditions = existing.get("conditions", [])
            if isinstance(conditions, str):
                conditions = json.loads(conditions)
            self.conditions = [dict(c) for c in conditions]
        else:
            self.conditions = []

    def stop_editing(self) -> None:
        """Close inline editor."""
        self.editing_category = ""
        self.conditions = []

    def add_condition(self) -> None:
        """Add empty condition to editor."""
        self.conditions.append({"field": "payee", "operator": "contains", "value": ""})

    def remove_condition(self, index: int) -> None:
        """Remove condition from editor."""
        if 0 <= index < len(self.conditions):
            self.conditions.pop(index)

    def update_condition_field(self, index: int, field: str) -> None:
        if 0 <= index < len(self.conditions):
            self.conditions[index]["field"] = field

    def update_condition_operator(self, index: int, operator: str) -> None:
        if 0 <= index < len(self.conditions):
            self.conditions[index]["operator"] = operator

    def update_condition_value(self, index: int, value: str) -> None:
        if 0 <= index < len(self.conditions):
            self.conditions[index]["value"] = value

    def save_conditions(self) -> None:
        """Save conditions for the currently editing category."""
        if not self.editing_category:
            return

        # Validate non-empty values
        for cond in self.conditions:
            if not cond.get("value"):
                self.error = "All conditions must have a value"
                return

        try:
            category = self.editing_category
            existing = rule_service.get_rule_for_category(self.data_dir, category)

            if not self.conditions:
                # No conditions — delete the rule if it exists
                if existing:
                    rule_service.delete_rule(self.data_dir, existing["id"])
                self.stop_editing()
                self.load_rules()
                self.success = f"Conditions cleared for '{category}'"
                return

            from sankash.core.models import Rule, RuleAction
            rule_conditions = [
                RuleCondition(field=c["field"], operator=c["operator"], value=c["value"])
                for c in self.conditions
            ]

            rule = Rule(
                name=category,
                priority=existing.get("priority", 0) if existing else 0,
                is_active=existing.get("is_active", True) if existing else True,
                match_type="any",
                conditions=rule_conditions,
                actions=[RuleAction(action_type="set_category", value=category)],
            )

            if existing:
                rule_service.update_rule(self.data_dir, existing["id"], rule)
            else:
                rule_service.create_rule(self.data_dir, rule)

            self.stop_editing()
            self.load_rules()
            self.success = f"Conditions saved for '{category}'"
        except Exception as e:
            self.error = f"Failed to save conditions: {str(e)}"

    def toggle_rule_active(self, category: str, current_active: bool) -> None:
        """Toggle rule active status."""
        try:
            existing = rule_service.get_rule_for_category(self.data_dir, category)
            if not existing:
                return
            rule = rule_service.parse_rule_from_row(existing)
            rule.is_active = not current_active
            rule_service.update_rule(self.data_dir, existing["id"], rule)
            self.load_rules()
        except Exception as e:
            self.error = f"Failed to toggle rule: {str(e)}"

    def update_rule_priority(self, category: str, new_priority: str) -> None:
        """Update rule priority."""
        try:
            existing = rule_service.get_rule_for_category(self.data_dir, category)
            if not existing:
                return
            rule = rule_service.parse_rule_from_row(existing)
            rule.priority = int(new_priority) if new_priority else 0
            rule_service.update_rule(self.data_dir, existing["id"], rule)
            self.load_rules()
        except Exception as e:
            self.error = f"Failed to update priority: {str(e)}"

    # --- Quick-assign from uncategorized panel ---

    def start_assign(self, payee: str) -> None:
        """Start quick-assign flow for a transaction payee."""
        self.assigning_tx_payee = payee

    def quick_assign_category(self, category_display: str) -> None:
        """Add the payee as a condition to the selected category's rule."""
        if not self.assigning_tx_payee or not category_display:
            return

        try:
            actual_category = self.category_display_map.get(
                category_display, category_display
            )
            condition = RuleCondition(
                field="payee",
                operator="contains",
                value=self.assigning_tx_payee,
            )
            rule_service.add_condition_to_category(self.data_dir, actual_category, condition)
            self.assigning_tx_payee = ""
            self.load_rules()
            self.success = f"Added '{condition.value}' to {actual_category}"
        except Exception as e:
            self.error = f"Failed to assign: {str(e)}"

    def cancel_assign(self) -> None:
        """Cancel quick-assign."""
        self.assigning_tx_payee = ""

    # --- Apply rules ---

    def apply_rules(self) -> None:
        """Apply rules to uncategorized transactions."""
        try:
            count = rule_service.apply_rules_to_uncategorized(self.data_dir)
            self.load_rules()
            self.load_uncategorized()
            self.success = f"Categorized {count} transactions"
        except Exception as e:
            self.error = f"Failed to apply rules: {str(e)}"

    def apply_rules_all(self) -> None:
        """Re-apply all rules (rules dominate, manual fallback preserved)."""
        try:
            count = rule_service.apply_rules_to_all(self.data_dir)
            self.load_rules()
            self.load_uncategorized()
            self.success = f"Re-categorized {count} transactions"
        except Exception as e:
            self.error = f"Failed to apply rules: {str(e)}"

    # --- Export/Import ---

    def export_rules(self) -> rx.Component:
        """Export rules as YAML."""
        try:
            yaml_content = rule_service.export_rules(self.data_dir)
            return rx.download(data=yaml_content, filename="rules.yaml")
        except Exception as e:
            self.error = f"Failed to export rules: {str(e)}"

    async def handle_rules_upload(self, files: list[rx.UploadFile]) -> None:
        """Import rules from YAML."""
        if not files:
            return
        try:
            file = files[0]
            content = (await file.read()).decode("utf-8")
            added, updated = rule_service.import_rules(self.data_dir, content)
            self.load_rules()
            self.load_uncategorized()
            self.success = f"Added {added} rules, updated {updated} existing"
        except Exception as e:
            self.error = f"Failed to import rules: {str(e)}"
