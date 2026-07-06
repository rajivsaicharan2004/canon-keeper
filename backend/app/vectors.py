"""Vector storage: embeds facts and stores them in Qdrant for semantic lookup."""

from __future__ import annotations

import hashlib
import math
import re

import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.config import (
    EMBED_PROVIDER,
    EMBED_MODEL,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
)

COLLECTION = QDRANT_COLLECTION

_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)


def _hash_embedding(text: str, dims: int = 384) -> list[float]:
    """Small deterministic embedding fallback for hosted demos.

    This avoids requiring Ollama on Render. It is not as semantically rich as
    a real embedding model, but it is stable, fast, and good enough for the
    hybrid detector because same-entity/same-attribute candidates are also
    generated before vector search.
    """
    vector = [0.0] * dims
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def embed_text(text: str) -> list[float]:
    provider = (EMBED_PROVIDER or "ollama").lower().strip()

    if provider == "hash":
        return _hash_embedding(text)

    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    if "embedding" not in response:
        raise ValueError(f"Ollama embedding response missing 'embedding': {response}")
    return response["embedding"]


def _ensure_collection(vector_size: int):
    existing = {c.name for c in _client.get_collections().collections}

    if COLLECTION not in existing:
        _client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def store_facts(facts: list[dict]) -> int:
    if not facts:
        return 0

    points = []

    for i, f in enumerate(facts):
        sentence = f"{f['entity']} — {f['attribute']}: {f['value']}"
        vector = embed_text(sentence)

        if i == 0:
            _ensure_collection(len(vector))

        points.append(PointStruct(id=i, vector=vector, payload=f))

    _client.upsert(collection_name=COLLECTION, points=points)
    return len(points)
