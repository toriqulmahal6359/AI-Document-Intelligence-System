from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

import os
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")


def extract_image_text(file_path: str) -> str:
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
            raise ValueError("Unable to read image. File may be corrupted.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Improve contrast and remove minor image noise.
        gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

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
