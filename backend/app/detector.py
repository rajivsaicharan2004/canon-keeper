"""Contradiction detection: finds facts that conflict using semantic
search (Qdrant) to surface candidates and the configured LLM to judge them."""

import json
from qdrant_client.models import Filter
from app.vectors import _client, embed_text, COLLECTION
from app.llm import chat_text

# Ask the configured LLM to judge whether two facts genuinely contradict.
_JUDGE_PROMPT = """You are a story continuity checker. Two facts were extracted
from a story. Decide if they CONTRADICT each other.

They contradict if they describe the SAME subject and the SAME underlying
property, but with values that cannot both be true. Note that the subject may
be named slightly differently (e.g. "Dr. Watson" and "Watson" are the same
person) and the property may be worded differently (e.g. "war wound location"
and "wound location" are the same property).

They do NOT contradict if they are about different properties, or if both
values could be true at once.

Examples:
- "Watson — wound location: shoulder" vs "Watson — wound location: leg" → contradiction (a wound cannot be in two places)
- "Watson — location: Afghanistan" vs "Watson — weapon: Jezail bullet" → not a contradiction (different properties)
- "Elena — age: 34" vs "Elena — age: 41" → contradiction
- "Holmes — state: not slept in two days" vs "Holmes — reaction: noticed" → not a contradiction (different properties, both can be true)
- "Holmes — action: watching street" vs "Holmes — reaction: noticed" → not a contradiction (different actions at different times)

Only flag a contradiction when BOTH facts clearly describe the SAME property
and the values genuinely cannot coexist. When in doubt, answer false.

Think step by step, then respond with ONLY valid JSON on the last line:
{"contradiction": true} or {"contradiction": false}

Fact A: %s
Fact B: %s
"""


def _judge(fact_a: dict, fact_b: dict) -> bool:
    """Ask the configured LLM whether two facts contradict."""
    a = f"{fact_a['entity']} — {fact_a['attribute']}: {fact_a['value']}"
    b = f"{fact_b['entity']} — {fact_b['attribute']}: {fact_b['value']}"
    try:
        raw = chat_text(_JUDGE_PROMPT % (a, b), temperature=0)
    except Exception as exc:
        print("LLM judge failed, using deterministic fallback:", repr(exc))
        same_entity = fact_a.get("entity", "").lower() == fact_b.get("entity", "").lower()
        same_attr = fact_a.get("attribute", "").lower() == fact_b.get("attribute", "").lower()
        different_value = fact_a.get("value") != fact_b.get("value")
        return bool(same_entity and same_attr and different_value)
    try:
        # Find the JSON object even if the model adds stray text.
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        return bool(data.get("contradiction", False))
    except (json.JSONDecodeError, ValueError):
        return False


def find_contradictions(facts: list[dict], top_k: int = 8) -> list[dict]:
    """
    Hybrid contradiction detection:
    1. Entity+attribute normalization surfaces same-property candidates
       even when worded differently ("type" vs "breed").
    2. Vector search surfaces semantically-close candidates the clustering
       might miss.
    Both candidate sets are judged by the configured LLM; results are de-duplicated.
    """
    from app.normalize import group_candidate_pairs

    contradictions = []
    seen = set()

    def _record(fa, fb, sim):
        # De-dup on entity+values regardless of order.
        key = tuple(sorted([
            f"{fa['entity']}:{fa['value']}",
            f"{fb['entity']}:{fb['value']}",
        ]))
        if key in seen:
            return
        seen.add(key)
        if _judge(fa, fb):
            contradictions.append({"fact_a": fa, "fact_b": fb, "similarity": sim})

    # --- Method 1: normalization-based candidates ---
    for fa, fb in group_candidate_pairs(facts):
        _record(fa, fb, None)

    # --- Method 2: vector-search candidates ---
    for i, fact in enumerate(facts):
        sentence = f"{fact['entity']} — {fact['attribute']}: {fact['value']}"
        qv = embed_text(sentence)
        resp = _client.query_points(collection_name=COLLECTION, query=qv, limit=top_k + 1)
        for hit in resp.points:
            j = hit.id
            if j == i or hit.score < 0.7:
                continue
            other = hit.payload
            def _is_transient(attr):
                attr = attr.lower()
                TRANSIENT = ("action", "activity", "task", "emotion", "thought",
                             "position preference", "location preference")
                if any(t in attr for t in TRANSIENT):
                    return True
                if attr.strip() in ("location", "position", "current location"):
                    return True
                return False
            if _is_transient(fact["attribute"]) or _is_transient(other["attribute"]):
                continue
            _record(fact, other, round(hit.score, 3))

    return contradictions
