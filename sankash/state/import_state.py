"""Import page state management."""

import reflex as rx

from sankash.converters.bank_converters import BankFormat
from sankash.services import import_service, account_service
from sankash.state.base import BaseState


class ImportState(BaseState):
    """State for CSV import page."""

    state_auto_setters = True  # Explicitly enable auto setters

    accounts: list[dict] = []
    loading: bool = False
    error: str = ""
    success: str = ""

    # Form fields
    selected_account_id: int = 0
    uploaded_file: str = ""
    bank_format: str = BankFormat.STANDARD.value

    # Preview
    preview_data: list[dict] = []
    show_preview: bool = False

    # Import results
    import_stats: dict[str, int] = {}
    show_results: bool = False

    @rx.var
    def account_options(self) -> list[str]:
        """Get formatted account options for select."""
        return [f"{acc['name']} ({acc['bank']})" for acc in self.accounts]

    @rx.var
    def bank_format_options(self) -> list[str]:
        """Get bank format options for select."""
        return ["Standard CSV", "Deutsche Bank", "ING"]

    @rx.var
    def selected_bank_format_display(self) -> str:
        """Get display name for selected bank format."""
        format_map = {
            BankFormat.STANDARD.value: "Standard CSV",
            BankFormat.DEUTSCHE_BANK.value: "Deutsche Bank",
            BankFormat.ING.value: "ING",
        }
        return format_map.get(self.bank_format, "Standard CSV")

    def handle_account_selection(self, value: str) -> None:
        """Handle account selection from dropdown."""
        # Find account by matching the formatted string
        for acc in self.accounts:
            if f"{acc['name']} ({acc['bank']})" == value:
                self.selected_account_id = acc["id"]
                break

    def handle_bank_format_selection(self, value: str) -> None:
        """Handle bank format selection from dropdown."""
        # Map display name to enum value
        format_map = {
            "Standard CSV": BankFormat.STANDARD.value,
            "Deutsche Bank": BankFormat.DEUTSCHE_BANK.value,
            "ING": BankFormat.ING.value,
        }
        self.bank_format = format_map.get(value, BankFormat.STANDARD.value)

    def load_accounts(self) -> None:
        """Load available accounts."""
        try:
            df = account_service.get_accounts(self.db_path)
            self.accounts = df.to_dicts()
        except Exception as e:
            self.error = f"Failed to load accounts: {str(e)}"

    async def handle_upload(self, files: list[rx.UploadFile]) -> None:
        """Handle file upload."""
        if not files:
            return

        file = files[0]
        upload_data = await file.read()

        # Save to temporary location
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(upload_data)
            self.uploaded_file = tmp.name

        self.success = f"File '{file.filename}' uploaded successfully"
        self.show_preview = False
        self.show_results = False

    def preview_import(self) -> None:
        """Preview import data."""
        if not self.uploaded_file or self.selected_account_id == 0:
            self.error = "Please select an account and upload a file"
            return

        self.loading = True
        self.error = ""

        try:
            df = import_service.preview_import(
                self.uploaded_file,
                self.selected_account_id,
                bank_format=BankFormat(self.bank_format),
                limit=20,
            )
            self.preview_data = df.to_dicts()
            self.show_preview = True
        except Exception as e:
            self.error = f"Failed to preview import: {str(e)}"
        finally:
            self.loading = False

    def perform_import(self) -> None:
        """Perform actual import."""
        if not self.uploaded_file or self.selected_account_id == 0:
            self.error = "Please select an account and upload a file"
            return

        self.loading = True
        self.error = ""

        try:
            stats = import_service.import_transactions(
                self.db_path,
                self.uploaded_file,
                self.selected_account_id,
                bank_format=BankFormat(self.bank_format),
            )

            self.import_stats = stats
            self.show_results = True
            self.success = f"Import completed! {stats['imported']} transactions imported."

            # Cleanup
            import os
            if os.path.exists(self.uploaded_file):
                os.remove(self.uploaded_file)

            self.uploaded_file = ""
            self.show_preview = False
        except Exception as e:
            self.error = f"Failed to import: {str(e)}"
        finally:
            self.loading = False
