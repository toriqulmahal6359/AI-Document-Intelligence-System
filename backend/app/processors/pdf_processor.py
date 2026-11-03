from pathlib import Path
import os

import fitz
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_CMD", "tesseract"
)


# def extract_pdf_text(file_path: str) -> dict:
def extract_pdf_text(
    file_path: str,
    document_category: str | None = None,
) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Expected a PDF file.")

    pages = []

    try:
        with fitz.open(path) as pdf:
            if pdf.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported.")

            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()
                extraction_method = "digital"

                # Preserve the PDF's text blocks for structured parsing.
                blocks = [
                    {
                        "text": block[4].strip(),
                        "bbox": list(block[:4]),
                    }
                    for block in page.get_text("blocks")
                    if len(block) >= 5 and block[4].strip()
                ]

                # OCR only when embedded text is insufficient.
                if len(text) < 30:
                    pixmap = page.get_pixmap(
                        # matrix=fitz.Matrix(2, 2),
                        matrix=fitz.Matrix(
                            3 if document_category == "receipt" else 2,
                            3 if document_category == "receipt" else 2,
                        ),
                        colorspace=fitz.csGRAY,
                        alpha=False,
                    )

                    image = Image.frombytes(
                        "L",
                        [pixmap.width, pixmap.height],
                        pixmap.samples,
                    )

                    text = pytesseract.image_to_string(
                        image,
                        # config="--oem 3 --psm 3",
                        config=(
                            "--oem 3 --psm 6"
                            if document_category == "receipt"
                            else "--oem 3 --psm 3"
                        ),
                    ).strip()

                    extraction_method = "ocr"

                    # OCR text is retained as one block.
                    blocks = (
                        [{"text": text, "bbox": None}]
                        if text else []
                    )

                pages.append({
                    "page_number": page_number,
                    "text": text,
                    "blocks": blocks,
                    "extraction_method": extraction_method,
                    "needs_review": len(text) < 30,
                })

    except fitz.FileDataError as exc:
        raise ValueError("Invalid or corrupted PDF file.") from exc

    return {
        "filename": path.name,
        "total_pages": len(pages),
        "pages": pages,
        "full_text": "\n\n".join(p["text"] for p in pages),
        "pages_requiring_review": [
            p["page_number"]
            for p in pages
            if p["needs_review"]
        ],
    }
