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

    # Inline subcategory creation
    adding_subcategory_to: str = ""  # Parent name when adding inline subcategory
    inline_subcategory_name: str = ""

    # Delete confirmation
    confirm_delete_id: int | None = None

    # Delete all confirmation
    show_delete_all_dialog: bool = False
    delete_all_confirm_text: str = ""

    @rx.var
    def parent_category_options(self) -> list[str]:
        """Get list of parent categories for dropdown."""
        parents = [c for c in self.categories if c.get("parent_category") is None]
        return ["(None)"] + [p["name"] for p in parents]

    @rx.var
    def parent_categories(self) -> list[dict]:
        """Get only parent categories (no parent_category field)."""
        return [c for c in self.categories if c.get("parent_category") is None]

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
            categories = df.to_dicts()
            logger.info(f"Loaded {len(categories)} categories")

            # Create a map of parent names to colors for quick lookup
            parent_colors = {
                cat["name"]: cat["color"]
                for cat in categories
                if cat.get("parent_category") is None
            }

            # Update subcategories to use their parent's color
            for cat in categories:
                if cat.get("parent_category"):
                    parent_name = cat["parent_category"]
                    if parent_name in parent_colors:
                        cat["color"] = parent_colors[parent_name]
                        logger.info(f"Subcategory '{cat['name']}' inheriting color from '{parent_name}': {cat['color']}")

            self.categories = categories

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

            # If this is a subcategory, inherit parent's color
            if parent:
                color = category_service.get_parent_color(self.db_path, parent)
                logger.info(f"Subcategory inheriting color from parent '{parent}': {color}")
            else:
                color = self.form_color
                logger.info(f"Parent category using selected color: {color}")

            category = Category(
                name=self.form_name,
                parent_category=parent,
                color=color,
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

    def add_subcategory(self, parent_name: str) -> None:
        """Start adding a subcategory inline."""
        logger.info(f"Starting inline subcategory creation under '{parent_name}'")
        self.adding_subcategory_to = parent_name
        self.inline_subcategory_name = ""
        self.error = ""
        self.success = ""

    def create_inline_subcategory(self) -> None:
        """Create subcategory from inline form."""
        if not self.inline_subcategory_name or not self.adding_subcategory_to:
            self.error = "Subcategory name is required"
            return

        self.loading = True
        self.error = ""
        self.success = ""

        try:
            # Get parent's color
            color = category_service.get_parent_color(self.db_path, self.adding_subcategory_to)

            category = Category(
                name=self.inline_subcategory_name,
                parent_category=self.adding_subcategory_to,
                color=color,
            )

            new_id = category_service.create_category(self.db_path, category)
            self.success = f"Subcategory '{self.inline_subcategory_name}' created successfully"
            logger.info(f"Inline subcategory created with ID {new_id}")

            # Clear inline form
            self.cancel_inline_subcategory()
            self.load_categories()
        except Exception as e:
            self.error = f"Failed to create subcategory: {str(e)}"
            log_error("create_inline_subcategory", e)
        finally:
            self.loading = False

    def cancel_inline_subcategory(self) -> None:
        """Cancel inline subcategory creation."""
        self.adding_subcategory_to = ""
        self.inline_subcategory_name = ""
        self.error = ""

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

    def open_delete_all_dialog(self) -> None:
        """Open the delete-all confirmation dialog."""
        self.show_delete_all_dialog = True
        self.delete_all_confirm_text = ""
        self.error = ""
        self.success = ""

    def close_delete_all_dialog(self) -> None:
        """Close the delete-all confirmation dialog."""
        self.show_delete_all_dialog = False
        self.delete_all_confirm_text = ""

    def handle_delete_all_dialog_open_change(self, is_open: bool) -> None:
        """Handle dialog open state change."""
        if not is_open:
            self.close_delete_all_dialog()

    def delete_all_categories(self) -> None:
        """Delete all categories after confirmation."""
        if self.delete_all_confirm_text.strip().lower() != "delete":
            self.error = "Please type 'delete' to confirm"
            return

        self.loading = True
        self.error = ""
        self.success = ""

        try:
            category_service.delete_all_categories(self.db_path)
            self.close_delete_all_dialog()
            self.load_categories()
            self.success = "All categories deleted"
        except Exception as e:
            self.error = f"Failed to delete categories: {str(e)}"
            log_error("delete_all_categories", e)
        finally:
            self.loading = False

    def seed_default_german(self) -> None:
        """Add German default categories, skipping existing ones."""
        self.loading = True
        self.error = ""
        self.success = ""

        try:
            added, skipped = category_service.seed_default_categories_german(self.db_path)
            self.load_categories()
            if added == 0:
                self.success = f"All default categories already exist ({skipped} skipped)"
            else:
                self.success = f"{added} categories added, {skipped} skipped"
        except Exception as e:
            self.error = f"Failed to add categories: {str(e)}"
            log_error("seed_default_german", e)
        finally:
            self.loading = False
