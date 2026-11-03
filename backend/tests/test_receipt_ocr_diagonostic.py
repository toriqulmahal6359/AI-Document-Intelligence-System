import cv2
import pytesseract
from pathlib import Path

from PIL import Image

# image_path = "../sample_artifacts/sample-receipt-photo.jpg"

image_path = str(
    Path(__file__).resolve().parents[2]
    / "sample_artifacts"
    / "sample-receipt-photo.jpg"
)

image = cv2.imread(image_path)
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

data = pytesseract.image_to_data(
    Image.fromarray(processed),
    # config="--oem 3 --psm 11",
    config="--oem 3 --psm 11",
    output_type=pytesseract.Output.DICT,
)

print("\nWORD-LEVEL OCR RESULTS")
print("=" * 75)

for i, word in enumerate(data["text"]):
    if word.strip():
        print(
            f"{word!r:35} "
            f"confidence={data['conf'][i]:>6} "
            f"x={data['left'][i]:4} "
            f"y={data['top'][i]:4}"
        )