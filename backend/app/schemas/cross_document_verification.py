from typing import Any, Optional

from pydantic import BaseModel, Field


class RecordMatch(BaseModel):
    document_1_record: Optional[dict[str, Any]] = None
    document_2_record: Optional[dict[str, Any]] = None
    matching_fields: list[str] = Field(default_factory=list)
    mismatched_fields: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )


class CrossDocumentVerificationResult(BaseModel):
    document_1: str
    document_2: str
    document_category: str

    verification_status: str

    matched_records: list[RecordMatch] = Field(
        default_factory=list
    )

    mismatched_records: list[RecordMatch] = Field(
        default_factory=list
    )

    missing_from_document_1: list[dict[str, Any]] = Field(
        default_factory=list
    )

    missing_from_document_2: list[dict[str, Any]] = Field(
        default_factory=list
    )

    requires_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
