"""Rules management page — one rule per category, inline editing."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.rule_state import RuleState


def condition_item(condition: dict, index: int) -> rx.Component:
    """Single condition row in the inline editor."""
    return rx.hstack(
        rx.select(
            ["payee", "amount", "notes"],
            value=condition["field"],
            on_change=lambda val: RuleState.update_condition_field(index, val),
            size="1",
        ),
        rx.select(
            ["contains", "equals", "<", ">"],
            value=condition["operator"],
            on_change=lambda val: RuleState.update_condition_operator(index, val),
            size="1",
        ),
        rx.input(
            placeholder="Value",
            value=condition["value"],
            on_change=lambda val: RuleState.update_condition_value(index, val),
            size="1",
            flex="1",
        ),
        rx.button(
            rx.icon("trash-2", size=14),
            on_click=lambda: RuleState.remove_condition(index),
            size="1",
            variant="ghost",
            color_scheme="red",
        ),
        spacing="2",
        width="100%",
        align="center",
    )


def inline_editor() -> rx.Component:
    """Inline condition editor that appears below the editing row."""
    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.hstack(
                    rx.text("Editing conditions", size="2", weight="bold"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("plus", size=14),
                        "Add",
                        on_click=RuleState.add_condition,
                        size="1",
                        variant="soft",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.cond(
                    RuleState.conditions.length() == 0,
                    rx.text("No conditions. Add one or save to clear.", color="gray", size="2"),
                    rx.vstack(
                        rx.foreach(
                            RuleState.conditions,
                            lambda cond, idx: condition_item(cond, idx),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                rx.hstack(
                    rx.button(
                        "Save",
                        on_click=RuleState.save_conditions,
                        size="1",
                        color_scheme="green",
                    ),
                    rx.button(
                        "Cancel",
                        on_click=RuleState.stop_editing,
                        size="1",
                        variant="soft",
                    ),
                    spacing="2",
                ),
                spacing="3",
                width="100%",
                padding="3",
            ),
            col_span=6,
        ),
        style={"background": "var(--gray-2)"},
    )


def category_rule_row(cat_rule: dict) -> rx.Component:
    """Row for a category in the rules table."""
    is_editing = RuleState.editing_category == cat_rule["category"]

    return rx.fragment(
        rx.table.row(
            rx.table.cell(
                rx.badge(cat_rule["display_name"], color_scheme="blue", variant="soft"),
            ),
            rx.table.cell(
                rx.cond(
                    cat_rule["has_conditions"],
                    rx.text(cat_rule["condition_text"], size="2"),
                    rx.text("No conditions", size="2", color="gray"),
                ),
            ),
            rx.table.cell(
                rx.cond(
                    cat_rule["has_conditions"],
                    rx.badge(str(cat_rule["match_count"]), color_scheme="blue", variant="soft"),
                    rx.text("-", color="gray", size="2"),
                ),
            ),
            rx.table.cell(
                rx.cond(
                    cat_rule["has_conditions"],
                    rx.switch(
                        checked=cat_rule["is_active"],
                        on_change=lambda _: RuleState.toggle_rule_active(
                            cat_rule["category"], cat_rule["is_active"]
                        ),
                    ),
                    rx.text("-", color="gray", size="2"),
                ),
            ),
            rx.table.cell(
                rx.cond(
                    cat_rule["has_conditions"],
                    rx.input(
                        type="number",
                        value=str(cat_rule["priority"]),
                        on_blur=lambda val: RuleState.update_rule_priority(
                            cat_rule["category"], val
                        ),
                        width="60px",
                        size="1",
                    ),
                    rx.text("-", color="gray", size="2"),
                ),
            ),
            rx.table.cell(
                rx.tooltip(
                    rx.button(
                        rx.cond(
                            cat_rule["has_conditions"],
                            rx.icon("pencil", size=16),
                            rx.icon("plus", size=16),
                        ),
                        on_click=lambda: RuleState.start_editing(cat_rule["category"]),
                        size="1",
                        variant="soft",
                    ),
                    content=rx.cond(
                        cat_rule["has_conditions"],
                        "Edit conditions",
                        "Add conditions",
                    ),
                ),
            ),
        ),
        rx.cond(is_editing, inline_editor()),
    )


def rules_table() -> rx.Component:
    """Rules table — one row per category."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Category Rules", size="5"),
                rx.spacer(),
                rx.tooltip(
                    rx.button(
                        rx.icon("download", size=16),
                        "Export",
                        on_click=RuleState.export_rules,
                        size="2",
                        variant="soft",
                    ),
                    content="Export rules as YAML",
                ),
                rx.upload(
                    rx.tooltip(
                        rx.button(
                            rx.icon("upload", size=16),
                            "Import",
                            size="2",
                            variant="soft",
                        ),
                        content="Import rules from YAML",
                    ),
                    id="rules_upload",
                    accept={".yaml": ["application/x-yaml"], ".yml": ["application/x-yaml"]},
                    on_drop=RuleState.handle_rules_upload,
                    no_drag=True,
                    border="none",
                    padding="0",
                ),
                rx.tooltip(
                    rx.button(
                        "Apply to Uncategorized",
                        on_click=RuleState.apply_rules,
                        size="2",
                        color_scheme="green",
                    ),
                    content="Apply rules to uncategorized transactions",
                ),
                rx.tooltip(
                    rx.button(
                        "Apply to All",
                        on_click=RuleState.apply_rules_all,
                        size="2",
                        color_scheme="blue",
                    ),
                    content="Re-apply all rules (rules dominate, manual preserved as fallback)",
                ),
                width="100%",
                align="center",
                spacing="2",
            ),
            # Messages
            rx.cond(
                RuleState.error != "",
                rx.callout(RuleState.error, icon="triangle_alert", color_scheme="red", size="1"),
            ),
            rx.cond(
                RuleState.success != "",
                rx.callout(RuleState.success, icon="check", color_scheme="green", size="1"),
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Category"),
                        rx.table.column_header_cell("Conditions"),
                        rx.table.column_header_cell("Matches"),
                        rx.table.column_header_cell("Active"),
                        rx.table.column_header_cell("Priority"),
                        rx.table.column_header_cell(""),
                    ),
                ),
                rx.table.body(rx.foreach(RuleState.category_rules, category_rule_row)),
            ),
            spacing="3",
            width="100%",
        ),
    )


def uncategorized_row(tx: dict) -> rx.Component:
    """Uncategorized transaction row with quick-assign."""
    is_assigning = RuleState.assigning_tx_payee == tx["payee"]

    return rx.table.row(
        rx.table.cell(rx.text(tx["date"], size="1"), white_space="nowrap"),
        rx.table.cell(
            rx.text(tx["payee"], size="2"),
        ),
        rx.table.cell(rx.text(tx["amount"], size="2"), white_space="nowrap"),
        rx.table.cell(
            rx.text(
                tx["notes"],
                size="1",
                color="gray",
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_assigning,
                rx.hstack(
                    rx.select(
                        RuleState.categories,
                        placeholder="Category",
                        on_change=RuleState.quick_assign_category,
                        size="1",
                    ),
                    rx.button(
                        rx.icon("x", size=14),
                        on_click=RuleState.cancel_assign,
                        size="1",
                        variant="ghost",
                    ),
                    spacing="1",
                ),
                rx.tooltip(
                    rx.button(
                        rx.icon("plus", size=14),
                        on_click=lambda: RuleState.start_assign(tx["payee"]),
                        size="1",
                        variant="ghost",
                    ),
                    content="Assign to category",
                ),
            ),
        ),
    )


def uncategorized_panel() -> rx.Component:
    """Panel showing uncategorized transactions."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("circle-alert", size=18, color="orange"),
                rx.heading("Uncategorized", size="4"),
                rx.badge(RuleState.uncategorized_count, color_scheme="orange", variant="soft"),
                spacing="2",
                align="center",
            ),
            rx.cond(
                RuleState.uncategorized_count == 0,
                rx.text("All transactions are categorized!", color="green", size="2"),
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Date"),
                                rx.table.column_header_cell("Payee"),
                                rx.table.column_header_cell("Amount"),
                                rx.table.column_header_cell("Notes"),
                                rx.table.column_header_cell(""),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(RuleState.uncategorized_transactions, uncategorized_row),
                        ),
                        size="1",
                        width="100%",
                    ),
                    max_height="400px",
                    overflow_y="auto",
                    width="100%",
                ),
            ),
            spacing="3",
            width="100%",
        ),
    )


@rx.page(
    route="/rules",
    on_load=[RuleState.load_rules, RuleState.load_categories, RuleState.load_uncategorized],
)
def rules_page() -> rx.Component:
    """Rules page."""
    return layout(
        rx.vstack(
            rx.heading("Rules Management", size="8"),
            rx.text(
                "Each category can have conditions to auto-match transactions",
                color="gray",
                size="3",
            ),
            rx.divider(),
            uncategorized_panel(),
            rules_table(),
            spacing="4",
            width="100%",
        ),
    )
