"""Account page state management."""

import reflex as rx

from sankash.core.models import Account
from sankash.services import account_service
from sankash.state.base import BaseState


class AccountState(BaseState):
    """State for account management page."""

    state_auto_setters = True  # Explicitly enable auto setters

    accounts: list[dict] = []
    loading: bool = False
    error: str = ""

    # Form fields
    form_name: str = ""
    form_bank: str = ""
    form_account_number: str = ""
    form_currency: str = "EUR"
    form_is_active: bool = True

    # Edit mode
    editing_id: int | None = None

    def load_accounts(self) -> None:
        """Load accounts with balances."""
        self.loading = True
        self.error = ""

        try:
            df = account_service.get_accounts_with_balances(self.db_path)
            self.accounts = df.to_dicts()
        except Exception as e:
            self.error = f"Failed to load accounts: {str(e)}"
        finally:
            self.loading = False

    def create_account(self) -> None:
        """Create new account from form data."""
        if not self.form_name or not self.form_bank or not self.form_account_number:
            self.error = "Name, bank, and account number are required"
            return

        try:
            account = Account(
                name=self.form_name,
                bank=self.form_bank,
                account_number=self.form_account_number,
                currency=self.form_currency,
                is_active=self.form_is_active,
            )
            account_service.create_account(self.db_path, account)
            self.clear_form()
            self.load_accounts()
        except Exception as e:
            self.error = f"Failed to create account: {str(e)}"

    def deactivate_account(self, account_id: int) -> None:
        """Deactivate an account."""
        try:
            account_service.deactivate_account(self.db_path, account_id)
            self.load_accounts()
        except Exception as e:
            self.error = f"Failed to deactivate account: {str(e)}"

    def clear_form(self) -> None:
        """Clear form fields."""
        self.form_name = ""
        self.form_bank = ""
        self.form_account_number = ""
        self.form_currency = "EUR"
        self.form_is_active = True
        self.editing_id = None
        self.error = ""
