"""Formatting utilities using pure functions."""

from datetime import date, datetime


def format_currency(amount: float, currency: str = "EUR") -> str:
    """Format amount as currency (pure function)."""
    # Simple formatting, can be enhanced with locale support
    if currency == "EUR":
        return f"€{amount:,.2f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"


def format_date(d: date | datetime, format_str: str = "%Y-%m-%d") -> str:
    """Format date (pure function)."""
    if isinstance(d, datetime):
        return d.strftime(format_str)
    return d.strftime(format_str)


def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> date:
    """Parse date string (pure function)."""
    return datetime.strptime(date_str, format_str).date()


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format as percentage (pure function)."""
    return f"{value:.{decimals}f}%"


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis (pure function)."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
