"""Reflex configuration."""

import reflex as rx
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(
    app_name="sankash",
    db_url="sqlite:///reflex.db",  # Reflex's own DB for state
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],  # Disable sitemap
    state_auto_setters=True,  # Explicitly enable auto setters globally
)
