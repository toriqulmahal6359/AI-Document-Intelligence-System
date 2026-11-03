import json
import time

import requests
from pydantic import ValidationError

from app.core.config import OLLAMA_URL, OLLAMA_MODEL
from app.schemas.receipt import ReceiptExtraction

from decimal import Decimal, InvalidOperation


# SYSTEM_PROMPT = """
# You are a receipt data extraction system.

# Extract structured information from the supplied receipt text.

# Return these fields:
# - merchant_name
# - receipt_number
# - receipt_date
# - currency
# - subtotal
# - tax_amount
# - total
# - payment_method
# - line_items

# Each line item must contain:
# - description
# - quantity
# - unit_price
# - amount

# Rules:
# 1. Never invent or assume missing information.
# 2. Use null for unavailable or uncertain values.
# 3. Use ISO format YYYY-MM-DD for dates.
# 4. Return numeric values for monetary amounts.
# 5. Do not confuse subtotal, tax, and total.
# 6. Extract currency only when an explicit currency code or
#    unambiguous currency symbol is present. Otherwise return null.
# 7. Extract payment_method only when explicitly visible.
# 8. Set requires_review to true when important fields are
#    missing, unclear, or inconsistent.
# 9. Explain review concerns in review_reason.
# 10. Return only data matching the supplied JSON schema.
# """


SYSTEM_PROMPT = """
You are a precise receipt data extraction system.

Extract structured information only from the supplied receipt text.
Do not use external knowledge or assumptions.

Return these fields:
- merchant_name
- receipt_number
- receipt_date
- currency
- subtotal
- tax_amount
- total
- payment_method
- line_items
- requires_review
- review_reason

Each line item must contain:
- description
- quantity
- unit_price
- amount

CRITICAL FINANCIAL EXTRACTION RULES:

1. Never invent, assume, or calculate missing receipt values.

2. A printed line-item amount is the amount for that line
   unless the receipt explicitly identifies it as a unit price.

3. Never multiply a printed line amount by the quantity.

4. Extract unit_price only when the receipt explicitly
   provides a per-unit price. Otherwise use null.

5. Preserve the printed line amount in amount.
   Do not replace it with a calculated value.

6. Extract quantity separately from the item description
   when it is clearly identifiable.

7. Extract subtotal only when it is explicitly labelled
   as subtotal or an equivalent term.
   Never copy the total into subtotal.

8. Extract tax_amount only when an actual tax amount
   is explicitly printed. Do not calculate it from a
   tax percentage.

9. Extract total from the explicitly labelled final
   receipt amount. Do not add tax to it again.

10. Do not infer currency from the merchant, country,
    language, address, or surrounding context.
    Return null unless an explicit currency code or
    unambiguous currency symbol appears.

11. Extract payment_method only when explicitly visible.
    For example, "Paid by card" means "card".
    Do not assume a specific card network or card type.

12. Use null for missing or uncertain monetary values.
    Never use zero to represent an unknown amount.

13. Use ISO format YYYY-MM-DD for dates.

REVIEW RULES:

14. Set requires_review to true when important values
    cannot be reliably extracted or financial information
    is inconsistent.

15. Review reasons must describe actual problems visible
    in the supplied text. Never invent inconsistencies.

16. Do not flag missing currency, subtotal, card type,
    or transaction ID as errors by themselves.

17. Do not interpret OCR noise as evidence of a financial
    calculation error.

18. When the text contains enough information for reliable
    extraction, do not request review unnecessarily.

Return only data matching the supplied JSON schema.
"""



def extract_receipt(document_text: str) -> ReceiptExtraction:

    if not document_text or not document_text.strip():
        raise ValueError("Receipt text is empty.")

    schema = ReceiptExtraction.model_json_schema()

    prompt = f"""
Extract receipt information from the following text.

RECEIPT TEXT:
{document_text}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "keep_alive": "30m",
        "format": schema,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "options": {
            "temperature": 0,
        },
    }

    start_time = time.time()

    response = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        json=payload,
        timeout=600,
    )

    response.raise_for_status()

    elapsed = time.time() - start_time

    response_data = response.json()
    model_response = response_data.get("message", {}).get(
        "content", ""
    )

    try:
        extracted_data = json.loads(model_response)

        if not isinstance(extracted_data, dict):
            raise ValueError(
                "Receipt extraction returned an invalid structure."
            )

        # Do not accept a guessed currency when the receipt
        # contains no explicit currency indicator.
        import re

        currency_indicators = re.search(
            r"\b(?:USD|BDT|EUR|GBP|INR|JPY|CAD|AUD)\b|[$৳€£¥₹]",
            document_text,
            re.IGNORECASE,
        )

        if not currency_indicators:
            extracted_data["currency"] = None

        # Only accept subtotal when it is explicitly labelled
        # in the original OCR text.
        subtotal_label = re.search(
            r"\bsub[\s-]?total\b",
            document_text,
            re.IGNORECASE,
        )

        if not subtotal_label:
            extracted_data["subtotal"] = None

        review_reasons = list(
            extracted_data.get("review_reason") or []
        )

        required_fields = {
            "merchant_name": "Merchant name",
            "receipt_date": "Receipt date",
            "total": "Total amount",
        }

        for field, label in required_fields.items():
            if not extracted_data.get(field):
                review_reasons.append(
                    f"{label} could not be extracted."
                )

        if not extracted_data.get("line_items"):
            review_reasons.append(
                "No receipt line items were extracted."
            )

        extracted_data["review_reason"] = list(
            dict.fromkeys(review_reasons)
        )

        extracted_data["requires_review"] = bool(
            extracted_data.get("requires_review")
            or review_reasons
        )

        # # Derive unit price only when it was not extracted,
        # # but both quantity and printed line amount are available.
        # for item in extracted_data.get("line_items") or []:
        #     if not isinstance(item, dict):
        #         continue

        #     if item.get("unit_price") is not None:
        #         continue

        #     quantity = item.get("quantity")
        #     amount = item.get("amount")

        #     if quantity is None or amount is None:
        #         continue

        #     try:
        #         quantity_value = Decimal(str(quantity))
        #         amount_value = Decimal(str(amount))

        #         if (
        #             quantity_value.is_finite()
        #             and amount_value.is_finite()
        #             and quantity_value != 0
        #         ):
        #             item["unit_price"] = str(
        #                 amount_value / quantity_value
        #             )

        #     except (InvalidOperation, ValueError, TypeError):
        #         continue

        receipt = ReceiptExtraction.model_validate(
            extracted_data
        )

        print(
            f"Receipt extraction completed in {elapsed:.2f}s"
        )

        return receipt

    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            f"Receipt extraction failed: {exc}"
        ) from exc