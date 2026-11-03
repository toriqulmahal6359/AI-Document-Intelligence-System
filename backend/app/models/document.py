from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )

    filename: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    stored_path: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    file_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    document_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    document_category: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    processing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="uploaded"
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    extraction_result: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    ai_extraction: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    validation_result: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    source_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_documents_category_status",
              "document_category", "processing_status"),
    )