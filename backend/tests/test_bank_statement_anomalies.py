import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from decimal import Decimal

from app.schemas.bank_statement import BankStatement, BankTransaction
from app.services.bank_statement_validation_service import (
    validate_bank_statement,
)


# These values reproduce the suspicious rows
# from the supplied August bank statement.

statement = BankStatement(
    opening_balance=Decimal("48230.55"),
    transactions=[
        BankTransaction(
            description="Salary - Example Traders",
            debit=Decimal("62500"),
            credit=Decimal("110730.6"),
        ),
        BankTransaction(
            description="Refund - Online Store Example",
            debit=Decimal("1299"),
            credit=Decimal("86198.65"),
        ),
        BankTransaction(
            description="Transfer from Alex Example",
            debit=Decimal("4000"),
            credit=Decimal("79370.45"),
        ),
        BankTransaction(
            description="Interest credit",
            debit=Decimal("112.48"),
            credit=Decimal("70853.88"),
        ),
    ],
)

result = validate_bank_statement(statement)

print("AUGUST STATEMENT DATA-QUALITY TEST")
print("==================================")
print("Status:", result["status"])
print("Errors detected:", len(result["errors"]))

for error in result["errors"]:
    print(error)
