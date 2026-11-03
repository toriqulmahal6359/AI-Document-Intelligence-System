from pathlib import Path
import os

import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from rapidocr_onnxruntime import RapidOCR
from PIL import Image


pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_CMD", "tesseract"
)

_receipt_ocr = None


def _get_receipt_ocr():
    """Initialize RapidOCR once and reuse the engine."""
    global _receipt_ocr

    if _receipt_ocr is None:
        _receipt_ocr = RapidOCR()

    return _receipt_ocr


def _extract_receipt_text(image: np.ndarray) -> str:
    """Extract receipt text using RapidOCR."""

    ocr = _get_receipt_ocr()
    result, _ = ocr(image)

    if not result:
        return ""

    # Sort recognized text regions by their vertical position.
    sorted_results = sorted(
        result,
        key=lambda item: (
            sum(point[1] for point in item[0]) / 4,
            min(point[0] for point in item[0]),
        ),
    )

    extracted_lines = []

    for item in sorted_results:
        text = item[1].strip()

        try:
            confidence = float(item[2])
        except (ValueError, TypeError):
            continue

        # Do not silently include very uncertain OCR results.
        if not text or confidence < 0.50:
            continue

        extracted_lines.append(text)

    return "\n".join(extracted_lines)


def extract_image_text(
    file_path: str,
    document_category: str | None = None,
) -> str:
    """Extract text from JPG, PNG and TIFF images."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    supported = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

    if path.suffix.lower() not in supported:
        raise ValueError(f"Unsupported image format: {path.suffix}")

    try:
        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(
                "Unable to read image. File may be corrupted."
            )

        # Use RapidOCR for receipts.
        if document_category == "receipt":
            return _extract_receipt_text(image)

        # Retain existing Tesseract processing for other categories.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        gray = cv2.fastNlMeansDenoising(
            gray, None, 10, 7, 21
        )

        processed = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

        pil_image = Image.fromarray(processed)

        text = pytesseract.image_to_string(
            pil_image,
            config="--oem 3 --psm 3",
        )

        return text.strip()

    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR is not installed or its executable is not configured."
        ) from exc
