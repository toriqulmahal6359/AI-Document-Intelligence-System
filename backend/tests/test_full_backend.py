
"""
AI-POWERED DOCUMENT INTELLIGENCE
FULL BACKEND INTEGRATION TEST SUITE

Run from backend directory:
    python .\tests\test_full_backend.py

Requires:
    PostgreSQL running
    RabbitMQ running
    Ollama running (for Qwen/embeddings tests)
    Dramatiq worker running in another terminal

Uses synthetic test files and records only.
"""

import os
import sys
import time
import uuid
import tempfile
import traceback
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

RESULTS = []
RUN_ID = str(uuid.uuid4())[:8]
TEMP_DIR = Path(tempfile.mkdtemp(prefix="backend_test_"))


def report(name, status, detail=""):
    RESULTS.append((name, status))
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))


def check(name, function):
    try:
        function()
        report(name, "PASS")
        return True
    except SkipTest as exc:
        report(name, "SKIP", str(exc))
    except Exception as exc:
        report(name, "FAIL", f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    return False


class SkipTest(Exception):
    pass


# ---------------------------------------------------------
# 1. DATABASE
# ---------------------------------------------------------

def test_database():
    from sqlalchemy import text
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        assert db.execute(text("SELECT 1")).scalar() == 1
    finally:
        db.close()


def test_pgvector():
    from sqlalchemy import text
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT extversion FROM pg_extension WHERE extname='vector'")
        ).scalar()

        assert result is not None, "pgvector extension is missing"
    finally:
        db.close()


# ---------------------------------------------------------
# 2. DOCUMENT PARSING
# ---------------------------------------------------------

def create_test_pdf():
    import pymupdf

    path = TEMP_DIR / "synthetic_document.pdf"

    pdf = pymupdf.open()
    page = pdf.new_page()

    page.insert_text(
        (60, 60),
        "SYNTHETIC DOCUMENT INTELLIGENCE TEST"
    )
    page.insert_text(
        (60, 100),
        "Document Reference: TEST-001"
    )
    page.insert_text(
        (60, 140),
        "This document tests PDF text extraction."
    )

    pdf.save(path)
    pdf.close()

    return path


def test_pdf_parser():
    from app.processors.pdf_processor import extract_pdf_text

    path = create_test_pdf()
    result = extract_pdf_text(str(path))

    assert result is not None
    assert "SYNTHETIC" in str(result).upper()


def test_document_processor():
    from app.services.document_processor import process_document

    path = create_test_pdf()

    result = process_document(
        file_path=str(path),
        document_category="other",
    )

    assert result is not None


def test_ocr_processor():
    from PIL import Image, ImageDraw, ImageFont
    from app.processors.image_processor import extract_image_text

    image_path = TEMP_DIR / "synthetic_ocr.png"

    image = Image.new("RGB", (1200, 350), "white")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 45)
    except OSError:
        font = ImageFont.load_default()

    draw.text(
        (50, 100),
        "SYNTHETIC OCR TEST 12345",
        fill="black",
        font=font,
    )

    image.save(image_path)

    result = extract_image_text(str(image_path))

    assert result is not None
    assert "OCR" in str(result).upper()


# ---------------------------------------------------------
# 3. BANK STATEMENT EXTRACTION AND VALIDATION
# ---------------------------------------------------------

def test_bank_statement_extraction():
    import pandas as pd

    from app.services.bank_statement_extraction_service import (
        extract_bank_statement,
    )

    frame = pd.DataFrame([
        {
            "Date": "05/01/2026",
            "Description": "Synthetic deposit",
            "Debit": None,
            "Credit": "250.00",
            "Balance": "1250.00",
        },
        {
            "Date": "12/01/2026",
            "Description": "Synthetic purchase",
            "Debit": "100.00",
            "Credit": None,
            "Balance": "1150.00",
        },
    ])

    statement = extract_bank_statement(frame)

    assert len(statement.transactions) == 2


def test_bank_statement_validation():
    import pandas as pd

    from app.services.bank_statement_extraction_service import (
        extract_bank_statement,
    )
    from app.services.bank_statement_validation_service import (
        validate_bank_statement,
    )

    frame = pd.DataFrame([
        {
            "Date": "05/01/2026",
            "Description": "Synthetic deposit",
            "Debit": None,
            "Credit": "250.00",
            "Balance": "1250.00",
        }
    ])

    statement = extract_bank_statement(frame)
    result = validate_bank_statement(statement)

    assert result is not None


def test_csv_parser():
    from app.services.bank_statement_extraction_service import (
        extract_bank_statement_from_spreadsheet,
    )

    path = TEMP_DIR / "synthetic_statement.csv"

    path.write_text(
        "Date,Description,Debit,Credit,Balance\n"
        "05/01/2026,Synthetic deposit,,250.00,1250.00\n"
        "12/01/2026,Synthetic purchase,100.00,,1150.00\n",
        encoding="utf-8",
    )

    result = extract_bank_statement_from_spreadsheet(str(path))

    assert len(result.transactions) == 2


# ---------------------------------------------------------
# 4. QWEN EXTRACTION
# ---------------------------------------------------------

def test_qwen_extraction():
    import requests

    from app.core.config import OLLAMA_URL, OLLAMA_MODEL
    from app.services.bank_statement_ai_extraction_service import (
        extract_bank_statement_from_text,
    )

    try:
        response = requests.get(
            f"{OLLAMA_URL.rstrip('/')}/api/tags",
            timeout=5,
        )
        response.raise_for_status()
    except Exception as exc:
        raise SkipTest(f"Ollama unavailable: {exc}")

    models = [
        item.get("name", "")
        for item in response.json().get("models", [])
    ]

    if not any(
        model == OLLAMA_MODEL or model.startswith(OLLAMA_MODEL + ":")
        for model in models
    ):
        raise SkipTest(f"Configured model {OLLAMA_MODEL} is unavailable")

    synthetic_text = """
    SYNTHETIC TEST STATEMENT
    Account holder: Synthetic Test User
    Account number: TEST-000001
    Account type: Current
    Statement period: 01/01/2026 - 31/01/2026
    Currency: BDT
    Opening balance: 1000.00

    Date Description Debit Credit Balance
    05/01/2026 Synthetic deposit 0 250.00 1250.00
    """

    result = extract_bank_statement_from_text(synthetic_text)

    assert result is not None
    assert result.transactions


def test_qwen_page_fallback():
    import requests

    from app.core.config import OLLAMA_URL
    from app.services.bank_statement_ai_extraction_service import (
        extract_bank_statement_from_pages,
    )

    try:
        requests.get(
            f"{OLLAMA_URL.rstrip('/')}/api/tags",
            timeout=5,
        ).raise_for_status()
    except Exception as exc:
        raise SkipTest(f"Ollama unavailable: {exc}")

    result = extract_bank_statement_from_pages([
        {
            "page": 1,
            "text": """
            SYNTHETIC STATEMENT
            Account holder: Synthetic Fallback User
            Account number: TEST-000002
            Currency: BDT
            Date Description Debit Credit Balance
            05/01/2026 Synthetic deposit 0 250.00 1250.00
            """,
        }
    ])

    assert result is not None
    assert result.transactions


# ---------------------------------------------------------
# 5. EMBEDDING AND CHUNK INDEXING
# ---------------------------------------------------------

def test_embedding_endpoint():
    import requests

    from app.core.config import OLLAMA_URL

    try:
        response = requests.post(
            f"{OLLAMA_URL.rstrip('/')}/api/embed",
            json={
                "model": "nomic-embed-text",
                "input": "Synthetic backend embedding test",
            },
            timeout=180,
        )
        response.raise_for_status()
    except Exception as exc:
        raise SkipTest(f"Ollama embedding service unavailable: {exc}")

    data = response.json()
    embeddings = data.get("embeddings", [])

    assert embeddings
    assert len(embeddings[0]) == 768


# def test_chunk_indexing_function():
#     from app.services.embedding_service import embed_document_chunks

#     import inspect

#     signature = inspect.signature(embed_document_chunks)
#     parameters = signature.parameters

#     synthetic_text = (
#         "Synthetic document chunk indexing test. "
#         "This text is generated for backend verification. "
#     ) * 30

#     synthetic_id = str(uuid.uuid4())
#     kwargs = {}

#     for name, parameter in parameters.items():
#         if name in ("document_id", "doc_id", "id"):
#             kwargs[name] = synthetic_id
#         elif name in ("text", "content", "extracted_text", "document_text"):
#             kwargs[name] = synthetic_text
#         elif name in ("db", "session", "database"):
#             from app.core.database import SessionLocal
#             kwargs[name] = SessionLocal()
#         elif parameter.default is inspect.Parameter.empty:
#             raise SkipTest(
#                 f"Adapt test to required parameter: {name}"
#             )

#     try:
#         result = embed_document_chunks(**kwargs)
#         assert result is not None or result == 0
#     finally:
#         for value in kwargs.values():
#             if value.__class__.__name__ == "Session":
#                 value.close()


def test_chunk_indexing_function():
    from app.core.database import SessionLocal
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.services.embedding_service import embed_document_chunks

    db = SessionLocal()
    document_id = str(uuid.uuid4())

    synthetic_text = (
        "Synthetic document indexing verification. "
        "Testing text chunking, embedding generation, "
        "and PostgreSQL persistence. "
    ) * 30

    try:
        document = Document(
            document_id=document_id,
            filename="synthetic_index_test.txt",
            stored_path="synthetic_index_test.txt",
            file_type="txt",
            document_type="text",
            document_category="other",
            processing_status="completed",
            extracted_text=synthetic_text,
        )

        db.add(document)
        db.commit()

        # result = embed_document_chunks(
        #     document_id=document_id,
        #     extracted_text=synthetic_text,
        #     db=db,
        # )

        result = embed_document_chunks(
            db=db,
            document_id=document_id,
            text=synthetic_text,
        )

        assert result > 0, "No chunks were indexed"

        db.expire_all()

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .all()
        )

        assert chunks, "No chunks were persisted"
        assert all(len(chunk.embedding) == 768 for chunk in chunks)

        print(f"Persisted chunks: {len(chunks)}")

    finally:
        db.rollback()
        db.query(Document).filter(
            Document.document_id == document_id
        ).delete(synchronize_session=False)
        db.commit()
        db.close()


# ---------------------------------------------------------
# 6. RABBITMQ / DRAMATIQ
# ---------------------------------------------------------

# def test_rabbitmq_connection():
#     from app.core.broker import rabbitmq_broker

#     connection = rabbitmq_broker.connection
#     connection.connect()
#     connection.close()

# def test_rabbitmq_connection():
#     from app.core.broker import rabbitmq_broker

#     connection = rabbitmq_broker.connection

#     try:
#         assert connection.is_open, "RabbitMQ connection is not open"
#     finally:
#         if connection.is_open:
#             connection.close()


def test_rabbitmq_connection():
    from app.core.broker import rabbitmq_broker

    connection = rabbitmq_broker.connection

    assert connection.is_open, "RabbitMQ connection is not open"


# def test_dramatiq_message_delivery():
#     from app.tasks.document_tasks import index_document_task

#     message = index_document_task.send(str(uuid.uuid4()))

#     assert message is not None
#     assert message.message_id

# def test_dramatiq_message_delivery():
#     from app.core.database import SessionLocal
#     from app.models.document import Document
#     from app.tasks.document_tasks import index_document_task

#     db = SessionLocal()
#     document_id = str(uuid.uuid4())

#     try:
#         document = Document(
#             document_id=document_id,
#             filename="synthetic_dramatiq_test.txt",
#             stored_path="synthetic_dramatiq_test.txt",
#             file_type="txt",
#             document_type="text",
#             document_category="other",
#             processing_status="completed",
#             extracted_text=(
#                 "Synthetic Dramatiq indexing test. "
#                 "This document exists only for backend verification. "
#             ) * 20,
#         )

#         db.add(document)
#         db.commit()

#         message = index_document_task.send(document_id)

#         assert message is not None
#         assert message.message_id is not None

#         print(f"Published indexing task: {message.message_id}")
#         print(f"Synthetic document ID: {document_id}")

#     finally:
#         db.close()

def test_dramatiq_message_delivery():
    from app.core.database import SessionLocal
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.tasks.document_tasks import index_document_task

    db = SessionLocal()
    document_id = str(uuid.uuid4())
    completed = False

    synthetic_text = (
        "Synthetic Dramatiq worker integration test. "
        "Verifying RabbitMQ delivery, worker execution, "
        "Ollama embeddings, and PostgreSQL chunk persistence. "
    ) * 30

    try:
        document = Document(
            document_id=document_id,
            filename="synthetic_worker_test.txt",
            stored_path="synthetic_worker_test.txt",
            file_type="txt",
            document_type="text",
            document_category="other",
            processing_status="completed",
            extracted_text=synthetic_text,
        )

        db.add(document)
        db.commit()

        message = index_document_task.send(document_id)

        assert message is not None
        print(f"Published message: {message.message_id}")

        timeout = time.time() + 180

        while time.time() < timeout:
            db.expire_all()

            chunks = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == document_id)
                .all()
            )

            if chunks:
                assert all(
                    len(chunk.embedding) == 768
                    for chunk in chunks
                )

                print(f"Worker persisted chunks: {len(chunks)}")
                completed = True
                break

            time.sleep(2)

        assert completed, (
            "Worker did not persist document chunks within 180 seconds"
        )

    finally:
        if completed:
            db.query(Document).filter(
                Document.document_id == document_id
            ).delete(synchronize_session=False)
            db.commit()
        else:
            print(
                f"Document retained for investigation: {document_id}"
            )

        db.close()


# ---------------------------------------------------------
# 7. API AND EXISTING APPLICATION TESTS
# ---------------------------------------------------------

def test_existing_api_suite():
    import subprocess

    script = BACKEND_DIR / "tests" / "test_backend_api_suite.py"

    if not script.exists():
        raise SkipTest("Existing test_backend_api_suite.py not found")

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=900,
    )

    print("\n--- Existing API suite ---")
    print(result.stdout)

    if result.stderr:
        print(result.stderr)

    assert result.returncode == 0, "Existing API test suite failed"


def test_application_import():
    from app.main import app

    assert app is not None
    assert len(app.routes) > 0


# ---------------------------------------------------------
# 8. CLEANUP AND SUMMARY
# ---------------------------------------------------------

def cleanup():
    import shutil
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


def main():
    print("\n" + "=" * 65)
    print("FULL BACKEND INTEGRATION TEST")
    print("Run ID:", RUN_ID)
    print("=" * 65)

    tests = [
        ("Existing API/database/pgvector suite", test_existing_api_suite),
        ("Application startup/import", test_application_import),
        ("PostgreSQL connectivity", test_database),
        ("pgvector extension", test_pgvector),
        ("PDF parser", test_pdf_parser),
        ("Document processor", test_document_processor),
        ("Tesseract OCR processor", test_ocr_processor),
        ("Bank statement extraction", test_bank_statement_extraction),
        ("Bank statement validation", test_bank_statement_validation),
        ("CSV parser", test_csv_parser),
        ("Qwen extraction", test_qwen_extraction),
        ("Qwen page fallback", test_qwen_page_fallback),
        ("Ollama embedding endpoint", test_embedding_endpoint),
        ("Chunk indexing function", test_chunk_indexing_function),
        ("RabbitMQ connection", test_rabbitmq_connection),
        ("Dramatiq message publishing", test_dramatiq_message_delivery),
    ]

    try:
        for name, function in tests:
            check(name, function)
    finally:
        cleanup()

    passed = sum(status == "PASS" for _, status in RESULTS)
    failed = sum(status == "FAIL" for _, status in RESULTS)
    skipped = sum(status == "SKIP" for _, status in RESULTS)

    print("\n" + "=" * 65)
    print("FINAL BACKEND TEST SUMMARY")
    print("=" * 65)
    print("PASS:", passed)
    print("FAIL:", failed)
    print("SKIP:", skipped)
    print("TOTAL:", len(RESULTS))

    if failed:
        print("\nRESULT: FAILED")
        return 1

    if skipped:
        print("\nRESULT: PARTIAL — check skipped services")
        return 2

    print("\nRESULT: ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())