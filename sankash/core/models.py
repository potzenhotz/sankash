"""Data models using Pydantic for type safety."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class Account(BaseModel):
    """Account model."""

    id: Optional[int] = None
    name: str
    bank: str
    account_number: str
    currency: str = "EUR"
    is_active: bool = True


class Category(BaseModel):
    """Category model."""

    id: Optional[int] = None
    name: str
    parent_category: Optional[str] = None
    color: str = "#6366f1"


class ImportHistory(BaseModel):
    """Import history model."""

    id: Optional[int] = None
    filename: str
    account_id: int
    bank_format: str
    import_date: Optional[datetime] = None
    total_count: int
    imported_count: int
    duplicate_count: int
    categorized_count: int
    file_hash: Optional[str] = None


class Transaction(BaseModel):
    """Transaction model."""

    id: Optional[int] = None
    account_id: int
    date: date
    payee: str
    notes: Optional[str] = None
    amount: float
    category: Optional[str] = None
    is_categorized: bool = False
    is_transfer: bool = False
    transfer_account_id: Optional[int] = None
    imported_id: Optional[str] = None
    import_session_id: Optional[int] = None


class RuleCondition(BaseModel):
    """Rule condition model."""

    field: str  # payee, amount, notes
    operator: str  # contains, equals, <, >
    value: str


class RuleAction(BaseModel):
    """Rule action model."""

    action_type: str  # set_category, mark_transfer
    value: str


class Rule(BaseModel):
    """Rule model."""

    id: Optional[int] = None
    name: str
    priority: int = 0
    is_active: bool = True
    match_type: str = "any"  # "all" for AND, "any" for OR
    conditions: list[RuleCondition] = Field(default_factory=list)
    actions: list[RuleAction] = Field(default_factory=list)
