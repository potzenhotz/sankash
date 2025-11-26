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


def sankey_chart() -> rx.Component:
    """Sankey diagram component (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Money Flow", size="5"),
            rx.plotly(data=DashboardState.sankey_figure),
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
            sankey_chart(),
            expenses_trend_chart(),
            spacing="4",
            width="100%",
        ),
    )
