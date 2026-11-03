from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BankTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    transaction_date: Optional[date] = None
    description: Optional[str] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    balance: Optional[Decimal] = None


class BankStatement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    branch: Optional[str] = None

    statement_start_date: Optional[date] = None
    statement_end_date: Optional[date] = None

    currency: Optional[str] = None

    opening_balance: Optional[Decimal] = None
    total_debits: Optional[Decimal] = None
    total_credits: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None

    transactions: list[BankTransaction] = Field(
        default_factory=list
    )

    requires_review: bool = False
    review_reason: list[str] = Field(default_factory=list)
