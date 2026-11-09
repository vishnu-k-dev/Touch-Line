"""Day 3 acceptance: relevant documents are retrieved. Run `pytest -s tests/test_retrieval.py` to see the metrics.

Queries are written the way a user would ask, not copied from document titles. Expected answers for the
knowledge set are fixed by hand; match and shot-sequence checks use ground truth from the event data."""

import pytest

from app.services import rag

# query -> acceptable knowledge-document titles
KNOWLEDGE_CASES = [
    ("What does a 0.3 xG shot actually mean?", ["Expected goals (xG)"]),
    ("A team took lots of shots but all from distance, is that good?", ["Shot quality versus shot volume (xG per shot)"]),
    ("How should I treat penalties when judging chance creation?", ["Non-penalty xG (npxG)", "Penalties in xG"]),
    ("Why would the team with better chances lose the match?", ["Why a team can lose despite higher xG"]),
    ("A striker scored way more than his xG, will that continue?", ["Finishing and goalkeeping: goals versus xG"]),
    ("Where on the pitch are shots most dangerous?", ["Reading a shot map (location and distance)"]),
    ("How much is a penalty kick worth in expected goals?", ["Penalties in xG"]),
    ("How do teams create chances from corners and throw-ins?", ["Set pieces: corners, free kicks and throw-ins"]),
    ("Why do trailing teams shoot more late in matches?", ["Game state and its effect on shots"]),
    ("How do you measure pressing intensity?", ["Pressing and PPDA"]),
    ("How do I tell how high up the pitch a team defends?", ["High press, mid block and low block"]),
    ("What is gegenpressing?", ["Counter-pressing and transitions"]),
    ("Does more possession mean a team played better?", ["Possession versus chance creation (pass share)"]),
    ("Is a high pass completion percentage a sign of quality?", ["Pass accuracy: what it does and does not tell you"]),
    ("Who creates the most chances for teammates?", ["Key passes and assists"]),
    ("How reliable is a single match's xG?", ["Small samples: why one match is noisy"]),
    ("How do penalty shootouts count in the statistics?", ["Penalty shootouts"]),
    ("Can this data tell us a team's formation or a player's running speed?", ["What event data cannot tell you"]),
    ("What is expected threat?", ["Action-value models (xT and VAEP)"]),
    ("How should I separate facts from opinion in a tactical answer?", ["Measurement versus interpretation"]),
]

# query -> expected match_id (top-1 among the 5 match summaries)
MATCH_CASES = [
    ("Which game did Germany lose to Japan?", 3857284),
    ("A goalless draw that went to penalties", 3869220),
    ("Argentina's shock defeat", 3857300),
    ("England against France in the quarter-final", 3869354),
]

# query -> predicate on a shot sequence's metadata; at least one of the top 3 must satisfy it
MOMENT_CASES = [
    ("Messi penalty against Saudi Arabia", lambda m, mid: "Messi" in m["player"] and m["shot_type"] == "Penalty" and mid == 3857300),
    ("Harry Kane scored a penalty against France", lambda m, mid: "Kane" in m["player"] and m["shot_type"] == "Penalty" and m["outcome"] == "Goal"),
    ("Giroud header against England", lambda m, mid: "Giroud" in m["player"] and m["body_part"] == "Head" and mid == 3869354),
    ("Mbappé scored in the World Cup final", lambda m, mid: "Mbapp" in m["player"] and m["outcome"] == "Goal" and mid == 3869685),
    ("Doan goal for Japan against Germany", lambda m, mid: "Doan" in m["player"] and m["outcome"] == "Goal" and mid == 3857284),
]

# attribute-only queries: how well does dense retrieval alone respect an exact attribute?
ATTRIBUTE_CASES = [
    ("header from a corner", lambda m: m["body_part"] == "Head" and m["play_pattern"] == "From Corner"),
    ("penalty kick", lambda m: m["shot_type"] == "Penalty"),
    ("long-range shot from outside the box", lambda m: m["distance"] >= 20),
    ("goal scored from a counter-attack", lambda m: m["play_pattern"] == "From Counter" and m["outcome"] == "Goal"),
]


def _rank(db, query, expected_titles, k=3):
    titles = [h["title"] for h in rag.search(db, query, k=10, kind="knowledge")]
    return next((i + 1 for i, t in enumerate(titles) if t in expected_titles), None)


def test_knowledge_retrieval(indexed):
    ranks = [_rank(indexed, q, ok) for q, ok in KNOWLEDGE_CASES]
    recall3 = sum(r is not None and r <= 3 for r in ranks) / len(ranks)
    top1 = sum(r == 1 for r in ranks) / len(ranks)
    mrr = sum(1 / r for r in ranks if r) / len(ranks)
    print(f"\nknowledge ({len(ranks)} queries): recall@3={recall3:.2f} top1={top1:.2f} MRR={mrr:.2f}")
    for (q, _), r in zip(KNOWLEDGE_CASES, ranks):
        if r != 1:
            print(f"   rank {r}: {q}")
    assert recall3 >= 0.9


def test_match_summary_retrieval(indexed):
    ranks = []
    for q, mid in MATCH_CASES:
        ids = [h["match_id"] for h in rag.search(indexed, q, k=5, kind="match")]
        ranks.append(ids.index(mid) + 1)
    top1 = sum(r == 1 for r in ranks) / len(ranks)
    hit3 = sum(r <= 3 for r in ranks) / len(ranks)
    print(f"\nmatch summaries ({len(ranks)} queries, 5 matches): top1={top1:.2f} hit@3={hit3:.2f}")
    for (q, _), r in zip(MATCH_CASES, ranks):
        if r != 1:
            print(f"   rank {r}: {q}")  # known: a vague query naming one team can rank the right match second
    assert hit3 == 1.0 and top1 >= 0.75


def test_find_the_moment(indexed):
    hits = []
    for q, pred in MOMENT_CASES:
        top = rag.search(indexed, q, k=3, kind="sequence")
        hits.append(any(pred(h["meta"], h["match_id"]) for h in top))
    print(f"\nfind-the-moment ({len(hits)} queries): hit@3={sum(hits) / len(hits):.2f}")
    for (q, _), ok in zip(MOMENT_CASES, hits):
        if not ok:
            print(f"   missed: {q}")
    assert sum(hits) / len(hits) >= 0.8


def test_attribute_queries_dense_only_is_reported_not_trusted(indexed):
    """Documents the known weakness: embeddings alone do not respect exact attributes. Filters fix it (next test)."""
    for q, pred in ATTRIBUTE_CASES:
        top = rag.search(indexed, q, k=3, kind="sequence")
        print(f"\n   dense-only precision@3 {sum(pred(h['meta']) for h in top)}/3: {q}")


def test_metadata_filters_are_exact(indexed):
    hits = rag.search(indexed, "chance", k=20, kind="sequence", filters={"body_part": "Head", "play_pattern": "From Corner"})
    assert hits and all(h["meta"]["body_part"] == "Head" and h["meta"]["play_pattern"] == "From Corner" for h in hits)
    pens = rag.search(indexed, "goal", k=50, kind="sequence", filters={"shot_type": "Penalty", "player": "messi"})
    assert pens and all("Messi" in h["meta"]["player"] and h["meta"]["shot_type"] == "Penalty" for h in pens)
    with pytest.raises(ValueError):
        rag.search(indexed, "x", filters={"minute": "5"})


def test_sequence_hits_carry_evidence_ids(indexed):
    for h in rag.search(indexed, "shot from a corner", k=5, kind="sequence"):
        assert h["meta"]["event_ids"] and h["meta"]["event_ids"][0]  # first id is the shot event
