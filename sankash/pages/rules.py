"""Rules management page."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.rule_state import RuleState


def rule_form() -> rx.Component:
    """Rule creation form (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Create New Rule", size="4"),
            # Basic info
            rx.input(
                placeholder="Rule Name",
                value=RuleState.form_name,
                on_change=RuleState.set_form_name,
            ),
            rx.hstack(
                rx.input(
                    type="number",
                    placeholder="Priority",
                    value=RuleState.form_priority,
                    on_change=RuleState.set_form_priority,
                ),
                rx.checkbox(
                    "Active",
                    checked=RuleState.form_is_active,
                    on_change=RuleState.set_form_is_active,
                ),
                spacing="2",
                width="100%",
            ),
            # Condition
            rx.divider(),
            rx.heading("Condition", size="3"),
            rx.hstack(
                rx.select(
                    ["payee", "amount", "notes"],
                    value=RuleState.condition_field,
                    on_change=RuleState.set_condition_field,
                ),
                rx.select(
                    ["contains", "equals", "<", ">"],
                    value=RuleState.condition_operator,
                    on_change=RuleState.set_condition_operator,
                ),
                rx.input(
                    placeholder="Value",
                    value=RuleState.condition_value,
                    on_change=RuleState.set_condition_value,
                ),
                spacing="2",
                width="100%",
            ),
            # Action
            rx.divider(),
            rx.heading("Action", size="3"),
            rx.hstack(
                rx.select(
                    ["set_category"],
                    value=RuleState.action_type,
                    on_change=RuleState.set_action_type,
                ),
                rx.select(
                    RuleState.categories,
                    placeholder="Select Category",
                    value=RuleState.action_value,
                    on_change=RuleState.set_action_value,
                ),
                spacing="2",
                width="100%",
            ),
            # Messages
            rx.cond(
                RuleState.error != "",
                rx.text(RuleState.error, color="red", size="2"),
            ),
            rx.cond(
                RuleState.success != "",
                rx.text(RuleState.success, color="green", size="2"),
            ),
            # Submit
            rx.button(
                "Create Rule",
                on_click=RuleState.create_rule,
                size="3",
            ),
            spacing="3",
            width="100%",
        ),
    )


def rule_row(rule: dict) -> rx.Component:
    """Rule table row (functional component)."""
    return rx.table.row(
        rx.table.cell(rule["name"]),
        rx.table.cell(rule["priority"]),
        rx.table.cell(rule.get("condition_text", "-")),
        rx.table.cell(rule.get("action_text", "-")),
        rx.table.cell(
            rx.cond(
                rule["is_active"],
                rx.badge("Active", color_scheme="green"),
                rx.badge("Inactive", color_scheme="gray"),
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon("play", size=16),
                    on_click=lambda: RuleState.toggle_rule_active(
                        rule["id"], rule["is_active"]
                    ),
                    size="1",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("test-tube", size=16),
                    on_click=lambda: RuleState.test_rule(rule["id"]),
                    size="1",
                    variant="soft",
                    color_scheme="blue",
                ),
                rx.button(
                    rx.icon("trash-2", size=16),
                    on_click=lambda: RuleState.delete_rule(rule["id"]),
                    size="1",
                    variant="soft",
                    color_scheme="red",
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
                rx.button(
                    "Apply Rules to Uncategorized",
                    on_click=RuleState.apply_rules,
                    size="2",
                    color_scheme="green",
                ),
                width="100%",
                align="center",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Name"),
                        rx.table.column_header_cell("Priority"),
                        rx.table.column_header_cell("Condition"),
                        rx.table.column_header_cell("Action"),
                        rx.table.column_header_cell("Status"),
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
