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
    """Update existing category."""
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
