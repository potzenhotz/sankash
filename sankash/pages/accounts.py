"""Accounts management page."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.account_state import AccountState
from sankash.utils.formatters import format_currency


def account_form() -> rx.Component:
    """Account creation form (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Add New Account", size="4"),
            rx.input(
                placeholder="Account Name",
                value=AccountState.form_name,
                on_change=AccountState.set_form_name,
            ),
            rx.input(
                placeholder="Bank Name",
                value=AccountState.form_bank,
                on_change=AccountState.set_form_bank,
            ),
            rx.input(
                placeholder="Account Number",
                value=AccountState.form_account_number,
                on_change=AccountState.set_form_account_number,
            ),
            rx.select(
                ["EUR", "USD", "GBP"],
                value=AccountState.form_currency,
                on_change=AccountState.set_form_currency,
            ),
            rx.cond(
                AccountState.error != "",
                rx.text(AccountState.error, color="red", size="2"),
            ),
            rx.button(
                "Create Account",
                on_click=AccountState.create_account,
                size="3",
            ),
            spacing="3",
            width="100%",
        ),
    )


def account_row(account: dict) -> rx.Component:
    """Account table row (functional component)."""
    return rx.table.row(
        rx.table.cell(account["name"]),
        rx.table.cell(account["bank"]),
        rx.table.cell(account["account_number"]),
        rx.table.cell(
            rx.text(
                format_currency(float(account.get("balance", 0)), account["currency"]),
                weight="bold",
                color="green" if float(account.get("balance", 0)) > 0 else "red",
            )
        ),
        rx.table.cell(str(account.get("transaction_count", 0))),
        rx.table.cell(
            rx.badge(
                "Active" if account["is_active"] else "Inactive",
                color_scheme="green" if account["is_active"] else "gray",
            )
        ),
        rx.table.cell(
            rx.cond(
                account["is_active"],
                rx.button(
                    rx.icon("trash-2", size=16),
                    on_click=lambda: AccountState.deactivate_account(account["id"]),
                    size="1",
                    variant="soft",
                    color_scheme="red",
                ),
            )
        ),
    )


def accounts_table() -> rx.Component:
    """Accounts table (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Accounts", size="5"),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Name"),
                        rx.table.column_header_cell("Bank"),
                        rx.table.column_header_cell("Account Number"),
                        rx.table.column_header_cell("Balance"),
                        rx.table.column_header_cell("Transactions"),
                        rx.table.column_header_cell("Status"),
                        rx.table.column_header_cell("Actions"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(AccountState.accounts, account_row)
                ),
            ),
            spacing="3",
            width="100%",
        ),
    )


@rx.page(route="/accounts", on_load=AccountState.load_accounts)
def accounts_page() -> rx.Component:
    """Accounts page."""
    return layout(
        rx.vstack(
            rx.heading("Account Management", size="8"),
            rx.text("Manage your financial accounts", color="gray", size="3"),
            rx.divider(),
            rx.grid(
                account_form(),
                accounts_table(),
                columns="1",
                spacing="4",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
    )
