"""Transaction page state management."""

from datetime import date, timedelta

import reflex as rx

from sankash.core.models import Rule, RuleAction, RuleCondition
from sankash.services import transaction_service, category_service, rule_service
from sankash.state.base import BaseState


class TransactionState(BaseState):
    """State for transaction management page."""

    state_auto_setters = True  # Explicitly enable auto setters

    transactions: list[dict] = []
    categories: list[str] = []
    category_display_map: dict[str, str] = {}  # Maps display name -> actual name
    _reverse_category_map: dict[str, str] = {}  # Maps actual name -> display name
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

    # Sorting
    sort_by: str = "date"  # "date" or "amount"
    sort_order: str = "desc"  # "asc" or "desc"

    # Pagination
    current_page: int = 1
    page_size: int = 50
    total_count: int = 0

    @rx.var
    def total_pages(self) -> int:
        if self.total_count == 0:
            return 1
        return (self.total_count + self.page_size - 1) // self.page_size

    # Selection
    selected_ids: list[int] = []
    bulk_category: str = ""

    # Editing
    editing_id: int | None = None
    edit_category: str = ""
    edit_payee: str = ""
    edit_notes: str = ""

    # Rule dialog
    show_rule_dialog: bool = False
    rule_form_name: str = ""
    rule_form_match_type: str = "all"
    rule_form_conditions: list[dict] = []  # Each: {field, operator, value}
    rule_form_action_type: str = "set_category"
    rule_form_action_value: str = ""
    rule_form_error: str = ""
    rule_form_success: str = ""

    # Delete all confirmation
    show_delete_all_dialog: bool = False
    delete_all_confirm_text: str = ""

    def load_transactions(self) -> None:
        """Load transactions with current filters, search, sort, and pagination."""
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

            # Get paginated transactions (search, sort, pagination all in SQL)
            df, total_count = transaction_service.get_transactions(
                self.data_dir,
                account_id=self.filter_account_id,
                start_date=start_date,
                end_date=end_date,
                category=self.filter_category if self.filter_category else None,
                min_amount=min_amount,
                max_amount=max_amount,
                is_categorized=False if self.filter_uncategorized_only else None,
                search_query=self.search_query if self.search_query else None,
                sort_by=self.sort_by,
                sort_order=self.sort_order,
                limit=self.page_size,
                offset=(self.current_page - 1) * self.page_size,
            )

            self.total_count = total_count

            # Enrich transactions with category display names using in-memory map
            # (avoids N+1 DB queries — uses reverse_category_map built by load_categories)
            reverse_map = self._reverse_category_map
            transactions = df.to_dicts()
            for txn in transactions:
                cat = txn.get("category")
                txn["category_display"] = reverse_map.get(cat) if cat else None

            self.transactions = transactions
        except Exception as e:
            self.error = f"Failed to load transactions: {str(e)}"
        finally:
            self.loading = False

    def load_categories(self) -> None:
        """Load available categories with hierarchical display names."""
        try:
            df = category_service.get_categories(self.data_dir)
            categories = df.to_dicts()

            # Build display names and both forward/reverse mappings in one pass
            display_names = []
            display_map = {}  # display name -> actual name
            reverse_map = {}  # actual name -> display name

            for cat in categories:
                name = cat["name"]
                parent = cat.get("parent_category")
                display_name = f"{parent} > {name}" if parent else name
                display_names.append(display_name)
                display_map[display_name] = name
                reverse_map[name] = display_name

            # Sort categories alphabetically
            display_names.sort()

            self.categories = display_names
            self.category_display_map = display_map
            self._reverse_category_map = reverse_map
        except Exception as e:
            self.error = f"Failed to load categories: {str(e)}"

    # --- Pagination Methods ---

    def next_page(self) -> None:
        """Go to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_transactions()

    def prev_page(self) -> None:
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_transactions()

    def go_to_page(self, page: int) -> None:
        """Go to a specific page."""
        page = max(1, min(page, self.total_pages))
        self.current_page = page
        self.load_transactions()

    def update_category(self, transaction_id: int, category: str) -> None:
        """Update single transaction category."""
        try:
            # Convert display name to actual category name
            actual_category = self.category_display_map.get(category, category)

            transaction_service.update_transaction_category(
                self.data_dir,
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
                self.data_dir,
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
        self.current_page = 1
        self.load_transactions()

    def clear_search(self) -> None:
        """Clear only the search query."""
        self.search_query = ""
        self.current_page = 1
        self.load_transactions()

    def apply_filters(self) -> None:
        """Apply filters and reset to page 1."""
        self.current_page = 1
        self.load_transactions()

    def apply_search(self) -> None:
        """Apply search and reset to page 1."""
        self.current_page = 1
        self.load_transactions()

    def set_last_30_days(self) -> None:
        """Set filter to last 30 days."""
        end = date.today()
        start = end - timedelta(days=30)
        self.filter_start_date = start.isoformat()
        self.filter_end_date = end.isoformat()
        self.current_page = 1
        self.load_transactions()

    def toggle_sort_by_date(self) -> None:
        """Toggle date column sorting."""
        if self.sort_by == "date":
            self.sort_order = "asc" if self.sort_order == "desc" else "desc"
        else:
            self.sort_by = "date"
            self.sort_order = "desc"
        self.current_page = 1
        self.load_transactions()

    def toggle_sort_by_amount(self) -> None:
        """Toggle amount column sorting."""
        if self.sort_by == "amount":
            self.sort_order = "asc" if self.sort_order == "desc" else "desc"
        else:
            self.sort_by = "amount"
            self.sort_order = "desc"
        self.current_page = 1
        self.load_transactions()

    def apply_rules(self) -> None:
        """Apply all active rules to uncategorized transactions."""
        self.loading = True
        self.error = ""
        try:
            count = rule_service.apply_rules_to_uncategorized(self.data_dir)
            self.load_transactions()
            if count == 0:
                self.error = "No transactions matched any rules"
        except Exception as e:
            self.error = f"Failed to apply rules: {str(e)}"
        finally:
            self.loading = False

    # --- Rule Dialog Methods ---

    def open_rule_dialog(self, transaction_id: int) -> None:
        """Open rule creation dialog pre-filled from a transaction."""
        txn = None
        for t in self.transactions:
            if t.get("id") == transaction_id:
                txn = t
                break

        if txn is None:
            self.error = "Transaction not found"
            return

        payee = txn.get("payee", "")
        category_display = txn.get("category_display") or ""

        self.rule_form_name = f"Rule: {payee}"
        self.rule_form_match_type = "all"
        self.rule_form_conditions = [
            {"field": "payee", "operator": "contains", "value": payee}
        ]
        self.rule_form_action_type = "set_category"
        self.rule_form_action_value = category_display
        self.rule_form_error = ""
        self.rule_form_success = ""
        self.show_rule_dialog = True

    def close_rule_dialog(self) -> None:
        """Close rule dialog and reset form."""
        self.show_rule_dialog = False
        self.rule_form_name = ""
        self.rule_form_match_type = "all"
        self.rule_form_conditions = []
        self.rule_form_action_type = "set_category"
        self.rule_form_action_value = ""
        self.rule_form_error = ""
        self.rule_form_success = ""

    def handle_rule_dialog_open_change(self, is_open: bool) -> None:
        """Handle dialog open state change (Escape/outside click)."""
        if not is_open:
            self.close_rule_dialog()

    def rule_add_condition(self) -> None:
        """Add a new condition to rule form."""
        self.rule_form_conditions.append(
            {"field": "payee", "operator": "contains", "value": ""}
        )

    def rule_remove_condition(self, index: int) -> None:
        """Remove a condition from rule form by index."""
        if 0 <= index < len(self.rule_form_conditions):
            self.rule_form_conditions.pop(index)

    def rule_update_condition_field(self, index: int, val: str) -> None:
        """Update condition field at index."""
        if 0 <= index < len(self.rule_form_conditions):
            self.rule_form_conditions[index]["field"] = val

    def rule_update_condition_operator(self, index: int, val: str) -> None:
        """Update condition operator at index."""
        if 0 <= index < len(self.rule_form_conditions):
            self.rule_form_conditions[index]["operator"] = val

    def rule_update_condition_value(self, index: int, val: str) -> None:
        """Update condition value at index."""
        if 0 <= index < len(self.rule_form_conditions):
            self.rule_form_conditions[index]["value"] = val

    def submit_rule_from_dialog(self) -> None:
        """Create a rule from the dialog form."""
        self.rule_form_error = ""
        self.rule_form_success = ""

        if not self.rule_form_name:
            self.rule_form_error = "Rule name is required"
            return

        if not self.rule_form_conditions:
            self.rule_form_error = "At least one condition is required"
            return

        for cond in self.rule_form_conditions:
            if not cond.get("value"):
                self.rule_form_error = "All conditions must have a value"
                return

        if not self.rule_form_action_value:
            self.rule_form_error = "Please select a category"
            return

        try:
            # Convert display category to actual name
            actual_category = self.category_display_map.get(
                self.rule_form_action_value, self.rule_form_action_value
            )

            rule_conditions = [
                RuleCondition(
                    field=cond["field"],
                    operator=cond["operator"],
                    value=cond["value"],
                )
                for cond in self.rule_form_conditions
            ]

            rule = Rule(
                name=self.rule_form_name,
                priority=0,
                is_active=True,
                match_type=self.rule_form_match_type,
                conditions=rule_conditions,
                actions=[
                    RuleAction(
                        action_type=self.rule_form_action_type,
                        value=actual_category,
                    )
                ],
            )

            rule_service.create_rule(self.data_dir, rule)
            rule_service.apply_rules_to_uncategorized(self.data_dir)
            self.close_rule_dialog()
            self.load_transactions()
        except Exception as e:
            self.rule_form_error = f"Failed to create rule: {str(e)}"

    # --- Delete All Methods ---

    def open_delete_all_dialog(self) -> None:
        """Open the delete-all transactions confirmation dialog."""
        self.show_delete_all_dialog = True
        self.delete_all_confirm_text = ""
        self.error = ""

    def close_delete_all_dialog(self) -> None:
        """Close the delete-all dialog."""
        self.show_delete_all_dialog = False
        self.delete_all_confirm_text = ""

    def handle_delete_all_dialog_open_change(self, is_open: bool) -> None:
        """Handle dialog open state change."""
        if not is_open:
            self.close_delete_all_dialog()

    def delete_all_transactions(self) -> None:
        """Delete all transactions after confirmation."""
        if self.delete_all_confirm_text.strip().lower() != "delete":
            self.error = "Please type 'delete' to confirm"
            return

        self.loading = True
        self.error = ""

        try:
            transaction_service.delete_all_transactions(self.data_dir)
            self.close_delete_all_dialog()
            self.load_transactions()
        except Exception as e:
            self.error = f"Failed to delete transactions: {str(e)}"
        finally:
            self.loading = False
