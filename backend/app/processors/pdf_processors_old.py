from pathlib import Path
import fitz


def extract_pdf_text(file_path: str) -> dict:
    """
    Extract embedded text from every page of a PDF.
    OCR is handled separately for pages without usable text.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Unsupported file type. Expected PDF.")

    pages = []

    try:
        with fitz.open(path) as pdf:
            if pdf.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported.")

            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()

                pages.append({
                    "page_number": page_number,
                    "text": text,
                    "needs_ocr": len(text) < 30,
                })

    except fitz.FileDataError as exc:
        raise ValueError("Invalid or corrupted PDF file.") from exc

    return {
        "filename": path.name,
        "total_pages": len(pages),
        "pages": pages,
        "full_text": "\n\n".join(
            page["text"] for page in pages
        ),
        "pages_requiring_ocr": [
            page["page_number"]
            for page in pages
            if page["needs_ocr"]
        ],
    }
