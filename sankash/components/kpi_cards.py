"""KPI card components for dashboard."""

import reflex as rx


def kpi_card(
    title: str,
    value: str,
    icon: str = "trending-up",
    color: str = "blue",
) -> rx.Component:
    """
    KPI card component (functional).

    Args:
        title: Card title
        value: Main value to display
        icon: Icon name
        color: Color theme

    Returns:
        KPI card component
    """
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=20, color=f"var(--{color}-9)"),
                rx.text(title, size="2", color="gray"),
                spacing="2",
                align="center",
                width="100%",
                justify="between",
            ),
            rx.text(value, size="7", weight="bold"),
            spacing="2",
            align="start",
        ),
    )


def kpi_grid(
    income: str,
    expense: str,
    net: str,
    uncategorized: int = 0,
) -> rx.Component:
    """
    Grid of KPI cards (functional).

    Args:
        income: Income value formatted as string
        expense: Expense value formatted as string
        net: Net value formatted as string
        uncategorized: Count of uncategorized transactions

    Returns:
        Grid of KPI cards
    """
    return rx.grid(
        kpi_card("Income", income, "trending-up", "green"),
        kpi_card("Expenses", expense, "trending-down", "red"),
        kpi_card("Net", net, "wallet", "blue"),
        kpi_card(
            "Uncategorized",
            uncategorized,
            "alert-circle",
            "orange",
        ),
        columns="4",
        spacing="4",
        width="100%",
    )
