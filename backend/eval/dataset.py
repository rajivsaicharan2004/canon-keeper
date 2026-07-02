"""
Labeled benchmark for CanonKeeper's contradiction detector.

Each entry pairs a document with its KNOWN contradictions (ground truth).
A contradiction is identified by the entity and the two conflicting values —
we don't require exact attribute wording, just that the system flags a
conflict about the right entity with the right pair of values.
"""

DATASET = [
    {
        "name": "sherlock",
        "file": "test.txt",
        "truth": [
            # Watson's wound moves from shoulder to leg
            {"entity": "watson", "values": {"left shoulder", "leg"}},
        ],
    },
    {
        "name": "lighthouse",
        "file": "the_lighthouse_keeper.txt",
        "truth": [
            {"entity": "elena", "values": {"thirty-four", "forty-one"}},   # age drift
            {"entity": "elena", "values": {"green", "brown"}},             # eye color
            {"entity": "captain", "values": {"black labrador", "golden retriever"}},  # breed
            # Steps: 98 vs 240 — worded many ways, so we match loosely on the numbers
            {"entity": "lighthouse", "values": {"ninety-eight", "two hundred and forty"}},
        ],
    },
]
