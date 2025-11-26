"""Analytics service for dashboard data using pure functions."""

from datetime import date
from typing import Optional

import polars as pl

from sankash.core.database import execute_query


def get_available_months(db_path: str) -> pl.DataFrame:
    """
    Get distinct months/years that have transaction data (pure function).

    Returns DataFrame with columns: year, month, transaction_count
    Sorted by year and month descending (most recent first).
    """
    query = """
    SELECT
        DISTINCT YEAR(date) as year,
        MONTH(date) as month,
        COUNT(*) as transaction_count
    FROM transactions
    GROUP BY YEAR(date), MONTH(date)
    ORDER BY year DESC, month DESC
    """
    return execute_query(db_path, query)


def get_transactions_for_period(
    db_path: str,
    start_date: date,
    end_date: date,
    account_ids: Optional[list[int]] = None,
) -> pl.DataFrame:
    """Get all transactions for a time period (pure function)."""
    query = """
    SELECT
        t.*,
        a.name as account_name
    FROM transactions t
    JOIN accounts a ON t.account_id = a.id
    WHERE t.date BETWEEN $start_date AND $end_date
    """

    params = {"start_date": start_date, "end_date": end_date}

    if account_ids:
        query += " AND t.account_id = ANY($account_ids)"
        params["account_ids"] = account_ids

    return execute_query(db_path, query, params)


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

    # Get unique accounts and categories
    accounts = df["account_name"].unique().to_list()
    categories = df["category"].unique().to_list()

    # Create node list: accounts + categories
    nodes = accounts + categories
    node_dict = {name: idx for idx, name in enumerate(nodes)}

    # Create links
    links = []

    # Income: categories -> accounts (source is category, target is account)
    if not income_df.is_empty():
        income_flows = income_df.group_by(["account_name", "category"]).agg(
            pl.col("amount").sum().alias("total")
        )

        for row in income_flows.to_dicts():
            if row["category"] and row["account_name"]:
                links.append({
                    "source": node_dict[row["category"]],
                    "target": node_dict[row["account_name"]],
                    "value": abs(float(row["total"])),
                })

    # Expenses: accounts -> categories (source is account, target is category)
    if not expense_df.is_empty():
        expense_flows = expense_df.group_by(["account_name", "category"]).agg(
            pl.col("amount").sum().alias("total")
        )

        for row in expense_flows.to_dicts():
            if row["category"] and row["account_name"]:
                links.append({
                    "source": node_dict[row["account_name"]],
                    "target": node_dict[row["category"]],
                    "value": abs(float(row["total"])),
                })

    return {
        "nodes": [{"label": name} for name in nodes],
        "links": links,
    }


def calculate_spending_trend(
    db_path: str,
    start_date: date,
    end_date: date,
    account_ids: Optional[list[int]] = None,
    frequency: str = "D",  # D=daily, W=weekly, M=monthly
) -> pl.DataFrame:
    """
    Calculate spending trend over time (pure function).

    Args:
        db_path: Database path
        start_date: Start date
        end_date: End date
        account_ids: Optional account filter
        frequency: Aggregation frequency (D, W, M)

    Returns:
        DataFrame with date and income/expense columns
    """
    df = get_transactions_for_period(db_path, start_date, end_date, account_ids)

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
        # Group by week
        daily = daily.with_columns(
            pl.col("date").dt.truncate("1w").alias("week")
        ).group_by("week").agg([
            pl.col("income").sum(),
            pl.col("expense").sum(),
        ]).rename({"week": "date"}).sort("date")
    elif frequency == "M":
        # Group by month
        daily = daily.with_columns(
            pl.col("date").dt.truncate("1mo").alias("month")
        ).group_by("month").agg([
            pl.col("income").sum(),
            pl.col("expense").sum(),
        ]).rename({"month": "date"}).sort("date")

    return daily


def get_top_spending_categories(
    db_path: str,
    start_date: date,
    end_date: date,
    limit: int = 10,
    account_ids: Optional[list[int]] = None,
) -> pl.DataFrame:
    """
    Get top spending categories for a period (pure function).

    Returns DataFrame with category and total spending (expenses only).
    """
    df = get_transactions_for_period(db_path, start_date, end_date, account_ids)

    if df.is_empty():
        return pl.DataFrame()

    # Filter to expenses only (negative amounts) and categorized
    expenses = df.filter(
        (pl.col("amount") < 0) & (pl.col("category").is_not_null())
    )

    if expenses.is_empty():
        return pl.DataFrame()

    # Group by category and sum
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


def get_monthly_summary(db_path: str, year: int, month: int) -> dict:
    """
    Get comprehensive monthly summary (pure function).

    Returns dict with income, expenses, net, and category breakdown.
    """
    from datetime import datetime

    # Calculate month start and end
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    # Get transactions
    df = get_transactions_for_period(db_path, start_date, end_date)

    # Calculate summary
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
