"""Transaction page state management."""

from datetime import date, timedelta

import reflex as rx

from sankash.services import transaction_service, category_service
from sankash.state.base import BaseState


class TransactionState(BaseState):
    """State for transaction management page."""

    state_auto_setters = True  # Explicitly enable auto setters

    transactions: list[dict] = []
    categories: list[str] = []
    category_display_map: dict[str, str] = {}  # Maps display name -> actual name
    loading: bool = False
    error: str = ""

    # Filters
    filter_account_id: int | None = None
    filter_start_date: str = ""
    filter_end_date: str = ""
    filter_category: str = ""
    filter_min_amount: str = ""
    filter_max_amount: str = ""
    filter_uncategorized_only: bool = False
    search_query: str = ""  # Quick search across payee, notes, category

    # Selection
    selected_ids: list[int] = []
    bulk_category: str = ""

    # Editing
    editing_id: int | None = None
    edit_category: str = ""
    edit_payee: str = ""
    edit_notes: str = ""

    def load_transactions(self) -> None:
        """Load transactions with current filters."""
        self.loading = True
        self.error = ""

        try:
            # Parse filters
            start_date = None
            end_date = None
            min_amount = None
            max_amount = None

            if self.filter_start_date:
                start_date = date.fromisoformat(self.filter_start_date)
            if self.filter_end_date:
                end_date = date.fromisoformat(self.filter_end_date)
            if self.filter_min_amount:
                min_amount = float(self.filter_min_amount)
            if self.filter_max_amount:
                max_amount = float(self.filter_max_amount)

            # Get transactions
            df = transaction_service.get_transactions(
                self.db_path,
                account_id=self.filter_account_id,
                start_date=start_date,
                end_date=end_date,
                category=self.filter_category if self.filter_category else None,
                min_amount=min_amount,
                max_amount=max_amount,
                is_categorized=False if self.filter_uncategorized_only else None,
            )

            # Enrich transactions with hierarchical category display names
            transactions = df.to_dicts()
            for txn in transactions:
                if txn.get("category"):
                    txn["category_display"] = category_service.get_category_display_name(
                        self.db_path, txn["category"]
                    )
                else:
                    txn["category_display"] = None

            # Apply search filter if search query exists
            if self.search_query:
                query = self.search_query.lower()
                transactions = [
                    txn for txn in transactions
                    if query in txn.get("payee", "").lower()
                    or query in txn.get("notes", "").lower()
                    or query in txn.get("category", "").lower()
                    or query in txn.get("category_display", "").lower()
                ]

            self.transactions = transactions
        except Exception as e:
            self.error = f"Failed to load transactions: {str(e)}"
        finally:
            self.loading = False

    def load_categories(self) -> None:
        """Load available categories with hierarchical display names."""
        try:
            df = category_service.get_categories(self.db_path)
            categories = df.to_dicts()

            # Build list of display names and mapping
            display_names = []
            display_map = {}

            for cat in categories:
                display_name = category_service.get_category_display_name(
                    self.db_path, cat["name"]
                )
                display_names.append(display_name)
                display_map[display_name] = cat["name"]

            self.categories = display_names
            self.category_display_map = display_map
        except Exception as e:
            self.error = f"Failed to load categories: {str(e)}"

    def update_category(self, transaction_id: int, category: str) -> None:
        """Update single transaction category."""
        try:
            # Convert display name to actual category name
            actual_category = self.category_display_map.get(category, category)

            transaction_service.update_transaction_category(
                self.db_path,
                transaction_id,
                actual_category,
            )
            self.load_transactions()
        except Exception as e:
            self.error = f"Failed to update category: {str(e)}"

    def bulk_update_categories(self) -> None:
        """Update categories for selected transactions."""
        if not self.selected_ids or not self.bulk_category:
            self.error = "Select transactions and category"
            return

        try:
            # Convert display name to actual category name
            actual_category = self.category_display_map.get(
                self.bulk_category, self.bulk_category
            )

            transaction_service.bulk_update_categories(
                self.db_path,
                self.selected_ids,
                actual_category,
            )
            self.selected_ids = []
            self.bulk_category = ""
            self.load_transactions()
        except Exception as e:
            self.error = f"Failed to update categories: {str(e)}"

    def toggle_selection(self, transaction_id: int) -> None:
        """Toggle transaction selection."""
        if transaction_id in self.selected_ids:
            self.selected_ids.remove(transaction_id)
        else:
            self.selected_ids.append(transaction_id)

    def clear_filters(self) -> None:
        """Clear all filters."""
        self.filter_account_id = None
        self.filter_start_date = ""
        self.filter_end_date = ""
        self.filter_category = ""
        self.filter_min_amount = ""
        self.filter_max_amount = ""
        self.filter_uncategorized_only = False
        self.search_query = ""
        self.load_transactions()

    def clear_search(self) -> None:
        """Clear only the search query."""
        self.search_query = ""
        self.load_transactions()

    def set_last_30_days(self) -> None:
        """Set filter to last 30 days."""
        end = date.today()
        start = end - timedelta(days=30)
        self.filter_start_date = start.isoformat()
        self.filter_end_date = end.isoformat()
        self.load_transactions()
