"""Sidebar navigation component."""

import reflex as rx


def nav_link(text: str, href: str, icon: str = "circle") -> rx.Component:
    """Navigation link component (functional)."""
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text, size="3"),
            spacing="2",
            align="center",
        ),
        href=href,
        style={
            "text_decoration": "none",
            "color": "inherit",
            "_hover": {"background": "var(--gray-3)", "border_radius": "6px"},
            "padding": "0.5rem",
            "width": "100%",
        },
    )


def sidebar() -> rx.Component:
    """Sidebar navigation component (functional)."""
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.icon("wallet", size=28, color="var(--accent-9)"),
                rx.heading("Sankash", size="6"),
                spacing="2",
                align="center",
                padding_bottom="1rem",
            ),
            rx.divider(),
            # Navigation links
            rx.vstack(
                nav_link("Dashboard", "/", "layout-dashboard"),
                nav_link("Transactions", "/transactions", "list"),
                nav_link("Accounts", "/accounts", "building-2"),
                nav_link("Categories", "/categories", "tags"),
                nav_link("Rules", "/rules", "list-checks"),
                nav_link("Import", "/import", "upload"),
                spacing="1",
                align="start",
                width="100%",
                padding_top="1rem",
            ),
            # Footer
            rx.spacer(),
            rx.divider(),
            rx.text(
                "Personal Finance Tracker",
                size="1",
                color="gray",
                padding_top="1rem",
            ),
            spacing="2",
            align="start",
            height="100%",
            padding="1.5rem",
        ),
        width="250px",
        height="100vh",
        border_right="1px solid var(--gray-5)",
        position="sticky",
        top="0",
    )
