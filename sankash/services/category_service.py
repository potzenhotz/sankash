"""Category service with pure functions."""

import polars as pl

from sankash.core.database import execute_command, execute_query
from sankash.core.models import Category


def get_categories(db_path: str) -> pl.DataFrame:
    """Get all categories (pure function)."""
    return execute_query(db_path, "SELECT * FROM categories ORDER BY name")


def get_category_by_name(db_path: str, name: str) -> pl.DataFrame:
    """Get category by name (pure function)."""
    return execute_query(
        db_path,
        "SELECT * FROM categories WHERE name = $name",
        {"name": name}
    )


def get_categories_with_spending(db_path: str) -> pl.DataFrame:
    """Get categories with total spending (pure function)."""
    query = """
    SELECT
        c.*,
        COALESCE(SUM(ABS(t.amount)), 0) as total_spending,
        COUNT(t.id) as transaction_count
    FROM categories c
    LEFT JOIN transactions t ON c.name = t.category
    GROUP BY c.id, c.name, c.parent_category, c.color, c.created_at
    ORDER BY total_spending DESC
    """
    return execute_query(db_path, query)


def create_category(db_path: str, category: Category) -> int:
    """Create new category and return its ID."""
    result = execute_query(
        db_path,
        """INSERT INTO categories (name, parent_category, color)
        VALUES ($name, $parent_category, $color)
        RETURNING id""",
        {
            "name": category.name,
            "parent_category": category.parent_category,
            "color": category.color,
        }
    )
    return int(result["id"][0])


def update_category(db_path: str, category_id: int, category: Category) -> None:
    """Update existing category, cascading name changes to children and transactions."""
    # Get the old name before updating
    old_df = execute_query(
        db_path,
        "SELECT name FROM categories WHERE id = $id",
        {"id": category_id},
    )
    old_name = old_df["name"][0] if not old_df.is_empty() else None

    execute_command(
        db_path,
        """UPDATE categories
        SET name = $name,
            parent_category = $parent_category,
            color = $color
        WHERE id = $id""",
        {
            "id": category_id,
            "name": category.name,
            "parent_category": category.parent_category,
            "color": category.color,
        }
    )

    # Cascade name change to subcategories and transactions
    if old_name and old_name != category.name:
        execute_command(
            db_path,
            "UPDATE categories SET parent_category = $new WHERE parent_category = $old",
            {"new": category.name, "old": old_name},
        )
        execute_command(
            db_path,
            "UPDATE transactions SET category = $new WHERE category = $old",
            {"new": category.name, "old": old_name},
        )


def delete_category(db_path: str, category_id: int) -> None:
    """Delete category (also uncategorizes related transactions)."""
    # First, uncategorize transactions using this category
    execute_command(
        db_path,
        """UPDATE transactions
        SET category = NULL,
            is_categorized = FALSE
        WHERE category = (SELECT name FROM categories WHERE id = $id)""",
        {"id": category_id}
    )

    # Then delete the category
    execute_command(
        db_path,
        "DELETE FROM categories WHERE id = $id",
        {"id": category_id}
    )


def delete_all_categories(db_path: str) -> None:
    """Delete all categories and uncategorize all transactions."""
    execute_command(
        db_path,
        "UPDATE transactions SET category = NULL, is_categorized = FALSE WHERE is_categorized = TRUE",
    )
    execute_command(db_path, "DELETE FROM categories")


def get_parent_categories(db_path: str) -> pl.DataFrame:
    """Get all parent categories (categories with no parent) - pure function."""
    return execute_query(
        db_path,
        "SELECT * FROM categories WHERE parent_category IS NULL ORDER BY name"
    )


def get_subcategories(db_path: str, parent_name: str) -> pl.DataFrame:
    """Get all subcategories for a given parent - pure function."""
    return execute_query(
        db_path,
        "SELECT * FROM categories WHERE parent_category = $parent_name ORDER BY name",
        {"parent_name": parent_name}
    )


def get_category_hierarchy(db_path: str) -> list[dict]:
    """
    Get categories organized in hierarchy - pure function.

    Returns list of dicts with parent categories and their children.
    Format: [{"parent": {...}, "children": [...]}, ...]
    """
    all_categories = get_categories(db_path).to_dicts()

    # Separate parents and children
    parents = [c for c in all_categories if c.get("parent_category") is None]
    children_by_parent = {}

    for cat in all_categories:
        parent = cat.get("parent_category")
        if parent:
            if parent not in children_by_parent:
                children_by_parent[parent] = []
            children_by_parent[parent].append(cat)

    # Build hierarchy
    hierarchy = []
    for parent in parents:
        hierarchy.append({
            "parent": parent,
            "children": children_by_parent.get(parent["name"], [])
        })

    return hierarchy


def get_category_display_name(db_path: str, category_name: str | None) -> str:
    """
    Get full display name for category (Parent > Child or just Parent).

    Pure function that returns formatted category name.
    """
    if not category_name:
        return "Uncategorized"

    cat_df = get_category_by_name(db_path, category_name)
    if len(cat_df) == 0:
        return category_name

    cat = cat_df.to_dicts()[0]
    parent = cat.get("parent_category")

    if parent:
        return f"{parent} > {category_name}"
    return category_name


def get_parent_color(db_path: str, parent_name: str) -> str:
    """
    Get the color of a parent category by name.

    Returns the parent's color or default color if not found.
    """
    parent_df = get_category_by_name(db_path, parent_name)
    if len(parent_df) == 0:
        return "#6366f1"  # Default color

    parent = parent_df.to_dicts()[0]
    return parent.get("color", "#6366f1")


def seed_default_categories(db_path: str) -> None:
    """Seed database with default categories."""
    default_categories = [
        Category(name="Groceries", color="#10b981"),
        Category(name="Dining Out", color="#f59e0b"),
        Category(name="Transportation", color="#3b82f6"),
        Category(name="Utilities", color="#8b5cf6"),
        Category(name="Rent", color="#ef4444"),
        Category(name="Healthcare", color="#ec4899"),
        Category(name="Entertainment", color="#14b8a6"),
        Category(name="Shopping", color="#f97316"),
        Category(name="Income", color="#22c55e"),
        Category(name="Salary", parent_category="Income", color="#15803d"),
        Category(name="Investment", parent_category="Income", color="#166534"),
        Category(name="Other", color="#6b7280"),
    ]

    for category in default_categories:
        try:
            create_category(db_path, category)
        except Exception:
            # Category might already exist, skip
            pass


def seed_default_categories_german(db_path: str) -> tuple[int, int]:
    """
    Seed database with German default categories, skipping duplicates.

    Returns (added_count, skipped_count).
    """
    from sankash.core.default_categories import DEFAULT_CATEGORIES_DE

    existing_df = get_categories(db_path)
    existing_names = set(existing_df["name"].to_list()) if not existing_df.is_empty() else set()

    added = 0
    skipped = 0

    for category in DEFAULT_CATEGORIES_DE:
        if category.name in existing_names:
            skipped += 1
            continue
        create_category(db_path, category)
        existing_names.add(category.name)
        added += 1

    return added, skipped
