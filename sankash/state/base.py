"""Base state class with shared functionality."""

import reflex as rx

from config.settings import load_settings


class BaseState(rx.State):
    """Base state with common functionality."""

    @property
    def db_path(self) -> str:
        """Get database path from settings."""
        settings = load_settings()
        return settings.db_path

    @property
    def default_currency(self) -> str:
        """Get default currency from settings."""
        settings = load_settings()
        return settings.default_currency
