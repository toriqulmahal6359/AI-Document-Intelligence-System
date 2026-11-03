from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.document_processor import (
    process_document,
    SUPPORTED_EXTENSIONS,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...)
):
    results = []

    for uploaded_file in files:
        original_name = uploaded_file.filename or "unnamed"

        extension = Path(original_name).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            results.append({
                "filename": original_name,
                "status": "rejected",
                "error": "Unsupported file format",
            })
            continue

        document_id = str(uuid4())
        saved_path = UPLOAD_DIR / f"{document_id}{extension}"

        try:
            with saved_path.open("wb") as destination:
                while chunk := await uploaded_file.read(1024 * 1024):
                    destination.write(chunk)

            processing_result = process_document(saved_path)

            results.append({
                "document_id": document_id,
                "filename": original_name,
                "status": processing_result["status"],
                "result": processing_result,
            })

        except Exception as exc:
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
