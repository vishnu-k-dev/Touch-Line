"""Analytics are cached (the data is static) without ever returning shared or stale mutable results."""

import threading
import time

from sqlalchemy import event

from app.core.db import engine
from app.services import analytics


def count_queries(fn):
    n = []
    listener = lambda *a, **k: n.append(1)  # noqa: E731
    event.listen(engine, "before_cursor_execute", listener)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    return len(n)


def test_a_second_call_reads_no_database_and_a_clear_recomputes(db):
    analytics.clear_cache()
    first = count_queries(lambda: analytics.match_stats(db, 3857300))
    second = count_queries(lambda: analytics.match_stats(db, 3857300))
    assert first > 0 and second == 0
    analytics.clear_cache()
    assert count_queries(lambda: analytics.match_stats(db, 3857300)) > 0


def test_cached_results_are_copies_so_a_caller_cannot_corrupt_the_next_one(db):
    analytics.clear_cache()
    analytics.match_stats(db, 3857300)  # first call computes and stores
    hit = analytics.match_stats(db, 3857300)  # second call is served from the cache
    hit["home"]["xg"] = -1
    hit["definitions"].clear()
    again = analytics.match_stats(db, 3857300)
    assert again["home"]["xg"] == 2.49 and again["definitions"]
    analytics.player_stats(db, 3857300)
    analytics.player_stats(db, 3857300).clear()
    assert len(analytics.player_stats(db, 3857300)) > 10


def test_arguments_are_part_of_the_key_and_unknown_matches_are_not_cached(db):
    analytics.clear_cache()
    assert len(analytics.shot_map(db, 3869685, include_shootout=True)) > len(analytics.shot_map(db, 3869685))
    assert analytics.match_stats(db, 1) is None
    assert ("match_stats", (1,), ()) not in analytics._cache
    assert analytics.heatmap(db, 3857300, team_id=779)["total"] != analytics.heatmap(db, 3857300, team_id=779, kind="pressures")["total"]


def test_entries_expire(db, monkeypatch):
    analytics.clear_cache()
    analytics.match_stats(db, 3857300)
    real = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: real() + analytics.CACHE_TTL_SECONDS + 1)
    assert count_queries(lambda: analytics.match_stats(db, 3857300)) > 0


def test_a_burst_of_first_requests_computes_once(db):
    from app.core.db import SessionLocal

    def go():
        with SessionLocal() as s:
            analytics.player_stats(s, 3869685)

    def burst():
        threads = [threading.Thread(target=go) for _ in range(8)]
        for t in threads:  # start them all first, so they genuinely overlap
            t.start()
        for t in threads:
            t.join()

    analytics.clear_cache()
    one = count_queries(go)
    analytics.clear_cache()
    eight = count_queries(burst)
    assert eight <= one + 8  # eight concurrent first requests cost about one computation (plus a session each), not eight
