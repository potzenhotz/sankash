"""Transactions management page."""

import reflex as rx

from sankash.components.layout import layout
from sankash.pages.rules import inline_rule_editor
from sankash.state.rule_state import RuleState
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


def transaction_row(transaction: dict) -> rx.Component:
    """Transaction table row plus the inline rule editor when opened for it."""
    return rx.fragment(transaction_cells(transaction), rx.cond(
        (RuleState.ai_suggesting_tx_id == transaction["id"]) & (RuleState.ai_suggesting_provider == "manual"),
        inline_rule_editor(col_span=9, on_done=[TransactionState.load_transactions]),
    ))


def transaction_cells(transaction: dict) -> rx.Component:
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
        rx.table.cell(
            rx.hstack(
                rx.text(transaction["payee"]),
                rx.cond(
                    transaction.get("parent_id"),
                    rx.badge("Split", color_scheme="orange", size="1"),
                ),
                spacing="1",
                align="center",
            ),
        ),
        rx.table.cell(transaction.get("notes", "-")),
        rx.table.cell(
            rx.text(
                f"\u20ac{transaction['amount']:.2f}",
                weight="medium",
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.select(
                    TransactionState.categories,
                    value=transaction["category_display"],
                    placeholder="Uncategorized",
                    on_change=lambda cat: TransactionState.update_category(
                        transaction["id"], cat
                    ),
                    size="1",
                ),
                rx.cond(
                    transaction["category_source"] == "manual",
                    rx.tooltip(
                        rx.icon_button(
                            rx.icon("rotate-ccw", size=14),
                            on_click=lambda: TransactionState.reset_category(transaction["id"]),
                            size="1",
                            variant="ghost",
                            aria_label="Reset to rule",
                        ),
                        content="Manually set. Click to let rules decide again",
                    ),
                ),
                spacing="1",
                align="center",
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
        # Wand button: opens the shared inline rule editor
        rx.table.cell(
            rx.tooltip(
                rx.button(
                    rx.icon("wand-sparkles", size=16),
                    on_click=lambda: RuleState.start_manual_rule(transaction),
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
    on_load=[
        TransactionState.load_categories,
        TransactionState.load_transactions,
        RuleState.load_categories,
        RuleState.load_uncategorized,
    ],
)
def transactions_page() -> rx.Component:
    """Transactions page."""
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Transaction Management", size="8"),
                rx.spacer(),
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
            rx.divider(),
            search_bar(),
            transaction_filters(),
            rx.cond(
                TransactionState.selected_ids.length() > 0,
                bulk_actions(),
            ),
            transactions_table(),
            pagination_controls(),
            spacing="4",
            width="100%",
        ),
        delete_all_transactions_dialog(),
    )
