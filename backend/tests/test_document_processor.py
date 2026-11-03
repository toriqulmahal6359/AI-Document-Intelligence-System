import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_processor import process_document


def test_document(file_path: str):
    path = Path(file_path)

    if not path.exists():
        print(f"File not found: {path}")
        return

    try:
        result = process_document(path)
        extraction = result.get("extraction_result", {})

        print("\nDOCUMENT PROCESSING RESULT")
        print("=" * 50)
        print("Filename:", result.get("filename"))
        print("Status:", result.get("status"))
        print("Document type:", result.get("document_type"))

        if result.get("document_type") in {"pdf", "image"}:
            print("Pages:", extraction.get("page_count",
                                           extraction.get("total_pages", 0)))

            for page in extraction.get("pages", []):
                print(f"\nPage {page.get('page_number')}:")
                # print(page.get("text", "")[:500])
                print(page.get("text", ""))

        elif result.get("document_type") == "spreadsheet":
            for name, sheet in extraction.get("sheets", {}).items():
                print(
                    f"Sheet: {name} | Rows: {sheet['row_count']}"
                )

        for error in extraction.get("errors", []):
            print("Error:", error)

    except Exception as error:
        print(f"\nDOCUMENT PROCESSING FAILED: {error}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            'Usage: python test_document_processor.py "path_to_document"'
        )
        sys.exit(1)

    test_document(sys.argv[1])
