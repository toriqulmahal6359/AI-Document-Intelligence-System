import json
import time
import requests

from pydantic import ValidationError

from app.core.config import OLLAMA_URL, OLLAMA_MODEL
from app.schemas.invoice import InvoiceExtraction


SYSTEM_PROMPT = """
You are an expert financial document information extraction system.

Extract invoice information from the supplied document text.

Rules:
1. Extract only information explicitly supported by the document.
2. Never invent missing values.
3. Use null when a field is missing or uncertain.
4. Extract every identifiable invoice line item.
5. Preserve the original financial values.
6. Do not calculate or correct financial totals.
7. Convert dates to YYYY-MM-DD when unambiguous.
8. Return only valid JSON matching the supplied schema.
9. Do not include Markdown code fences or explanatory text.
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

    try:
        extracted_data = json.loads(content)
        return InvoiceExtraction.model_validate(extracted_data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            f"Qwen returned invalid invoice data: {exc}"
        ) from exc



# def extract_invoice(document_text: str) -> InvoiceExtraction:
#     if not document_text or not document_text.strip():
#         raise ValueError("Document text is empty.")

#     schema = InvoiceExtraction.model_json_schema()

#     prompt = f"""
# Extract the invoice information from the following document.

# Required JSON schema:
# {json.dumps(schema, indent=2)}

# DOCUMENT TEXT:
# {document_text}
# """
#     start_time = time.perf_counter()
#     response = requests.post(
#         f"{OLLAMA_URL.rstrip('/')}/api/chat",
#         json={
#             "model": OLLAMA_MODEL,
#             "stream": False,
#             "format": schema,
#             "messages": [
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content": prompt},
#             ],
#             "options": {
#                 "temperature": 0
#             }
#         },
#         timeout=300,
#     )

#     response.raise_for_status()

#     elapsed = time.perf_counter() - start_time
#     print(f"Qwen extraction time: {elapsed:.2f} seconds")

#     result = response.json()
#     content = result["message"]["content"]

#     try:
#         extracted_data = json.loads(content)
#         return InvoiceExtraction.model_validate(extracted_data)
#     except (json.JSONDecodeError, ValidationError) as exc:
#         raise ValueError(
#             f"Qwen returned invalid invoice data: {exc}"
#         ) from exc
