"""Category service with pure functions."""

from datetime import datetime

import polars as pl

from sankash.core.models import Category
from sankash.core.storage import (
    merge_overrides,
    next_id,
    read_overrides,
    read_parquet,
    read_yaml,
    write_overrides,
    write_yaml,
)


def get_categories(data_dir: str) -> pl.DataFrame:
    """Get all categories."""
    records = read_yaml(data_dir, "categories")
    if not records:
        return pl.DataFrame()
    df = pl.DataFrame(records)
    if "name" in df.columns:
        df = df.sort("name")
    return df


def get_category_by_name(data_dir: str, name: str) -> pl.DataFrame:
    """Get category by name."""
    records = read_yaml(data_dir, "categories")
    if not records:
        return pl.DataFrame()
    df = pl.DataFrame(records)
    return df.filter(pl.col("name") == name)


def get_categories_with_spending(data_dir: str) -> pl.DataFrame:
    """Get categories with total spending."""
    records = read_yaml(data_dir, "categories")
    if not records:
        return pl.DataFrame()

    cats_df = pl.DataFrame(records)
    txns = read_parquet(data_dir, "transactions")

    if txns.is_empty():
        return cats_df.with_columns(
            pl.lit(0.0).alias("total_spending"),
            pl.lit(0).cast(pl.Int64).alias("transaction_count"),
        ).sort("total_spending", descending=True)

    overrides = read_overrides(data_dir)
    txns = merge_overrides(txns, overrides)

    spending = txns.filter(pl.col("category").is_not_null()).group_by("category").agg(
        pl.col("amount").abs().sum().alias("total_spending"),
        pl.col("id").count().alias("transaction_count"),
    )

    result = cats_df.join(
        spending, left_on="name", right_on="category", how="left"
    ).with_columns(
        pl.col("total_spending").fill_null(0.0),
        pl.col("transaction_count").fill_null(0).cast(pl.Int64),
    )

    return result.sort("total_spending", descending=True)


def create_category(data_dir: str, category: Category) -> int:
    """Create new category and return its ID."""
    records = read_yaml(data_dir, "categories")

    # Check for duplicate name
    existing_names = {r["name"] for r in records}
    if category.name in existing_names:
        raise ValueError(f"Category '{category.name}' already exists")

    new_id = next_id(records)
    record = {
        "id": new_id,
        "name": category.name,
        "parent_category": category.parent_category,
        "color": category.color,
        "created_at": datetime.now().isoformat(),
    }
    records.append(record)
    write_yaml(data_dir, "categories", records)
    return new_id


def update_category(data_dir: str, category_id: int, category: Category) -> None:
    """Update existing category, cascading name changes to children and transactions."""
    records = read_yaml(data_dir, "categories")

    # Find old name
    old_name = None
    for rec in records:
        if rec["id"] == category_id:
            old_name = rec["name"]
            rec["name"] = category.name
            rec["parent_category"] = category.parent_category
            rec["color"] = category.color
            break

    # Cascade name change to subcategories
    if old_name and old_name != category.name:
        for rec in records:
            if rec.get("parent_category") == old_name:
                rec["parent_category"] = category.name

        # Cascade to transaction overrides
        overrides = read_overrides(data_dir)
        changed = False
        for tid, vals in overrides.items():
            if vals.get("category") == old_name:
                vals["category"] = category.name
                changed = True
        if changed:
            write_overrides(data_dir, overrides)

    write_yaml(data_dir, "categories", records)


def delete_category(data_dir: str, category_id: int) -> None:
    """Delete category (also uncategorizes related transactions)."""
    records = read_yaml(data_dir, "categories")

    # Find category name
    cat_name = None
    for rec in records:
        if rec["id"] == category_id:
            cat_name = rec["name"]
            break

    # Remove from overrides
    if cat_name:
        overrides = read_overrides(data_dir)
        changed = False
        for tid, vals in overrides.items():
            if vals.get("category") == cat_name:
                vals["category"] = None
                vals["is_categorized"] = False
                changed = True
        if changed:
            write_overrides(data_dir, overrides)

    # Remove from records
    records = [r for r in records if r["id"] != category_id]
    write_yaml(data_dir, "categories", records)


def delete_all_categories(data_dir: str) -> None:
    """Delete all categories and uncategorize all transactions."""
    # Clear all category overrides
    overrides = read_overrides(data_dir)
    changed = False
    for tid, vals in overrides.items():
        if vals.get("category") is not None or vals.get("is_categorized"):
            vals["category"] = None
            vals["is_categorized"] = False
            changed = True
    if changed:
        write_overrides(data_dir, overrides)

    write_yaml(data_dir, "categories", [])


def get_parent_categories(data_dir: str) -> pl.DataFrame:
    """Get all parent categories (categories with no parent)."""
    records = read_yaml(data_dir, "categories")
    if not records:
        return pl.DataFrame()
    df = pl.DataFrame(records)
    return df.filter(pl.col("parent_category").is_null()).sort("name")


def get_subcategories(data_dir: str, parent_name: str) -> pl.DataFrame:
    """Get all subcategories for a given parent."""
    records = read_yaml(data_dir, "categories")
    if not records:
        return pl.DataFrame()
    df = pl.DataFrame(records)
    return df.filter(pl.col("parent_category") == parent_name).sort("name")


def get_category_hierarchy(data_dir: str) -> list[dict]:
    """Get categories organized in hierarchy.

    Returns list of dicts with parent categories and their children.
    Format: [{"parent": {...}, "children": [...]}, ...]
    """
    all_categories = get_categories(data_dir).to_dicts()

    parents = [c for c in all_categories if c.get("parent_category") is None]
    children_by_parent: dict[str, list[dict]] = {}

    for cat in all_categories:
        parent = cat.get("parent_category")
        if parent:
            if parent not in children_by_parent:
                children_by_parent[parent] = []
            children_by_parent[parent].append(cat)

    hierarchy = []
    for parent in parents:
        hierarchy.append({
            "parent": parent,
            "children": children_by_parent.get(parent["name"], [])
        })

    return hierarchy


def get_category_display_name(data_dir: str, category_name: str | None) -> str:
    """Get full display name for category (Parent > Child or just Parent)."""
    if not category_name:
        return "Uncategorized"

    cat_df = get_category_by_name(data_dir, category_name)
    if len(cat_df) == 0:
        return category_name

    cat = cat_df.to_dicts()[0]
    parent = cat.get("parent_category")

    if parent:
        return f"{parent} > {category_name}"
    return category_name


def get_parent_color(data_dir: str, parent_name: str) -> str:
    """Get the color of a parent category by name."""
    parent_df = get_category_by_name(data_dir, parent_name)
    if len(parent_df) == 0:
        return "#6366f1"

    parent = parent_df.to_dicts()[0]
    return parent.get("color", "#6366f1")


def seed_default_categories(data_dir: str) -> None:
    """Seed with default categories."""
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
            create_category(data_dir, category)
        except Exception:
            pass


def seed_default_categories_german(data_dir: str) -> tuple[int, int]:
    """Seed with German default categories, skipping duplicates.

    Returns (added_count, skipped_count).
    """
    from sankash.core.default_categories import DEFAULT_CATEGORIES_DE

    existing_df = get_categories(data_dir)
    existing_names = set(existing_df["name"].to_list()) if not existing_df.is_empty() else set()

    added = 0
    skipped = 0

    for category in DEFAULT_CATEGORIES_DE:
        if category.name in existing_names:
            skipped += 1
            continue
        create_category(data_dir, category)
        existing_names.add(category.name)
        added += 1

    return added, skipped
