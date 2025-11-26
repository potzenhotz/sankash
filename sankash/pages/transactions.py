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
                on_blur=TransactionState.load_transactions,
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
                    on_click=TransactionState.load_transactions,
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
                f"€{transaction['amount']:.2f}",
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
    )


def transactions_table() -> rx.Component:
    """Transactions table (functional component)."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Transactions", size="5"),
                rx.spacer(),
                rx.text(
                    f"Total: {TransactionState.transactions.length()}",
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


@rx.page(
    route="/transactions",
    on_load=[TransactionState.load_transactions, TransactionState.load_categories],
)
def transactions_page() -> rx.Component:
    """Transactions page."""
    return layout(
        rx.vstack(
            rx.heading("Transaction Management", size="8"),
            rx.text("View and categorize your transactions", color="gray", size="3"),
            rx.divider(),
            search_bar(),
            transaction_filters(),
            rx.cond(
                TransactionState.selected_ids.length() > 0,
                bulk_actions(),
            ),
            transactions_table(),
            spacing="4",
            width="100%",
        ),
    )
