"""Evaluate CanonKeeper's contradiction detector against the labeled benchmark.
Run from the project root:  python -m backend.eval.evaluate
"""
from backend.app.ingestion import ingest
from backend.app.extraction import extract_all
from backend.app.vectors import store_facts
from backend.app.detector import find_contradictions
from backend.eval.dataset import DATASET
from pathlib import Path

UPLOAD_DIR = Path("backend/uploads")


def _norm(s: str) -> str:
    """Lowercase and strip for lenient matching."""
    return s.lower().strip()


def _matches_truth(found: list[dict], truth: dict) -> bool:
    """
    Does any detected contradiction correspond to this ground-truth item?
    We check that the contradiction is about the right entity and involves
    both expected values (order-independent, substring-tolerant).
    """
    entity = truth["entity"]
    want = {_norm(v) for v in truth["values"]}

    for c in found:
        ea = _norm(c["fact_a"]["entity"])
        eb = _norm(c["fact_b"]["entity"])
        # entity name appears on either side (handles "Watson"/"Dr. Watson")
        if entity not in ea and entity not in eb:
            continue
        va = _norm(c["fact_a"]["value"])
        vb = _norm(c["fact_b"]["value"])
        found_vals = f"{va} {vb}"
        # both expected values must appear somewhere in the pair
        if all(any(w in fv for fv in (va, vb)) for w in want):
            return True
    return False


def evaluate():
    total_tp = total_fp = total_fn = 0

    for entry in DATASET:
        path = UPLOAD_DIR / entry["file"]
        if not path.exists():
            print(f"⚠ Skipping {entry['name']}: {entry['file']} not in uploads/")
            continue

        print(f"\n=== {entry['name']} ({entry['file']}) ===")

        # Run the full pipeline
        chunks = ingest(str(path))
        facts = extract_all(chunks)
        store_facts(facts)
        found = find_contradictions(facts)

        truths = entry["truth"]
        # Which ground-truth contradictions did we catch?
        caught = [t for t in truths if _matches_truth(found, t)]
        tp = len(caught)
        fn = len(truths) - tp
        # False positives: detected contradictions that match NO ground truth
        fp = sum(
            1 for c in found
            if not any(_matches_truth([c], t) for t in truths)
        )

        total_tp += tp
        total_fp += fp
        total_fn += fn

        print(f"  Ground-truth contradictions: {len(truths)}")
        print(f"  Detected: {len(found)}")
        print(f"  ✓ Caught (TP): {tp}   ✗ Missed (FN): {fn}   ⚠ False alarms (FP): {fp}")

    # Overall metrics
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    print("\n" + "=" * 40)
    print("OVERALL")
    print(f"  Precision: {precision:.2f}")
    print(f"  Recall:    {recall:.2f}")
    print(f"  F1 score:  {f1:.2f}")
    print("=" * 40)


if __name__ == "__main__":
    evaluate()
