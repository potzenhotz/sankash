"""Main Reflex app entry point."""

import reflex as rx

# Import all pages to register routes
from sankash.pages import accounts, dashboard, import_page, rules, transactions


app = rx.App()
