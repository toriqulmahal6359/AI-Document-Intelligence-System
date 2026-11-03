from datetime import datetime, timezone
from uuid import uuid4
import json

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models import (
    Document,
    Invoice,
    ProcessingJob,
    ValidationIssue,
)
from app.schemas.invoice import InvoiceExtraction


# def persist_document_result(
#     db: Session,
#     document_id: str,
#     filename: str,
#     stored_path: str,
#     file_size_bytes: int,
#     processing_result: dict | None = None,
#     error_message: str | None = None,
# ) -> None:

def persist_document_result(
    db: Session,
    document_id: str,
    filename: str,
    stored_path: str,
    file_size_bytes: int,
    processing_result: dict | None = None,
    error_message: str | None = None,
    file_type: str | None = None,
    document_category: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)

    result = processing_result or {}

    status = (
        result.get("status", "failed")
        if not error_message
        else "failed"
    )

    extraction_result = result.get("extraction_result")
    ai_extraction = result.get("ai_extraction")
    validation = result.get("validation")

    if extraction_result:
        extracted_text = extraction_result.get("full_text")

        if not extracted_text:
            extracted_text = json.dumps(
                extraction_result,
                ensure_ascii=False,
                default=str,
            )
    else:
        extracted_text = None

    document = Document(
        document_id=document_id,
        filename=filename,
        stored_path=stored_path,
        # file_type=result.get(
        #     "file_type", ""
        # ),
        file_type=result.get("file_type") or file_type or "",
        document_type=result.get("document_type"),
        # document_category=result.get("document_category"),
        document_category=(
            result.get("document_category") or document_category
        ),
        processing_status=status,
        file_size_bytes=file_size_bytes,
        extracted_text=extracted_text,
        extraction_result=jsonable_encoder(extraction_result),
        ai_extraction=jsonable_encoder(ai_extraction),
        validation_result=jsonable_encoder(validation),
    )

    job = ProcessingJob(
        job_id=str(uuid4()),
        document_id=document_id,
        # status="failed" if error_message else "completed",
        status="failed" if error_message else status,
        retry_count=0,
        max_retries=3,
        error_message=error_message,
        started_at=now,
        completed_at=now,
    )

    db.add(document)
    db.add(job)

    # Store structured invoice fields separately.
    if (
        not error_message
        # and result.get("document_category") == "invoice"
        and (result.get("document_category") or document_category) == "invoice"
        and ai_extraction
    ):
        invoice_data = InvoiceExtraction.model_validate(
            ai_extraction
        )

        db.add(
            Invoice(
                document_id=document_id,
                invoice_number=invoice_data.invoice_number,
                invoice_date=invoice_data.invoice_date,
                due_date=invoice_data.due_date,
                supplier=invoice_data.supplier,
                customer=invoice_data.customer,
                currency=invoice_data.currency,
                subtotal=invoice_data.subtotal,
                tax_rate=invoice_data.tax_rate,
                tax_amount=invoice_data.tax_amount,
                total=invoice_data.total,
                line_items=[
                    item.model_dump(mode="json")
                    for item in invoice_data.line_items
                ],
                requires_review=invoice_data.requires_review,
                review_reasons=invoice_data.review_reason,
            )
        )

    # Store deterministic validation errors and warnings.
    if validation:
        for severity, key in (
            ("error", "errors"),
            ("warning", "warnings"),
        ):
            for issue in validation.get(key, []):
                if isinstance(issue, dict):
                    message = issue.get(
                        "issue", "Validation issue"
                    )
                    field_name = issue.get("field")
                    error_code = issue.get("code")
                else:
                    message = str(issue)
                    field_name = None
                    error_code = None

                db.add(
                    ValidationIssue(
                        document_id=document_id,
                        error_code=error_code,
                        severity=severity,
                        field_name=field_name,
                        message=str(message),
                        details=jsonable_encoder(issue),
                    )
                )

    db.commit()