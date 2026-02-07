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


def inline_subcategory_form() -> rx.Component:
    """Inline form for adding subcategory."""
    return rx.box(
        rx.hstack(
            # Indentation to align with subcategories
            rx.box(width="24px"),
            rx.text("└─", size="2", color="gray"),
            # Input field
            rx.input(
                placeholder="Enter subcategory name...",
                value=CategoryState.inline_subcategory_name,
                on_change=CategoryState.set_inline_subcategory_name,
                size="2",
                flex="1",
                auto_focus=True,
            ),
            # Action buttons
            rx.button(
                rx.icon("check", size=14),
                on_click=CategoryState.create_inline_subcategory,
                size="1",
                color="green",
                loading=CategoryState.loading,
            ),
            rx.button(
                rx.icon("x", size=14),
                on_click=CategoryState.cancel_inline_subcategory,
                size="1",
                variant="soft",
            ),
            spacing="2",
            width="100%",
            align="center",
        ),
        padding="8px 12px",
        background="rgba(0, 128, 0, 0.05)",
        border_radius="6px",
        margin_top="4px",
    )


def color_swatch(color: str) -> rx.Component:
    """Individual color swatch button - modern design."""
    return rx.box(
        # Check icon when selected
        rx.cond(
            CategoryState.form_color == color,
            rx.icon("check", size=18, color="white", weight="bold"),
        ),
        background=color,
        width="48px",
        height="48px",
        border_radius="12px",
        cursor="pointer",
        border=rx.cond(
            CategoryState.form_color == color,
            "3px solid #000",
            "2px solid rgba(0, 0, 0, 0.08)"
        ),
        display="flex",
        align_items="center",
        justify_content="center",
        on_click=CategoryState.select_color(color),
        box_shadow=rx.cond(
            CategoryState.form_color == color,
            "0 4px 12px rgba(0, 0, 0, 0.15)",
            "0 2px 4px rgba(0, 0, 0, 0.05)"
        ),
        _hover={
            "transform": "translateY(-2px)",
            "box_shadow": "0 6px 16px rgba(0, 0, 0, 0.12)",
            "border": "2px solid rgba(0, 0, 0, 0.2)",
        },
        transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
    )


def color_palette_picker() -> rx.Component:
    """Modern color palette with preset colors."""
    return rx.vstack(
        rx.hstack(
            rx.icon("palette", size=18),
            rx.text("Quick Colors", size="3", weight="bold"),
            spacing="2",
            align="center",
        ),
        rx.box(
            rx.grid(
                *[color_swatch(color) for color in COLOR_PALETTE],
                columns="8",
                spacing="3",
                width="100%",
            ),
            padding="12px",
            border_radius="12px",
            background="rgba(0, 0, 0, 0.02)",
            border="1px solid rgba(0, 0, 0, 0.06)",
        ),
        spacing="3",
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
            # Show parent info if adding subcategory
            rx.cond(
                (CategoryState.form_parent_category != "(None)") & (CategoryState.form_parent_category != ""),
                rx.callout(
                    rx.text(
                        ["Adding subcategory under: ", rx.text(CategoryState.form_parent_category, weight="bold")],
                        size="2",
                    ),
                    icon="info",
                    color_scheme="blue",
                    size="1",
                ),
            ),
            # Color picker (only for parent categories)
            rx.cond(
                (CategoryState.form_parent_category == "(None)") | (CategoryState.form_parent_category == ""),
                rx.vstack(
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
                    spacing="3",
                    width="100%",
                ),
                # Info for subcategories
                rx.callout(
                    "Subcategories inherit their parent category's color",
                    icon="info",
                    color_scheme="blue",
                    size="1",
                ),
            ),
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


def subcategory_item(category: dict) -> rx.Component:
    """Subcategory item with indentation and subtle styling."""
    return rx.hstack(
        # Indentation spacer
        rx.box(width="24px"),
        # Tree connector
        rx.text("└─", size="2", color="gray"),
        # Subtle color dot
        rx.box(
            width="8px",
            height="8px",
            background=category["color"],
            border_radius="50%",
            flex_shrink="0",
        ),
        # Category name
        rx.text(
            category["name"],
            size="3",
            weight="medium",
            flex="1",
        ),
        # Actions
        rx.hstack(
            rx.button(
                rx.icon("pencil", size=14),
                on_click=lambda: CategoryState.edit_category(category["id"]),
                size="1",
                variant="ghost",
            ),
            rx.button(
                rx.icon("trash-2", size=14),
                on_click=lambda: CategoryState.confirm_delete(category["id"]),
                size="1",
                variant="ghost",
                color="red",
            ),
            spacing="1",
        ),
        spacing="2",
        width="100%",
        align="center",
        padding="8px 12px",
        border_radius="6px",
        _hover={
            "background": "rgba(0, 0, 0, 0.02)",
        },
    )


def parent_category_item(parent: dict) -> rx.Component:
    """Parent category with prominent styling."""
    return rx.hstack(
        # Prominent color indicator (circle)
        rx.box(
            width="12px",
            height="12px",
            background=parent["color"],
            border_radius="50%",
            flex_shrink="0",
        ),
        # Parent category name (larger, bolder)
        rx.text(
            parent["name"],
            size="4",
            weight="bold",
            flex="1",
        ),
        # Actions
        rx.hstack(
            rx.tooltip(
                rx.button(
                    rx.icon("plus", size=16),
                    on_click=lambda: CategoryState.add_subcategory(parent["name"]),
                    size="1",
                    variant="soft",
                    color="green",
                ),
                content="Add subcategory",
            ),
            rx.tooltip(
                rx.button(
                    rx.icon("pencil", size=16),
                    on_click=lambda: CategoryState.edit_category(parent["id"]),
                    size="1",
                    variant="soft",
                ),
                content="Edit category",
            ),
            rx.tooltip(
                rx.button(
                    rx.icon("trash-2", size=16),
                    on_click=lambda: CategoryState.confirm_delete(parent["id"]),
                    size="1",
                    variant="soft",
                    color="red",
                ),
                content="Delete category",
            ),
            spacing="2",
        ),
        spacing="3",
        width="100%",
        align="center",
        padding="12px",
        border_radius="8px",
        background=f"color-mix(in srgb, {parent['color']} 5%, transparent)",
        border=f"1px solid color-mix(in srgb, {parent['color']} 20%, transparent)",
    )


def subcategory_item_filtered(category: dict, parent_name: str) -> rx.Component:
    """Render subcategory only if it belongs to the given parent."""
    return rx.cond(
        category.get("parent_category") == parent_name,
        subcategory_item(category),
        rx.box(),  # Empty if not matching
    )


def subcategory_with_parent_color(category: dict, parent_color: str) -> rx.Component:
    """Subcategory item using parent's color."""
    return rx.hstack(
        # Indentation spacer
        rx.box(width="24px"),
        # Tree connector
        rx.text("└─", size="2", color="gray"),
        # Subtle color dot (using parent color)
        rx.box(
            width="8px",
            height="8px",
            background=parent_color,
            border_radius="50%",
            flex_shrink="0",
        ),
        # Category name
        rx.text(
            category["name"],
            size="3",
            weight="medium",
            flex="1",
        ),
        # Actions
        rx.hstack(
            rx.button(
                rx.icon("pencil", size=14),
                on_click=lambda: CategoryState.edit_category(category["id"]),
                size="1",
                variant="ghost",
            ),
            rx.button(
                rx.icon("trash-2", size=14),
                on_click=lambda: CategoryState.confirm_delete(category["id"]),
                size="1",
                variant="ghost",
                color="red",
            ),
            spacing="1",
        ),
        spacing="2",
        width="100%",
        align="center",
        padding="8px 12px",
        border_radius="6px",
        _hover={
            "background": "rgba(0, 0, 0, 0.02)",
        },
    )


def parent_with_children_card(parent: dict) -> rx.Component:
    """Display parent category with its children grouped in a card."""
    return rx.card(
        rx.vstack(
            # Parent category as header
            rx.hstack(
                # Prominent color indicator
                rx.box(
                    width="12px",
                    height="12px",
                    background=parent["color"],
                    border_radius="50%",
                    flex_shrink="0",
                ),
                # Parent name (header style)
                rx.text(
                    parent["name"],
                    size="5",
                    weight="bold",
                    flex="1",
                ),
                # Actions
                rx.hstack(
                    rx.tooltip(
                        rx.button(
                            rx.icon("plus", size=16),
                            on_click=lambda: CategoryState.add_subcategory(parent["name"]),
                            size="1",
                            variant="soft",
                            color="green",
                        ),
                        content="Add subcategory",
                    ),
                    rx.tooltip(
                        rx.button(
                            rx.icon("pencil", size=16),
                            on_click=lambda: CategoryState.edit_category(parent["id"]),
                            size="1",
                            variant="soft",
                        ),
                        content="Edit category",
                    ),
                    rx.tooltip(
                        rx.button(
                            rx.icon("trash-2", size=16),
                            on_click=lambda: CategoryState.confirm_delete(parent["id"]),
                            size="1",
                            variant="soft",
                            color="red",
                        ),
                        content="Delete category",
                    ),
                    spacing="2",
                ),
                spacing="3",
                width="100%",
                align="center",
            ),
            # Divider
            rx.divider(),
            # Inline subcategory form (shown when adding to this parent)
            rx.cond(
                CategoryState.adding_subcategory_to == parent["name"],
                inline_subcategory_form(),
            ),
            # Children categories (using parent color)
            rx.vstack(
                rx.foreach(
                    CategoryState.categories,
                    lambda cat: rx.cond(
                        cat.get("parent_category") == parent["name"],
                        subcategory_with_parent_color(cat, parent["color"]),
                        rx.fragment(),
                    ),
                ),
                spacing="1",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
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


def delete_all_dialog() -> rx.Component:
    """Dialog to confirm deleting all categories."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Delete All Categories"),
            rx.dialog.description(
                "This will delete all categories and uncategorize all transactions. "
                "This action cannot be undone.",
                color="red",
            ),
            rx.vstack(
                rx.text("Type 'delete' to confirm:", size="2", weight="bold"),
                rx.input(
                    placeholder="delete",
                    value=CategoryState.delete_all_confirm_text,
                    on_change=CategoryState.set_delete_all_confirm_text,
                    width="100%",
                ),
                rx.cond(
                    CategoryState.error != "",
                    rx.callout(
                        CategoryState.error,
                        icon="triangle_alert",
                        color_scheme="red",
                        size="1",
                    ),
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                        ),
                    ),
                    rx.button(
                        rx.icon("trash-2", size=16),
                        "Delete All",
                        on_click=CategoryState.delete_all_categories,
                        color_scheme="red",
                        loading=CategoryState.loading,
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
                padding_top="16px",
            ),
        ),
        open=CategoryState.show_delete_all_dialog,
        on_open_change=CategoryState.handle_delete_all_dialog_open_change,
    )


@rx.page(route="/categories", on_load=CategoryState.load_categories)
def categories_page() -> rx.Component:
    """Categories management page."""
    return layout(
        rx.vstack(
            rx.hstack(
                rx.heading("Categories", size="8"),
                rx.spacer(),
                rx.button(
                    rx.icon("list-plus", size=18),
                    "German Defaults",
                    on_click=CategoryState.seed_default_german,
                    size="2",
                    variant="soft",
                    loading=CategoryState.loading,
                ),
                rx.button(
                    rx.icon("trash-2", size=18),
                    "Delete All",
                    on_click=CategoryState.open_delete_all_dialog,
                    size="2",
                    variant="soft",
                    color_scheme="red",
                ),
                width="100%",
                align="center",
            ),
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
                                        CategoryState.parent_categories,
                                        parent_with_children_card
                                    ),
                                    spacing="4",
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
            delete_all_dialog(),
            spacing="4",
            width="100%",
        ),
    )
