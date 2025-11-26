"""Rules management page."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.rule_state import RuleState


def condition_item(condition: dict, index: int) -> rx.Component:
    """Single condition row with field, operator, value, and remove button."""
    return rx.hstack(
        rx.select(
            ["payee", "amount", "notes"],
            value=condition["field"],
            on_change=lambda val: RuleState.update_condition_field(index, val),
            size="2",
        ),
        rx.select(
            ["contains", "equals", "<", ">"],
            value=condition["operator"],
            on_change=lambda val: RuleState.update_condition_operator(index, val),
            size="2",
        ),
        rx.input(
            placeholder="Value",
            value=condition["value"],
            on_change=lambda val: RuleState.update_condition_value(index, val),
            size="2",
            flex="1",
        ),
        rx.tooltip(
            rx.button(
                rx.icon("trash-2", size=16),
                on_click=lambda: RuleState.remove_condition(index),
                size="1",
                variant="ghost",
                color_scheme="red",
            ),
            content="Remove this condition",
        ),
        spacing="2",
        width="100%",
        align="center",
    )


def rule_form() -> rx.Component:
    """Rule creation form (functional component)."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading(
                    rx.cond(
                        RuleState.editing_id != None,
                        "Edit Rule",
                        "Create New Rule"
                    ),
                    size="4"
                ),
                rx.spacer(),
                rx.cond(
                    RuleState.editing_id != None,
                    rx.button(
                        "Cancel",
                        on_click=RuleState.clear_form,
                        size="2",
                        variant="soft",
                    ),
                ),
                width="100%",
                align="center",
            ),
            # Rule name
            rx.vstack(
                rx.text("Rule Name", size="2", weight="bold"),
                rx.input(
                    placeholder="e.g., Groceries at Walmart",
                    value=RuleState.form_name,
                    on_change=RuleState.set_form_name,
                    width="100%",
                ),
                spacing="1",
                width="100%",
            ),
            # Match type selector
            rx.divider(),
            rx.vstack(
                rx.hstack(
                    rx.icon("git-branch", size=18),
                    rx.text("Match Type", size="3", weight="bold"),
                    spacing="2",
                    align="center",
                ),
                rx.radio(
                    ["all", "any"],
                    value=RuleState.form_match_type,
                    on_change=RuleState.set_form_match_type,
                    direction="row",
                ),
                rx.text(
                    rx.cond(
                        RuleState.form_match_type == "all",
                        "Match ALL conditions (AND logic)",
                        "Match ANY condition (OR logic)",
                    ),
                    size="1",
                    color="gray",
                ),
                spacing="2",
                width="100%",
            ),
            # Conditions section
            rx.divider(),
            rx.vstack(
                rx.hstack(
                    rx.icon("filter", size=18),
                    rx.text("Conditions", size="3", weight="bold"),
                    rx.spacer(),
                    rx.tooltip(
                        rx.button(
                            rx.icon("plus", size=16),
                            "Add Condition",
                            on_click=RuleState.add_condition,
                            size="2",
                            variant="soft",
                        ),
                        content="Add a new condition to this rule",
                    ),
                    spacing="2",
                    align="center",
                    width="100%",
                ),
                # List of conditions
                rx.cond(
                    RuleState.conditions.length() == 0,
                    rx.text("No conditions yet. Add one to get started!", color="gray", size="2"),
                    rx.vstack(
                        rx.foreach(
                            RuleState.conditions,
                            lambda cond, idx: condition_item(cond, idx),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            # Action section
            rx.divider(),
            rx.vstack(
                rx.hstack(
                    rx.icon("zap", size=18),
                    rx.text("Action", size="3", weight="bold"),
                    spacing="2",
                    align="center",
                ),
                rx.hstack(
                    rx.select(
                        ["set_category"],
                        value=RuleState.action_type,
                        on_change=RuleState.set_action_type,
                        size="2",
                    ),
                    rx.select(
                        RuleState.categories,
                        placeholder="Select Category",
                        value=RuleState.action_value,
                        on_change=RuleState.set_action_value,
                        size="2",
                        flex="1",
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            # Messages
            rx.cond(
                RuleState.error != "",
                rx.callout(
                    RuleState.error,
                    icon="triangle_alert",
                    color_scheme="red",
                    size="1",
                ),
            ),
            rx.cond(
                RuleState.success != "",
                rx.callout(
                    RuleState.success,
                    icon="check",
                    color_scheme="green",
                    size="1",
                ),
            ),
            # Submit
            rx.button(
                rx.icon("plus", size=18),
                rx.cond(
                    RuleState.editing_id != None,
                    "Update Rule",
                    "Create Rule"
                ),
                on_click=RuleState.create_rule,
                size="3",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )


def rule_row(rule: dict) -> rx.Component:
    """Rule table row (functional component)."""
    return rx.table.row(
        rx.table.cell(rule["name"]),
        rx.table.cell(rule.get("condition_text", "-"), max_width="300px"),
        rx.table.cell(rule.get("action_text", "-")),
        rx.table.cell(
            rx.badge(
                str(rule.get("match_count", 0)),
                color_scheme="blue",
                variant="soft",
            )
        ),
        rx.table.cell(
            rx.tooltip(
                rx.switch(
                    checked=rule["is_active"],
                    on_change=lambda _: RuleState.toggle_rule_active(
                        rule["id"], rule["is_active"]
                    ),
                ),
                content="Enable or disable this rule",
            )
        ),
        rx.table.cell(
            rx.tooltip(
                rx.input(
                    type="number",
                    value=str(rule["priority"]),
                    on_blur=lambda val: RuleState.update_rule_priority(rule["id"], val),
                    width="60px",
                    size="1",
                ),
                content="Higher priority rules are applied first",
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.button(
                        rx.icon("pencil", size=16),
                        on_click=lambda: RuleState.edit_rule(rule["id"]),
                        size="1",
                        variant="soft",
                    ),
                    content="Edit this rule",
                ),
                rx.tooltip(
                    rx.button(
                        rx.icon("test-tube", size=16),
                        on_click=lambda: RuleState.test_rule(rule["id"]),
                        size="1",
                        variant="soft",
                        color_scheme="blue",
                    ),
                    content="Test rule against recent transactions",
                ),
                rx.tooltip(
                    rx.button(
                        rx.icon("trash-2", size=16),
                        on_click=lambda: RuleState.delete_rule(rule["id"]),
                        size="1",
                        variant="soft",
                        color_scheme="red",
                    ),
                    content="Delete this rule",
                ),
                spacing="1",
            )
        ),
    )


def rules_table() -> rx.Component:
    """Rules table (functional component)."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Rules", size="5"),
                rx.spacer(),
                rx.tooltip(
                    rx.button(
                        "Apply Rules to Uncategorized",
                        on_click=RuleState.apply_rules,
                        size="2",
                        color_scheme="green",
                    ),
                    content="Apply all active rules to uncategorized transactions",
                ),
                width="100%",
                align="center",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Name"),
                        rx.table.column_header_cell("Conditions"),
                        rx.table.column_header_cell("Action"),
                        rx.table.column_header_cell("Matches"),
                        rx.table.column_header_cell("Active"),
                        rx.table.column_header_cell("Priority"),
                        rx.table.column_header_cell("Actions"),
                    ),
                ),
                rx.table.body(rx.foreach(RuleState.rules, rule_row)),
            ),
            spacing="3",
            width="100%",
        ),
    )


@rx.page(route="/rules", on_load=[RuleState.load_rules, RuleState.load_categories])
def rules_page() -> rx.Component:
    """Rules page."""
    return layout(
        rx.vstack(
            rx.heading("Rules Management", size="8"),
            rx.text("Create and manage categorization rules", color="gray", size="3"),
            rx.divider(),
            rx.grid(
                rule_form(),
                rules_table(),
                columns="1",
                spacing="4",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
    )
