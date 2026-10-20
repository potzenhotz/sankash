"""JSON API over the service layer for the React frontend.

Run: uv run uvicorn sankash.api.main:app --port 8001
"""

from datetime import date
from pathlib import Path
from typing import Annotated, Literal

import polars as pl
from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, StringConstraints

from config.settings import load_settings
from sankash.core.models import RuleCondition
from sankash.services import account_service, category_service, rule_service, transaction_service

app = FastAPI(title="Sankash API")


def get_data_dir() -> str:
    """Data directory, re-read per request like the Reflex app does."""
    data_dir = load_settings().data_dir
    # A missing directory would otherwise look like an empty account
    if not Path(data_dir).is_dir():
        raise HTTPException(status_code=500, detail=f"Data directory not found: {data_dir}")
    return data_dir


DataDir = Annotated[str, Depends(get_data_dir)]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TransactionOut(BaseModel):
    id: int
    date: date
    payee: str
    notes: str | None
    amount: float
    account_name: str | None
    category: str | None
    category_source: Literal["manual", "rule"] | None
    is_transfer: bool
    parent_id: int | None
    import_filename: str | None


class CategoryOut(BaseModel):
    name: str
    parent: str | None
    display: str


class CategoryAssignment(BaseModel):
    category: NonEmpty


class RuleConditionIn(BaseModel):
    category: NonEmpty
    field: Literal["payee", "notes"]
    value: NonEmpty


def _category_names(data_dir: str) -> set[str]:
    df = category_service.get_categories(data_dir)
    return set(df["name"].to_list()) if not df.is_empty() else set()


def _require_category(data_dir: str, category: str) -> None:
    if category not in _category_names(data_dir):
        raise HTTPException(status_code=400, detail=f"Unknown category '{category}'")


def _require_transaction(data_dir: str, transaction_id: int) -> None:
    df = transaction_service.load_transactions(data_dir)
    if df.is_empty() or df.filter(pl.col("id") == transaction_id).is_empty():
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")


@app.get("/api/transactions")
def list_transactions(data_dir: DataDir) -> list[TransactionOut]:
    """All leaf transactions (split parents excluded), newest first."""
    df, _ = transaction_service.get_transactions(data_dir, limit=1_000_000)
    if df.is_empty():
        return []

    accounts = account_service.get_accounts(data_dir, include_inactive=True)
    names = dict(zip(accounts["id"], accounts["name"])) if not accounts.is_empty() else {}

    rows = []
    for row in df.to_dicts():
        if not row.get("category"):
            source = None
        else:
            source = "manual" if row.get("category_source") == "manual" else "rule"
        rows.append(
            TransactionOut(
                id=row["id"],
                date=row["date"],
                payee=row["payee"] or "",
                notes=row.get("notes"),
                amount=row["amount"],
                account_name=names.get(row["account_id"]),
                category=row.get("category"),
                category_source=source,
                is_transfer=bool(row.get("is_transfer")),
                parent_id=row.get("parent_id"),
                import_filename=row.get("import_filename"),
            )
        )
    return rows


@app.get("/api/categories")
def list_categories(data_dir: DataDir) -> list[CategoryOut]:
    df = category_service.get_categories(data_dir)
    if df.is_empty():
        return []
    out = [
        CategoryOut(
            name=c["name"],
            parent=c.get("parent_category"),
            display=f"{c['parent_category']} > {c['name']}"
            if c.get("parent_category")
            else c["name"],
        )
        for c in df.to_dicts()
    ]
    return sorted(out, key=lambda c: c.display.lower())


@app.put("/api/transactions/{transaction_id}/category", status_code=204)
def assign_category(transaction_id: int, body: CategoryAssignment, data_dir: DataDir) -> Response:
    """Manually assign a category (wins over rules)."""
    _require_category(data_dir, body.category)
    _require_transaction(data_dir, transaction_id)
    transaction_service.update_transaction_category(data_dir, transaction_id, body.category)
    return Response(status_code=204)


@app.delete("/api/transactions/{transaction_id}/category", status_code=204)
def reset_category(transaction_id: int, data_dir: DataDir) -> Response:
    """Drop the manual category so rules decide again."""
    transaction_service.clear_manual_category(data_dir, transaction_id)
    return Response(status_code=204)


@app.post("/api/rules/conditions", status_code=204)
def add_rule_condition(body: RuleConditionIn, data_dir: DataDir) -> Response:
    """Add '<field> contains <value>' to the category's rule (created if missing)."""
    _require_category(data_dir, body.category)
    condition = RuleCondition(field=body.field, operator="contains", value=body.value)
    rule_service.add_condition_to_category(data_dir, body.category, condition)
    return Response(status_code=204)
