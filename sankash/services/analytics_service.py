"""Analytics service for dashboard data using pure functions."""

from datetime import date
from typing import Optional

import polars as pl

from sankash.core.storage import merge_overrides, read_overrides, read_parquet, read_yaml


def get_available_months(data_dir: str) -> pl.DataFrame:
    """
    Get distinct months/years that have transaction data.

    Returns DataFrame with columns: year, month, transaction_count
    Sorted by year and month descending (most recent first).
    """
    df = read_parquet(data_dir, "transactions")
    if df.is_empty() or "date" not in df.columns:
        return pl.DataFrame()

    return (
        df.with_columns(
            pl.col("date").dt.year().alias("year"),
            pl.col("date").dt.month().alias("month"),
        )
        .group_by(["year", "month"])
        .agg(pl.col("date").count().alias("transaction_count"))
        .sort(["year", "month"], descending=[True, True])
    )


def get_transactions_for_period(
    data_dir: str,
    start_date: date,
    end_date: date,
    account_ids: Optional[list[int]] = None,
) -> pl.DataFrame:
    """Get all transactions for a time period with overrides merged."""
    df = read_parquet(data_dir, "transactions")
    if df.is_empty():
        return pl.DataFrame()

    overrides = read_overrides(data_dir)
    df = merge_overrides(df, overrides)

    # Filter by date range
    df = df.filter(pl.col("date").is_between(start_date, end_date))

    if account_ids:
        df = df.filter(pl.col("account_id").is_in(account_ids))

    # Join account names
    accounts = read_yaml(data_dir, "accounts")
    if accounts:
        accounts_df = pl.DataFrame(accounts).select(
            pl.col("id").alias("acc_id"),
            pl.col("name").alias("account_name"),
        )
        df = df.join(accounts_df, left_on="account_id", right_on="acc_id", how="left")
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias("account_name"))

    return df


def calculate_flow_by_category(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate money flow by category (pure function).

    Separates income (positive) and expenses (negative).
    """
    return (
        df.filter(pl.col("category").is_not_null())
        .group_by("category")
        .agg([
            pl.col("amount").sum().alias("total"),
            pl.col("amount").count().alias("count"),
        ])
        .sort("total", descending=True)
    )


def calculate_flow_by_account(df: pl.DataFrame) -> pl.DataFrame:
    """Calculate money flow by account (pure function)."""
    return (
        df.group_by(["account_id", "account_name"])
        .agg([
            pl.col("amount").sum().alias("total"),
            pl.col("amount").count().alias("count"),
        ])
        .sort("total", descending=True)
    )


def calculate_income_expense(df: pl.DataFrame) -> dict[str, float]:
    """
    Calculate total income and expenses (pure function).

    Returns dict with income, expense, and net.
    """
    if df.is_empty():
        return {"income": 0.0, "expense": 0.0, "net": 0.0}

    income = df.filter(pl.col("amount") > 0)["amount"].sum()
    expense = df.filter(pl.col("amount") < 0)["amount"].sum()

    return {
        "income": float(income) if income else 0.0,
        "expense": abs(float(expense)) if expense else 0.0,
        "net": float(income + expense) if income or expense else 0.0,
    }


def prepare_sankey_data(df: pl.DataFrame) -> dict:
    """
    Prepare data for Sankey diagram (pure function).

    Layout: Income Categories (left) → Accounts (center) → Expense Categories (right)
    Uses prefixed internal keys to avoid collisions between accounts and categories
    that share the same name.

    Returns dict with nodes and links for Plotly Sankey.
    """
    if df.is_empty():
        return {"nodes": [], "links": []}

    # Filter to only categorized transactions
    df = df.filter(pl.col("category").is_not_null())

    if df.is_empty():
        return {"nodes": [], "links": []}

    # Separate income and expenses
    income_df = df.filter(pl.col("amount") > 0)
    expense_df = df.filter(pl.col("amount") < 0)

    # Collect unique income categories, accounts, and expense categories
    income_categories = sorted(income_df["category"].unique().to_list()) if not income_df.is_empty() else []
    expense_categories = sorted(expense_df["category"].unique().to_list()) if not expense_df.is_empty() else []
    accounts = sorted(df["account_name"].unique().to_list())

    # Build node list with prefixed keys to avoid name collisions
    # Order: income categories | accounts | expense categories (left to right)
    node_keys: list[str] = []
    node_labels: list[str] = []

    for cat in income_categories:
        node_keys.append(f"inc_{cat}")
        node_labels.append(cat)

    for acc in accounts:
        node_keys.append(f"acc_{acc}")
        node_labels.append(acc)

    for cat in expense_categories:
        node_keys.append(f"exp_{cat}")
        node_labels.append(cat)

    key_to_idx = {k: i for i, k in enumerate(node_keys)}

    # Create links
    links = []

    # Income: income category → account
    if not income_df.is_empty():
        income_flows = income_df.group_by(["account_name", "category"]).agg(
            pl.col("amount").sum().alias("total")
        )
        for row in income_flows.to_dicts():
            src_key = f"inc_{row['category']}"
            tgt_key = f"acc_{row['account_name']}"
            if src_key in key_to_idx and tgt_key in key_to_idx:
                links.append({
                    "source": key_to_idx[src_key],
                    "target": key_to_idx[tgt_key],
                    "value": abs(float(row["total"])),
                })

    # Expenses: account → expense category
    if not expense_df.is_empty():
        expense_flows = expense_df.group_by(["account_name", "category"]).agg(
            pl.col("amount").sum().alias("total")
        )
        for row in expense_flows.to_dicts():
            src_key = f"acc_{row['account_name']}"
            tgt_key = f"exp_{row['category']}"
            if src_key in key_to_idx and tgt_key in key_to_idx:
                links.append({
                    "source": key_to_idx[src_key],
                    "target": key_to_idx[tgt_key],
                    "value": abs(float(row["total"])),
                })

    return {
        "nodes": [{"label": label} for label in node_labels],
        "links": links,
    }


def calculate_spending_trend(
    data_dir: str,
    start_date: date,
    end_date: date,
    account_ids: Optional[list[int]] = None,
    frequency: str = "D",  # D=daily, W=weekly, M=monthly
) -> pl.DataFrame:
    """
    Calculate spending trend over time.

    Returns DataFrame with date and income/expense columns.
    """
    df = get_transactions_for_period(data_dir, start_date, end_date, account_ids)

    if df.is_empty():
        return pl.DataFrame()

    # Group by date and calculate daily totals
    daily = (
        df.group_by("date")
        .agg([
            pl.col("amount").filter(pl.col("amount") > 0).sum().alias("income"),
            pl.col("amount").filter(pl.col("amount") < 0).sum().abs().alias("expense"),
        ])
        .sort("date")
    )

    # Fill nulls with 0
    daily = daily.with_columns([
        pl.col("income").fill_null(0),
        pl.col("expense").fill_null(0),
    ])

    # Resample if needed (for weekly/monthly)
    if frequency == "W":
        daily = daily.with_columns(
            pl.col("date").dt.truncate("1w").alias("week")
        ).group_by("week").agg([
            pl.col("income").sum(),
            pl.col("expense").sum(),
        ]).rename({"week": "date"}).sort("date")
    elif frequency == "M":
        daily = daily.with_columns(
            pl.col("date").dt.truncate("1mo").alias("month")
        ).group_by("month").agg([
            pl.col("income").sum(),
            pl.col("expense").sum(),
        ]).rename({"month": "date"}).sort("date")

    return daily


def get_top_spending_categories(
    data_dir: str,
    start_date: date,
    end_date: date,
    limit: int = 10,
    account_ids: Optional[list[int]] = None,
) -> pl.DataFrame:
    """Get top spending categories for a period (expenses only)."""
    df = get_transactions_for_period(data_dir, start_date, end_date, account_ids)

    if df.is_empty():
        return pl.DataFrame()

    expenses = df.filter(
        (pl.col("amount") < 0) & (pl.col("category").is_not_null())
    )

    if expenses.is_empty():
        return pl.DataFrame()

    top_categories = (
        expenses.group_by("category")
        .agg([
            pl.col("amount").sum().abs().alias("total_spent"),
            pl.col("amount").count().alias("transaction_count"),
        ])
        .sort("total_spent", descending=True)
        .head(limit)
    )

    return top_categories


def get_monthly_summary(data_dir: str, year: int, month: int) -> dict:
    """Get comprehensive monthly summary."""
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    df = get_transactions_for_period(data_dir, start_date, end_date)

    income_expense = calculate_income_expense(df)
    category_flow = calculate_flow_by_category(df)

    return {
        "period": f"{year}-{month:02d}",
        "income": income_expense["income"],
        "expense": income_expense["expense"],
        "net": income_expense["net"],
        "categories": category_flow.to_dicts() if not category_flow.is_empty() else [],
        "transaction_count": len(df),
    }
