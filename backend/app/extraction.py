"""Fact extraction: turns document chunks into structured canon facts using Granite."""

import json
import ollama

MODEL = "granite4:micro"

# The instruction we give Granite for every chunk. Being explicit and giving
# an example ("few-shot") dramatically improves small-model reliability.
_PROMPT = """You are a story continuity analyst. Read the passage and extract
canon facts: concrete, checkable statements about characters, their traits,
locations, and events.

Return ONLY a JSON array containing ALL facts you find (there are usually
several). Even if you find only one fact, wrap it in an array. Extract
facts from EVERY sentence, even if a later fact seems to
contradict or repeat an earlier one — those contradictions are important
and must NOT be skipped. Each item must have exactly these keys:
- "entity": who or what the fact is about (e.g. "Watson")
- "attribute": the property (e.g. "war wound location")
- "value": the specific value (e.g. "left shoulder")

Example output:
[{"entity": "Watson", "attribute": "war wound location", "value": "left shoulder"}]

If there are no clear facts, return [].

Passage:
"""


def extract_facts(chunk_text: str, chunk_index: int) -> list[dict]:
    """Send one chunk to Granite and get back a list of canon facts."""
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": _PROMPT + chunk_text}],
        options={"temperature": 0},
    )
    raw = response["message"]["content"]

    # Defensive parsing — Granite may return several shapes:
    #   1. A bare array:      [{...}, {...}]
    #   2. A single object:   {"entity": ..., "attribute": ..., "value": ...}
    #   3. A wrapped array:   {"facts": [{...}]} or {"canon_facts": [{...}]}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []  # unparseable — skip this chunk rather than crash

    if isinstance(data, list):
        facts = data
    elif isinstance(data, dict):
        # If it looks like a single fact (has our keys), wrap it in a list.
        if "entity" in data and "attribute" in data and "value" in data:
            facts = [data]
        else:
            # Otherwise it's a wrapper — grab the first list value we find.
            facts = next((v for v in data.values() if isinstance(v, list)), [])
    else:
        facts = []

    # Stamp each fact with its source chunk so we can cite it later.
    clean = []
    for f in facts:
        if isinstance(f, dict) and "entity" in f and "attribute" in f and "value" in f:
            clean.append({
                "entity": f["entity"],
                "attribute": f["attribute"],
                "value": f["value"],
                "chunk_index": chunk_index,
            })
    return clean


def extract_all(chunks: list[dict]) -> list[dict]:
    """Run extraction across every chunk and combine the facts."""
    all_facts = []
    for chunk in chunks:
        all_facts.extend(extract_facts(chunk["text"], chunk["index"]))
    return all_facts
