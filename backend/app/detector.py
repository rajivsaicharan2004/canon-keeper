"""Contradiction detection: finds facts that conflict using semantic
search (Qdrant) to surface candidates and Granite to judge them."""

import json
import ollama
from qdrant_client.models import Filter
from backend.app.vectors import _client, embed_text, COLLECTION

MODEL = "granite4:micro"

# Ask Granite to judge whether two facts genuinely contradict.
_JUDGE_PROMPT = """You are a story continuity checker. Two facts were
extracted from a story. Decide if they CONTRADICT each other — meaning they
describe the SAME subject and SAME property but with INCOMPATIBLE values.

Two facts about different subjects or different properties do NOT contradict.
Two compatible facts (e.g. a location and a weapon) do NOT contradict.

Respond with ONLY valid JSON: {"contradiction": true} or {"contradiction": false}

Fact A: %s
Fact B: %s
"""


def _judge(fact_a: dict, fact_b: dict) -> bool:
    """Ask Granite whether two facts contradict."""
    a = f"{fact_a['entity']} — {fact_a['attribute']}: {fact_a['value']}"
    b = f"{fact_b['entity']} — {fact_b['attribute']}: {fact_b['value']}"
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": _JUDGE_PROMPT % (a, b)}],
    )
    raw = response["message"]["content"]
    try:
        # Find the JSON object even if the model adds stray text.
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        return bool(data.get("contradiction", False))
    except (json.JSONDecodeError, ValueError):
        return False


def find_contradictions(facts: list[dict], top_k: int = 4) -> list[dict]:
    """
    For each fact, find its nearest neighbors in Qdrant, then ask Granite
    whether any of them contradict it. Returns a list of contradiction pairs.
    """
    contradictions = []
    seen_pairs = set()  # avoid reporting the same pair twice (A-B and B-A)

    for i, fact in enumerate(facts):
        sentence = f"{fact['entity']} — {fact['attribute']}: {fact['value']}"
        query_vector = embed_text(sentence)

        # Ask Qdrant for the closest facts (semantic neighbors).
        # query_points is the current method (replaced the old .search()).
        response = _client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            limit=top_k + 1,  # +1 because the fact itself will match
        )
        results = response.points  # the actual hits live under .points

        for hit in results:
            other = hit.payload
            j = hit.id
            if j == i:
                continue  # skip the fact matching itself

            # Skip if we've already checked this pair in the other order.
            pair_key = tuple(sorted([i, j]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Let Granite make the final call.
            if _judge(fact, other):
                contradictions.append({
                    "fact_a": fact,
                    "fact_b": other,
                    "similarity": round(hit.score, 3),
                })

    return contradictions
