"""Reflex configuration."""

import reflex as rx

config = rx.Config(
    app_name="sankash",
    db_url="sqlite:///reflex.db",  # Reflex's own DB for state
)
