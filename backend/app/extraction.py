from __future__ import annotations

"""Fact extraction: turns document chunks into structured canon facts using the configured LLM."""

import json
from app.llm import chat_text

# The instruction we give the configured LLM for every chunk. Being explicit and giving
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
"""


def extract_facts(chunk_text: str, chunk_index: int, known_entities: list[str] | None = None) -> list[dict]:
    """Send one chunk to the configured LLM and get back a list of canon facts,
    resolving pronouns/vague references to known character names."""
    known = known_entities or []
    context = ""
    if known:
        context = (
            "\nKnown characters so far: " + ", ".join(known) + ".\n"
            "IMPORTANT: If a fact refers to someone by pronoun (he, she, her, his) "
            "or a vague term ('the woman', 'the dog'), attribute it to the correct "
            "KNOWN CHARACTER by name. Never use a pronoun or generic noun as the entity.\n"
        )

    raw = chat_text(_PROMPT + context + "\nPassage:\n" + chunk_text, temperature=0)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        facts = data
    elif isinstance(data, dict):
        if "entity" in data and "attribute" in data and "value" in data:
            facts = [data]
        else:
            facts = next((v for v in data.values() if isinstance(v, list)), [])
    else:
        facts = []

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


def _collect_entities(all_facts: list[dict]) -> list[str]:
    """Gather the proper-named characters seen so far, to help resolve
    pronouns and vague references ('the woman') in later chunks."""
    names = set()
    for f in all_facts:
        ent = f["entity"]
        # Keep things that look like proper names (capitalized, not generic).
        generic = {"woman", "man", "girl", "boy", "dog", "cat", "child",
                   "person", "villagers", "journal", "clock", "storm"}
        if ent.lower() not in generic and ent[0:1].isupper():
            names.add(ent)
    return sorted(names)


def extract_all(chunks: list[dict]) -> list[dict]:
    """
    Extract facts across all chunks with coreference resolution: as we go,
    we build a list of known character names and pass it to later chunks so
    the configured LLM can bind pronouns and vague references ('the woman', 'her') to
    the correct named character.
    """
    all_facts = []
    for chunk in chunks:
        known = _collect_entities(all_facts)
        all_facts.extend(extract_facts(chunk["text"], chunk["index"], known))
    return all_facts
