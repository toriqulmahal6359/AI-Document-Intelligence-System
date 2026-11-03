import logging

import httpx
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import OLLAMA_URL, OLLAMA_EMBED_MODEL
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 768
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 200
# EMBEDDING_BATCH_SIZE = 16
EMBEDDING_BATCH_SIZE = 2
MAX_INDEXED_CHUNKS = 100


def split_text_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split extracted text into overlapping, non-empty chunks."""

    if not text or not text.strip():
        return []

    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    text = text.strip()
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            boundary = text.rfind(" ", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings through the local Ollama API."""

    if not texts:
        return []

    url = f"{OLLAMA_URL.rstrip('/')}/api/embed"

    response = httpx.post(
        url,
        json={
            "model": OLLAMA_EMBED_MODEL,
            "input": texts,
        },
        timeout=180.0,
    )
    response.raise_for_status()

    embeddings = response.json().get("embeddings", [])

    if len(embeddings) != len(texts):
        raise ValueError(
            "Ollama returned a different number of embeddings "
            "than the number of input chunks."
        )

    for embedding in embeddings:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Expected {EMBEDDING_DIMENSIONS} dimensions, "
                f"received {len(embedding)}."
            )

    return embeddings


def embed_document_chunks(
    db: Session,
    document_id: str,
    text: str,
) -> int:
    """Generate and persist embeddings for a document."""

    chunks = split_text_into_chunks(text)

    if len(chunks) > MAX_INDEXED_CHUNKS:
        logger.warning(
            "Document %s has %s chunks; indexing limited to %s chunks",
            document_id,
            len(chunks),
            MAX_INDEXED_CHUNKS,
        )
        chunks = chunks[:MAX_INDEXED_CHUNKS]

    if not chunks:
        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        )
        db.commit()
        return 0

    new_records = []

    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[start:start + EMBEDDING_BATCH_SIZE]
        embeddings = generate_embeddings(batch)

        for offset, (content, embedding) in enumerate(
            zip(batch, embeddings)
        ):
            new_records.append(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=start + offset,
                    content=content,
                    embedding=embedding,
                )
            )

    try:
        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        )

        db.add_all(new_records)
        db.commit()

    except Exception:
        db.rollback()
        raise

    return len(new_records)
