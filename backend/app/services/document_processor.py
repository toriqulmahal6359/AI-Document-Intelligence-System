import pytesseract

from app.core.config import TESSERACT_CMD

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

from pathlib import Path

from app.processors.pdf_processor import extract_pdf_text
from app.processors.image_processor import extract_image_text
from app.processors.spreadsheet_processor import process_spreadsheet

from app.services.extraction_service import extract_invoice
from app.services.receipt_extraction_service import extract_receipt

from app.services.bank_statement_extraction_service import (
    extract_bank_statement_from_spreadsheet,
    extract_bank_statement_from_pdf,
    extract_bank_statement_from_image,
)

from app.services.bank_statement_ai_extraction_service import (
    # extract_bank_statement_from_text,
    extract_bank_statement_from_pages,
)

# from app.services.bank_statement_extraction_service import extract_bank_statement_from_image

# from app.services.bank_statement_extraction_service import (
#     extract_bank_statement_from_pdf,
# )

from app.services.bank_statement_validation_service import (
    validate_bank_statement,
)

from app.services.receipt_validation_service import validate_receipt


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


def process_document(
    file_path: str,
    document_category: str | None = None,
) -> dict:

    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported document format: {extension}"
        )

    # -----------------------------------------
    # STEP 1: Document text/data extraction
    # -----------------------------------------

    if extension == ".pdf":

        # result = extract_pdf_text(str(path))
        result = extract_pdf_text(
            str(path),
            document_category=document_category,
        )
        document_type = "pdf"

    # elif extension in {
    #     ".jpg",
    #     ".jpeg",
    #     ".png",
    #     ".tif",
    #     ".tiff",
    # }:

    #     extracted_text = extract_image_text(str(path))

    #     result = {
    #         "filename": path.name,
    #         "total_pages": 1,
    #         "pages": [
    #             {
    #                 "page_number": 1,
    #                 "text": extracted_text,
    #                 "extraction_method": "ocr",
    #                 "needs_review": len(extracted_text) < 30,
    #             }
    #         ],
    #         "full_text": extracted_text,
    #         "pages_requiring_review": (
    #             [1] if len(extracted_text) < 30 else []
    #         ),
    #     }

    #     document_type = "image"

    elif extension in {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    }:

        document_type = "image"

        if document_category == "bank_statement":

            # Bank statements use coordinate-based OCR extraction.
            # Avoid running the ordinary image OCR pipeline first.
            result = {
                "filename": path.name,
                "total_pages": 1,
                "pages": [],
                "full_text": "",
                "pages_requiring_review": [],
            }

        else:

            # Preserve existing image extraction for other document types.
            # extracted_text = extract_image_text(str(path))

            extracted_text = extract_image_text(
                str(path),
                document_category=document_category,
            )

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

    else:

        result = process_spreadsheet(str(path))
        document_type = "spreadsheet"

    # -----------------------------------------
    # STEP 2: Document-specific AI extraction
    # -----------------------------------------

    ai_extraction = None
    validation = None

    status = result.get("status", "completed")

    if document_category == "invoice":

        if document_type == "spreadsheet":

            import json

            document_text = json.dumps(
                result["sheets"],
                default=str,
                ensure_ascii=False,
            )

        else:
            document_text = result.get("full_text", "")

        invoice = extract_invoice(document_text)

        ai_extraction = invoice.model_dump(mode="json")

    # elif document_category == "receipt":

    #     if document_type == "spreadsheet":

    #         import json

    #         document_text = json.dumps(
    #             result["sheets"],
    #             default=str,
    #             ensure_ascii=False,
    #         )

    #     else:
    #         document_text = result.get("full_text", "")

    #     receipt = extract_receipt(document_text)

    #     ai_extraction = receipt.model_dump(mode="json")

    #     status = (
    #         "requires_review"
    #         if receipt.requires_review
    #         else "completed"
    #     )
    
    elif document_category == "receipt":
        document_text = (
            json.dumps(result["sheets"], ensure_ascii=False)
            if extension in [".xlsx", ".xls", ".csv"]
            else result["full_text"]
        )

        receipt = extract_receipt(document_text)

        validation = validate_receipt(receipt)

        if validation["requires_review"]:
            receipt.requires_review = True
            receipt.review_reason = list(dict.fromkeys(
                receipt.review_reason + validation["errors"]
            ))

        ai_extraction = receipt.model_dump(mode="json")

        status = (
            "requires_review"
            if receipt.requires_review
            else "completed"
        )

    # elif document_category == "bank_statement":

    #     if document_type == "spreadsheet":

    #         bank_statement = extract_bank_statement_from_spreadsheet(
    #             file_path=str(path),
    #         )

    #     else:

    #         # document_text = result.get("full_text", "")

    #         # bank_statement = extract_bank_statement_from_text(
    #         #     document_text
    #         # )
    #         bank_statement = extract_bank_statement_from_pages(
    #             result.get("pages", [])
    # )

    elif document_category == "bank_statement":

        #extract bank-statement data
        if extension in {".xlsx", ".xls", ".csv"}:

            bank_statement = extract_bank_statement_from_spreadsheet(
                file_path
            )

        # elif extension == ".pdf":

        #     is_digital_pdf = all(
        #         page.get("extraction_method") == "digital"
        #         for page in result.get("pages", [])
        #     )

        #     if is_digital_pdf:
        #         bank_statement = extract_bank_statement_from_pdf(
        #             file_path
        #         )
        #     else:
        #         bank_statement = extract_bank_statement_from_pages(
        #             result.get("pages", [])
        #         )

        # calling from back_statement_ai_extraction_service
        elif extension == ".pdf":
            bank_statement = extract_bank_statement_from_pdf(
                file_path=str(path),
            )

        elif extension in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:

            bank_statement = extract_bank_statement_from_image(
                file_path=str(path),
        )

        else:
            bank_statement = extract_bank_statement_from_pages(
                result.get("pages", [])
            )

        # validation = validate_bank_statement(bank_statement)

        ###### Keep your existing validation-result handling here.

        # -----------------------------------------
        # STEP 3: Deterministic validation
        # -----------------------------------------

        validation = validate_bank_statement(
            bank_statement
        )

        # Combine extraction and validation review flags.
        review_reasons = list(
            bank_statement.review_reason or []
        )

        for error in validation["errors"]:
            issue = error.get("issue", "Validation error")
            review_reasons.append(issue)

        for warning in validation["warnings"]:
            issue = warning.get("issue", "Validation warning")
            review_reasons.append(issue)

        bank_statement.review_reason = list(
            dict.fromkeys(review_reasons)
        )

        bank_statement.requires_review = (
            bank_statement.requires_review
            or validation["requires_review"]
        )

        ai_extraction = bank_statement.model_dump(
            mode="json"
        )

        status = (
            "requires_review"
            if bank_statement.requires_review
            else "completed"
        )

    # -----------------------------------------
    # STEP 4: Common response
    # -----------------------------------------

    return {
        "filename": path.name,
        "file_type": extension,
        "document_type": document_type,
        "document_category": document_category,
        "status": status,
        "extraction_result": result,
        "ai_extraction": ai_extraction,
        "validation": validation,
    }