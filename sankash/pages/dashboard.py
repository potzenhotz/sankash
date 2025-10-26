"""Dashboard page with Sankey diagram."""

import reflex as rx

from sankash.components.layout import layout
from sankash.components.kpi_cards import kpi_grid
from sankash.state.dashboard_state import DashboardState
from sankash.utils.formatters import format_currency


def date_range_selector() -> rx.Component:
    """Date range selection controls (functional component)."""
    return rx.card(
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
    )


def sankey_chart() -> rx.Component:
    """Sankey diagram component (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Money Flow", size="5"),
            rx.cond(
                len(DashboardState.sankey_nodes) > 0,
                rx.text(
                    "Sankey diagram will be rendered here with Plotly",
                    size="2",
                    color="gray",
                ),
                rx.text(
                    "No categorized transactions in this period",
                    size="2",
                    color="gray",
                ),
            ),
            # TODO: Add Plotly Sankey diagram
            # This will require custom component integration
            rx.text(
                f"Nodes: {len(DashboardState.sankey_nodes)}, Links: {len(DashboardState.sankey_links)}",
                size="1",
                color="gray",
            ),
            spacing="3",
            width="100%",
            min_height="400px",
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
                income=format_currency(DashboardState.income),
                expense=format_currency(DashboardState.expense),
                net=format_currency(DashboardState.net),
                uncategorized=DashboardState.uncategorized_count,
            ),
            rx.cond(
                DashboardState.error != "",
                rx.text(DashboardState.error, color="red", size="2"),
            ),
            sankey_chart(),
            spacing="4",
            width="100%",
        ),
    )
