"""Settings page for configuring Ollama and other preferences."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.settings_state import SettingsState


def ollama_status_badge() -> rx.Component:
    """Show connection status as a colored badge."""
    return rx.cond(
        SettingsState.ollama_status != "",
        rx.cond(
            SettingsState.ollama_status == "connected",
            rx.badge("Connected", color_scheme="green"),
            rx.badge("Unreachable", color_scheme="red"),
        ),
    )


def ollama_settings_card() -> rx.Component:
    """Card with Ollama configuration inputs."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("bot", size=20),
                rx.heading("AI / Ollama", size="4"),
                spacing="2",
                align="center",
            ),
            rx.text(
                "Configure the local Ollama instance used for AI-powered category suggestions.",
                size="2",
                color="gray",
            ),
            rx.separator(),
            # Base URL
            rx.vstack(
                rx.text("Base URL", size="2", weight="medium"),
                rx.input(
                    placeholder="http://localhost:11434",
                    value=SettingsState.ollama_base_url,
                    on_change=SettingsState.set_ollama_base_url,
                    width="100%",
                ),
                spacing="1",
                width="100%",
            ),
            # Model
            rx.vstack(
                rx.text("Model", size="2", weight="medium"),
                rx.input(
                    placeholder="llama3.2",
                    value=SettingsState.ollama_model,
                    on_change=SettingsState.set_ollama_model,
                    width="100%",
                ),
                spacing="1",
                width="100%",
            ),
            # Test connection row
            rx.hstack(
                rx.button(
                    rx.icon("wifi", size=14),
                    "Test Connection",
                    on_click=SettingsState.test_ollama_connection,
                    variant="outline",
                    size="2",
                ),
                ollama_status_badge(),
                spacing="3",
                align="center",
            ),
            rx.separator(),
            # Save button + messages
            rx.hstack(
                rx.button(
                    "Save",
                    on_click=SettingsState.save_settings,
                    loading=SettingsState.saving,
                    size="2",
                ),
                spacing="3",
                align="center",
            ),
            rx.cond(
                SettingsState.success_message != "",
                rx.callout(
                    SettingsState.success_message,
                    icon="check",
                    color_scheme="green",
                    size="1",
                ),
            ),
            rx.cond(
                SettingsState.error != "",
                rx.callout(
                    SettingsState.error,
                    icon="alert-triangle",
                    color_scheme="red",
                    size="1",
                ),
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
        max_width="600px",
    )


@rx.page(route="/settings", on_load=SettingsState.load_settings)
def settings_page() -> rx.Component:
    """Settings page."""
    return layout(
        rx.vstack(
            rx.heading("Settings", size="6"),
            ollama_settings_card(),
            spacing="4",
            width="100%",
            padding="1rem",
        ),
    )
