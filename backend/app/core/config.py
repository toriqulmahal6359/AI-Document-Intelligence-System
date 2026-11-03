import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# Load application configuration
load_dotenv(BASE_DIR / "app.env")

# Storage directories
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / os.getenv("UPLOAD_DIR", "uploads")
PROCESSED_DIR = STORAGE_DIR / os.getenv("PROCESSED_DIR", "processed")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from app.env")

# Background processing
# REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/",
)

# AI model
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

OLLAMA_EMBED_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "nomic-embed-text",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3-vl:4b-instruct"
)

#tesseract Connection

TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Upload configuration
MAX_UPLOAD_SIZE_MB = int(
    os.getenv("MAX_UPLOAD_SIZE_MB", "100")
)