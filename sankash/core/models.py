"""Data models using Pydantic for type safety."""

from datetime import date
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
    conditions: list[RuleCondition] = Field(default_factory=list)
    actions: list[RuleAction] = Field(default_factory=list)
