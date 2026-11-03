from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class InvoiceLineItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Optional[Decimal] = None


class InvoiceExtraction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None

    supplier: Optional[str] = None
    customer: Optional[str] = None

    currency: Optional[str] = None

    subtotal: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total: Optional[Decimal] = None

    line_items: list[InvoiceLineItem] = Field(default_factory=list)

    requires_review: bool = False
    review_reason: list[str] = Field(default_factory=list)

# correction

class InvoiceCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None

    supplier: Optional[str] = None
    customer: Optional[str] = None
    currency: Optional[str] = None

    subtotal: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total: Optional[Decimal] = None

    line_items: list[InvoiceLineItem] = Field(default_factory=list)
