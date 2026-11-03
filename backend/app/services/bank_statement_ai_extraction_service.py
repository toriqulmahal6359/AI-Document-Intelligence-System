import json
import time
import requests

from decimal import Decimal, InvalidOperation
from pydantic import ValidationError

from app.core.config import OLLAMA_URL, OLLAMA_MODEL
from app.schemas.bank_statement import BankStatement


BANK_STATEMENT_SYSTEM_PROMPT = """
You are a precise bank statement information extraction system.

Extract structured information from the supplied bank statement text.

Extract these statement fields when available:
- account_holder
- account_number
- account_type
- branch
- statement_start_date
- statement_end_date
- currency
- opening_balance
- total_debits
- total_credits
- closing_balance

Extract every identifiable transaction with:
- transaction_date
- description
- debit
- credit
- balance

Rules:
1. Never invent missing information.
2. Use null for unavailable or uncertain fields.
3. Do not confuse opening balance with a transaction.
4. Do not confuse closing balance with a transaction.
5. Keep debit and credit amounts in their correct fields.
6. Do not put the same transaction amount in both debit and credit.
7. Preserve the original transaction order.
8. Do not calculate or modify financial amounts.
9. Convert unambiguous dates to YYYY-MM-DD.
10. Use ISO currency codes when the currency is identifiable.
11. Do not include account numbers or reference numbers as transaction amounts.
12. Return all identifiable transactions.
13. Return JSON matching the supplied schema only.
"""


def extract_bank_statement_from_text(document_text: str, require_transactions: bool = True,
) -> BankStatement:

    if not document_text or not document_text.strip():
        raise ValueError("Bank statement text is empty.")

    schema = BankStatement.model_json_schema()

    prompt = f"""
Extract the bank statement information from the document text below.

Pay particular attention to:
- Account holder and account details
- Statement period
- Opening and closing balances
- Total debit and credit amounts
- Individual transaction dates and descriptions
- Debit, credit and running balance columns

Do not calculate missing values.
Do not invent transaction records.
Return all identifiable transactions.

Document text:
{document_text}
"""

    start_time = time.perf_counter()

    response = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "keep_alive": "30m",
            "format": schema,
            "messages": [
                {
                    "role": "system",
                    "content": BANK_STATEMENT_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "options": {
                "temperature": 0,
            },
        },
        timeout=600,
    )

    response.raise_for_status()

    result = response.json()

    elapsed = time.perf_counter() - start_time

    print(f"Qwen bank statement extraction time: {elapsed:.2f} seconds")
    print(f"Prompt tokens: {result.get('prompt_eval_count', 0)}")
    print(f"Generated tokens: {result.get('eval_count', 0)}")

    try:
        extracted_data = json.loads(
            result["message"]["content"]
        )

        if not isinstance(extracted_data, dict):
            raise ValueError("Qwen did not return a JSON object.")

        review_reasons = []

        # Normalize clearly identifiable currency symbols.
        currency_symbols = {
            "₹": "INR",
            "৳": "BDT",
            "€": "EUR",
            "£": "GBP",
        }

        document_currency = next(
            (
                currency_code
                for symbol, currency_code in currency_symbols.items()
                if symbol in document_text
            ),
            None,
        )

        if document_currency:
            extracted_data["currency"] = document_currency

        # Sanitize invalid numeric statement fields.
        numeric_fields = [
            "opening_balance",
            "total_debits",
            "total_credits",
            "closing_balance",
        ]

        for field in numeric_fields:
            value = extracted_data.get(field)

            if value is not None:
                try:
                    Decimal(str(value).replace(",", ""))
                except (InvalidOperation, ValueError, TypeError):
                    extracted_data[field] = None
                    review_reasons.append(
                        f"Invalid numeric value extracted for {field}."
                    )

        # Sanitize transaction amounts.
        transactions = extracted_data.get("transactions") or []

        if not isinstance(transactions, list):
            transactions = []
            extracted_data["transactions"] = transactions
            review_reasons.append(
                "Transaction data was not returned as a list."
            )

        for index, transaction in enumerate(transactions, start=1):

            if not isinstance(transaction, dict):
                review_reasons.append(
                    f"Invalid transaction structure at row {index}."
                )
                continue

            for field in ["debit", "credit", "balance"]:
                value = transaction.get(field)

                if value is not None:
                    try:
                        Decimal(str(value).replace(",", ""))
                    except (InvalidOperation, ValueError, TypeError):
                        transaction[field] = None
                        review_reasons.append(
                            f"Invalid {field} amount in transaction {index}."
                        )

        if not transactions and require_transactions:
            review_reasons.append(
                "No bank transactions could be identified."
            )

        # Check basic transaction completeness.
        for index, transaction in enumerate(transactions, start=1):
            if not isinstance(transaction, dict):
                continue

            if not transaction.get("transaction_date"):
                review_reasons.append(
                    f"Transaction {index} has no identifiable date."
                )

            if not transaction.get("description"):
                review_reasons.append(
                    f"Transaction {index} has no identifiable description."
                )

        try:
            statement = BankStatement.model_validate(extracted_data)
        except ValidationError as exc:
            raise ValueError(
                f"Qwen returned invalid bank statement data: {exc}"
            ) from exc

        statement.review_reason = list(
            dict.fromkeys(
                (statement.review_reason or []) + review_reasons
            )
        )

        if statement.review_reason:
            statement.requires_review = True

        return statement

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Qwen returned invalid JSON: {exc}"
        ) from exc

def extract_bank_statement_from_pages(pages: list[dict]) -> BankStatement:

    if not pages:
        raise ValueError("No PDF pages available for extraction.")

    combined_statement = BankStatement()
    review_reasons = []

    metadata_fields = [
        "account_holder",
        "account_number",
        "account_type",
        "branch",
        "statement_start_date",
        "statement_end_date",
        "currency",
        "opening_balance",
        "total_debits",
        "total_credits",
        "closing_balance",
    ]

    processed_pages = 0

    for page in pages:

        page_text = page.get("text", "")

        if not page_text.strip():
            continue

        print(
            f"Extracting bank statement page "
            f"{page.get('page_number', processed_pages + 1)}"
        )

        page_statement = extract_bank_statement_from_text(
            page_text,
            require_transactions=False
        )

        processed_pages += 1

        # Merge statement-level metadata.
        for field in metadata_fields:

            current_value = getattr(combined_statement, field)
            extracted_value = getattr(page_statement, field)

            if current_value is None and extracted_value is not None:
                setattr(combined_statement, field, extracted_value)

        # Preserve transaction order across pages.
        combined_statement.transactions.extend(
            page_statement.transactions
        )

        review_reasons.extend(
            page_statement.review_reason or []
        )

    if processed_pages == 0:
        raise ValueError("No readable PDF page text was available.")

    if not combined_statement.transactions:
        review_reasons.append(
            "No bank transactions could be identified."
        )

    combined_statement.review_reason = list(
        dict.fromkeys(review_reasons)
    )

    combined_statement.requires_review = bool(
        combined_statement.review_reason
    )

    print(
        f"Total pages processed: {processed_pages}"
    )

    print(
        f"Total transactions extracted: "
        f"{len(combined_statement.transactions)}"
    )

    return combined_statement