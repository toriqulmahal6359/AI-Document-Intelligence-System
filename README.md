# AI-Powered Document Intelligence System

An AI-assisted document intelligence application designed to process business documents, extract structured information, validate extracted data, and support document search and cross-document verification.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Vector Search | pgvector |
| Background Tasks | RabbitMQ, Dramatiq |
| PDF Processing | PyMuPDF |
| OCR | Tesseract OCR, RapidOCR, OpenCV, Pillow |
| Spreadsheet Processing | pandas, openpyxl, xlrd |
| Local AI | Ollama |

## Project Structure

```text
AIDocumentIntelligence/
├── backend/
│   ├── app/
│   ├── storage/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── datasets/
├── docs/
│   ├── architecture.md
│   └── database-schema.md
├── frontend/
│   ├── public/
│   ├── src/
│   └── package.json
├── sample_artifacts/
├── .gitignore
└── README.md
```

## Main Capabilities

- Document upload through the backend API.
- PDF text extraction and scanned-document OCR.
- Image and spreadsheet processing.
- Invoice information extraction and structured storage.
- Bank statement extraction and validation.
- Cross-document verification.
- Document processing status and retry support.
- Keyword-based and semantic document search.
- Background processing and document indexing.

Actual processing and available functionality depend on the document type and configured services.

## Prerequisites

- Python 3.13
- Node.js and npm
- PostgreSQL with pgvector support
- RabbitMQ
- Ollama
- Tesseract OCR

The project was developed in a Windows environment. The following setup instructions use PowerShell and local services.

## Backend Setup

From the project root:

```powershell
cd backend

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example app.env
```

Configure `backend/app.env` with your local PostgreSQL and RabbitMQ connection details.

The backend loads its configuration from `backend/app.env`. Keep this file private and never commit it to Git.

### Supporting Services

Ensure PostgreSQL and RabbitMQ are running and accessible using the connection strings in `app.env`.

Start Ollama and download the configured models:

```powershell
ollama pull qwen3-vl:4b-instruct
ollama pull nomic-embed-text
```

Install Tesseract OCR and configure `TESSERACT_CMD` with the full path to `tesseract.exe`.

### Database Initialization

If the database has not yet been initialized, apply the available Alembic migrations:

```powershell
alembic upgrade head
```

### Start the Backend API

From the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

Interactive API documentation: `http://127.0.0.1:8000/docs`

### Start the Background Worker

Open another PowerShell window, activate the backend virtual environment, navigate to `backend`, and run:

```powershell
dramatiq app.tasks.document_tasks
```

RabbitMQ must be running for background task processing.

## Frontend Setup

Open another PowerShell window:

```powershell
cd frontend
npm ci
npm run dev
```

Frontend URL: `http://localhost:3000`

### Production Build

```powershell
npm run build
npm run start
```

## API Endpoints

The document API is mounted under `/api/documents`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/documents/upload` | Upload documents |
| POST | `/api/documents/verify` | Cross-document verification |
| GET | `/api/documents/{document_id}/status` | Check processing status |
| GET | `/api/documents/search` | Search documents |
| GET | `/api/documents/semantic-search` | Semantic search |
| PATCH | `/api/documents/{document_id}/corrections` | Correct invoice information |
| POST | `/api/documents/{document_id}/retry` | Retry processing |
| GET | `/api/documents/verifications/{verification_id}` | Retrieve verification results |
| GET | `/api/documents/{document_id}/validation-issues` | Retrieve validation issues |
| GET | `/api/documents/{document_id}` | Retrieve document details |

The application also provides `/` and `/health` endpoints.

For complete request and response schemas, use the live Swagger documentation at `/docs`.

## Database Overview

The main database tables are:

- `documents`
- `invoices`
- `document_chunks`
- `processing_jobs`
- `validation_issues`
- `cross_document_verifications`

See [Database Schema](docs/database-schema.md) for the model overview.

## Architecture

See [System Architecture](docs/architecture.md) for the component diagram and processing workflow.

## Testing

Automated tests are located in `backend/tests/`.

API and database test suite:

```powershell
python tests/test_backend_api_suite.py
```

Broader backend integration suite:

```powershell
python tests/test_full_backend.py
```

The broader integration suite requires the relevant supporting services and a running Dramatiq worker.

Test results must be recorded from actual executions. The API test suite mocks background task enqueueing and Ollama embeddings; it does not independently verify live RabbitMQ delivery or real OCR and AI extraction.

## Security Notes

- Never commit environment files containing credentials or secrets.
- Do not commit real uploaded documents or private customer information.
- Protect PostgreSQL and RabbitMQ credentials.
- Use appropriate access controls before deploying beyond a local development environment.

## Evaluation and Demonstration

The project submission should include:

- Actual automated test results.
- An evaluation report containing measured results.
- A recorded walkthrough of the working application.
- Relevant AI prompts and an AI-assisted development disclosure.

These materials should reflect the implementation and tests actually completed.