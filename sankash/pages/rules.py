"""Rules management page — one rule per category, inline editing, per-transaction AI."""

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
                        rx.cond(
                            RuleState.rule_sort == "relevance",
                            rx.icon("arrow-down-wide-narrow", size=16),
                            rx.icon("arrow-down-a-z", size=16),
                        ),
                        rx.cond(
                            RuleState.rule_sort == "relevance",
                            "Relevance",
                            "A-Z",
                        ),
                        on_click=RuleState.toggle_rule_sort,
                        size="2",
                        variant="soft",
                    ),
                    content="Toggle sort: relevance or alphabetic",
                ),
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


# --- Per-transaction AI suggestion components ---


def inline_rule_editor() -> rx.Component:
    """Inline rule editor row — used for both manual and AI-suggested rules."""
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                # Confidence badge (only shown for AI suggestions)
                rx.cond(
                    RuleState.ai_suggesting_provider != "manual",
                    rx.badge(
                        RuleState.ai_suggestion_confidence,
                        color_scheme=rx.cond(
                            RuleState.ai_suggestion_confidence == "high",
                            "green",
                            rx.cond(
                                RuleState.ai_suggestion_confidence == "medium",
                                "yellow",
                                "red",
                            ),
                        ),
                        size="1",
                    ),
                ),
                # Category dropdown
                rx.select(
                    RuleState.categories,
                    value=RuleState.ai_suggested_category,
                    on_change=RuleState.update_ai_suggested_category,
                    size="1",
                    placeholder="Category",
                ),
                # Rule pattern: field selector + editable match value
                rx.text("when", size="1", color="gray"),
                rx.select(
                    ["payee", "notes"],
                    value=RuleState.ai_match_field,
                    on_change=RuleState.update_ai_match_field,
                    size="1",
                    width="80px",
                ),
                rx.text("contains", size="1", color="gray"),
                rx.input(
                    value=RuleState.ai_match_value,
                    on_change=RuleState.update_ai_match_value,
                    size="1",
                    width="150px",
                    placeholder="match keyword",
                ),
                # Reasoning tooltip (only shown for AI suggestions)
                rx.cond(
                    RuleState.ai_suggesting_provider != "manual",
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=RuleState.ai_suggestion_reasoning,
                    ),
                ),
                # Create rule (applies to future too)
                rx.tooltip(
                    rx.button(
                        rx.icon("check", size=14),
                        "Create Rule",
                        on_click=RuleState.accept_ai_suggestion,
                        size="1",
                        color_scheme="green",
                    ),
                    content="Create a rule that auto-categorizes future transactions too",
                ),
                # Just this one (no rule)
                rx.tooltip(
                    rx.button(
                        "Just This Once",
                        on_click=RuleState.apply_once,
                        size="1",
                        variant="soft",
                    ),
                    content="Categorize only the current transaction(s), no rule created",
                ),
                # Cancel
                rx.button(
                    rx.icon("x", size=14),
                    on_click=RuleState.reject_ai_suggestion,
                    size="1",
                    variant="ghost",
                    color_scheme="red",
                ),
                spacing="2",
                align="center",
                padding="2",
            ),
            col_span=5,
        ),
        style={"background": "var(--green-2)"},
    )


def inline_ai_error() -> rx.Component:
    """Inline error row for a failed AI suggestion."""
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.callout(
                    RuleState.ai_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    size="1",
                ),
                rx.button(
                    rx.icon("x", size=14),
                    on_click=RuleState.reject_ai_suggestion,
                    size="1",
                    variant="ghost",
                ),
                spacing="2",
                align="center",
            ),
            col_span=5,
        ),
    )


def uncategorized_row(tx: dict) -> rx.Component:
    """Uncategorized transaction row with manual rule creation and per-row AI buttons."""
    is_active = RuleState.ai_suggesting_tx_id == tx["id"]

    return rx.fragment(
        rx.table.row(
            rx.table.cell(rx.text(tx["date"], size="1"), white_space="nowrap"),
            rx.table.cell(rx.text(tx["payee"], size="2")),
            rx.table.cell(rx.text(tx["amount"], size="2"), white_space="nowrap"),
            rx.table.cell(rx.text(tx["notes"], size="1", color="gray")),
            # Action buttons: manual rule + AI providers
            rx.table.cell(
                rx.hstack(
                    rx.tooltip(
                        rx.button(
                            rx.icon("plus", size=14),
                            on_click=lambda: RuleState.start_manual_rule(
                                tx["payee"], tx["id"]
                            ),
                            size="1",
                            variant="ghost",
                        ),
                        content="Create rule manually",
                    ),
                    rx.tooltip(
                        rx.button(
                            rx.icon("smartphone", size=14),
                            on_click=lambda: RuleState.request_ai_suggestion(
                                tx["payee"], "apfel", tx["id"]
                            ),
                            size="1",
                            variant="ghost",
                            loading=is_active
                            & (RuleState.ai_suggesting_provider == "apfel")
                            & RuleState.ai_loading,
                        ),
                        content="Suggest via Apfel (local)",
                    ),
                    rx.tooltip(
                        rx.button(
                            rx.icon("globe", size=14),
                            on_click=lambda: RuleState.request_ai_suggestion(
                                tx["payee"], "openrouter", tx["id"]
                            ),
                            size="1",
                            variant="ghost",
                            loading=is_active
                            & (RuleState.ai_suggesting_provider == "openrouter")
                            & RuleState.ai_loading,
                        ),
                        content="Suggest via OpenRouter",
                    ),
                    spacing="1",
                ),
            ),
        ),
        # Inline rule editor (shown when active and not loading, no error)
        rx.cond(
            is_active & ~RuleState.ai_loading & (RuleState.ai_error == ""),
            inline_rule_editor(),
        ),
        # Inline error (shown when active and not loading, has error)
        rx.cond(
            is_active & ~RuleState.ai_loading & (RuleState.ai_error != ""),
            inline_ai_error(),
        ),
    )


def uncategorized_panel() -> rx.Component:
    """Panel showing uncategorized transactions with per-row AI buttons."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("circle-alert", size=18, color="orange"),
                rx.heading("Uncategorized", size="4"),
                rx.badge(RuleState.uncategorized_count, color_scheme="orange", variant="soft"),
                rx.spacer(),
                rx.cond(
                    RuleState.apfel_running,
                    rx.badge(
                        rx.icon("smartphone", size=12),
                        "Apfel running",
                        color_scheme="green",
                        variant="soft",
                    ),
                    rx.tooltip(
                        rx.button(
                            rx.icon("smartphone", size=14),
                            "Start Apfel",
                            on_click=RuleState.start_apfel,
                            size="1",
                            variant="soft",
                        ),
                        content="Start local Apfel server for on-device AI",
                    ),
                ),
                spacing="2",
                align="center",
                width="100%",
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
    on_load=[RuleState.load_rules, RuleState.load_categories, RuleState.load_uncategorized, RuleState.check_apfel_status],
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
