from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cross_document_verification_service import verify_documents


def test_bank_statement_matching():
    doc1 = {
        "transactions": [
            {
                "transaction_date": "2026-08-01",
                "description": "Synthetic transaction A",
                "debit": "100.00",
                "credit": None,
                "balance": "900.00",
            }
        ]
    }

    doc2 = {
        "transactions": [
            {
                "transaction_date": "2026-08-01",
                "description": "Synthetic transaction A",
                "debit": "100.00",
                "credit": None,
                "balance": "900.00",
            }
        ]
    }

    result = verify_documents(doc1, doc2, "bank_statement")

    assert result["verification_status"] == "matched"
    assert len(result["matched_records"]) == 1
    assert not result["mismatched_records"]


def test_bank_statement_mismatch():
    doc1 = {
        "transactions": [
            {
                "transaction_date": "2026-08-01",
                "description": "Synthetic transaction B",
                "debit": "100.00",
                "credit": None,
                "balance": "900.00",
            }
        ]
    }

    doc2 = {
        "transactions": [
            {
                "transaction_date": "2026-08-01",
                "description": "Synthetic transaction B",
                "debit": "120.00",
                "credit": None,
                "balance": "880.00",
            }
        ]
    }

    result = verify_documents(doc1, doc2, "bank_statement")

    assert result["verification_status"] == "mismatched"
    assert len(result["mismatched_records"]) == 1


def test_invoice_matching():
    doc1 = {
        "invoice_number": "SYN-001",
        "invoice_date": "2026-08-01",
        "due_date": None,
        "supplier": "Synthetic Supplier",
        "customer": "Synthetic Customer",
        "currency": "BDT",
        "subtotal": "1000.00",
        "tax_rate": None,
        "tax_amount": None,
        "total": "1000.00",
        "line_items": [
            {
                "description": "Synthetic service",
                "quantity": "2",
                "unit_price": "500.00",
                "amount": "1000.00",
            }
        ],
    }

    doc2 = dict(doc1)

    result = verify_documents(doc1, doc2, "invoice")

    assert result["verification_status"] == "matched"
    assert len(result["matched_records"]) == 2


def test_invoice_mismatch():
    doc1 = {
        "invoice_number": "SYN-002",
        "invoice_date": "2026-08-01",
        "supplier": "Synthetic Supplier",
        "customer": "Synthetic Customer",
        "currency": "BDT",
        "subtotal": "1000.00",
        "total": "1000.00",
        "line_items": [
            {
                "description": "Synthetic service",
                "quantity": "2",
                "unit_price": "500.00",
                "amount": "1000.00",
            }
        ],
    }

    doc2 = {
        **doc1,
        "total": "1100.00",
        "line_items": [
            {
                "description": "Synthetic service",
                "quantity": "2",
                "unit_price": "550.00",
                "amount": "1100.00",
            }
        ],
    }

    result = verify_documents(doc1, doc2, "invoice")

    assert result["verification_status"] == "mismatched"
    assert len(result["mismatched_records"]) == 2


if __name__ == "__main__":
    test_bank_statement_matching()
    test_bank_statement_mismatch()
    test_invoice_matching()
    test_invoice_mismatch()

    print("All 4 cross-document verification tests passed.")
