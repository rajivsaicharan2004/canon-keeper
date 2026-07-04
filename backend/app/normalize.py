"""
Entity + attribute normalization for contradiction detection.

The problem: Granite labels the same property inconsistently — "type" vs
"breed", "eye color" vs "eyes". Naive comparison misses these. We fix it by
grouping each entity's facts and clustering their ATTRIBUTES by semantic
similarity, so differently-worded-but-equivalent properties get compared.
"""

import numpy as np
from app.vectors import embed_text


def _normalize_entity(name: str) -> str:
    """Collapse entity name variants to a stable key.
    'Dr. Watson' -> 'watson', 'Elena Marsh' and 'Elena' -> 'elena'.
    We use the FIRST name token, which is the most stable reference in
    fiction (characters are called by first name or full name, rarely by
    surname alone)."""
    cleaned = (name.lower()
               .replace("dr.", "").replace("mr.", "")
               .replace("mrs.", "").replace("ms.", "").strip())
    parts = cleaned.split()
    if not parts:
        return cleaned
    # For "Elena Marsh" -> "elena"; for "Watson" -> "watson".
    # But "Dr. Watson" -> "watson" (title stripped, one token left).
    return parts[0]


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    a, b = np.array(a), np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def group_candidate_pairs(facts: list[dict], attr_threshold: float = 0.5) -> list[tuple[dict, dict]]:
    """
    Return pairs of facts that describe the SAME entity and a semantically
    SIMILAR attribute but have DIFFERENT values — i.e. contradiction candidates.

    These pairs are what we then send to Granite to confirm.
    """
    # 1. Group facts by normalized entity.
    by_entity: dict[str, list[dict]] = {}
    for f in facts:
        key = _normalize_entity(f["entity"])
        by_entity.setdefault(key, []).append(f)

    # 2. Pre-compute an embedding for each fact's ATTRIBUTE (cached per call).
    attr_vectors: dict[str, list[float]] = {}

    def attr_vec(attr: str) -> list[float]:
        if attr not in attr_vectors:
            attr_vectors[attr] = embed_text(attr)
        return attr_vectors[attr]

    candidates = []

    # 3. Within each entity, compare every pair of facts.
    for entity_facts in by_entity.values():
        for i in range(len(entity_facts)):
            for j in range(i + 1, len(entity_facts)):
                fa, fb = entity_facts[i], entity_facts[j]

                # Same value = no conflict, skip.
                if fa["value"].strip().lower() == fb["value"].strip().lower():
                    continue

                # Skip attributes about a character's changing position or
                # transient action — a character moving isn't a contradiction.
                # But do NOT skip physical facts like "wound location".
                fa_attr = fa["attribute"].lower()
                fb_attr = fb["attribute"].lower()
                TRANSIENT = ("action", "activity", "task", "emotion", "thought",
                             "position preference", "location preference")
                # "location"/"position" alone = movable; but keep "wound location" etc.
                def _is_transient(attr: str) -> bool:
                    if any(t in attr for t in TRANSIENT):
                        return True
                    # bare location/position (not part of a body/physical phrase)
                    if attr.strip() in ("location", "position", "current location"):
                        return True
                    return False
                if _is_transient(fa_attr) or _is_transient(fb_attr):
                    continue

                # Are the two ATTRIBUTES semantically the same property?
                sim = _cosine(attr_vec(fa["attribute"]), attr_vec(fb["attribute"]))
                if sim >= attr_threshold:
                    # Same entity, same property, different values → candidate.
                    candidates.append((fa, fb))

    return candidates
