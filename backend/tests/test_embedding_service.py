import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.embedding_service import (
    split_text_into_chunks,
    generate_embeddings,
)

sample_text = (
    "Document intelligence system. "
    "Invoice extraction. "
    "Semantic search. "
) * 100

chunks = split_text_into_chunks(sample_text)

print("Chunks generated:", len(chunks))
print("First chunk length:", len(chunks[0]))

embeddings = generate_embeddings(chunks[:2])

print("Embedding count:", len(embeddings))
print("Embedding dimensions:", len(embeddings[0]))

assert len(embeddings) == 2
assert len(embeddings[0]) == 768

print("Embedding service test passed.")
