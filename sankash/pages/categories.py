"""Categories management page."""

import reflex as rx

from sankash.components.layout import layout
from sankash.state.category_state import CategoryState


# Kanagawa-inspired color palette
COLOR_PALETTE = [
    "#16161d",  # 0 - Dark background
    "#c34043",  # 1 - Red
    "#76946a",  # 2 - Green
    "#c0a36e",  # 3 - Yellow/Gold
    "#7e9cd8",  # 4 - Blue
    "#957fb8",  # 5 - Purple
    "#6a9589",  # 6 - Cyan/Teal
    "#c8c093",  # 7 - Light beige
    "#727169",  # 8 - Gray
    "#e82424",  # 9 - Bright red
    "#98bb6c",  # 10 - Bright green
    "#e6c384",  # 11 - Bright yellow
    "#7fb4ca",  # 12 - Bright blue
    "#938aa9",  # 13 - Bright purple
    "#7aa89f",  # 14 - Bright cyan
    "#dcd7ba",  # 15 - Light cream
]


def color_swatch(color: str) -> rx.Component:
    """Individual color swatch button."""
    return rx.box(
        rx.cond(
            CategoryState.form_color == color,
            rx.icon("check", size=16, color="white"),
        ),
        background=color,
        width="40px",
        height="40px",
        border_radius="6px",
        cursor="pointer",
        border=rx.cond(
            CategoryState.form_color == color,
            "2px solid #000",
            "1px solid #e5e7eb"
        ),
        display="flex",
        align_items="center",
        justify_content="center",
        on_click=CategoryState.select_color(color),
        _hover={
            "transform": "scale(1.1)",
            "box_shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
        },
        transition="all 0.2s ease",
    )


def color_palette_picker() -> rx.Component:
    """Color palette with preset colors in a grid."""
    return rx.vstack(
        rx.text("Quick Color Palette", size="2", weight="bold"),
        rx.grid(
            *[color_swatch(color) for color in COLOR_PALETTE],
            columns="8",
            spacing="2",
            width="100%",
        ),
        spacing="2",
        width="100%",
    )


def category_form() -> rx.Component:
    """Category creation/edit form (functional component)."""
    return rx.card(
        rx.vstack(
            rx.heading(
                rx.cond(
                    CategoryState.is_editing,
                    "Edit Category",
                    "Add New Category"
                ),
                size="4"
            ),
            # Name input
            rx.vstack(
                rx.text("Category Name", size="2", weight="bold"),
                rx.input(
                    placeholder="e.g., Groceries",
                    value=CategoryState.form_name,
                    on_change=CategoryState.set_form_name,
                    width="100%",
                ),
                spacing="1",
                width="100%",
            ),
            # Parent category dropdown
            rx.vstack(
                rx.text("Parent Category (Optional)", size="2", weight="bold"),
                rx.select(
                    CategoryState.parent_category_options,
                    placeholder="Select parent",
                    value=CategoryState.form_parent_category,
                    on_change=CategoryState.set_form_parent_category,
                ),
                rx.text(
                    "Leave as '(None)' for a top-level category",
                    size="1",
                    color="gray",
                ),
                spacing="1",
                width="100%",
            ),
            # Color picker
            rx.vstack(
                rx.text("Color", size="2", weight="bold"),
                rx.hstack(
                    rx.input(
                        type="color",
                        value=CategoryState.form_color,
                        on_change=CategoryState.set_form_color,
                        width="80px",
                    ),
                    rx.input(
                        value=CategoryState.form_color,
                        on_change=CategoryState.set_form_color,
                        placeholder="#6366f1",
                        width="120px",
                    ),
                    spacing="2",
                ),
                spacing="1",
                width="100%",
            ),
            # Color palette picker
            color_palette_picker(),
            # Messages
            rx.cond(
                CategoryState.error != "",
                rx.text(CategoryState.error, color="red", size="2"),
            ),
            rx.cond(
                CategoryState.success != "",
                rx.text(CategoryState.success, color="green", size="2"),
            ),
            # Actions
            rx.hstack(
                rx.button(
                    rx.cond(
                        CategoryState.is_editing,
                        "Update Category",
                        "Create Category"
                    ),
                    on_click=CategoryState.create_or_update_category,
                    size="2",
                    loading=CategoryState.loading,
                ),
                rx.cond(
                    CategoryState.is_editing,
                    rx.button(
                        "Cancel",
                        on_click=CategoryState.clear_form,
                        size="2",
                        variant="soft",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )


def category_item(category: dict, is_subcategory: bool = False) -> rx.Component:
    """Single category item (functional component)."""
    return rx.card(
        rx.hstack(
            # Color indicator
            rx.box(
                width="4px",
                height="100%",
                background=category["color"],
                border_radius="2px",
            ),
            # Category info
            rx.vstack(
                rx.hstack(
                    rx.cond(
                        is_subcategory,
                        rx.text("  └─", size="2", color="gray"),
                    ),
                    rx.text(
                        category["name"],
                        size="3",
                        weight="bold",
                    ),
                    rx.cond(
                        category.get("parent_category") is not None,
                        rx.badge(
                            f"under {category['parent_category']}",
                            variant="soft",
                            size="1",
                        ),
                    ),
                    spacing="2",
                ),
                spacing="1",
                flex="1",
            ),
            # Actions
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=16),
                    on_click=lambda: CategoryState.edit_category(category["id"]),
                    size="1",
                    variant="soft",
                ),
                rx.button(
                    rx.icon("trash-2", size=16),
                    on_click=lambda: CategoryState.confirm_delete(category["id"]),
                    size="1",
                    variant="soft",
                    color="red",
                ),
                spacing="2",
            ),
            spacing="3",
            width="100%",
            align="center",
        ),
        width="100%",
    )


def category_display_item(category: dict) -> rx.Component:
    """Category display item with visual hierarchy indication."""
    return category_item(
        category,
        is_subcategory=category.get("parent_category") is not None
    )


def delete_confirmation_dialog() -> rx.Component:
    """Delete confirmation dialog."""
    return rx.cond(
        CategoryState.confirm_delete_id != None,
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Delete Category"),
                rx.dialog.description(
                    "Are you sure you want to delete this category? "
                    "All transactions using this category will be uncategorized."
                ),
                rx.flex(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color="gray",
                            on_click=CategoryState.cancel_delete,
                        ),
                    ),
                    rx.dialog.close(
                        rx.button(
                            "Delete",
                            color="red",
                            on_click=CategoryState.delete_category,
                        ),
                    ),
                    spacing="3",
                    justify="end",
                ),
            ),
            open=True,
        ),
    )


@rx.page(route="/categories", on_load=CategoryState.load_categories)
def categories_page() -> rx.Component:
    """Categories management page."""
    return layout(
        rx.vstack(
            rx.heading("Categories", size="8"),
            rx.text(
                "Manage your transaction categories and subcategories",
                color="gray",
                size="3"
            ),
            rx.divider(),
            rx.grid(
                # Left column: Form
                category_form(),
                # Right column: Category list
                rx.card(
                    rx.vstack(
                        rx.heading("Your Categories", size="4"),
                        rx.cond(
                            CategoryState.loading,
                            rx.spinner(),
                            rx.cond(
                                CategoryState.categories.length() == 0,
                                rx.text("No categories yet. Create one to get started!", color="gray"),
                                rx.vstack(
                                    rx.foreach(
                                        CategoryState.categories,
                                        category_display_item
                                    ),
                                    spacing="3",
                                    width="100%",
                                ),
                            ),
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),
            delete_confirmation_dialog(),
            spacing="4",
            width="100%",
        ),
    )
