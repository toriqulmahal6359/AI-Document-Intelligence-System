from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.invoice import InvoiceLineItem


class ReceiptExtraction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    merchant_name: Optional[str] = None
    receipt_number: Optional[str] = None
    receipt_date: Optional[date] = None

    currency: Optional[str] = None

    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total: Optional[Decimal] = None

    payment_method: Optional[str] = None

    line_items: list[InvoiceLineItem] = Field(
        default_factory=list
    )

    requires_review: bool = False
    review_reason: list[str] = Field(
        default_factory=list
    )