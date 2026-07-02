import os
import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()  # read .env into environment variables

EMBED_MODEL = "granite-embedding:278m"
COLLECTION = "canon_facts"

# Connect to YOUR Qdrant Cloud cluster using the credentials from .env.
# Swapping to embedded/local later means changing only these two lines.
_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


def embed_text(text: str) -> list[float]:
    """Turn a piece of text into a vector using Granite's embedding model."""
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return response["embeddings"][0]


def _ensure_collection(vector_size: int):
    """Create the Qdrant collection if it doesn't exist yet.
    A 'collection' is like a table, but for vectors."""
    existing = [c.name for c in _client.get_collections().collections]
    if COLLECTION not in existing:
        _client.create_collection(
            collection_name=COLLECTION,
            # COSINE distance measures angle between vectors — the standard
            # choice for semantic similarity.
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def store_facts(facts: list[dict]) -> int:
    """Embed each fact and store it in Qdrant. Returns how many we stored."""
    if not facts:
        return 0

    # We embed a readable sentence version of each fact so the meaning is
    # captured (entity + attribute + value together).
    points = []
    for i, f in enumerate(facts):
        sentence = f"{f['entity']} — {f['attribute']}: {f['value']}"
        vector = embed_text(sentence)

        # First fact tells us the vector size; ensure the collection exists.
        if i == 0:
            _ensure_collection(len(vector))

        # A 'point' = one vector + its original fact stored as payload.
        points.append(PointStruct(id=i, vector=vector, payload=f))

    _client.upsert(collection_name=COLLECTION, points=points)
    return len(points)
