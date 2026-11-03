import json
import logging
from datetime import datetime, timezone

import dramatiq
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.broker import rabbitmq_broker
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.invoice import Invoice
from app.models.validation_issue import ValidationIssue
from app.schemas.invoice import InvoiceExtraction
from app.services.document_processor import process_document
from app.services.embedding_service import embed_document_chunks
from fastapi.encoders import jsonable_encoder


logger = logging.getLogger(__name__)

dramatiq.set_broker(rabbitmq_broker)


@dramatiq.actor(
    max_retries=3,
    min_backoff=1000,
    max_backoff=30000,
)
def process_document_task(document_id: str) -> None:
    db: Session = SessionLocal()

    try:
        # Find the existing document and its latest processing job.
        document = (
            db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )

        if document is None:
            raise ValueError(f"Document not found: {document_id}")

        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at.desc())
            .first()
        )

        if job is None:
            raise ValueError(
                f"Processing job not found for document: {document_id}"
            )

        # Mark processing as started.
        now = datetime.now(timezone.utc)

        document.processing_status = "processing"
        job.status = "processing"
        job.started_at = now
        job.completed_at = None
        job.error_message = None

        db.commit()

        # Run the existing document-processing pipeline.
        result = process_document(
            file_path=document.stored_path,
            document_category=document.document_category,
        )

        extraction_result = result.get("extraction_result") or {}
        ai_extraction = result.get("ai_extraction")
        validation = result.get("validation") or {}

        # Update the existing document.
        document.processing_status = result.get("status") or "completed"
        document.document_type = result.get("document_type")
        document.document_category = (
            result.get("document_category")
            or document.document_category
        )
        document.file_type = (
            result.get("file_type") or document.file_type
        )

        extracted_text = extraction_result.get("full_text")

        if not extracted_text and extraction_result:
            extracted_text = json.dumps(
                extraction_result,
                ensure_ascii=False,
                default=str,
            )

        document.extracted_text = extracted_text
        document.extraction_result = jsonable_encoder(
            extraction_result
        )
        document.ai_extraction = jsonable_encoder(ai_extraction)
        document.validation_result = jsonable_encoder(validation)

        # Update the existing invoice instead of inserting duplicates.
        if (
            document.document_category == "invoice"
            and ai_extraction
        ):
            invoice_data = InvoiceExtraction.model_validate(
                ai_extraction
            )

            invoice = (
                db.query(Invoice)
                .filter(Invoice.document_id == document_id)
                .first()
            )

            if invoice is None:
                invoice = Invoice(document_id=document_id)
                db.add(invoice)

            invoice.invoice_number = invoice_data.invoice_number
            invoice.invoice_date = invoice_data.invoice_date
            invoice.due_date = invoice_data.due_date
            invoice.supplier = invoice_data.supplier
            invoice.customer = invoice_data.customer
            invoice.currency = invoice_data.currency
            invoice.subtotal = invoice_data.subtotal
            invoice.tax_rate = invoice_data.tax_rate
            invoice.tax_amount = invoice_data.tax_amount
            invoice.total = invoice_data.total
            invoice.line_items = [
                item.model_dump(mode="json")
                for item in invoice_data.line_items
            ]
            invoice.requires_review = invoice_data.requires_review
            invoice.review_reasons = invoice_data.review_reason

        # Replace previous validation issues with the latest results.
        db.execute(
            delete(ValidationIssue).where(
                ValidationIssue.document_id == document_id
            )
        )

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

        # Mark the processing job as completed.
        job.status = "completed"
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)

        db.commit()

        logger.info(
            "Document processing completed: %s",
            document_id,
        )

        # Semantic indexing runs separately so an indexing failure
        # does not invalidate successful document processing.

        # try:
        #     if extracted_text and extracted_text.strip():
        #         chunk_count = embed_document_chunks(
        #             db=db,
        #             document_id=document_id,
        #             text=extracted_text,
        #         )

        #         logger.info(
        #             "Semantic indexing completed: %s chunks for %s",
        #             chunk_count,
        #             document_id,
        #         )
        # except Exception:
        #     db.rollback()
        #     logger.exception(
        #         "Semantic indexing failed for document %s",
        #         document_id,
        #     )

        # Queue semantic indexing separately after processing is committed.
        if extracted_text and extracted_text.strip():
            try:
                index_document_task.send(document_id)
                logger.info(
                    "Semantic indexing queued for document %s",
                    document_id,
                )
            except Exception:
                logger.exception(
                    "Could not queue semantic indexing for %s",
                    document_id,
                )

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Document processing failed: %s",
            document_id,
        )

        document = (
            db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )

        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at.desc())
            .first()
        )

        if document:
            document.processing_status = "failed"

        if job:
            job.status = "failed"
            job.retry_count = (job.retry_count or 0) + 1
            job.error_message = str(exc)[:5000]
            job.completed_at = datetime.now(timezone.utc)

        db.commit()

        # Dramatiq will retry according to the actor's retry policy.
        raise

    finally:
        db.close()


@dramatiq.actor(
    max_retries=1,
    min_backoff=5000,
    max_backoff=30000,
)
def index_document_task(document_id: str) -> None:
    """Generate semantic embeddings independently of document extraction."""
    db: Session = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )

        if document is None:
            raise ValueError(f"Document not found: {document_id}")

        text = document.extracted_text

        if not text or not text.strip():
            logger.info(
                "No extracted text to index for document %s",
                document_id,
            )
            return

        chunk_count = embed_document_chunks(
            db=db,
            document_id=document_id,
            text=text,
        )

        logger.info(
            "Semantic indexing completed: %s chunks for %s",
            chunk_count,
            document_id,
        )

        logger.info(
            "Semantic indexing task finished successfully for %s",
            document_id,
        )

    except Exception:
        db.rollback()
        logger.exception(
            "Semantic indexing failed for document %s",
            document_id,
        )
        raise

    finally:
        db.close()


def enqueue_document_processing(document_id: str) -> str:
    """Enqueue a document and return its Dramatiq message ID."""
    message = process_document_task.send(document_id)
    return message.message_id


## temporaray actor

# @dramatiq.actor
# def rabbitmq_smoke_test(message: str) -> None:
#     logger.info("RabbitMQ smoke test received: %s", message)
