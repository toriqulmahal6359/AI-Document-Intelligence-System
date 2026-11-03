from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CrossDocumentVerification(Base):
    __tablename__ = "cross_document_verifications"

    verification_id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )

    document_1_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_2_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    verification_result: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )