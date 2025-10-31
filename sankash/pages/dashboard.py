"""Dashboard page with Sankey diagram."""

import reflex as rx

from sankash.components.layout import layout
from sankash.components.kpi_cards import kpi_grid
from sankash.state.dashboard_state import DashboardState


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
            rx.plotly(data=DashboardState.sankey_figure),
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
            spacing="4",
            width="100%",
        ),
    )
