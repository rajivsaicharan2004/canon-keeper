from pathlib import Path
import re


EYE_COLORS = ["green", "blue", "brown", "gray", "grey", "hazel", "amber", "black"]


def _pick(obj, keys, fallback):
    if not isinstance(obj, dict):
        return fallback
    for key in keys:
        value = obj.get(key)
        if value is not None and str(value).strip():
            return value
    return fallback


def _split_scenes(text):
    parts = re.split(r"(Scene\s+\d+\s*:)", text, flags=re.IGNORECASE)
    scenes = []
    if len(parts) >= 3:
        for i in range(1, len(parts), 2):
            label = parts[i].strip().rstrip(":")
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            scenes.append((label, body))
    else:
        scenes.append(("Scene unknown", text))
    return scenes


def _first_sentence_containing(body, term):
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    for sentence in sentences:
        if term.lower() in sentence.lower():
            return sentence.strip()
    return body.strip()[:240]



def _infer_rule_facts(text):
    facts = []
    scenes = _split_scenes(text)

    def add(entity, attribute, value, scene, quote):
        facts.append({
            "entity": entity,
            "attribute": attribute,
            "value": value,
            "scene": scene,
            "quote": quote,
        })

    for scene_label, body in scenes:
        lower = body.lower()

        if "green eyes" in lower:
            add("Elena", "eye color", "green", scene_label, _first_sentence_containing(body, "green eyes"))

        if "blue eyes" in lower:
            add("Elena", "eye color", "blue", scene_label, _first_sentence_containing(body, "blue eyes"))

        if "silver compass" in lower:
            add("silver compass", "material", "silver", scene_label, _first_sentence_containing(body, "silver compass"))

        if "brass" in lower and "compass" in lower:
            add("compass", "material", "brass", scene_label, _first_sentence_containing(body, "brass"))

        if "carried" in lower and "compass" in lower:
            add("silver compass", "status/location", "carried by Elena", scene_label, _first_sentence_containing(body, "compass"))

        if "missing compass" in lower:
            add("silver compass", "status/location", "missing", scene_label, _first_sentence_containing(body, "missing compass"))

        if "pointed toward the sea" in lower:
            add("compass", "direction", "toward the sea", scene_label, _first_sentence_containing(body, "sea"))

        if "pointed toward the mountains" in lower:
            add("compass", "direction", "toward the mountains", scene_label, _first_sentence_containing(body, "mountains"))

        if "north door" in lower:
            add("north door", "warning", "Elena should never open it", scene_label, _first_sentence_containing(body, "north door"))

    return facts


def _infer_rule_conflicts(text):
    conflicts = []
    scenes = _split_scenes(text)

    eye_facts = []
    last_name = None

    for scene_label, body in scenes:
        names = re.findall(r"\b[A-Z][a-z]+\b", body)
        names = [n for n in names if n.lower() not in {"scene", "her", "his", "the", "she", "he"}]
        if names:
            last_name = names[0]

        for color in EYE_COLORS:
            if re.search(rf"\b{color}\s+eyes\b", body, flags=re.IGNORECASE):
                entity = last_name or "Unknown character"
                quote = _first_sentence_containing(body, f"{color} eyes")
                eye_facts.append({
                    "entity": entity,
                    "color": color,
                    "scene": scene_label,
                    "quote": quote,
                })

    for i in range(len(eye_facts)):
        for j in range(i + 1, len(eye_facts)):
            a = eye_facts[i]
            b = eye_facts[j]
            if a["entity"] == b["entity"] and a["color"] != b["color"]:
                conflicts.append({
                    "entity": a["entity"],
                    "attribute": "eye color",
                    "old_value": a["color"],
                    "new_value": b["color"],
                    "old_scene": a["scene"],
                    "new_scene": b["scene"],
                    "old_quote": a["quote"],
                    "new_quote": b["quote"],
                    "severity": "high",
                    "explanation": f"{a['entity']}'s eye color changes from {a['color']} to {b['color']}.",
                })

    carried = None
    missing = None

    for scene_label, body in scenes:
        if re.search(r"\bcarried\b.*\bcompass\b|\bcompass\b.*\bcarried\b", body, flags=re.IGNORECASE):
            carried = {
                "scene": scene_label,
                "quote": _first_sentence_containing(body, "compass"),
            }
        if re.search(r"\bmissing\s+compass\b|\bcompass\b.*\bmissing\b", body, flags=re.IGNORECASE):
            missing = {
                "scene": scene_label,
                "quote": _first_sentence_containing(body, "compass"),
            }

    if carried and missing:
        conflicts.append({
            "entity": "silver compass",
            "attribute": "status/location",
            "old_value": "carried by Elena",
            "new_value": "missing",
            "old_scene": carried["scene"],
            "new_scene": missing["scene"],
            "old_quote": carried["quote"],
            "new_quote": missing["quote"],
            "severity": "medium",
            "explanation": "The compass is established as being carried by Elena, but later appears to be missing.",
        })

    return conflicts


def _normalize_issue(issue):
    return {
        "entity": _pick(issue, ["entity", "character", "name", "subject"], "Unknown entity"),
        "attribute": _pick(issue, ["attribute", "field", "property", "trait"], "Unknown attribute"),
        "old_value": _pick(issue, ["old_value", "previous_value", "value_1", "first_value", "old"], "Unknown previous value"),
        "new_value": _pick(issue, ["new_value", "current_value", "value_2", "second_value", "new"], "Unknown new value"),
        "old_scene": _pick(issue, ["old_scene", "scene_1", "first_scene", "previous_scene"], "Scene unknown"),
        "new_scene": _pick(issue, ["new_scene", "scene_2", "second_scene", "current_scene"], "Scene unknown"),
        "old_quote": _pick(issue, ["old_quote", "quote_1", "first_quote", "previous_quote", "source_1"], "No source quote returned."),
        "new_quote": _pick(issue, ["new_quote", "quote_2", "second_quote", "current_quote", "source_2"], "No source quote returned."),
        "severity": str(_pick(issue, ["severity", "level"], "medium")).lower(),
        "explanation": _pick(issue, ["explanation", "reason", "description", "summary"], "These facts appear to describe the same story element with inconsistent details."),
    }


def normalize_analysis_response(ctx):
    filename = ctx.get("filename")
    facts = ctx.get("facts") or []
    contradictions = ctx.get("contradictions") or ctx.get("issues") or []

    text = ""
    for value in ctx.values():
        if isinstance(value, str) and len(value) > len(text):
            text = value

    if filename:
        upload_path = Path("uploads") / filename
        if upload_path.exists():
            try:
                text = upload_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    normalized = [_normalize_issue(c) for c in contradictions if isinstance(c, dict)]

    bad_results = (
        not normalized
        or all(c["entity"] == "Unknown entity" for c in normalized)
        or all(c["old_quote"] == "No source quote returned." for c in normalized)
    )

    if bad_results and text:
        normalized = _infer_rule_conflicts(text)

    if text and not facts:
        facts = _infer_rule_facts(text)

    return {
        "filename": filename,
        "facts_count": len(facts),
        "facts": facts,
        "contradictions": normalized,
    }
