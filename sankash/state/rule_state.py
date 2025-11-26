"""Rules page state management."""

import reflex as rx

from sankash.core.models import Rule, RuleAction, RuleCondition
from sankash.services import rule_service, category_service
from sankash.state.base import BaseState


class RuleState(BaseState):
    """State for rules management page."""

    state_auto_setters = True  # Explicitly enable auto setters

    rules: list[dict] = []
    categories: list[str] = []
    category_display_map: dict[str, str] = {}  # Maps display name -> actual name
    loading: bool = False
    error: str = ""
    success: str = ""

    # Form fields
    form_name: str = ""
    form_match_type: str = "any"  # "all" for AND, "any" for OR

    # Multiple conditions
    conditions: list[dict] = []  # List of {field, operator, value}

    # Action fields
    action_type: str = "set_category"
    action_value: str = ""

    # Test results
    test_results: list[dict] = []
    show_test_results: bool = False

    # Edit mode
    editing_id: int | None = None

    def load_rules(self) -> None:
        """Load all rules."""
        import json

        self.loading = True
        self.error = ""

        try:
            df = rule_service.get_rules(self.db_path, active_only=False)
            rules_list = df.to_dicts()

            # Format conditions and actions for display
            for rule in rules_list:
                conditions = json.loads(rule["conditions"]) if isinstance(rule["conditions"], str) else rule["conditions"]
                actions = json.loads(rule["actions"]) if isinstance(rule["actions"], str) else rule["actions"]

                # Get match_type (default to "any" if not present for backward compatibility)
                match_type = rule.get("match_type", "any")
                rule["match_type"] = match_type

                # Format multiple conditions
                if conditions:
                    match_text = " AND " if match_type == "all" else " OR "
                    condition_parts = [
                        f"{cond['field']} {cond['operator']} '{cond['value']}'"
                        for cond in conditions
                    ]
                    rule["condition_text"] = match_text.join(condition_parts)
                else:
                    rule["condition_text"] = "-"

                # Add formatted action text
                rule["action_text"] = f"{actions[0]['action_type']}: {actions[0]['value']}" if actions else "-"

                # Count matching transactions
                try:
                    parsed_rule = rule_service.parse_rule_from_row(rule)
                    rule["match_count"] = rule_service.count_matching_transactions(self.db_path, parsed_rule)
                except Exception:
                    rule["match_count"] = 0

            self.rules = rules_list
        except Exception as e:
            self.error = f"Failed to load rules: {str(e)}"
        finally:
            self.loading = False

    def load_categories(self) -> None:
        """Load available categories with hierarchical display names."""
        try:
            df = category_service.get_categories(self.db_path)
            categories = df.to_dicts()

            # Build list of display names and mapping
            display_names = []
            display_map = {}

            for cat in categories:
                display_name = category_service.get_category_display_name(
                    self.db_path, cat["name"]
                )
                display_names.append(display_name)
                display_map[display_name] = cat["name"]

            # Sort categories alphabetically
            display_names.sort()

            self.categories = display_names
            self.category_display_map = display_map
        except Exception as e:
            self.error = f"Failed to load categories: {str(e)}"

    def add_condition(self) -> None:
        """Add a new condition to the list."""
        self.conditions.append({
            "field": "payee",
            "operator": "contains",
            "value": ""
        })

    def remove_condition(self, index: int) -> None:
        """Remove a condition by index."""
        if 0 <= index < len(self.conditions):
            self.conditions.pop(index)

    def update_condition_field(self, index: int, field: str) -> None:
        """Update condition field."""
        if 0 <= index < len(self.conditions):
            self.conditions[index]["field"] = field

    def update_condition_operator(self, index: int, operator: str) -> None:
        """Update condition operator."""
        if 0 <= index < len(self.conditions):
            self.conditions[index]["operator"] = operator

    def update_condition_value(self, index: int, value: str) -> None:
        """Update condition value."""
        if 0 <= index < len(self.conditions):
            self.conditions[index]["value"] = value

    def edit_rule(self, rule_id: int) -> None:
        """Load rule data into form for editing."""
        import json

        try:
            # Get the rule
            rules_df = rule_service.get_rules(self.db_path, active_only=False)
            rule_data = rules_df.filter(rules_df["id"] == rule_id).to_dicts()[0]

            # Parse conditions and actions
            conditions = json.loads(rule_data["conditions"]) if isinstance(rule_data["conditions"], str) else rule_data["conditions"]
            actions = json.loads(rule_data["actions"]) if isinstance(rule_data["actions"], str) else rule_data["actions"]

            # Set editing mode
            self.editing_id = rule_id
            self.form_name = rule_data["name"]
            self.form_match_type = rule_data.get("match_type", "all")
            self.conditions = conditions
            self.action_type = actions[0]["action_type"] if actions else "set_category"
            self.action_value = actions[0]["value"] if actions else ""

            # Clear messages
            self.error = ""
            self.success = ""
        except Exception as e:
            self.error = f"Failed to load rule: {str(e)}"

    def create_rule(self) -> None:
        """Create or update rule from form data."""
        if not self.form_name or not self.conditions or not self.action_value:
            self.error = "Please fill in all fields and add at least one condition"
            return

        # Validate that all conditions have values
        for cond in self.conditions:
            if not cond.get("value"):
                self.error = "All conditions must have a value"
                return

        try:
            # Convert display name to actual category name
            actual_category = self.category_display_map.get(
                self.action_value, self.action_value
            )

            # Convert conditions to RuleCondition objects
            rule_conditions = [
                RuleCondition(
                    field=cond["field"],
                    operator=cond["operator"],
                    value=cond["value"]
                )
                for cond in self.conditions
            ]

            rule = Rule(
                name=self.form_name,
                priority=0,  # Default priority, will be editable inline
                is_active=True,  # Default active, will be editable inline
                match_type=self.form_match_type,
                conditions=rule_conditions,
                actions=[
                    RuleAction(
                        action_type=self.action_type,
                        value=actual_category,
                    )
                ],
            )

            rule_name = self.form_name

            if self.editing_id:
                # Update existing rule
                rule_service.update_rule(self.db_path, self.editing_id, rule)
                success_msg = f"Rule '{rule_name}' updated successfully"
            else:
                # Create new rule
                rule_service.create_rule(self.db_path, rule)
                success_msg = f"Rule '{rule_name}' created successfully"

            # Clear form first
            self.clear_form()
            # Reload rules to get updated data
            self.load_rules()
            # Set success message after reload
            self.success = success_msg
        except Exception as e:
            self.error = f"Failed to save rule: {str(e)}"

    def delete_rule(self, rule_id: int) -> None:
        """Delete a rule."""
        try:
            rule_service.delete_rule(self.db_path, rule_id)
            self.load_rules()
            self.success = "Rule deleted successfully"
        except Exception as e:
            self.error = f"Failed to delete rule: {str(e)}"

    def toggle_rule_active(self, rule_id: int, current_active: bool) -> None:
        """Toggle rule active status."""
        try:
            # Get the rule
            rules_df = rule_service.get_rules(self.db_path, active_only=False)
            rule_data = rules_df.filter(rules_df["id"] == rule_id).to_dicts()[0]
            rule = rule_service.parse_rule_from_row(rule_data)

            # Toggle active
            rule.is_active = not current_active

            # Update
            rule_service.update_rule(self.db_path, rule_id, rule)
            self.load_rules()
        except Exception as e:
            self.error = f"Failed to toggle rule: {str(e)}"

    def update_rule_priority(self, rule_id: int, new_priority: str) -> None:
        """Update rule priority."""
        try:
            # Get the rule
            rules_df = rule_service.get_rules(self.db_path, active_only=False)
            rule_data = rules_df.filter(rules_df["id"] == rule_id).to_dicts()[0]
            rule = rule_service.parse_rule_from_row(rule_data)

            # Update priority
            rule.priority = int(new_priority) if new_priority else 0

            # Update
            rule_service.update_rule(self.db_path, rule_id, rule)
            self.load_rules()
        except Exception as e:
            self.error = f"Failed to update priority: {str(e)}"

    def apply_rules(self) -> None:
        """Apply all active rules to uncategorized transactions."""
        try:
            count = rule_service.apply_rules_to_uncategorized(self.db_path)
            # Reload rules to update match counts
            self.load_rules()
            self.success = f"Categorized {count} transactions"
        except Exception as e:
            self.error = f"Failed to apply rules: {str(e)}"

    def test_rule(self, rule_id: int) -> None:
        """Test a rule and show matching transactions."""
        try:
            # Get the rule
            rules_df = rule_service.get_rules(self.db_path, active_only=False)
            rule_data = rules_df.filter(rules_df["id"] == rule_id).to_dicts()[0]
            rule = rule_service.parse_rule_from_row(rule_data)

            # Test rule
            matches_df = rule_service.test_rule(self.db_path, rule, limit=50)
            self.test_results = matches_df.to_dicts() if not matches_df.is_empty() else []
            self.show_test_results = True
        except Exception as e:
            self.error = f"Failed to test rule: {str(e)}"

    def clear_form(self) -> None:
        """Clear form fields."""
        self.form_name = ""
        self.form_match_type = "any"
        self.conditions = []
        self.action_type = "set_category"
        self.action_value = ""
        self.editing_id = None
        self.error = ""
        self.success = ""
