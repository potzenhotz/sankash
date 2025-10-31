"""Category page state management."""

import reflex as rx

from sankash.core.logger import logger, log_state_change, log_error
from sankash.core.models import Category
from sankash.services import category_service
from sankash.state.base import BaseState


class CategoryState(BaseState):
    """State for category management page."""

    state_auto_setters = True  # Explicitly enable auto setters

    categories: list[dict] = []
    hierarchy: list[dict] = []
    loading: bool = False
    error: str = ""
    success: str = ""

    # Form fields
    form_name: str = ""
    form_parent_category: str = ""
    form_color: str = "#6366f1"
    editing_id: int | None = None

    # Delete confirmation
    confirm_delete_id: int | None = None

    @rx.var
    def parent_category_options(self) -> list[str]:
        """Get list of parent categories for dropdown."""
        parents = [c for c in self.categories if c.get("parent_category") is None]
        return ["(None)"] + [p["name"] for p in parents]

    @rx.var
    def is_editing(self) -> bool:
        """Check if currently editing a category."""
        return self.editing_id is not None

    def load_categories(self) -> None:
        """Load categories and build hierarchy."""
        logger.info("Loading categories...")
        self.loading = True
        self.error = ""

        try:
            # Load all categories
            df = category_service.get_categories(self.db_path)
            self.categories = df.to_dicts()
            logger.info(f"Loaded {len(self.categories)} categories")

            # Build hierarchy
            self.hierarchy = category_service.get_category_hierarchy(self.db_path)
            logger.info(f"Built hierarchy with {len(self.hierarchy)} parent categories")
        except Exception as e:
            self.error = f"Failed to load categories: {str(e)}"
            log_error("load_categories", e)
        finally:
            self.loading = False

    def create_or_update_category(self) -> None:
        """Create new category or update existing one."""
        logger.info(f"create_or_update_category called - name='{self.form_name}', parent='{self.form_parent_category}', color='{self.form_color}', editing_id={self.editing_id}")

        if not self.form_name:
            self.error = "Category name is required"
            logger.warning("Category creation failed: name is required")
            return

        self.loading = True
        self.error = ""
        self.success = ""

        try:
            # Prepare parent category (None if "(None)" selected)
            parent = None if self.form_parent_category == "(None)" or not self.form_parent_category else self.form_parent_category
            logger.info(f"Prepared parent category: {parent}")

            category = Category(
                name=self.form_name,
                parent_category=parent,
                color=self.form_color,
            )

            if self.editing_id:
                # Update existing
                logger.info(f"Updating category ID {self.editing_id}")
                category_service.update_category(self.db_path, self.editing_id, category)
                self.success = f"Category '{self.form_name}' updated successfully"
                logger.info(f"Category updated successfully")
            else:
                # Create new
                logger.info(f"Creating new category: {category}")
                new_id = category_service.create_category(self.db_path, category)
                self.success = f"Category '{self.form_name}' created successfully"
                logger.info(f"Category created successfully with ID {new_id}")

            self.clear_form()
            self.load_categories()
        except Exception as e:
            self.error = f"Failed to save category: {str(e)}"
            log_error("create_or_update_category", e)
        finally:
            self.loading = False

    def edit_category(self, category_id: int) -> None:
        """Load category data into form for editing."""
        category = next((c for c in self.categories if c["id"] == category_id), None)
        if category:
            self.editing_id = category_id
            self.form_name = category["name"]
            self.form_parent_category = category.get("parent_category") or "(None)"
            self.form_color = category.get("color", "#6366f1")
            self.error = ""
            self.success = ""

    def confirm_delete(self, category_id: int) -> None:
        """Show delete confirmation dialog."""
        self.confirm_delete_id = category_id

    def cancel_delete(self) -> None:
        """Cancel delete operation."""
        self.confirm_delete_id = None

    def delete_category(self) -> None:
        """Delete the confirmed category."""
        if not self.confirm_delete_id:
            return

        self.loading = True
        self.error = ""

        try:
            # Get category name for success message
            category = next(
                (c for c in self.categories if c["id"] == self.confirm_delete_id),
                None
            )
            category_name = category["name"] if category else "Category"

            category_service.delete_category(self.db_path, self.confirm_delete_id)
            self.success = f"'{category_name}' deleted successfully"
            self.confirm_delete_id = None
            self.load_categories()
        except Exception as e:
            self.error = f"Failed to delete category: {str(e)}"
        finally:
            self.loading = False

    def clear_form(self) -> None:
        """Clear form fields."""
        logger.info("Clearing form")
        self.form_name = ""
        self.form_parent_category = "(None)"
        self.form_color = "#6366f1"
        self.editing_id = None
        self.error = ""
        self.success = ""

    def select_color(self, color: str) -> None:
        """Set form color from palette."""
        logger.info(f"Color selected from palette: {color}")
        self.form_color = color
