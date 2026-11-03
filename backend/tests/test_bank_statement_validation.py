import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from decimal import Decimal

from app.schemas.bank_statement import BankStatement, BankTransaction
from app.services.bank_statement_validation_service import (
    validate_bank_statement,
)


statement = BankStatement(
    account_holder="Sam Specimen",
    account_number="SPECIMEN-0000-4821",
    account_type="Savings",
    branch="Sampleton Main",
    statement_start_date="2026-08-01",
    statement_end_date="2026-08-31",
    currency="INR",
    opening_balance=Decimal("1000.00"),
    total_debits=Decimal("150.00"),
    total_credits=Decimal("500.00"),
    closing_balance=Decimal("1350.00"),
    transactions=[
        BankTransaction(
            transaction_date="2026-08-01",
            description="Salary",
            credit=Decimal("500.00"),
            balance=Decimal("1500.00"),
        ),
        BankTransaction(
            transaction_date="2026-08-02",
            description="Shopping",
            debit=Decimal("150.00"),
            balance=Decimal("1350.00"),
        ),
    ],
)

result = validate_bank_statement(statement)

print("BANK STATEMENT VALIDATION")
print("=========================")

for key, value in result.items():
    print(f"{key}: {value}")
