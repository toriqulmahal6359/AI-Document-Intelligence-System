import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.bank_statement_extraction_service import (
    extract_bank_statement_from_spreadsheet,
)
from app.services.bank_statement_validation_service import (
    validate_bank_statement,
)


# Actual spreadsheet location
# SAMPLE_FILE = (
#     BACKEND_DIR / "test_files" / "sample_bank_statement.xlsx"
# )

PROJECT_ROOT = BACKEND_DIR.parent

SAMPLE_ARTIFACTS_DIR = PROJECT_ROOT / "sample_artifacts"

SAMPLE_FILE = SAMPLE_ARTIFACTS_DIR / "sample-bank-statement-pdf.csv"

metadata = {
    "account_holder": "Sam Specimen",
    "currency": "INR",
    "opening_balance": "1000.00",
    "total_debits": "150.00",
    "total_credits": "500.00",
    "closing_balance": "1350.00",
}


def main():

    # 1. Extract bank statement directly from spreadsheet
    statement = extract_bank_statement_from_spreadsheet(
        file_path=str(SAMPLE_FILE),
        metadata=metadata,
    )

    # 2. Validate extracted statement
    result = validate_bank_statement(statement)

    # 3. Display extraction
    print("\nBANK STATEMENT EXTRACTION")
    print("=========================")
    print(statement.model_dump(mode="json"))

    # 4. Display validation
    print("\nVALIDATION RESULT")
    print("=================")
    print(result)


if __name__ == "__main__":
    main()
