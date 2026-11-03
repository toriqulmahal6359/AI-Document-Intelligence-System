import json
import time
import requests

from pydantic import ValidationError

from app.core.config import OLLAMA_URL, OLLAMA_MODEL
from app.schemas.invoice import InvoiceExtraction

from decimal import Decimal, InvalidOperation


SYSTEM_PROMPT = """
You are a financial document information extraction system.

Extract invoice fields accurately.

Important field identification rules:
- supplier: The business issuing the invoice.
- customer: The business or person receiving the invoice.
- invoice_number: The invoice's unique reference.
- invoice_date: The date the invoice was issued.
- subtotal: The amount before tax.
- tax_amount: The stated tax amount.
- total: The final payable amount.
- currency: Extract the currency symbol or currency code when available.

Rules:
1. Use null only when information is genuinely absent or uncertain.
2. Do not confuse the supplier with the customer.
3. Extract all identifiable line items.
4. Preserve the original financial values.
5. Never invent information.
6. Do not calculate or correct financial totals.
7. Return structured JSON only.
"""


def extract_invoice(document_text: str) -> InvoiceExtraction:
    if not document_text or not document_text.strip():
        raise ValueError("Document text is empty.")

    schema = InvoiceExtraction.model_json_schema()

    prompt = f"""
        Extract the invoice information from this document.

        Rules:
        - Extract only explicitly available information.
        - Use null for missing or uncertain fields.
        - Extract all identifiable line items.
        - Preserve financial values exactly.
        - Do not calculate or correct totals.
        - Use YYYY-MM-DD for unambiguous dates.

    Document:
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
                        "content": "You extract structured information from financial documents. Return only data matching the required JSON schema."
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

        # try:
        #     extracted_data = json.loads(content)
        #     return InvoiceExtraction.model_validate(extracted_data)
        # except (json.JSONDecodeError, ValidationError) as exc:
        #     raise ValueError(
        #         f"Qwen returned invalid invoice data: {exc}"
        #     ) from exc

        try:
            extracted_data = json.loads(content)

            if not isinstance(extracted_data, dict):
                raise ValueError("Qwen did not return a JSON object.")

            review_reasons = extracted_data.get("review_reason") or []

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

            line_items = extracted_data.get("line_items", [])

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
                extracted_data["review_reason"] = list(dict.fromkeys(review_reasons))

            return InvoiceExtraction.model_validate(extracted_data)

        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(
                f"Qwen returned invalid invoice data: {exc}"
            ) from exc
