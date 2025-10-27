"""Rules page state management."""

import reflex as rx

from sankash.core.models import Rule, RuleAction, RuleCondition
from sankash.services import rule_service
from sankash.state.base import BaseState


class RuleState(BaseState):
    """State for rules management page."""

    rules: list[dict] = []
    loading: bool = False
    error: str = ""
    success: str = ""

    # Form fields
    form_name: str = ""
    form_priority: str = "0"  # Keep as string for input compatibility
    form_is_active: bool = True

    # Condition fields
    condition_field: str = "payee"
    condition_operator: str = "contains"
    condition_value: str = ""

    # Action fields
    action_type: str = "set_category"
    action_value: str = ""

    # Test results
    test_results: list[dict] = []
    show_test_results: bool = False

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

                # Add formatted text
                rule["condition_text"] = f"{conditions[0]['field']} {conditions[0]['operator']} '{conditions[0]['value']}'" if conditions else "-"
                rule["action_text"] = f"{actions[0]['action_type']}: {actions[0]['value']}" if actions else "-"

            self.rules = rules_list
        except Exception as e:
            self.error = f"Failed to load rules: {str(e)}"
        finally:
            self.loading = False

    def create_rule(self) -> None:
        """Create new rule from form data."""
        if not self.form_name or not self.condition_value or not self.action_value:
            self.error = "Please fill in all fields"
            return

        try:
            rule = Rule(
                name=self.form_name,
                priority=int(self.form_priority) if self.form_priority else 0,
                is_active=self.form_is_active,
                conditions=[
                    RuleCondition(
                        field=self.condition_field,
                        operator=self.condition_operator,
                        value=self.condition_value,
                    )
                ],
                actions=[
                    RuleAction(
                        action_type=self.action_type,
                        value=self.action_value,
                    )
                ],
            )

            rule_service.create_rule(self.db_path, rule)
            self.success = f"Rule '{self.form_name}' created successfully"
            self.clear_form()
            self.load_rules()
        except Exception as e:
            self.error = f"Failed to create rule: {str(e)}"

    def delete_rule(self, rule_id: int) -> None:
        """Delete a rule."""
        try:
            rule_service.delete_rule(self.db_path, rule_id)
            self.success = "Rule deleted successfully"
            self.load_rules()
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

    def apply_rules(self) -> None:
        """Apply all active rules to uncategorized transactions."""
        try:
            count = rule_service.apply_rules_to_uncategorized(self.db_path)
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
        self.form_priority = "0"
        self.form_is_active = True
        self.condition_field = "payee"
        self.condition_operator = "contains"
        self.condition_value = ""
        self.action_type = "set_category"
        self.action_value = ""
        self.error = ""
        self.success = ""
