from pathlib import Path
from typing import Any

import pandas as pd
import pymupdf
import pytesseract
from PIL import Image, ImageSequence


SUPPORTED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff",
    ".xlsx", ".xls", ".csv"
}


def process_pdf(file_path: Path) -> dict[str, Any]:
    """Extract digital text and OCR pages with little or no text."""
    pages = []
    errors = []

    try:
        with pymupdf.open(file_path) as document:
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text").strip()
                extraction_method = "digital_text"

                if len(text) < 30:
                    try:
                        pixmap = page.get_pixmap(dpi=200, alpha=False)
                        image = Image.frombytes(
                            "RGB",
                            [pixmap.width, pixmap.height],
                            pixmap.samples,
                        )
                        text = pytesseract.image_to_string(image).strip()
                        extraction_method = "ocr"
                    except Exception as exc:
                        errors.append({
                            "page": page_number,
                            "error": f"OCR failed: {str(exc)}",
                        })
                        extraction_method = "ocr_failed"

                pages.append({
                    "page_number": page_number,
                    "text": text,
                    "method": extraction_method,
                })

    except Exception as exc:
        return {
            "document_type": "pdf",
            "status": "failed",
            "pages": [],
            "errors": [{"error": str(exc)}],
        }

    return {
        "document_type": "pdf",
        "status": "completed" if not errors else "completed_with_errors",
        "page_count": len(pages),
        "pages": pages,
        "errors": errors,
    }


def process_image(file_path: Path) -> dict[str, Any]:
    """OCR image files, including multi-frame TIFF images."""
    pages = []
    errors = []

    try:
        with Image.open(file_path) as image:
            for page_number, frame in enumerate(
                ImageSequence.Iterator(image), start=1
            ):
                try:
                    text = pytesseract.image_to_string(
                        frame.convert("RGB")
                    ).strip()

                    pages.append({
                        "page_number": page_number,
                        "text": text,
                        "method": "ocr",
                    })
                except Exception as exc:
                    errors.append({
                        "page": page_number,
                        "error": str(exc),
                    })

    except Exception as exc:
        return {
            "document_type": "image",
            "status": "failed",
            "pages": [],
            "errors": [{"error": str(exc)}],
        }

    return {
        "document_type": "image",
        "status": "completed" if not errors else "completed_with_errors",
        "page_count": len(pages),
        "pages": pages,
        "errors": errors,
    }


def process_spreadsheet(file_path: Path) -> dict[str, Any]:
    """Read every sheet in Excel files or the contents of a CSV."""
    try:
        sheets = {}

        if file_path.suffix.lower() == ".csv":
            dataframe = pd.read_csv(file_path, encoding="utf-8-sig")
            sheets["CSV"] = dataframe

        else:
            workbook = pd.ExcelFile(file_path)
            for sheet_name in workbook.sheet_names:
                sheets[sheet_name] = pd.read_excel(
                    workbook,
                    sheet_name=sheet_name,
                )

        results = {}

        for sheet_name, dataframe in sheets.items():
            dataframe = dataframe.astype(object).where(
                pd.notna(dataframe), None
            )

            results[sheet_name] = {
                "columns": [str(column) for column in dataframe.columns],
                "row_count": len(dataframe),
                "rows": dataframe.to_dict(orient="records"),
            }

        return {
            "document_type": "spreadsheet",
            "status": "completed",
            "sheets": results,
            "errors": [],
        }

    except Exception as exc:
        return {
            "document_type": "spreadsheet",
            "status": "failed",
            "sheets": {},
            "errors": [{"error": str(exc)}],
        }


def process_document(file_path: Path) -> dict[str, Any]:
    """Dispatch a document to the appropriate processor."""
    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        return {
            "status": "failed",
            "errors": [{"error": "Unsupported file format"}],
        }

    if extension == ".pdf":
        return process_pdf(file_path)

    if extension in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return process_image(file_path)

    if extension in {".xlsx", ".xls", ".csv"}:
        return process_spreadsheet(file_path)

    return {
        "status": "failed",
        "errors": [{"error": "No processor available"}],
    }
