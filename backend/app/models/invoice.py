from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    invoice_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )

    invoice_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )

    due_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )

    supplier: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    customer: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    currency: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )

    subtotal: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 4), nullable=True
    )

    tax_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )

    tax_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 4), nullable=True
    )

    total: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 4), nullable=True
    )

    line_items: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )

    requires_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    review_reasons: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_invoices_supplier_number", "supplier", "invoice_number"),
    )
