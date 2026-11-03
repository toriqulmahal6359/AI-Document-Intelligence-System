from decimal import Decimal
from app.schemas.receipt import ReceiptExtraction


def validate_receipt(receipt: ReceiptExtraction) -> dict:
    errors = []

    # Required receipt fields
    if not receipt.merchant_name:
        errors.append("Merchant name is missing.")

    if receipt.receipt_date is None:
        errors.append("Receipt date is missing.")

    if receipt.total is None:
        errors.append("Receipt total is missing.")

    # Validate receipt-level monetary values
    monetary_fields = {
        "subtotal": receipt.subtotal,
        "tax_amount": receipt.tax_amount,
        "total": receipt.total,
    }

    for field_name, value in monetary_fields.items():
        if value is not None and value < Decimal("0"):
            errors.append(
                f"{field_name.replace('_', ' ').capitalize()} cannot be negative."
            )

    # Validate explicitly extracted line-item values
    for index, item in enumerate(receipt.line_items, start=1):
        for field_name in ("quantity", "unit_price", "amount"):
            value = getattr(item, field_name)

            if value is not None and value < Decimal("0"):
                errors.append(
                    f"Line item {index}: {field_name.replace('_', ' ')} "
                    "cannot be negative."
                )

    requires_review = bool(errors)

    return {
        "status": "requires_review" if requires_review else "valid",
        "requires_review": requires_review,
        "errors": errors,
    }