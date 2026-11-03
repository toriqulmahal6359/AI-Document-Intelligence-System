from decimal import Decimal
from typing import Any

from app.schemas.bank_statement import BankStatement


ZERO = Decimal("0")
TOLERANCE = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def validate_bank_statement(statement: BankStatement) -> dict[str, Any]:
    errors = []
    warnings = []

    calculated_debits = ZERO
    calculated_credits = ZERO
    expected_balance = statement.opening_balance

    for index, transaction in enumerate(statement.transactions, start=1):
        debit = transaction.debit or ZERO
        credit = transaction.credit or ZERO

        if debit < ZERO or credit < ZERO:
            errors.append({
                "transaction": index,
                "issue": "Negative debit or credit amount."
            })

        if debit > ZERO and credit > ZERO:
            errors.append({
                "transaction": index,
                "issue": "Both debit and credit contain amounts."
            })

        if debit == ZERO and credit == ZERO:
            warnings.append({
                "transaction": index,
                "issue": "Transaction has no debit or credit amount."
            })

        calculated_debits += debit
        calculated_credits += credit

        if expected_balance is not None:
            expected_balance += credit - debit

            if transaction.balance is not None:
                difference = money(
                    transaction.balance - expected_balance
                )

                if abs(difference) > TOLERANCE:
                    errors.append({
                        "transaction": index,
                        "issue": "Running balance mismatch.",
                        "expected_balance": str(money(expected_balance)),
                        "reported_balance": str(money(transaction.balance)),
                        "difference": str(difference),
                    })

        # elif transaction.balance is not None:
        #     warnings.append({
        #         "transaction": index,
        #         "issue": "Cannot verify running balance because opening balance is missing."
        #     })
    if statement.opening_balance is None and any(
        transaction.balance is not None
        for transaction in statement.transactions
    ):
        warnings.append({
            "issue": "Cannot verify running balances because opening balance is missing."
        })
    calculated_debits = money(calculated_debits)
    calculated_credits = money(calculated_credits)

    # Check transaction totals against statement summary.
    if statement.total_debits is not None:
        difference = money(
            calculated_debits - statement.total_debits
        )

        if abs(difference) > TOLERANCE:
            errors.append({
                "issue": "Total debit mismatch.",
                "calculated": str(calculated_debits),
                "reported": str(money(statement.total_debits)),
                "difference": str(difference),
            })

    if statement.total_credits is not None:
        difference = money(
            calculated_credits - statement.total_credits
        )

        if abs(difference) > TOLERANCE:
            errors.append({
                "issue": "Total credit mismatch.",
                "calculated": str(calculated_credits),
                "reported": str(money(statement.total_credits)),
                "difference": str(difference),
            })

    # Independently reconcile the statement summary.
    summary_expected = None

    if (
        statement.opening_balance is not None
        and statement.total_credits is not None
        and statement.total_debits is not None
    ):
        summary_expected = money(
            statement.opening_balance
            + statement.total_credits
            - statement.total_debits
        )

        if statement.closing_balance is not None:
            difference = money(
                statement.closing_balance - summary_expected
            )

            if abs(difference) > TOLERANCE:
                errors.append({
                    "issue": "Statement closing balance mismatch.",
                    "calculated": str(summary_expected),
                    "reported": str(money(statement.closing_balance)),
                    "difference": str(difference),
                })

    # Compare final transaction balance with reported closing balance.
    if (
        expected_balance is not None
        and statement.closing_balance is not None
    ):
        difference = money(
            statement.closing_balance - expected_balance
        )

        if abs(difference) > TOLERANCE:
            errors.append({
                "issue": "Final transaction balance does not match closing balance.",
                "calculated": str(money(expected_balance)),
                "reported": str(money(statement.closing_balance)),
                "difference": str(difference),
            })

    return {
        "status": "requires_review" if errors or warnings else "valid",
        "calculated_debits": str(calculated_debits),
        "calculated_credits": str(calculated_credits),
        "calculated_closing_balance": (
            str(money(expected_balance))
            if expected_balance is not None
            else None
        ),
        "summary_expected_closing_balance": (
            str(summary_expected)
            if summary_expected is not None
            else None
        ),
        "errors": errors,
        "warnings": warnings,
        "requires_review": bool(errors or warnings),
    }
