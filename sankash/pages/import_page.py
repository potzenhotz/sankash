"""CSV import page."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.import_state import ImportState


def upload_form() -> rx.Component:
    """File upload form (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Import Transactions", size="4"),
            rx.text(
                "Upload a CSV file with columns: date, payee, amount, notes",
                size="2",
                color="gray",
            ),
            # Account selection
            rx.select(
                [f"{acc['name']} ({acc['bank']})" for acc in ImportState.accounts],
                placeholder="Select Account",
                on_change=lambda val: ImportState.set_selected_account_id(
                    ImportState.accounts[int(val.split(" ")[0])]["id"]
                    if val
                    else 0
                ),
            ),
            # File upload
            rx.upload(
                rx.vstack(
                    rx.button("Select CSV File", size="3"),
                    rx.text(
                        "Drag and drop or click to select",
                        size="2",
                        color="gray",
                    ),
                ),
                id="csv_upload",
                accept={".csv": ["text/csv"]},
                on_drop=ImportState.handle_upload,
            ),
            # Messages
            rx.cond(
                ImportState.error != "",
                rx.text(ImportState.error, color="red", size="2"),
            ),
            rx.cond(
                ImportState.success != "",
                rx.text(ImportState.success, color="green", size="2"),
            ),
            # Actions
            rx.hstack(
                rx.button(
                    "Preview",
                    on_click=ImportState.preview_import,
                    size="2",
                    variant="soft",
                    disabled=ImportState.uploaded_file == "",
                ),
                rx.button(
                    "Import",
                    on_click=ImportState.perform_import,
                    size="2",
                    disabled=ImportState.uploaded_file == "",
                ),
                spacing="2",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )


def preview_row(transaction: dict) -> rx.Component:
    """Preview table row (functional component)."""
    return rx.table.row(
        rx.table.cell(str(transaction.get("date", ""))),
        rx.table.cell(transaction.get("payee", "")),
        rx.table.cell(transaction.get("notes", "-")),
        rx.table.cell(f"€{float(transaction.get('amount', 0)):.2f}"),
    )


def preview_table() -> rx.Component:
    """Import preview table (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Preview", size="5"),
            rx.text(
                f"Showing first {len(ImportState.preview_data)} transactions",
                size="2",
                color="gray",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("Payee"),
                        rx.table.column_header_cell("Notes"),
                        rx.table.column_header_cell("Amount"),
                    ),
                ),
                rx.table.body(rx.foreach(ImportState.preview_data, preview_row)),
            ),
            spacing="3",
            width="100%",
        ),
    )


def import_results() -> rx.Component:
    """Import results display (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Import Results", size="5"),
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.text("Total", size="2", color="gray"),
                        rx.text(
                            str(ImportState.import_stats.get("total", 0)),
                            size="6",
                            weight="bold",
                        ),
                    ),
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Imported", size="2", color="gray"),
                        rx.text(
                            str(ImportState.import_stats.get("imported", 0)),
                            size="6",
                            weight="bold",
                            color="green",
                        ),
                    ),
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Duplicates", size="2", color="gray"),
                        rx.text(
                            str(ImportState.import_stats.get("duplicates", 0)),
                            size="6",
                            weight="bold",
                            color="orange",
                        ),
                    ),
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Auto-Categorized", size="2", color="gray"),
                        rx.text(
                            str(ImportState.import_stats.get("categorized", 0)),
                            size="6",
                            weight="bold",
                            color="blue",
                        ),
                    ),
                ),
                columns="4",
                spacing="3",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )


@rx.page(route="/import", on_load=ImportState.load_accounts)
def import_page() -> rx.Component:
    """CSV import page."""
    return layout(
        rx.vstack(
            rx.heading("Import Transactions", size="8"),
            rx.text("Upload CSV files to import transactions", color="gray", size="3"),
            rx.divider(),
            upload_form(),
            rx.cond(
                ImportState.show_preview,
                preview_table(),
            ),
            rx.cond(
                ImportState.show_results,
                import_results(),
            ),
            spacing="4",
            width="100%",
        ),
    )
