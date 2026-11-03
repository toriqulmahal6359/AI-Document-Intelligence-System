import re
from collections import defaultdict, deque
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.cross_document_verification import (
    CrossDocumentVerificationResult,
    RecordMatch,
)


def _to_dict(value: Any) -> dict:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value if isinstance(value, dict) else {}


def _get_payload(document_result: Any) -> dict:
    result = _to_dict(document_result)

    if "ai_extraction" in result:
        return _to_dict(result["ai_extraction"])

    if "extraction_result" in result:
        return _to_dict(result["extraction_result"])

    return result


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _normalize_value(value: Any) -> Any:
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        return value

    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        return _normalize_text(value)


def _compare_records(
    record_1: dict,
    record_2: dict,
    fields: list[str],
) -> RecordMatch:
    matching_fields = []
    mismatched_fields = {}

    for field in fields:
        value_1 = record_1.get(field)
        value_2 = record_2.get(field)

        if _normalize_value(value_1) == _normalize_value(value_2):
            matching_fields.append(field)
        else:
            mismatched_fields[field] = {
                "document_1": value_1,
                "document_2": value_2,
            }

    return RecordMatch(
        document_1_record=record_1,
        document_2_record=record_2,
        matching_fields=matching_fields,
        mismatched_fields=mismatched_fields,
    )


def _verify_bank_statements(
    payload_1: dict,
    payload_2: dict,
    result: CrossDocumentVerificationResult,
) -> None:
    fields = [
        "transaction_date",
        "description",
        "debit",
        "credit",
        "balance",
    ]

    transactions_1 = payload_1.get("transactions") or []
    transactions_2 = payload_2.get("transactions") or []

    indexed_2 = defaultdict(deque)

    for transaction in transactions_2:
        transaction = _to_dict(transaction)

        key = (
            _normalize_text(transaction.get("transaction_date")),
            _normalize_text(transaction.get("description")),
        )

        if not all(key):
            result.missing_from_document_1.append(transaction)
            result.requires_review = True
            result.review_reasons.append(
                "A transaction in document 2 is missing its matching fields."
            )
            continue

        indexed_2[key].append(transaction)

    for transaction in transactions_1:
        transaction = _to_dict(transaction)

        key = (
            _normalize_text(transaction.get("transaction_date")),
            _normalize_text(transaction.get("description")),
        )

        if not all(key):
            result.missing_from_document_2.append(transaction)
            result.requires_review = True
            result.review_reasons.append(
                "A transaction in document 1 is missing its matching fields."
            )
            continue

        candidates = indexed_2.get(key)

        if not candidates:
            result.missing_from_document_2.append(transaction)
            continue

        transaction_2 = candidates.popleft()

        comparison = _compare_records(
            transaction,
            transaction_2,
            fields,
        )

        if comparison.mismatched_fields:
            result.mismatched_records.append(comparison)
        else:
            result.matched_records.append(comparison)

    for remaining in indexed_2.values():
        while remaining:
            result.missing_from_document_1.append(remaining.popleft())


def _verify_invoices(
    payload_1: dict,
    payload_2: dict,
    result: CrossDocumentVerificationResult,
) -> None:
    invoice_fields = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "supplier",
        "customer",
        "currency",
        "subtotal",
        "tax_rate",
        "tax_amount",
        "total",
    ]

    if not payload_1 or not payload_2:
        result.requires_review = True
        result.review_reasons.append(
            "Invoice extraction data is missing from one or both documents."
        )
        return

    identity_fields = ["invoice_number", "supplier"]

    for field in identity_fields:
        if not payload_1.get(field) or not payload_2.get(field):
            result.requires_review = True
            result.review_reasons.append(
                f"Invoice matching requires the field '{field}' in both documents."
            )

    invoice_comparison = _compare_records(
        payload_1,
        payload_2,
        invoice_fields,
    )

    if invoice_comparison.mismatched_fields:
        result.mismatched_records.append(invoice_comparison)
    else:
        result.matched_records.append(invoice_comparison)

    items_1 = payload_1.get("line_items") or []
    items_2 = payload_2.get("line_items") or []

    indexed_items_2 = defaultdict(deque)

    for item in items_2:
        item = _to_dict(item)

        key = (
            _normalize_text(item.get("description")),
            _normalize_value(item.get("quantity")),
        )

        if not key[0]:
            result.requires_review = True
            result.review_reasons.append(
                "An invoice line item is missing its description."
            )
            result.missing_from_document_1.append({
                "record_type": "invoice_line_item",
                **item,
            })
            continue

        indexed_items_2[key].append(item)

    for item in items_1:
        item = _to_dict(item)

        key = (
            _normalize_text(item.get("description")),
            _normalize_value(item.get("quantity")),
        )

        if not key[0]:
            result.requires_review = True
            result.review_reasons.append(
                "An invoice line item is missing its description."
            )
            result.missing_from_document_2.append({
                "record_type": "invoice_line_item",
                **item,
            })
            continue

        candidates = indexed_items_2.get(key)

        if not candidates:
            result.missing_from_document_2.append({
                "record_type": "invoice_line_item",
                **item,
            })
            continue

        item_2 = candidates.popleft()

        comparison = _compare_records(
            item,
            item_2,
            ["description", "quantity", "unit_price", "amount"],
        )

        if comparison.mismatched_fields:
            result.mismatched_records.append(comparison)
        else:
            result.matched_records.append(comparison)

    for remaining in indexed_items_2.values():
        while remaining:
            result.missing_from_document_1.append({
                "record_type": "invoice_line_item",
                **remaining.popleft(),
            })


def verify_documents(
    document_1_result: Any,
    document_2_result: Any,
    document_category: str,
    document_1_name: str = "document_1",
    document_2_name: str = "document_2",
) -> dict:
    category = document_category.strip().lower()

    result = CrossDocumentVerificationResult(
        document_1=document_1_name,
        document_2=document_2_name,
        document_category=category,
        verification_status="requires_review",
    )

    payload_1 = _get_payload(document_1_result)
    payload_2 = _get_payload(document_2_result)

    if category == "bank_statement":
        _verify_bank_statements(payload_1, payload_2, result)

    elif category == "invoice":
        _verify_invoices(payload_1, payload_2, result)

    else:
        raise ValueError(
            "Unsupported verification category. "
            "Use 'invoice' or 'bank_statement'."
        )

    if result.requires_review:
        result.verification_status = "requires_review"
    elif result.mismatched_records:
        result.verification_status = "mismatched"
    elif (
        result.missing_from_document_1
        or result.missing_from_document_2
    ):
        result.verification_status = "partially_matched"
    else:
        result.verification_status = "matched"

    return result.model_dump(mode="json")
