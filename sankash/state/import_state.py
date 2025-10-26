"""Import page state management."""

import reflex as rx

from sankash.services import import_service, account_service
from sankash.state.base import BaseState


class ImportState(BaseState):
    """State for CSV import page."""

    accounts: list[dict] = []
    loading: bool = False
    error: str = ""
    success: str = ""

    # Form fields
    selected_account_id: int = 0
    uploaded_file: str = ""

    # Preview
    preview_data: list[dict] = []
    show_preview: bool = False

    # Import results
    import_stats: dict[str, int] = {}
    show_results: bool = False

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
