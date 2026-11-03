from app.services.bank_statement_extraction_service import (
    extract_bank_statement_from_spreadsheet,
)


def main():

    statement = extract_bank_statement_from_spreadsheet(
        file_path="test_files/sample_bank_statement.xlsx",
        metadata={
            "account_holder": "Sam Specimen",
            "currency": "INR",
            "opening_balance": "1000.00",
            "total_debits": "150.00",
            "total_credits": "500.00",
            "closing_balance": "1350.00",
        },
    )

    print("\nBANK STATEMENT EXTRACTION")
    print("=========================")

    print(statement.model_dump(mode="json"))


if __name__ == "__main__":
    main()