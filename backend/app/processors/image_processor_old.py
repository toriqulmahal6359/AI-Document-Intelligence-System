from pathlib import Path
import os

import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image


pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_CMD", "tesseract"
)


def _extract_receipt_text(image: np.ndarray) -> str:
    """Extract receipt text using word-level OCR confidence."""

    # Enlarge the image to improve recognition of small receipt text.
    height, width = image.shape[:2]
    image = cv2.resize(
        image,
        (width * 2, height * 2),
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Improve local contrast without aggressively removing text details.
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )
    enhanced = clahe.apply(gray)

    # Use adaptive thresholding for the receipt image.
    processed = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )

    pil_image = Image.fromarray(processed)

    data = pytesseract.image_to_data(
        pil_image,
        config="--oem 3 --psm 11",
        output_type=Output.DICT,
    )

    lines = {}

    for i, word in enumerate(data["text"]):
        word = word.strip()

        if not word:
            continue

        try:
            confidence = float(data["conf"][i])
        except (ValueError, TypeError):
            continue

        if confidence < 0:
            continue

        key = (
            data["block_num"][i],
            data["par_num"][i],
            data["line_num"][i],
        )

        if key not in lines:
            lines[key] = {
                "words": [],
                "confidences": [],
            }

        lines[key]["words"].append(word)
        lines[key]["confidences"].append(confidence)

    extracted_lines = []

    for line in lines.values():
        words = line["words"]
        confidences = line["confidences"]

        if not words:
            continue

        average_confidence = sum(confidences) / len(confidences)

        # Reject lines with consistently poor OCR confidence.
        # Do not remove individual low-confidence words from an
        # otherwise readable line.
        if average_confidence < 35:
            continue

        extracted_lines.append(" ".join(words))

    return "\n".join(extracted_lines).strip()


def extract_image_text(
    file_path: str,
    document_category: str | None = None,
) -> str:
    """Extract text from JPG, PNG and TIFF images using Tesseract OCR."""

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

        if document_category == "receipt":
            return _extract_receipt_text(image)

        # Preserve the existing OCR approach for other image categories.
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
