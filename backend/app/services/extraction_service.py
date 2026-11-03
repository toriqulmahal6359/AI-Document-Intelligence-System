import json
import time
import requests

from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from app.core.config import OLLAMA_URL, OLLAMA_MODEL
from app.schemas.invoice import InvoiceExtraction


# SYSTEM_PROMPT = """
# You are a financial document information extraction system.

# Extract invoice fields accurately.

# Important field identification rules:
# - supplier: The business issuing the invoice.
# - customer: The business or person receiving the invoice.
# - invoice_number: The invoice's unique reference.
# - invoice_date: The date the invoice was issued.
# - due_date: The payment due date, if available.
# - subtotal: The amount before tax.
# - tax_rate: The explicitly stated tax rate.
# - tax_amount: The stated tax amount.
# - total: The final payable amount.
# - currency: Extract the currency symbol or currency code when available.

# Rules:
# 1. Use null only when information is genuinely absent or uncertain.
# 2. Do not confuse the supplier with the customer.
# 3. Extract all identifiable line items.
# 4. Preserve the original financial values.
# 5. Never invent information.
# 6. Do not calculate or correct financial totals.
# 7. Return structured JSON only.
# """



SYSTEM_PROMPT = """
You are a precise invoice information extraction system.

Extract invoice fields directly from the supplied document text.

FIELD IDENTIFICATION RULES:

1. invoice_number:
   Extract the value appearing next to labels such as:
   "Invoice no.", "Invoice number", "Invoice #", or "Bill number".

2. invoice_date:
   Extract the date appearing next to "Invoice date",
   "Date", or "Issue date".

3. due_date:
   Extract the date appearing next to "Due date",
   "Payment due", or "Due".

4. supplier:
   Extract the business issuing the invoice.

5. customer:
   Extract the business or person appearing under
   "Bill To", "Customer", or equivalent labels.

6. subtotal:
   Extract the amount appearing next to "Subtotal",
   "Net amount", or equivalent labels.

7. tax_rate:
   Extract an explicitly stated tax percentage.

8. tax_amount:
   Extract the amount associated with GST, VAT, or tax.

9. total:
   Extract the final payable amount.

10. currency:
    Map unambiguous currency symbols to ISO 4217 codes:
    ₹ = INR
    ৳ = BDT
    € = EUR
    £ = GBP
    $ = USD

    For ambiguous symbols such as $, ¥, or other shared symbols,
    use document context. Return null if the currency cannot
    be determined confidently.

IMPORTANT RULES:

- Never return null when the corresponding value is
  explicitly identifiable in the document.
- Associate values with their correct labels.
- Convert unambiguous written dates into YYYY-MM-DD.
- Preserve monetary values without calculating or modifying them.
- Extract all identifiable line items.
- Never confuse tax identification numbers with monetary amounts.
- Never invent missing information.
- Return JSON matching the supplied schema only.
- Extract every identifiable invoice line item.
- Each line item should include description, quantity,
  unit_price, and amount whenever available.
- Never return an empty line_items array when
  identifiable line items exist in the document.
"""



def extract_invoice(document_text: str) -> InvoiceExtraction:

    if not document_text or not document_text.strip():
        raise ValueError("Document text is empty.")

    schema = InvoiceExtraction.model_json_schema()

    prompt = f"""
Extract all invoice fields from the following document.

Pay particular attention to labelled fields:
Invoice number, invoice date, due date, subtotal,
tax rate, tax amount, total and currency.

Do not skip fields simply because their values appear
on the line immediately following their labels.

Convert unambiguous dates into YYYY-MM-DD.
Map unambiguous currency symbols to their ISO currency codes.
Return null only when a field genuinely cannot be identified.

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
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            "options": {
                "temperature": 0
            }
        },
        timeout=600,
    )

    response.raise_for_status()

    result = response.json()

    elapsed = time.perf_counter() - start_time

    print(f"Qwen extraction time: {elapsed:.2f} seconds")
    print(f"Prompt tokens: {result.get('prompt_eval_count', 0)}")
    print(f"Generated tokens: {result.get('eval_count', 0)}")

    content = result["message"]["content"]

    try:
        extracted_data = json.loads(content)

        # Application-controlled currency identification
        currency_symbols = {
            "₹": "INR",
            "৳": "BDT",
            "€": "EUR",
            "£": "GBP",
            "$": "USD",
        }

        for symbol, currency_code in currency_symbols.items():
            if symbol in document_text:
                extracted_data["currency"] = currency_code
                break

        # Do not trust AI-generated review decisions
        review_reasons = []

        # Check required invoice fields
        required_fields = [
            "invoice_number",
            "invoice_date",
            "supplier",
            "customer",
            "currency",
            "subtotal",
            "total",
        ]

        for field in required_fields:
            if extracted_data.get(field) is None:
                review_reasons.append(
                    f"Missing or unidentified invoice field: {field}"
                )

        # Check line-item extraction
        if not extracted_data.get("line_items"):
            review_reasons.append(
                "No invoice line items were extracted."
            )

        if not isinstance(extracted_data, dict):
            raise ValueError("Qwen did not return a JSON object.")

        review_reasons = extracted_data.get("review_reason") or []

        if not isinstance(review_reasons, list):
            review_reasons = [str(review_reasons)]

        numeric_fields = [
            "subtotal",
            "tax_rate",
            "tax_amount",
            "total",
        ]

        for field in numeric_fields:
            value = extracted_data.get(field)

            if value is not None:
                try:
                    Decimal(str(value))
                except (InvalidOperation, ValueError, TypeError):
                    extracted_data[field] = None
                    review_reasons.append(
                        f"AI returned an invalid numeric value for {field}."
                    )

        line_items = extracted_data.get("line_items") or []

        for index, item in enumerate(line_items):

            if not isinstance(item, dict):
                continue

            for field in ["quantity", "unit_price", "amount"]:
                value = item.get(field)

                if value is not None:
                    try:
                        Decimal(str(value))
                    except (InvalidOperation, ValueError, TypeError):
                        item[field] = None
                        review_reasons.append(
                            f"AI returned an invalid {field} in line item {index + 1}."
                        )

        if review_reasons:
            extracted_data["requires_review"] = True
            extracted_data["review_reason"] = list(
                dict.fromkeys(review_reasons)
            )

        return InvoiceExtraction.model_validate(extracted_data)

    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            f"Qwen returned invalid invoice data: {exc}"
        ) from exc
