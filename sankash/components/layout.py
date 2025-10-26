"""Main layout component."""

import reflex as rx

from sankash.components.sidebar import sidebar


def layout(*children) -> rx.Component:
    """
    Main layout with sidebar (functional component).

    Args:
        *children: Child components to render in main content area

    Returns:
        Layout component with sidebar and content
    """
    return rx.hstack(
        # Sidebar
        sidebar(),
        # Main content
        rx.box(
            *children,
            width="100%",
            padding="2rem",
            height="100vh",
            overflow_y="auto",
        ),
        spacing="0",
        width="100%",
    )
