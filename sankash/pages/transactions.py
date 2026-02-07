"""Transactions management page."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.transaction_state import TransactionState


def search_bar() -> rx.Component:
    """Quick search bar for transactions."""
    return rx.card(
        rx.hstack(
            rx.icon("search", size=20),
            rx.input(
                placeholder="Search transactions (payee, notes, category)...",
                value=TransactionState.search_query,
                on_change=TransactionState.set_search_query,
                on_blur=TransactionState.apply_search,
                width="100%",
            ),
            rx.cond(
                TransactionState.search_query != "",
                rx.button(
                    rx.icon("x", size=16),
                    on_click=TransactionState.clear_search,
                    size="2",
                    variant="soft",
                ),
            ),
            spacing="2",
            width="100%",
            align="center",
        ),
    )


def transaction_filters() -> rx.Component:
    """Transaction filter controls (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Filters", size="4"),
            rx.hstack(
                rx.input(
                    type="date",
                    value=TransactionState.filter_start_date,
                    on_change=TransactionState.set_filter_start_date,
                    placeholder="Start Date",
                ),
                rx.input(
                    type="date",
                    value=TransactionState.filter_end_date,
                    on_change=TransactionState.set_filter_end_date,
                    placeholder="End Date",
                ),
                rx.button(
                    "Last 30 Days",
                    on_click=TransactionState.set_last_30_days,
                    size="2",
                    variant="soft",
                ),
                spacing="2",
                width="100%",
            ),
            rx.hstack(
                rx.input(
                    type="number",
                    value=TransactionState.filter_min_amount,
                    on_change=TransactionState.set_filter_min_amount,
                    placeholder="Min Amount",
                ),
                rx.input(
                    type="number",
                    value=TransactionState.filter_max_amount,
                    on_change=TransactionState.set_filter_max_amount,
                    placeholder="Max Amount",
                ),
                spacing="2",
                width="100%",
            ),
            rx.hstack(
                rx.checkbox(
                    "Show uncategorized only",
                    checked=TransactionState.filter_uncategorized_only,
                    on_change=TransactionState.set_filter_uncategorized_only,
                ),
                rx.spacer(),
                rx.button(
                    "Apply Filters",
                    on_click=TransactionState.apply_filters,
                    size="2",
                ),
                rx.button(
                    "Clear",
                    on_click=TransactionState.clear_filters,
                    size="2",
                    variant="soft",
                ),
                spacing="2",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )


def bulk_actions() -> rx.Component:
    """Bulk action controls (functional component)."""
    return rx.card(
        rx.hstack(
            rx.text(
                f"Selected: {TransactionState.selected_ids.length()}",
                size="2",
                weight="bold",
            ),
            rx.spacer(),
            rx.select(
                TransactionState.categories,
                placeholder="Select Category",
                value=TransactionState.bulk_category,
                on_change=TransactionState.set_bulk_category,
            ),
            rx.button(
                "Apply to Selected",
                on_click=TransactionState.bulk_update_categories,
                size="2",
                disabled=TransactionState.selected_ids.length() == 0,
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
    )


# --- Rule Dialog Components ---


def rule_dialog_condition_item(condition: dict, index: int) -> rx.Component:
    """Single condition row in the rule creation dialog."""
    return rx.hstack(
        rx.select(
            ["payee", "amount", "notes"],
            value=condition["field"],
            on_change=lambda val: TransactionState.rule_update_condition_field(index, val),
            size="2",
        ),
        rx.select(
            ["contains", "equals", "<", ">"],
            value=condition["operator"],
            on_change=lambda val: TransactionState.rule_update_condition_operator(index, val),
            size="2",
        ),
        rx.input(
            placeholder="Value",
            value=condition["value"],
            on_change=lambda val: TransactionState.rule_update_condition_value(index, val),
            size="2",
            flex="1",
        ),
        rx.button(
            rx.icon("trash-2", size=16),
            on_click=lambda: TransactionState.rule_remove_condition(index),
            size="1",
            variant="ghost",
            color_scheme="red",
        ),
        spacing="2",
        width="100%",
        align="center",
    )


def create_rule_dialog() -> rx.Component:
    """Dialog for creating a rule from a transaction."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Create Rule from Transaction"),
            rx.dialog.description(
                "Pre-filled from the selected transaction. Edit as needed.",
                size="2",
                color="gray",
            ),
            rx.vstack(
                # Rule name
                rx.vstack(
                    rx.text("Rule Name", size="2", weight="bold"),
                    rx.input(
                        value=TransactionState.rule_form_name,
                        on_change=TransactionState.set_rule_form_name,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Match type
                rx.vstack(
                    rx.text("Match Type", size="2", weight="bold"),
                    rx.radio(
                        ["all", "any"],
                        value=TransactionState.rule_form_match_type,
                        on_change=TransactionState.set_rule_form_match_type,
                        direction="row",
                    ),
                    rx.text(
                        rx.cond(
                            TransactionState.rule_form_match_type == "all",
                            "Match ALL conditions (AND logic)",
                            "Match ANY condition (OR logic)",
                        ),
                        size="1",
                        color="gray",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Conditions
                rx.vstack(
                    rx.hstack(
                        rx.text("Conditions", size="2", weight="bold"),
                        rx.spacer(),
                        rx.button(
                            rx.icon("plus", size=14),
                            "Add",
                            on_click=TransactionState.rule_add_condition,
                            size="1",
                            variant="soft",
                        ),
                        width="100%",
                        align="center",
                    ),
                    rx.foreach(
                        TransactionState.rule_form_conditions,
                        lambda cond, idx: rule_dialog_condition_item(cond, idx),
                    ),
                    spacing="2",
                    width="100%",
                ),
                # Action
                rx.vstack(
                    rx.text("Category", size="2", weight="bold"),
                    rx.select(
                        TransactionState.categories,
                        placeholder="Select Category",
                        value=TransactionState.rule_form_action_value,
                        on_change=TransactionState.set_rule_form_action_value,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Error message
                rx.cond(
                    TransactionState.rule_form_error != "",
                    rx.callout(
                        TransactionState.rule_form_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        size="1",
                    ),
                ),
                # Buttons
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                        ),
                    ),
                    rx.button(
                        rx.icon("plus", size=16),
                        "Create Rule",
                        on_click=TransactionState.submit_rule_from_dialog,
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
                padding_top="16px",
            ),
        ),
        open=TransactionState.show_rule_dialog,
        on_open_change=TransactionState.handle_rule_dialog_open_change,
    )


# --- AI Suggestions Components ---


def suggestion_row(suggestion: dict, index: int) -> rx.Component:
    """Single suggestion row in the AI suggestions panel."""
    return rx.hstack(
        # Approve/reject toggle
        rx.button(
            rx.cond(
                suggestion["approved"],
                rx.icon("check", size=16),
                rx.icon("x", size=16),
            ),
            on_click=lambda: TransactionState.toggle_suggestion_approval(index),
            size="1",
            variant=rx.cond(suggestion["approved"], "solid", "outline"),
            color_scheme=rx.cond(suggestion["approved"], "green", "red"),
        ),
        # Payee + notes
        rx.vstack(
            rx.text(suggestion["payee"], size="2", weight="bold"),
            rx.cond(
                suggestion.get("notes_sample", "") != "",
                rx.text(suggestion["notes_sample"], size="1", color="gray"),
            ),
            spacing="1",
            flex="1",
        ),
        # Category dropdown
        rx.select(
            TransactionState.categories,
            value=suggestion["suggested_category"],
            on_change=lambda val: TransactionState.update_suggestion_category(index, val),
            size="2",
        ),
        # Confidence badge
        rx.badge(
            suggestion["confidence"],
            color_scheme=rx.cond(
                suggestion["confidence"] == "high",
                "green",
                rx.cond(
                    suggestion["confidence"] == "medium",
                    "yellow",
                    "red",
                ),
            ),
            size="1",
        ),
        # Reasoning tooltip
        rx.tooltip(
            rx.icon("info", size=14, color="gray"),
            content=suggestion.get("reasoning", ""),
        ),
        spacing="3",
        width="100%",
        align="center",
        padding="8px",
    )


def ai_suggestions_panel() -> rx.Component:
    """Panel showing AI-generated category suggestions."""
    return rx.cond(
        TransactionState.show_suggestions,
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("sparkles", size=20),
                    rx.heading("AI Suggestions", size="4"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=16),
                        on_click=TransactionState.dismiss_suggestions,
                        size="1",
                        variant="ghost",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.cond(
                    TransactionState.llm_error != "",
                    rx.callout(
                        TransactionState.llm_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        size="1",
                    ),
                ),
                rx.vstack(
                    rx.foreach(
                        TransactionState.llm_suggestions,
                        lambda s, idx: suggestion_row(s, idx),
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("check", size=16),
                        "Create Rules from Approved",
                        on_click=TransactionState.create_rules_from_suggestions,
                        color_scheme="green",
                    ),
                    rx.button(
                        "Dismiss",
                        on_click=TransactionState.dismiss_suggestions,
                        variant="soft",
                        color_scheme="gray",
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
        ),
    )


# --- Transaction Table ---


def transaction_row(transaction: dict) -> rx.Component:
    """Transaction table row (functional component)."""
    return rx.table.row(
        rx.table.cell(
            rx.checkbox(
                on_change=lambda: TransactionState.toggle_selection(transaction["id"]),
            )
        ),
        rx.table.cell(
            rx.text(
                transaction["date"],
                size="2",
                weight="medium",
            ),
            min_width="110px",
        ),
        rx.table.cell(transaction["payee"]),
        rx.table.cell(transaction.get("notes", "-")),
        rx.table.cell(
            rx.text(
                f"\u20ac{transaction['amount']:.2f}",
                weight="medium",
            )
        ),
        rx.table.cell(
            rx.cond(
                transaction["is_categorized"],
                rx.badge(
                    transaction.get("category_display", transaction["category"]),
                    color_scheme="blue"
                ),
                rx.select(
                    TransactionState.categories,
                    placeholder="Uncategorized",
                    on_change=lambda cat: TransactionState.update_category(
                        transaction["id"], cat
                    ),
                    size="1",
                ),
            )
        ),
        rx.table.cell(
            rx.cond(
                transaction["is_transfer"],
                rx.badge("Transfer", color_scheme="purple"),
                rx.text("-", color="gray"),
            )
        ),
        rx.table.cell(
            rx.cond(
                transaction["import_filename"],
                rx.badge(
                    transaction["import_filename"],
                    color_scheme="gray",
                    size="1",
                ),
                rx.text("-", color="gray", size="1"),
            )
        ),
        # Wand button for rule creation
        rx.table.cell(
            rx.tooltip(
                rx.button(
                    rx.icon("wand-2", size=16),
                    on_click=lambda: TransactionState.open_rule_dialog(transaction["id"]),
                    size="1",
                    variant="ghost",
                ),
                content="Create rule from this transaction",
            ),
        ),
    )


def transactions_table() -> rx.Component:
    """Transactions table (functional component)."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Transactions", size="5"),
                rx.spacer(),
                rx.text(
                    TransactionState.total_count,
                    " transactions",
                    size="2",
                    color="gray",
                ),
                width="100%",
                align="center",
            ),
            rx.cond(
                TransactionState.error != "",
                rx.text(TransactionState.error, color="red", size="2"),
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(""),
                        rx.table.column_header_cell(
                            rx.hstack(
                                rx.text("Date", size="2", weight="bold"),
                                rx.button(
                                    rx.icon(
                                        rx.cond(
                                            (TransactionState.sort_by == "date") & (TransactionState.sort_order == "asc"),
                                            "arrow-up",
                                            "arrow-down",
                                        ),
                                        size=14,
                                    ),
                                    on_click=TransactionState.toggle_sort_by_date,
                                    size="1",
                                    variant="ghost",
                                ),
                                spacing="1",
                                align="center",
                            ),
                        ),
                        rx.table.column_header_cell("Payee"),
                        rx.table.column_header_cell("Notes"),
                        rx.table.column_header_cell(
                            rx.hstack(
                                rx.text("Amount", size="2", weight="bold"),
                                rx.button(
                                    rx.icon(
                                        rx.cond(
                                            (TransactionState.sort_by == "amount") & (TransactionState.sort_order == "asc"),
                                            "arrow-up",
                                            "arrow-down",
                                        ),
                                        size=14,
                                    ),
                                    on_click=TransactionState.toggle_sort_by_amount,
                                    size="1",
                                    variant="ghost",
                                ),
                                spacing="1",
                                align="center",
                            ),
                        ),
                        rx.table.column_header_cell("Category"),
                        rx.table.column_header_cell("Transfer"),
                        rx.table.column_header_cell("Import Source"),
                        rx.table.column_header_cell(""),  # Wand column
                    ),
                ),
                rx.table.body(
                    rx.foreach(TransactionState.transactions, transaction_row)
                ),
            ),
            spacing="3",
            width="100%",
        ),
    )


def pagination_controls() -> rx.Component:
    """Pagination controls for the transactions table."""
    return rx.hstack(
        rx.button(
            rx.icon("chevron-left", size=16),
            "Previous",
            on_click=TransactionState.prev_page,
            disabled=TransactionState.current_page <= 1,
            size="2",
            variant="soft",
        ),
        rx.text(
            "Page ",
            TransactionState.current_page,
            " of ",
            TransactionState.total_pages,
            size="2",
        ),
        rx.button(
            "Next",
            rx.icon("chevron-right", size=16),
            on_click=TransactionState.next_page,
            disabled=TransactionState.current_page >= TransactionState.total_pages,
            size="2",
            variant="soft",
        ),
        justify="center",
        align="center",
        spacing="3",
        width="100%",
    )


def delete_all_transactions_dialog() -> rx.Component:
    """Dialog to confirm deleting all transactions."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Delete All Transactions"),
            rx.dialog.description(
                "This will permanently delete all transactions. "
                "This action cannot be undone.",
                color="red",
            ),
            rx.vstack(
                rx.text("Type 'delete' to confirm:", size="2", weight="bold"),
                rx.input(
                    placeholder="delete",
                    value=TransactionState.delete_all_confirm_text,
                    on_change=TransactionState.set_delete_all_confirm_text,
                    width="100%",
                ),
                rx.cond(
                    TransactionState.error != "",
                    rx.callout(
                        TransactionState.error,
                        icon="triangle_alert",
                        color_scheme="red",
                        size="1",
                    ),
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                        ),
                    ),
                    rx.button(
                        rx.icon("trash-2", size=16),
                        "Delete All",
                        on_click=TransactionState.delete_all_transactions,
                        color_scheme="red",
                        loading=TransactionState.loading,
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
                padding_top="16px",
            ),
        ),
        open=TransactionState.show_delete_all_dialog,
        on_open_change=TransactionState.handle_delete_all_dialog_open_change,
    )


@rx.page(
    route="/transactions",
    on_load=[TransactionState.load_categories, TransactionState.load_transactions],
)
def transactions_page() -> rx.Component:
    """Transactions page."""
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Transaction Management", size="8"),
                rx.spacer(),
                rx.button(
                    rx.icon("play", size=18),
                    "Apply Rules",
                    on_click=TransactionState.apply_rules,
                    loading=TransactionState.loading,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("sparkles", size=18),
                    "AI Suggest Rules",
                    on_click=TransactionState.generate_suggestions,
                    loading=TransactionState.llm_loading,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("trash-2", size=18),
                    "Delete All",
                    on_click=TransactionState.open_delete_all_dialog,
                    size="2",
                    variant="soft",
                    color_scheme="red",
                ),
                width="100%",
                align="center",
            ),
            rx.text("View and categorize your transactions", color="gray", size="3"),
            rx.cond(
                TransactionState.llm_error != "",
                rx.callout(
                    TransactionState.llm_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    size="1",
                ),
            ),
            rx.divider(),
            search_bar(),
            transaction_filters(),
            ai_suggestions_panel(),
            rx.cond(
                TransactionState.selected_ids.length() > 0,
                bulk_actions(),
            ),
            transactions_table(),
            pagination_controls(),
            spacing="4",
            width="100%",
        ),
        create_rule_dialog(),
        delete_all_transactions_dialog(),
    )
