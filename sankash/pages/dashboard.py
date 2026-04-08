"""Dashboard page with Sankey diagram."""

import reflex as rx

from sankash.components.layout import layout
from sankash.components.kpi_cards import kpi_grid
from sankash.state.dashboard_state import DashboardState


def date_range_selector() -> rx.Component:
    """Date range selection controls (functional component)."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Time Period", size="4"),
                rx.spacer(),
                rx.button(
                    "Last Month",
                    on_click=DashboardState.set_period_last_month,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    "Last Quarter",
                    on_click=DashboardState.set_period_last_quarter,
                    size="2",
                    variant="soft",
                ),
                rx.button(
                    "Last Year",
                    on_click=DashboardState.set_period_last_year,
                    size="2",
                    variant="soft",
                ),
                spacing="2",
                width="100%",
                align="center",
            ),
            rx.divider(),
            # Account selector
            rx.hstack(
                rx.text("Account:", size="2", weight="medium"),
                rx.select(
                    DashboardState.account_options,
                    value=DashboardState.selected_account_display,
                    on_change=DashboardState.set_selected_account,
                    size="2",
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
            rx.divider(),
            # Month/Year selector
            rx.hstack(
                rx.text("Select Month & Year:", size="2", weight="medium"),
                rx.select(
                    DashboardState.available_month_names,
                    placeholder="Month",
                    size="2",
                    value=DashboardState.selected_month_name,
                    on_change=DashboardState.set_selected_month,
                ),
                rx.select(
                    DashboardState.available_years,
                    placeholder="Year",
                    size="2",
                    value=rx.cond(
                        DashboardState.selected_year > 0,
                        str(DashboardState.selected_year),
                        "",
                    ),
                    on_change=DashboardState.set_selected_year,
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
            rx.divider(),
            # Date range pickers
            rx.hstack(
                rx.vstack(
                    rx.text("Start Date:", size="2", weight="medium"),
                    rx.input(
                        type="date",
                        value=DashboardState.start_date,
                        on_change=DashboardState.set_start_date_input,
                        size="2",
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.vstack(
                    rx.text("End Date:", size="2", weight="medium"),
                    rx.input(
                        type="date",
                        value=DashboardState.end_date,
                        on_change=DashboardState.set_end_date_input,
                        size="2",
                    ),
                    spacing="1",
                    align="start",
                ),
                spacing="4",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )


def category_badge(category: str) -> rx.Component:
    """Toggleable category badge."""
    is_excluded = DashboardState.excluded_categories.contains(category)
    return rx.tooltip(
        rx.badge(
            category,
            color_scheme=rx.cond(is_excluded, "gray", "blue"),
            variant=rx.cond(is_excluded, "outline", "soft"),
            cursor="pointer",
            on_click=lambda: DashboardState.toggle_category(category),
        ),
        content=rx.cond(is_excluded, "Click to include", "Click to exclude"),
    )


def category_filter() -> rx.Component:
    """Category filter bar."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("filter", size=18),
                rx.heading("Categories", size="4"),
                rx.spacer(),
                rx.button(
                    "All",
                    on_click=DashboardState.include_all_categories,
                    size="1",
                    variant="soft",
                ),
                rx.button(
                    "None",
                    on_click=DashboardState.exclude_all_categories,
                    size="1",
                    variant="soft",
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.flex(
                rx.foreach(
                    DashboardState.all_categories,
                    category_badge,
                ),
                wrap="wrap",
                spacing="2",
            ),
            spacing="3",
            width="100%",
        ),
    )


def detail_row(tx: dict) -> rx.Component:
    """Transaction detail row."""
    return rx.table.row(
        rx.table.cell(rx.text(tx["date"], size="2")),
        rx.table.cell(rx.text(tx["payee"], size="2")),
        rx.table.cell(rx.text(tx["amount"], size="2")),
        rx.table.cell(rx.text(tx["notes"], size="1", color="gray")),
    )


def category_detail() -> rx.Component:
    """Category transaction detail panel."""
    return rx.card(
        rx.vstack(
            rx.cond(
                DashboardState.selected_detail_category != "",
                rx.vstack(
                    rx.hstack(
                        rx.heading(
                            DashboardState.selected_detail_category,
                            size="4",
                        ),
                        rx.badge(
                            DashboardState.detail_transactions.length(),
                            color_scheme="blue",
                            variant="soft",
                        ),
                        rx.spacer(),
                        rx.text(
                            f"Total: {DashboardState.detail_total:.2f}",
                            size="2",
                            weight="bold",
                        ),
                        rx.button(
                            rx.icon("x", size=16),
                            on_click=DashboardState.select_detail_category(""),
                            size="1",
                            variant="ghost",
                        ),
                        spacing="2",
                        align="center",
                        width="100%",
                    ),
                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Date"),
                                    rx.table.column_header_cell("Payee"),
                                    rx.table.column_header_cell("Amount"),
                                    rx.table.column_header_cell("Notes"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    DashboardState.detail_transactions,
                                    detail_row,
                                ),
                            ),
                            size="1",
                        ),
                        max_height="550px",
                        overflow_y="auto",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
                rx.vstack(
                    rx.icon("mouse-pointer-click", size=32, color="gray"),
                    rx.text(
                        "Click a category in the Sankey chart to see transactions",
                        color="gray",
                        size="2",
                        text_align="center",
                    ),
                    spacing="3",
                    align="center",
                    justify="center",
                    height="100%",
                    width="100%",
                ),
            ),
            spacing="3",
            width="100%",
            height="100%",
        ),
        height="100%",
    )


def sankey_chart() -> rx.Component:
    """Sankey diagram component (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Money Flow", size="5"),
            rx.plotly(
                data=DashboardState.sankey_figure,
                on_click=DashboardState.handle_sankey_click,
            ),
            spacing="3",
            width="100%",
        ),
    )


def expenses_trend_chart() -> rx.Component:
    """Expenses over time chart component (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Expenses & Income Trend", size="5"),
            rx.plotly(data=DashboardState.expenses_trend_figure),
            spacing="3",
            width="100%",
        ),
    )


@rx.page(route="/", on_load=DashboardState.load_dashboard)
def dashboard_page() -> rx.Component:
    """Dashboard page."""
    return layout(
        rx.vstack(
            rx.heading("Dashboard", size="8"),
            rx.text("Your financial overview", color="gray", size="3"),
            rx.divider(),
            date_range_selector(),
            kpi_grid(
                income=f"€{DashboardState.income:.2f}",
                expense=f"€{DashboardState.expense:.2f}",
                net=f"€{DashboardState.net:.2f}",
                uncategorized=DashboardState.uncategorized_count,
            ),
            rx.cond(
                DashboardState.error != "",
                rx.text(DashboardState.error, color="red", size="2"),
            ),
            category_filter(),
            rx.grid(
                sankey_chart(),
                category_detail(),
                columns="3fr 2fr",
                spacing="4",
                width="100%",
            ),
            expenses_trend_chart(),
            spacing="4",
            width="100%",
        ),
    )
