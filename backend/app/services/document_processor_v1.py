import pytesseract
from app.core.config import TESSERACT_CMD
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

from pathlib import Path

from app.processors.pdf_processor import extract_pdf_text
from app.processors.image_processor import extract_image_text
from app.processors.spreadsheet_processor import process_spreadsheet

import json

from app.services.extraction_service import extract_invoice


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".xlsx",
    ".xls",
    ".csv",
}


# def process_document(file_path: str) -> dict:
def process_document(
    file_path: str,
    document_category: str | None = None,
) -> dict:
    """
    Route a document to its appropriate processor.

    Returns a common structure containing document metadata
    and extracted content.
    """

    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Document not found: {path}")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported document format: {extension}"
        )

    if extension == ".pdf":
        result = extract_pdf_text(str(path))
        document_type = "pdf"

    elif extension in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        extracted_text = extract_image_text(str(path))

        result = {
            "filename": path.name,
            "total_pages": 1,
            "pages": [
                {
                    "page_number": 1,
                    "text": extracted_text,
                    "extraction_method": "ocr",
                    "needs_review": len(extracted_text) < 30,
                }
            ],
            "full_text": extracted_text,
            "pages_requiring_review": (
                [1] if len(extracted_text) < 30 else []
            ),
        }

        document_type = "image"

    else:
        result = process_spreadsheet(str(path))
        document_type = "spreadsheet"

    ai_extraction = None

    if document_category == "invoice":

        if document_type == "spreadsheet":
            document_text = json.dumps(
                result["sheets"],
                default=str,
                ensure_ascii=False,
            )
        else:
            document_text = result.get("full_text", "")

        ai_extraction = extract_invoice(document_text)

        ai_extraction = ai_extraction.model_dump(mode="json")

    # return {
    #     "filename": path.name,
    #     "file_type": extension,
    #     "document_type": document_type,
    #     "status": result.get("status", "completed"),
    #     "extraction_result": result,
    # }

    return {
        "filename": path.name,
        "file_type": extension,
        "document_type": document_type,
        "document_category": document_category,
        "status": result.get("status", "completed"),
        "extraction_result": result,
        "ai_extraction": ai_extraction,
    }
