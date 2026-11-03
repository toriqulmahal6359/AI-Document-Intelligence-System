"""Consolidated API/backend smoke suite for the AI Document Intelligence project.

Run from the backend directory with its virtual environment active:
    python .\tests\test_backend_api_suite.py

Uses the configured PostgreSQL database and FastAPI app. It mocks only the
Dramatiq enqueue and Ollama embedding calls. Synthetic test records are removed
at the end. No existing uploaded documents are read or analysed.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from app.main import app
import app.api.document as document_api
from app.core.database import SessionLocal, engine, get_db
from app.models import (
    CrossDocumentVerification,
    Document,
    DocumentChunk,
    Invoice,
    ProcessingJob,
    ValidationIssue,
)

RUN_TAG = f"api-suite-{uuid4().hex[:10]}"
CREATED_DOCUMENT_IDS: set[str] = set()
CREATED_FILE_PATHS: set[Path] = set()
RESULTS: list[tuple[str, str, str]] = []


def report(status: str, name: str, detail: str = "") -> None:
    RESULTS.append((status, name, detail))
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def check(name, fn) -> None:
    try:
        report("PASS", name, str(fn() or ""))
    except Exception as exc:
        report("FAIL", name, f"{type(exc).__name__}: {exc}")
        traceback.print_exc()


def test_db_dependency():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def fake_enqueue(document_id: str) -> str:
    return f"test-{uuid4()}"


def fake_embeddings(texts: list[str]) -> list[list[float]]:
    # Test vector only; no request is sent to Ollama.
    return [[0.01] * 768 for _ in texts]


def seed_records() -> dict[str, str]:
    invoice_id, failed_id, second_id, verification_id = [str(uuid4()) for _ in range(4)]
    CREATED_DOCUMENT_IDS.update({invoice_id, failed_id, second_id})

    with SessionLocal() as db:
        db.add_all([
            Document(
                document_id=invoice_id,
                filename=f"{RUN_TAG}-invoice.pdf",
                stored_path=f"test-data/{RUN_TAG}-invoice.pdf",
                file_type=".pdf",
                document_type="pdf",
                document_category="invoice",
                processing_status="completed",
                file_size_bytes=100,
                extracted_text=f"Synthetic API suite record {RUN_TAG}",
                extraction_result={"full_text": f"Synthetic API suite record {RUN_TAG}"},
                ai_extraction={"invoice_number": "SYNTHETIC-001"},
                validation_result={"errors": [], "warnings": []},
            ),
            Document(
                document_id=failed_id,
                filename=f"{RUN_TAG}-failed.pdf",
                stored_path=f"test-data/{RUN_TAG}-failed.pdf",
                file_type=".pdf",
                document_category="invoice",
                processing_status="failed",
                file_size_bytes=100,
                extracted_text="Synthetic failed document for retry API test.",
            ),
            Document(
                document_id=second_id,
                filename=f"{RUN_TAG}-second.pdf",
                stored_path=f"test-data/{RUN_TAG}-second.pdf",
                file_type=".pdf",
                document_category="invoice",
                processing_status="completed",
                file_size_bytes=100,
                extracted_text="Second synthetic document for verification lookup.",
            ),
        ])
        db.flush()
        db.add_all([
            Invoice(
                document_id=invoice_id,
                invoice_number="SYNTHETIC-001",
                supplier="Original Synthetic Supplier",
                currency="BDT",
                line_items=[],
                requires_review=False,
                review_reasons=[],
            ),
            ProcessingJob(
                job_id=str(uuid4()), document_id=invoice_id,
                status="completed", retry_count=0, max_retries=3,
            ),
            ProcessingJob(
                job_id=str(uuid4()), document_id=failed_id,
                status="failed", retry_count=1, max_retries=3,
                error_message="Synthetic test failure",
            ),
            ValidationIssue(
                document_id=invoice_id,
                error_code="TEST_WARNING",
                severity="warning",
                field_name="supplier",
                message="Synthetic validation issue for API testing.",
                details={"source": "automated_api_suite"},
            ),
            DocumentChunk(
                document_id=invoice_id,
                chunk_index=0,
                content=f"Synthetic semantic search content {RUN_TAG}",
                embedding=[0.01] * 768,
            ),
            CrossDocumentVerification(
                verification_id=verification_id,
                document_1_id=invoice_id,
                document_2_id=second_id,
                document_category="invoice",
                verification_status="requires_review",
                verification_result={
                    "verification_status": "requires_review",
                    "requires_review": True,
                    "review_reasons": ["Synthetic API suite record"],
                },
            ),
        ])
        db.commit()

    return {
        "invoice_id": invoice_id,
        "failed_id": failed_id,
        "second_id": second_id,
        "verification_id": verification_id,
    }


def cleanup() -> None:
    ids = list(CREATED_DOCUMENT_IDS)
    try:
        with SessionLocal() as db:
            if ids:
                db.execute(
                    delete(CrossDocumentVerification).where(
                        (CrossDocumentVerification.document_1_id.in_(ids))
                        | (CrossDocumentVerification.document_2_id.in_(ids))
                    )
                )
                for model in (DocumentChunk, ValidationIssue, Invoice, ProcessingJob):
                    db.execute(delete(model).where(model.document_id.in_(ids)))
                db.execute(delete(Document).where(Document.document_id.in_(ids)))
            db.commit()
    except Exception as exc:
        print(f"[WARN] Synthetic database cleanup failed: {exc}")
        traceback.print_exc()

    for path in CREATED_FILE_PATHS:
        try:
            path.unlink(missing_ok=True)
        except Exception as exc:
            print(f"[WARN] Could not remove test upload {path}: {exc}")


def main() -> int:
    print("=" * 72)
    print("AI DOCUMENT INTELLIGENCE — CONSOLIDATED BACKEND API TEST")
    print(f"Run ID: {RUN_TAG}")
    print("=" * 72)

    original_enqueue = document_api.enqueue_document_processing
    original_embeddings = document_api.generate_embeddings
    document_api.enqueue_document_processing = fake_enqueue
    document_api.generate_embeddings = fake_embeddings
    app.dependency_overrides[get_db] = test_db_dependency
    client = TestClient(app)
    ids: dict[str, str] = {}

    try:
        def db_check():
            with engine.connect() as connection:
                assert connection.execute(text("SELECT 1")).scalar_one() == 1
            return "PostgreSQL connection and SELECT 1 succeeded"
        check("PostgreSQL connectivity", db_check)

        def root_check():
            response = client.get("/")
            assert response.status_code == 200, response.text
            assert response.json().get("status") == "running"
            return "HTTP 200"
        check("Root endpoint", root_check)

        def health_check():
            response = client.get("/health")
            assert response.status_code == 200, response.text
            assert response.json().get("status") == "healthy"
            return "HTTP 200; healthy"
        check("Health endpoint", health_check)

        def openapi_check():
            response = client.get("/openapi.json")
            assert response.status_code == 200, response.text
            paths = response.json()["paths"]
            required = {
                "/api/documents/upload", "/api/documents/verify",
                "/api/documents/search", "/api/documents/semantic-search",
                "/api/documents/{document_id}",
                "/api/documents/{document_id}/status",
                "/api/documents/{document_id}/corrections",
                "/api/documents/{document_id}/retry",
                "/api/documents/{document_id}/validation-issues",
                "/api/documents/verifications/{verification_id}",
            }
            missing = required - set(paths)
            assert not missing, f"Missing paths: {sorted(missing)}"
            return f"All {len(required)} required routes are registered"
        check("OpenAPI route registration", openapi_check)

        ids = seed_records()

        def upload_check():
            response = client.post(
                "/api/documents/upload",
                files=[
                    ("files", (f"{RUN_TAG}.pdf", b"%PDF-1.4 synthetic test", "application/pdf")),
                    ("files", (f"{RUN_TAG}.exe", b"unsupported", "application/octet-stream")),
                    ("files", (f"{RUN_TAG}-empty.pdf", b"", "application/pdf")),
                ],
                data={"document_category": "invoice"},
            )
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["total_files"] == 3
            accepted = next(x for x in payload["results"] if x["filename"] == f"{RUN_TAG}.pdf")
            unsupported = next(x for x in payload["results"] if x["filename"] == f"{RUN_TAG}.exe")
            empty = next(x for x in payload["results"] if x["filename"] == f"{RUN_TAG}-empty.pdf")
            assert accepted["status"] == "queued", accepted
            assert accepted.get("task_id", "").startswith("test-"), accepted
            assert unsupported["status"] == "rejected", unsupported
            assert empty["status"] == "rejected", empty
            uploaded_id = accepted["document_id"]
            CREATED_DOCUMENT_IDS.add(uploaded_id)
            with SessionLocal() as db:
                doc = db.get(Document, uploaded_id)
                assert doc is not None
                CREATED_FILE_PATHS.add(Path(doc.stored_path))
                job = db.query(ProcessingJob).filter_by(document_id=uploaded_id).first()
                assert job is not None and job.status == "queued"
                assert job.task_id == accepted["task_id"]
            ids["uploaded_id"] = uploaded_id
            return "Valid PDF queued; unsupported and empty files rejected"
        check("Upload: valid, unsupported and empty files", upload_check)

        def detail_check():
            response = client.get(f"/api/documents/{ids['invoice_id']}")
            assert response.status_code == 200, response.text
            assert response.json()["document_id"] == ids["invoice_id"]
            return "Document metadata and extraction fields returned"
        check("Document detail endpoint", detail_check)

        def status_check():
            response = client.get(f"/api/documents/{ids['uploaded_id']}/status")
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["processing_status"] == "queued"
            assert payload["job"]["status"] == "queued"
            return "Queued document and job status returned"
        check("Document status endpoint", status_check)

        def keyword_search_check():
            response = client.get("/api/documents/search", params={"q": RUN_TAG, "limit": 10, "offset": 0})
            assert response.status_code == 200, response.text
            payload = response.json()
            found = {item["document_id"] for item in payload["results"]}
            assert ids["invoice_id"] in found
            assert ids["uploaded_id"] in found
            return f"Keyword search returned {payload['total']} matching synthetic records"
        check("Keyword search endpoint", keyword_search_check)

        def validation_check():
            response = client.get(f"/api/documents/{ids['invoice_id']}/validation-issues")
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["total_issues"] >= 1
            assert any(item["error_code"] == "TEST_WARNING" for item in payload["issues"])
            return "Synthetic validation issue returned"
        check("Validation issues endpoint", validation_check)

        def correction_check():
            response = client.patch(
                f"/api/documents/{ids['invoice_id']}/corrections",
                json={"supplier": "Corrected Synthetic Supplier", "total": "123.45"},
            )
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["invoice"]["supplier"] == "Corrected Synthetic Supplier"
            assert str(payload["invoice"]["total"]) == "123.45"
            return "Valid invoice correction persisted"
        check("Invoice correction endpoint", correction_check)

        def correction_schema_check():
            response = client.patch(
                f"/api/documents/{ids['invoice_id']}/corrections",
                json={"not_a_real_field": "reject me"},
            )
            assert response.status_code == 422, response.text
            return "Unknown correction field rejected with HTTP 422"
        check("Invoice correction input validation", correction_schema_check)

        def retry_check():
            response = client.post(f"/api/documents/{ids['failed_id']}/retry")
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["processing_status"] == "queued"
            assert payload["task_id"].startswith("test-")
            with SessionLocal() as db:
                doc = db.get(Document, ids["failed_id"])
                assert doc is not None and doc.processing_status == "queued"
            return "Failed document re-queued with a new job/task ID"
        check("Retry endpoint for failed document", retry_check)

        def retry_conflict_check():
            response = client.post(f"/api/documents/{ids['invoice_id']}/retry")
            assert response.status_code == 409, response.text
            return "Retry of non-failed document rejected with HTTP 409"
        check("Retry conflict validation", retry_conflict_check)

        def semantic_check():
            response = client.get(
                "/api/documents/semantic-search",
                params={"q": "synthetic semantic search", "limit": 5},
            )
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["total_results"] >= 1
            assert any(x["document_id"] == ids["invoice_id"] for x in payload["results"])
            assert "similarity_score" in payload["results"][0]
            return f"pgvector query returned {payload['total_results']} ranked result(s)"
        check("Semantic search API and pgvector query", semantic_check)

        def semantic_input_check():
            response = client.get("/api/documents/semantic-search", params={"q": "x"})
            assert response.status_code == 422, response.text
            return "Too-short query rejected with HTTP 422"
        check("Semantic search input validation", semantic_input_check)

        def verification_detail_check():
            response = client.get(f"/api/documents/verifications/{ids['verification_id']}")
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["document_1_id"] == ids["invoice_id"]
            assert payload["document_2_id"] == ids["second_id"]
            return "Stored synthetic verification record returned"
        check("Cross-document verification detail endpoint", verification_detail_check)

        def verification_category_check():
            response = client.post(
                "/api/documents/verify",
                files={
                    "document_1": ("one.pdf", b"%PDF-test", "application/pdf"),
                    "document_2": ("two.pdf", b"%PDF-test", "application/pdf"),
                },
                data={"document_category": "unsupported"},
            )
            assert response.status_code == 400, response.text
            return "Unsupported category rejected with HTTP 400"
        check("Verification category validation", verification_category_check)

        def verification_file_check():
            response = client.post(
                "/api/documents/verify",
                files={
                    "document_1": ("one.exe", b"bad", "application/octet-stream"),
                    "document_2": ("two.pdf", b"%PDF-test", "application/pdf"),
                },
                data={"document_category": "invoice"},
            )
            assert response.status_code == 400, response.text
            return "Unsupported verification file rejected with HTTP 400"
        check("Verification file validation", verification_file_check)

        def not_found_check():
            missing_id = str(uuid4())
            for suffix in ("", "/status", "/validation-issues"):
                response = client.get(f"/api/documents/{missing_id}{suffix}")
                assert response.status_code == 404, f"{suffix}: HTTP {response.status_code}: {response.text}"
            return "Detail, status and validation routes return HTTP 404 for unknown IDs"
        check("Unknown document ID handling", not_found_check)

    except Exception as exc:
        report("FAIL", "Suite execution", f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    finally:
        app.dependency_overrides.pop(get_db, None)
        document_api.enqueue_document_processing = original_enqueue
        document_api.generate_embeddings = original_embeddings
        client.close()
        cleanup()

    print("\n" + "=" * 72)
    print("FINAL SUMMARY")
    print("=" * 72)
    for status in ("PASS", "FAIL", "SKIP"):
        print(f"{status}: {sum(1 for item in RESULTS if item[0] == status)}")
    print(f"TOTAL: {len(RESULTS)}")
    print("\nMocked: Dramatiq enqueue and Ollama embeddings.")
    print("Real: FastAPI routes, PostgreSQL persistence, and pgvector query.")
    print("Not covered: actual OCR/Qwen extraction or live RabbitMQ delivery.")
    failed = any(item[0] == "FAIL" for item in RESULTS)
    print("\nRESULT:", "FAILED" if failed else "PASSED")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
