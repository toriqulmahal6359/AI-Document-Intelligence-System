import logging

from app.models.document_chunk import DocumentChunk

from app.services.embedding_service import (
    embed_document_chunks,
    generate_embeddings
)

logger = logging.getLogger(__name__)

import json

from datetime import datetime, timezone

from app.schemas.invoice import InvoiceExtraction

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.invoice import Invoice
from app.models.validation_issue import ValidationIssue

from app.tasks.document_tasks import enqueue_document_processing

from app.schemas.invoice import InvoiceCorrection

from app.core.config import UPLOAD_DIR, MAX_UPLOAD_SIZE_MB

from sqlalchemy import or_
from fastapi import Query

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.document_persistence_service import (
    persist_document_result,
)

from app.services.cross_document_verification_service import (
    verify_documents,
)

from app.services.document_processor import (
    process_document,
    SUPPORTED_EXTENSIONS,
)

from fastapi.encoders import jsonable_encoder
from app.models.cross_document_verification import CrossDocumentVerification

router = APIRouter(prefix="/api/documents", tags=["Documents"])

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

def index_document_for_search(
    db: Session,
    document_id: str,
    processing_result: dict,
) -> None:
    """Index extracted document text without affecting processing status."""

    extraction_result = processing_result.get("extraction_result") or {}

    text = extraction_result.get("full_text")

    if not text and extraction_result:
        text = json.dumps(
            extraction_result,
            ensure_ascii=False,
            default=str,
        )

    if not text or not text.strip():
        logger.warning(
            "No extracted text available for embedding: %s",
            document_id,
        )
        return

    try:
        chunk_count = embed_document_chunks(
            db=db,
            document_id=document_id,
            text=text,
        )

        logger.info(
            "Semantic indexing completed: document=%s, chunks=%s",
            document_id,
            chunk_count,
        )

    except Exception:
        db.rollback()

        logger.exception(
            "Semantic indexing failed for document %s",
            document_id,
        )


async def save_upload_file(upload_file: UploadFile, destination: Path) -> int:
    total_bytes = 0

    try:
        with destination.open("wb") as output_file:
            while chunk := await upload_file.read(1024 * 1024):
                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {MAX_UPLOAD_SIZE_MB} MB upload limit."
                    )

                output_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        return total_bytes

    except Exception:
        destination.unlink(missing_ok=True)
        raise



@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    document_category: str | None = Form(None),
    db: Session = Depends(get_db),
):
    results = []

    for uploaded_file in files:
        original_name = uploaded_file.filename or "unnamed"
        extension = Path(original_name).suffix.lower()

        document_id = str(uuid4())
        saved_path = UPLOAD_DIR / f"{document_id}{extension}"

        try:
            if extension not in SUPPORTED_EXTENSIONS:
                results.append({
                    "filename": original_name,
                    "status": "rejected",
                    "error": "Unsupported file format",
                })
                continue

            # Save the uploaded file with the existing size limit.
            try:
                file_size_bytes = await save_upload_file(
                    uploaded_file,
                    saved_path,
                )
            except HTTPException as upload_error:
                results.append({
                    "filename": original_name,
                    "status": "rejected",
                    "error": upload_error.detail,
                })
                continue

            # Create the document record.
            document = Document(
                document_id=document_id,
                filename=original_name,
                stored_path=str(saved_path),
                file_type=extension,
                document_category=document_category,
                processing_status="queued",
                file_size_bytes=file_size_bytes,
            )

            # Create its background-processing job.
            job = ProcessingJob(
                job_id=str(uuid4()),
                document_id=document_id,
                status="queued",
                retry_count=0,
                max_retries=3,
            )

            db.add(document)
            db.add(job)
            db.commit()

            # Send the document ID to RabbitMQ.
            try:
                task_id = enqueue_document_processing(document_id)

            except Exception as queue_error:
                db.rollback()

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
                    job.error_message = str(queue_error)[:5000]

                db.commit()

                results.append({
                    "document_id": document_id,
                    "filename": original_name,
                    "status": "failed",
                    "error": "Could not enqueue document for processing",
                })
                continue

            # Store the Dramatiq message ID for tracking.
            try:
                job.task_id = task_id
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(
                    "Could not save task ID for document %s",
                    document_id,
                )

            results.append({
                "document_id": document_id,
                "filename": original_name,
                "status": "queued",
                "task_id": task_id,
                "message": "Document uploaded and queued for processing",
            })

        except Exception as exc:
            db.rollback()
            logger.exception(
                "Document upload failed: %s",
                original_name,
            )

            results.append({
                "document_id": document_id,
                "filename": original_name,
                "status": "failed",
                "error": str(exc),
            })

        finally:
            await uploaded_file.close()

    return {
        "total_files": len(files),
        "results": results,
    }


# @router.post("/upload")
# async def upload_documents(
#     files: list[UploadFile] = File(...),
#     document_category: str | None = Form(None),
#     db: Session = Depends(get_db),
# ):
#     results = []

#     for uploaded_file in files:
#         original_name = uploaded_file.filename or "unnamed"
#         extension = Path(original_name).suffix.lower()

#         if extension not in SUPPORTED_EXTENSIONS:
#             results.append({
#                 "filename": original_name,
#                 "status": "rejected",
#                 "error": "Unsupported file format",
#             })
#             await uploaded_file.close()
#             continue

#         document_id = str(uuid4())
#         saved_path = UPLOAD_DIR / f"{document_id}{extension}"

#         try:
#             # Save file while enforcing the configured upload limit.
#             try:
#                 file_size_bytes = await save_upload_file(
#                     uploaded_file,
#                     saved_path,
#                 )

#             except HTTPException as upload_error:
#                 results.append({
#                     "filename": original_name,
#                     "status": "rejected",
#                     "error": upload_error.detail,
#                 })
#                 continue

#             # Process document.
#             try:
#                 processing_result = process_document(
#                     str(saved_path),
#                     document_category=document_category,
#                 )

#             except Exception as processing_error:
#                 persist_document_result(
#                     db=db,
#                     document_id=document_id,
#                     filename=original_name,
#                     stored_path=str(saved_path),
#                     file_size_bytes=file_size_bytes,
#                     error_message=str(processing_error),
#                     file_type=extension,
#                     document_category=document_category,
#                 )

#                 results.append({
#                     "document_id": document_id,
#                     "filename": original_name,
#                     "status": "failed",
#                     "error": str(processing_error),
#                 })
#                 continue

#             # Save successful processing results.
#             persist_document_result(
#                 db=db,
#                 document_id=document_id,
#                 filename=original_name,
#                 stored_path=str(saved_path),
#                 file_size_bytes=file_size_bytes,
#                 processing_result=processing_result,
#                 file_type=extension,
#                 document_category=document_category,
#             )

#             #enerate and store semmantic embedings
#             index_document_for_search(
#                 db=db,
#                 document_id=document_id,
#                 processing_result=processing_result,
#             )

#             results.append({
#                 "document_id": document_id,
#                 "filename": original_name,
#                 "status": processing_result["status"],
#                 "result": processing_result,
#             })

#         except Exception as exc:
#             db.rollback()

#             results.append({
#                 "document_id": document_id,
#                 "filename": original_name,
#                 "status": "failed",
#                 "error": str(exc),
#             })

#         finally:
#             await uploaded_file.close()

#     return {
#         "total_files": len(files),
#         "results": results,
#     }


# @router.post("/upload")
# async def upload_documents(
#     files: list[UploadFile] = File(...),
#     document_category: str | None = Form(None),
#     db: Session = Depends(get_db),
# ):
#     results = []

#     for uploaded_file in files:
#         original_name = uploaded_file.filename or "unnamed"
#         extension = Path(original_name).suffix.lower()

#         if extension not in SUPPORTED_EXTENSIONS:
#             results.append({
#                 "filename": original_name,
#                 "status": "rejected",
#                 "error": "Unsupported file format",
#             })
#             await uploaded_file.close()
#             continue

#         document_id = str(uuid4())
#         saved_path = UPLOAD_DIR / f"{document_id}{extension}"

#         try:
#             with saved_path.open("wb") as destination:
#                 while chunk := await uploaded_file.read(1024 * 1024):
#                     destination.write(chunk)

#             file_size_bytes = saved_path.stat().st_size

#             try:
#                 processing_result = process_document(
#                     str(saved_path),
#                     document_category=document_category,
#                 )

#             except Exception as processing_error:
#                 persist_document_result(
#                     db=db,
#                     document_id=document_id,
#                     filename=original_name,
#                     stored_path=str(saved_path),
#                     file_size_bytes=file_size_bytes,
#                     error_message=str(processing_error),
#                     file_type=extension,
#                     document_category=document_category,
#                 )

#                 results.append({
#                     "document_id": document_id,
#                     "filename": original_name,
#                     "status": "failed",
#                     "error": str(processing_error),
#                 })

#                 continue

#             persist_document_result(
#                 db=db,
#                 document_id=document_id,
#                 filename=original_name,
#                 stored_path=str(saved_path),
#                 file_size_bytes=file_size_bytes,
#                 processing_result=processing_result,
#                 file_type=extension,
#                 document_category=document_category,
#             )

#             results.append({
#                 "document_id": document_id,
#                 "filename": original_name,
#                 "status": processing_result["status"],
#                 "result": processing_result,
#             })

#         except Exception as exc:
#             db.rollback()

#             results.append({
#                 "document_id": document_id,
#                 "filename": original_name,
#                 "status": "failed",
#                 "error": str(exc),
#             })

#         finally:
#             await uploaded_file.close()

#     return {
#         "total_files": len(files),
#         "results": results,
#     }


# @router.post("/upload")
# async def upload_documents(
#     files: list[UploadFile] = File(...),
#     document_category: str | None = Form(None),
# ):
#     results = []

#     for uploaded_file in files:
#         original_name = uploaded_file.filename or "unnamed"
#         extension = Path(original_name).suffix.lower()

#         if extension not in SUPPORTED_EXTENSIONS:
#             results.append({
#                 "filename": original_name,
#                 "status": "rejected",
#                 "error": "Unsupported file format",
#             })
#             continue

#         document_id = str(uuid4())
#         saved_path = UPLOAD_DIR / f"{document_id}{extension}"

#         try:
#             with saved_path.open("wb") as destination:
#                 while chunk := await uploaded_file.read(1024 * 1024):
#                     destination.write(chunk)

#             processing_result = process_document(
#                 str(saved_path),
#                 document_category=document_category,
#             )

#             results.append({
#                 "document_id": document_id,
#                 "filename": original_name,
#                 "status": processing_result["status"],
#                 "result": processing_result,
#             })

#         except Exception as exc:
#             results.append({
#                 "document_id": document_id,
#                 "filename": original_name,
#                 "status": "failed",
#                 "error": str(exc),
#             })

#         finally:
#             await uploaded_file.close()

#     return {
#         "total_files": len(files),
#         "results": results,
#     }

# Add verification endpoint

@router.post("/verify")
async def verify_uploaded_documents(
    document_1: UploadFile = File(...),
    document_2: UploadFile = File(...),
    document_1_category: str = Form(...),
    document_2_category: str = Form(...),
    db: Session = Depends(get_db),
):
    category_1 = document_1_category.strip().lower()
    category_2 = document_2_category.strip().lower()

    supported_categories = {"invoice", "bank_statement", "receipt"}

    if category_1 not in supported_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported first document category: {category_1}"
        )

    if category_2 not in supported_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported second document category: {category_2}"
        )

    # Determine the comparison strategy.
    verification_category = (
        category_1
        if category_1 == category_2
        else f"{category_1}_{category_2}"
    )

    uploaded_files = [
        (document_1, category_1),
        (document_2, category_2),
    ]

    saved_files = []

    try:
        for uploaded_file, document_category in uploaded_files:
            original_name = uploaded_file.filename or "unnamed"
            extension = Path(original_name).suffix.lower()

            if extension not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {extension}"
                )

            document_id = str(uuid4())
            saved_path = UPLOAD_DIR / f"{document_id}{extension}"

            with saved_path.open("wb") as destination:
                while chunk := await uploaded_file.read(1024 * 1024):
                    destination.write(chunk)

            file_size_bytes = saved_path.stat().st_size

            processing_result = process_document(
                str(saved_path),
                document_category=document_category,
            )

            persist_document_result(
                db=db,
                document_id=document_id,
                filename=original_name,
                stored_path=str(saved_path),
                file_size_bytes=file_size_bytes,
                processing_result=processing_result,
                file_type=extension,
                document_category=document_category,
            )

            saved_files.append({
                "document_id": document_id,
                "filename": original_name,
                "document_category": document_category,
                "processing_result": processing_result,
            })

        # Perform cross-document verification.
        verification_result = verify_documents(
            saved_files[0]["processing_result"],
            saved_files[1]["processing_result"],
            document_category=verification_category,
            document_1_name=saved_files[0]["filename"],
            document_2_name=saved_files[1]["filename"],
        )

        verification_record = CrossDocumentVerification(
            verification_id=str(uuid4()),
            document_1_id=saved_files[0]["document_id"],
            document_2_id=saved_files[1]["document_id"],
            document_category=verification_category,
            verification_status=verification_result["verification_status"],
            verification_result=jsonable_encoder(verification_result),
        )

        db.add(verification_record)
        db.commit()

        return {
            "document_category": verification_category,
            "documents": [
                {
                    "document_id": item["document_id"],
                    "filename": item["filename"],
                    "document_category": item["document_category"],
                    "processing_status": item["processing_result"]["status"],
                }
                for item in saved_files
            ],
            "verification_id": verification_record.verification_id,
            "verification": verification_result,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"Document verification failed: {exc}"
        ) from exc

    finally:
        for uploaded_file, _ in uploaded_files:
            await uploaded_file.close()

# @router.post("/verify")
# async def verify_uploaded_documents(
#     document_1: UploadFile = File(...),
#     document_2: UploadFile = File(...),
#     document_category: str = Form(...),
#     db: Session = Depends(get_db),
# ):
#     category = document_category.strip().lower()

#     if category not in {"invoice", "bank_statement"}:
#         raise HTTPException(
#             status_code=400,
#             detail="Category must be 'invoice' or 'bank_statement'."
#         )

#     uploaded_files = [document_1, document_2]
#     saved_files = []

#     try:
#         # Save and process both documents.
#         for uploaded_file in uploaded_files:
#             original_name = uploaded_file.filename or "unnamed"
#             extension = Path(original_name).suffix.lower()

#             if extension not in SUPPORTED_EXTENSIONS:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Unsupported file format: {extension}"
#                 )

#             document_id = str(uuid4())
#             saved_path = UPLOAD_DIR / f"{document_id}{extension}"

#             with saved_path.open("wb") as destination:
#                 while chunk := await uploaded_file.read(1024 * 1024):
#                     destination.write(chunk)

#             file_size_bytes = saved_path.stat().st_size

#             processing_result = process_document(
#                 str(saved_path),
#                 document_category=category,
#             )

#             # Persist the individual document and processing job.
#             persist_document_result(
#                 db=db,
#                 document_id=document_id,
#                 filename=original_name,
#                 stored_path=str(saved_path),
#                 file_size_bytes=file_size_bytes,
#                 processing_result=processing_result,
#                 file_type=extension,
#                 document_category=category,
#             )

#             saved_files.append({
#                 "document_id": document_id,
#                 "filename": original_name,
#                 "processing_result": processing_result,
#             })

#         # Perform cross-document verification.
#         verification_result = verify_documents(
#             saved_files[0]["processing_result"],
#             saved_files[1]["processing_result"],
#             document_category=category,
#             document_1_name=saved_files[0]["filename"],
#             document_2_name=saved_files[1]["filename"],
#         )

#         # Persist the verification record.
#         verification_record = CrossDocumentVerification(
#             verification_id=str(uuid4()),
#             document_1_id=saved_files[0]["document_id"],
#             document_2_id=saved_files[1]["document_id"],
#             document_category=category,
#             verification_status=verification_result["verification_status"],
#             verification_result=jsonable_encoder(verification_result),
#         )

#         db.add(verification_record)
#         db.commit()

#         return {
#             "document_category": category,
#             "documents": [
#                 {
#                     "document_id": item["document_id"],
#                     "filename": item["filename"],
#                     "processing_status": item["processing_result"]["status"],
#                 }
#                 for item in saved_files
#             ],
#             "verification_id": verification_record.verification_id,
#             "verification": verification_result,
#         }

#     except HTTPException:
#         db.rollback()
#         raise

#     except Exception as exc:
#         db.rollback()
#         raise HTTPException(
#             status_code=422,
#             detail=f"Document verification failed: {exc}"
#         ) from exc

#     finally:
#         for uploaded_file in uploaded_files:
#             await uploaded_file.close()


# @router.post("/verify")
# async def verify_uploaded_documents(
#     document_1: UploadFile = File(...),
#     document_2: UploadFile = File(...),
#     document_category: str = Form(...),
# ):
#     category = document_category.strip().lower()

#     if category not in {"invoice", "bank_statement"}:
#         raise HTTPException(
#             status_code=400,
#             detail="Category must be 'invoice' or 'bank_statement'.",
#         )

#     uploaded_files = [document_1, document_2]
#     saved_files = []

#     try:
#         # Save and validate both uploaded documents.
#         for uploaded_file in uploaded_files:
#             original_name = uploaded_file.filename or "unnamed"
#             extension = Path(original_name).suffix.lower()

#             if extension not in SUPPORTED_EXTENSIONS:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Unsupported file format: {extension}",
#                 )

#             document_id = str(uuid4())
#             saved_path = UPLOAD_DIR / f"{document_id}{extension}"

#             with saved_path.open("wb") as destination:
#                 while chunk := await uploaded_file.read(1024 * 1024):
#                     destination.write(chunk)

#             saved_files.append({
#                 "document_id": document_id,
#                 "filename": original_name,
#                 "path": saved_path,
#             })

#         # Reuse the existing document extraction pipeline.
#         processing_result_1 = process_document(
#             str(saved_files[0]["path"]),
#             document_category=category,
#         )

#         processing_result_2 = process_document(
#             str(saved_files[1]["path"]),
#             document_category=category,
#         )

#         # Compare the extracted structured data.
#         verification_result = verify_documents(
#             processing_result_1,
#             processing_result_2,
#             document_category=category,
#             document_1_name=saved_files[0]["filename"],
#             document_2_name=saved_files[1]["filename"],
#         )

#         return {
#             "document_category": category,
#             "documents": [
#                 {
#                     "document_id": item["document_id"],
#                     "filename": item["filename"],
#                     "processing_status": processing_result_1["status"]
#                     if index == 0
#                     else processing_result_2["status"],
#                 }
#                 for index, item in enumerate(saved_files)
#             ],
#             "verification": verification_result,
#         }

#     except HTTPException:
#         raise

#     except Exception as exc:
#         raise HTTPException(
#             status_code=422,
#             detail=f"Document verification failed: {exc}",
#         ) from exc

#     finally:
#         for uploaded_file in uploaded_files:
#             await uploaded_file.close()


@router.get("/{document_id}/status")
def get_document_status(
    document_id: str,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.document_id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_id}",
        )

    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )

    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "processing_status": document.processing_status,
        "job": (
            {
                "job_id": job.job_id,
                "task_id": job.task_id,
                "status": job.status,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "error_message": job.error_message,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
            }
            if job else None
        ),
    }

@router.get("/search")
def search_documents(
    q: str | None = None,
    document_category: str | None = None,
    processing_status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Document)

    if q and q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Document.filename.ilike(keyword),
                Document.extracted_text.ilike(keyword),
            )
        )

    if document_category:
        query = query.filter(
            Document.document_category == document_category
        )

    if processing_status:
        query = query.filter(
            Document.processing_status == processing_status
        )

    total = query.count()

    documents = (
        query
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "document_category": doc.document_category,
                "processing_status": doc.processing_status,
                "file_size_bytes": doc.file_size_bytes,
                "created_at": doc.created_at,
            }
            for doc in documents
        ],
    }


@router.get("/semantic-search")
def semantic_search_documents(
    q: str = Query(..., min_length=2, max_length=2000),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    search_text = q.strip()

    if not search_text:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    try:
        # Generate an embedding for the search query.
        query_embedding = generate_embeddings([search_text])[0]

        # Calculate cosine distance between query and stored vectors.
        distance = DocumentChunk.embedding.cosine_distance(
            query_embedding
        ).label("distance")

        # Retrieve the most relevant document chunks.
        results = (
            db.query(
                DocumentChunk,
                Document.filename,
                Document.document_category,
                distance,
            )
            .join(
                Document,
                Document.document_id == DocumentChunk.document_id,
            )
            .order_by(distance.asc())
            .limit(limit)
            .all()
        )

        return {
            "query": search_text,
            "total_results": len(results),
            "results": [
                {
                    "document_id": chunk.document_id,
                    "filename": filename,
                    "document_category": category,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "similarity_score": round(
                        1 - float(chunk_distance), 4
                    ),
                }
                for chunk, filename, category, chunk_distance in results
            ],
        }

    except Exception as exc:
        logger.exception("Semantic document search failed.")

        raise HTTPException(
            status_code=503,
            detail="Semantic search is temporarily unavailable.",
        ) from exc


@router.patch("/{document_id}/corrections")
def correct_invoice(
    document_id: str,
    correction: InvoiceCorrection,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.document_id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_id}",
        )

    if document.document_category != "invoice":
        raise HTTPException(
            status_code=400,
            detail="Corrections are currently supported for invoices only.",
        )

    invoice = (
        db.query(Invoice)
        .filter(Invoice.document_id == document_id)
        .first()
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice extraction record not found.",
        )

    updates = correction.model_dump(
        exclude_unset=True,
        mode="json",
    )

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No correction fields were provided.",
        )

    if "line_items" in updates:
        if updates["line_items"] is None:
            raise HTTPException(
                status_code=422,
                detail="line_items cannot be null.",
            )

    try:
        for field, value in updates.items():
            setattr(invoice, field, value)

        ai_extraction = dict(document.ai_extraction or {})
        ai_extraction.update(updates)
        document.ai_extraction = ai_extraction

        db.commit()
        db.refresh(invoice)

        return {
            "message": "Invoice corrections saved successfully.",
            "document_id": document_id,
            "corrected_fields": list(updates.keys()),
            "invoice": {
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date,
                "due_date": invoice.due_date,
                "supplier": invoice.supplier,
                "customer": invoice.customer,
                "currency": invoice.currency,
                "subtotal": invoice.subtotal,
                "tax_rate": invoice.tax_rate,
                "tax_amount": invoice.tax_amount,
                "total": invoice.total,
                "line_items": invoice.line_items,
                "requires_review": invoice.requires_review,
                "review_reasons": invoice.review_reasons,
            },
        }

    except Exception:
        db.rollback()
        raise

@router.post("/{document_id}/retry")
def retry_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    # Find the existing document.
    document = (
        db.query(Document)
        .filter(Document.document_id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_id}",
        )

    # Only failed documents can be retried.
    if document.processing_status != "failed":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only failed documents can be retried. "
                f"Current status: {document.processing_status}"
            ),
        )

    # Create a fresh processing job.
    # Previous jobs remain available as processing history.
    now = datetime.now(timezone.utc)

    job = ProcessingJob(
        job_id=str(uuid4()),
        document_id=document_id,
        status="queued",
        retry_count=0,
        max_retries=3,
    )

    document.processing_status = "queued"

    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue the document for background processing.
    try:
        task_id = enqueue_document_processing(document_id)

        job.task_id = task_id
        db.commit()
        db.refresh(job)

    except Exception as exc:
        logger.exception(
            "Could not enqueue retry for document %s",
            document_id,
        )

        db.rollback()

        # Reload the records after rollback.
        document = (
            db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )

        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.job_id == job.job_id)
            .first()
        )

        if document is not None:
            document.processing_status = "failed"

        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)

        db.commit()

        raise HTTPException(
            status_code=503,
            detail="Could not queue document retry. Please try again.",
        )

    return {
        "message": "Document retry queued successfully.",
        "document_id": document_id,
        "job_id": job.job_id,
        "task_id": task_id,
        "processing_status": "queued",
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
    }

# @router.post("/{document_id}/retry")
# def retry_document(
#     document_id: str,
#     db: Session = Depends(get_db),
# ):
#     # Find the existing document.
#     document = (
#         db.query(Document)
#         .filter(Document.document_id == document_id)
#         .first()
#     )

#     if document is None:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Document not found: {document_id}",
#         )

#     # Only failed documents can be retried.
#     if document.processing_status != "failed":
#         raise HTTPException(
#             status_code=409,
#             detail=(
#                 "Only failed documents can be retried. "
#                 f"Current status: {document.processing_status}"
#             ),
#         )

#     # Retrieve the latest processing job.
#     previous_job = (
#         db.query(ProcessingJob)
#         .filter(ProcessingJob.document_id == document_id)
#         .order_by(ProcessingJob.created_at.desc())
#         .first()
#     )

#     retry_count = (
#         previous_job.retry_count + 1
#         if previous_job else 1
#     )

#     max_retries = (
#         previous_job.max_retries
#         if previous_job else 3
#     )

#     if retry_count > max_retries:
#         raise HTTPException(
#             status_code=409,
#             detail="Maximum retry attempts reached.",
#         )

#     # Create a new job while preserving previous job history.
#     now = datetime.now(timezone.utc)

#     job = ProcessingJob(
#         job_id=str(uuid4()),
#         document_id=document_id,
#         status="processing",
#         retry_count=retry_count,
#         max_retries=max_retries,
#         started_at=now,
#     )

#     document.processing_status = "processing"

#     db.add(job)
#     db.commit()
#     db.refresh(job)

#     # Reprocess the original uploaded file.
#     try:
#         result = process_document(
#             file_path=document.stored_path,
#             document_category=document.document_category,
#         )

#     except Exception as exc:
#         error_message = str(exc)

#         document.processing_status = "failed"

#         job.status = "failed"
#         job.error_message = error_message
#         job.completed_at = datetime.now(timezone.utc)

#         db.commit()

#         return {
#             "document_id": document_id,
#             "job_id": job.job_id,
#             "status": "failed",
#             "retry_count": retry_count,
#             "error_message": error_message,
#         }

#     # Update the existing document record.
#     document.file_type = result.get("file_type") or document.file_type
#     document.document_type = (
#         result.get("document_type") or document.document_type
#     )
#     document.document_category = (
#         result.get("document_category")
#         or document.document_category
#     )
#     document.processing_status = result.get("status", "completed")

#     extraction_result = result.get("extraction_result") or {}
#     ai_extraction = result.get("ai_extraction")
#     validation = result.get("validation")

#     extracted_text = extraction_result.get("full_text")

#     if not extracted_text and extraction_result:
#         extracted_text = json.dumps(
#             extraction_result,
#             ensure_ascii=False,
#             default=str,
#         )

#     document.extracted_text = extracted_text
#     document.extraction_result = jsonable_encoder(
#         extraction_result
#     )
#     document.ai_extraction = jsonable_encoder(ai_extraction)
#     document.validation_result = jsonable_encoder(validation)

#     # Update or create the invoice record.
#     if (
#         document.document_category == "invoice"
#         and ai_extraction
#     ):
#         invoice_data = InvoiceExtraction.model_validate(
#             ai_extraction
#         )

#         invoice = (
#             db.query(Invoice)
#             .filter(Invoice.document_id == document_id)
#             .first()
#         )

#         if invoice is None:
#             invoice = Invoice(document_id=document_id)
#             db.add(invoice)

#         invoice.invoice_number = invoice_data.invoice_number
#         invoice.invoice_date = invoice_data.invoice_date
#         invoice.due_date = invoice_data.due_date
#         invoice.supplier = invoice_data.supplier
#         invoice.customer = invoice_data.customer
#         invoice.currency = invoice_data.currency
#         invoice.subtotal = invoice_data.subtotal
#         invoice.tax_rate = invoice_data.tax_rate
#         invoice.tax_amount = invoice_data.tax_amount
#         invoice.total = invoice_data.total

#         invoice.line_items = [
#             item.model_dump(mode="json")
#             for item in invoice_data.line_items
#         ]

#         invoice.requires_review = invoice_data.requires_review
#         invoice.review_reasons = invoice_data.review_reason

#     # Replace previous validation issues with the latest results.
#     db.query(ValidationIssue).filter(
#         ValidationIssue.document_id == document_id
#     ).delete(synchronize_session=False)

#     if validation:
#         for severity, key in (
#             ("error", "errors"),
#             ("warning", "warnings"),
#         ):
#             for issue in validation.get(key, []):
#                 if isinstance(issue, dict):
#                     message = issue.get("issue", "Validation issue")
#                     field_name = issue.get("field")
#                     error_code = issue.get("code")
#                 else:
#                     message = str(issue)
#                     field_name = None
#                     error_code = None

#                 db.add(
#                     ValidationIssue(
#                         document_id=document_id,
#                         error_code=error_code,
#                         severity=severity,
#                         field_name=field_name,
#                         message=str(message),
#                         details=jsonable_encoder(issue),
#                     )
#                 )

#     # Complete the new processing job.
#     job.status = "completed"
#     job.error_message = None
#     job.completed_at = datetime.now(timezone.utc)

#     db.commit()

#     index_document_for_search(
#         db=db,
#         document_id=document_id,
#         processing_result=result,
#     )

#     return {
#         "message": "Document reprocessed successfully.",
#         "document_id": document_id,
#         "job_id": job.job_id,
#         "processing_status": document.processing_status,
#         "retry_count": retry_count,
#         "max_retries": max_retries,
#     }

@router.get("/verifications/{verification_id}")
def get_verification(
    verification_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(CrossDocumentVerification)
        .filter(
            CrossDocumentVerification.verification_id
            == verification_id
        )
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Verification record not found.",
        )

    return {
        "verification_id": record.verification_id,
        "document_1_id": record.document_1_id,
        "document_2_id": record.document_2_id,
        "document_category": record.document_category,
        "verification_status": record.verification_status,
        "verification_result": record.verification_result,
        "created_at": record.created_at,
    }

@router.get("/{document_id}/validation-issues")
def get_document_validation_issues(
    document_id: str,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.document_id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    issues = (
        db.query(ValidationIssue)
        .filter(ValidationIssue.document_id == document_id)
        .order_by(ValidationIssue.created_at.desc())
        .all()
    )

    return {
        "document_id": document_id,
        "total_issues": len(issues),
        "issues": [
            {
                "id": issue.id,
                "error_code": issue.error_code,
                "severity": issue.severity,
                "field_name": issue.field_name,
                "message": issue.message,
                "details": issue.details,
                "created_at": issue.created_at,
            }
            for issue in issues
        ],
    }

@router.get("/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.document_id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_id}",
        )

    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "file_type": document.file_type,
        "document_type": document.document_type,
        "document_category": document.document_category,
        "processing_status": document.processing_status,
        "file_size_bytes": document.file_size_bytes,
        "extracted_text": document.extracted_text,
        "extraction_result": document.extraction_result,
        "ai_extraction": document.ai_extraction,
        "validation_result": document.validation_result,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }