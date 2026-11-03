from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    job_id: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="queued"
    )

    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )