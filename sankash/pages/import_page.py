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
                "Upload a CSV file from your bank or in standard format",
                size="2",
                color="gray",
            ),
            # Account selection
            rx.vstack(
                rx.text("Select Account", size="2", weight="bold"),
                rx.select(
                    ImportState.account_options,
                    placeholder="Select Account",
                    on_change=ImportState.handle_account_selection,
                ),
                spacing="1",
                width="100%",
            ),
            # Bank format selection
            rx.vstack(
                rx.text("Bank Format", size="2", weight="bold"),
                rx.select(
                    ImportState.bank_format_options,
                    placeholder="Select Format",
                    value=ImportState.selected_bank_format_display,
                    on_change=ImportState.handle_bank_format_selection,
                ),
                rx.text(
                    "Standard CSV format: date (YYYY-MM-DD), payee, amount, notes",
                    size="1",
                    color="gray",
                ),
                spacing="1",
                width="100%",
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
        rx.table.cell(transaction.get("date", "")),
        rx.table.cell(transaction.get("payee", "")),
        rx.table.cell(transaction.get("notes", "-")),
        rx.table.cell(rx.text("€", transaction.get("amount", 0))),
    )


def preview_table() -> rx.Component:
    """Import preview table (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Preview", size="5"),
            rx.text(
                "Showing first ",
                ImportState.preview_data.length(),
                " transactions",
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
            rx.callout(
                rx.vstack(
                    rx.text(
                        "Successfully imported ",
                        ImportState.import_stats.get("imported", 0),
                        " transactions!",
                        size="3",
                        weight="bold",
                    ),
                    rx.cond(
                        ImportState.import_stats.get("duplicates", 0) > 0,
                        rx.text(
                            ImportState.import_stats.get("duplicates", 0),
                            " duplicates were skipped.",
                            size="2",
                        ),
                    ),
                    rx.cond(
                        ImportState.import_stats.get("categorized", 0) > 0,
                        rx.text(
                            ImportState.import_stats.get("categorized", 0),
                            " transactions were auto-categorized by rules.",
                            size="2",
                        ),
                    ),
                    spacing="1",
                ),
                icon="circle-check",
                color="green",
                size="2",
            ),
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.text("Total", size="2", color="gray"),
                        rx.text(
                            ImportState.import_stats.get("total", 0),
                            size="6",
                            weight="bold",
                        ),
                    ),
                ),
                rx.card(
                    rx.vstack(
                        rx.text("Imported", size="2", color="gray"),
                        rx.text(
                            ImportState.import_stats.get("imported", 0),
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
                            ImportState.import_stats.get("duplicates", 0),
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
                            ImportState.import_stats.get("categorized", 0),
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


def history_row(import_record: dict) -> rx.Component:
    """Import history row (functional component)."""
    return rx.table.row(
        rx.table.cell(
            rx.text(
                import_record.get("import_date", "-"),
                size="2",
            ),
        ),
        rx.table.cell(
            rx.text(
                import_record.get("filename", ""),
                size="2",
                weight="medium",
            ),
        ),
        rx.table.cell(
            rx.text(
                import_record.get("account_name", ""),
                " (",
                import_record.get("account_bank", ""),
                ")",
            ),
        ),
        rx.table.cell(
            rx.badge(
                import_record.get("bank_format", ""),
                color_scheme="blue",
                size="1",
            ),
        ),
        rx.table.cell(
            rx.text(
                import_record["total_count"],
                size="2",
            ),
        ),
        rx.table.cell(
            rx.text(
                import_record["imported_count"],
                size="2",
                color="green",
                weight="medium",
            ),
        ),
        rx.table.cell(
            rx.text(
                import_record["duplicate_count"],
                size="2",
                color="orange",
            ),
        ),
        rx.table.cell(
            rx.text(
                import_record["categorized_count"],
                size="2",
                color="blue",
            ),
        ),
        rx.table.cell(
            rx.cond(
                import_record["remaining_count"] == 0,
                rx.badge("Deleted", color_scheme="red", size="1"),
                rx.text(
                    import_record["remaining_count"],
                    size="2",
                    weight="medium",
                ),
            ),
        ),
    )


def import_history_section() -> rx.Component:
    """Import history display (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Import History", size="5"),
            rx.text(
                "Recent CSV imports",
                size="2",
                color="gray",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("File"),
                        rx.table.column_header_cell("Account"),
                        rx.table.column_header_cell("Format"),
                        rx.table.column_header_cell("Total"),
                        rx.table.column_header_cell("Imported"),
                        rx.table.column_header_cell("Duplicates"),
                        rx.table.column_header_cell("Categorized"),
                        rx.table.column_header_cell("Remaining"),
                    ),
                ),
                rx.table.body(rx.foreach(ImportState.import_history, history_row)),
            ),
            spacing="3",
            width="100%",
        ),
    )


@rx.page(route="/import", on_load=[ImportState.reset_ui, ImportState.load_accounts, ImportState.load_import_history])
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
            rx.cond(
                ImportState.show_history,
                import_history_section(),
            ),
            spacing="4",
            width="100%",
        ),
    )
