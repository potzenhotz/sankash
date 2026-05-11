"""Settings page for configuring LLM providers and other preferences."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.settings_state import SettingsState


def connection_status_badge() -> rx.Component:
    """Show connection status as a colored badge."""
    return rx.cond(
        SettingsState.ollama_status != "",
        rx.cond(
            SettingsState.ollama_status == "connected",
            rx.badge("Connected", color_scheme="green"),
            rx.badge("Unreachable", color_scheme="red"),
        ),
    )


def provider_selector() -> rx.Component:
    """Dropdown to choose the LLM provider."""
    return rx.vstack(
        rx.text("Provider", size="2", weight="medium"),
        rx.select(
            ["ollama", "openrouter", "apfel", "openai_compatible"],
            value=SettingsState.llm_provider,
            on_change=SettingsState.select_provider,
            width="100%",
        ),
        rx.text(
            rx.cond(
                SettingsState.llm_provider == "ollama",
                "Local Ollama instance — free, private, runs on your machine.",
                rx.cond(
                    SettingsState.llm_provider == "openrouter",
                    "Cloud LLM gateway — supports many models, requires API key.",
                    rx.cond(
                        SettingsState.llm_provider == "apfel",
                        "Apple on-device model via Apfel — free, private, macOS 26+ only.",
                        "Any endpoint that speaks the OpenAI chat completions API.",
                    ),
                ),
            ),
            size="1",
            color="gray",
        ),
        spacing="1",
        width="100%",
    )


def ollama_fields() -> rx.Component:
    """Fields shown when Ollama is selected."""
    return rx.fragment(
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
    )


def openai_fields() -> rx.Component:
    """Fields shown when an OpenAI-compatible provider is selected."""
    return rx.fragment(
        rx.vstack(
            rx.text("Base URL", size="2", weight="medium"),
            rx.input(
                placeholder="https://openrouter.ai/api",
                value=SettingsState.openai_base_url,
                on_change=SettingsState.set_openai_base_url,
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),
        rx.vstack(
            rx.text("Model", size="2", weight="medium"),
            rx.input(
                placeholder="meta-llama/llama-3.1-8b-instruct:free",
                value=SettingsState.openai_model,
                on_change=SettingsState.set_openai_model,
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),
        rx.vstack(
            rx.text("API Key", size="2", weight="medium"),
            rx.input(
                placeholder="sk-or-... (leave blank for local providers)",
                value=SettingsState.openai_api_key,
                on_change=SettingsState.set_openai_api_key,
                type="password",
                width="100%",
            ),
            rx.text(
                "Required for OpenRouter. Not needed for Apfel or other local endpoints.",
                size="1",
                color="gray",
            ),
            spacing="1",
            width="100%",
        ),
    )


def llm_settings_card() -> rx.Component:
    """Card with LLM provider configuration."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("bot", size=20),
                rx.heading("AI / LLM Provider", size="4"),
                spacing="2",
                align="center",
            ),
            rx.text(
                "Configure the LLM used for AI-powered category suggestions.",
                size="2",
                color="gray",
            ),
            rx.separator(),
            # Provider selector
            provider_selector(),
            rx.separator(),
            # Provider-specific fields
            rx.cond(
                SettingsState.llm_provider == "ollama",
                ollama_fields(),
                openai_fields(),
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
                connection_status_badge(),
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
                    icon="triangle-alert",
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
            llm_settings_card(),
            spacing="4",
            width="100%",
            padding="1rem",
        ),
    )
