import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import sys
from pathlib import Path

from app.services.document_processor import process_document


def test_document(file_path: str):
    path = Path(file_path)

    if not path.exists():
        print(f"File not found: {path}")
        return

    result = process_document(path)

    print("\nDOCUMENT PROCESSING RESULT")
    print("=" * 50)
    print("Filename:", path.name)
    print("Status:", result.get("status"))
    print("Document type:", result.get("document_type"))

    if result.get("document_type") == "pdf":
        print("Pages:", result.get("page_count"))

    elif result.get("document_type") == "image":
        print("Pages/frames:", result.get("page_count"))

    elif result.get("document_type") == "spreadsheet":
        for name, sheet in result.get("sheets", {}).items():
            print(f"Sheet: {name} | Rows: {sheet['row_count']}")

    for error in result.get("errors", []):
        print("Error:", error)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            'Usage: python test_document_processor.py "path_to_document"'
        )
        sys.exit(1)

    test_document(sys.argv[1])
