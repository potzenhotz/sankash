"""Validation utilities using pure functions."""

import re
from datetime import date


def is_valid_amount(amount: str | float) -> bool:
    """Validate amount (pure function)."""
    try:
        float(amount)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_date_range(start: date, end: date) -> bool:
    """Validate date range (pure function)."""
    return start <= end


def is_valid_iban(iban: str) -> bool:
    """Validate IBAN format (pure function, simplified)."""
    # Remove spaces and convert to uppercase
    iban = iban.replace(" ", "").upper()

    # Basic length check (15-34 characters)
    if not 15 <= len(iban) <= 34:
        return False

    # Check format: 2 letters, 2 digits, rest alphanumeric
    pattern = r"^[A-Z]{2}[0-9]{2}[A-Z0-9]+$"
    return bool(re.match(pattern, iban))


def sanitize_category_name(name: str) -> str:
    """Sanitize category name (pure function)."""
    # Remove extra whitespace and capitalize
    return " ".join(name.strip().split()).title()


def sanitize_payee_name(name: str) -> str:
    """Sanitize payee name (pure function)."""
    # Remove extra whitespace
    return " ".join(name.strip().split())
