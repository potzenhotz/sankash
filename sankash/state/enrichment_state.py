"""Enrichment state for updating transactions with Amazon/PayPal data."""

import reflex as rx

from sankash.services import enrichment_service
from sankash.state.base import BaseState


class EnrichmentState(BaseState):
    """State for transaction enrichment UI."""

    loading: bool = False
    error: str = ""
    success: str = ""

    # Upload
    uploaded_file: str = ""
    original_filename: str = ""
    enrichment_source: str = ""  # "amazon" or "paypal"

    # Preview
    preview_data: list[dict] = []
    show_preview: bool = False

    # Results
    enrich_stats: dict[str, int] = {}
    show_results: bool = False

    def reset_enrichment(self) -> None:
        """Reset enrichment UI state and migrate any old-format enriched payees."""
        self.loading = False
        self.error = ""
        self.success = ""
        self.uploaded_file = ""
        self.original_filename = ""
        self.enrichment_source = ""
        self.preview_data = []
        self.show_preview = False
        self.enrich_stats = {}
        self.show_results = False
        enrichment_service.migrate_enriched_payees(self.data_dir)

    async def handle_amazon_upload(self, files: list[rx.UploadFile]) -> None:
        """Handle Amazon CSV upload."""
        await self._handle_upload(files, "amazon")

    async def handle_paypal_upload(self, files: list[rx.UploadFile]) -> None:
        """Handle PayPal CSV upload."""
        await self._handle_upload(files, "paypal")

    async def _handle_upload(self, files: list[rx.UploadFile], source: str) -> None:
        """Handle file upload for enrichment."""
        if not files:
            return

        file = files[0]
        upload_data = await file.read()

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(upload_data)
            self.uploaded_file = tmp.name

        self.original_filename = file.filename or ""
        self.enrichment_source = source
        self.success = f"File '{file.filename}' uploaded ({source})"
        self.show_preview = False
        self.show_results = False
        self.error = ""

    def preview_enrichment(self) -> None:
        """Preview enrichment matches without applying."""
        if not self.uploaded_file or not self.enrichment_source:
            self.error = "Please upload a file first"
            return

        self.loading = True
        self.error = ""

        try:
            self.preview_data = enrichment_service.preview_enrichment(
                self.data_dir,
                self.uploaded_file,
                self.enrichment_source,
                limit=30,
            )
            self.show_preview = True
            if not self.preview_data:
                self.error = "No matching transactions found"
        except Exception as e:
            self.error = f"Preview failed: {str(e)}"
        finally:
            self.loading = False

    def apply_enrichment(self) -> None:
        """Apply enrichment to transactions."""
        if not self.uploaded_file or not self.enrichment_source:
            self.error = "Please upload a file first"
            return

        self.loading = True
        self.error = ""

        try:
            if self.enrichment_source == "amazon":
                stats = enrichment_service.enrich_with_amazon(
                    self.data_dir, self.uploaded_file
                )
            elif self.enrichment_source == "paypal":
                stats = enrichment_service.enrich_with_paypal(
                    self.data_dir, self.uploaded_file
                )
            else:
                self.error = f"Unknown source: {self.enrichment_source}"
                return

            self.enrich_stats = stats
            self.show_results = True
            self.show_preview = False
            matched = stats.get("matched", 0)
            skipped = stats.get("skipped", 0)
            self.success = f"Enriched {matched} transactions ({skipped} already enriched)"

            # Cleanup temp file
            import os
            if os.path.exists(self.uploaded_file):
                os.remove(self.uploaded_file)
            self.uploaded_file = ""
        except Exception as e:
            self.error = f"Enrichment failed: {str(e)}"
        finally:
            self.loading = False
