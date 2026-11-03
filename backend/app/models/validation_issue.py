from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    severity: Mapped[str] = mapped_column(
        String(30), nullable=False, default="warning"
    )

    field_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    message: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )