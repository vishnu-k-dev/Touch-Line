from agent_helpers import ScriptedProvider, answer, finding, submit, tool_use
from app.evals.agent_eval import build_cases, run_eval
from app.services import analytics


def _cases(db, *ids):
    return [c for c in build_cases(db) if c.id in ids]


def test_golden_cases_use_database_ground_truth(db):
    cases = {c.id: c for c in build_cases(db)}
    assert len(cases) == 9 and cases["upset_xg"].expect_numbers == [analytics.match_stats(db, 3857300)["home"]["xg"], analytics.match_stats(db, 3857300)["away"]["xg"]]
    assert cases["player_compare"].expect_numbers == [2, 3] and cases["shootout"].expect_numbers == [4, 2]
    assert cases["decline_formation"].must_decline and cases["decline_future"].must_decline
    assert cases["lane_360"].expect_numbers[0] > 0


def test_eval_scores_a_correct_answer_a_wrong_number_and_a_proper_decline(db):
    s = analytics.match_stats(db, 3857300)
    right = submit(answer(findings=[finding("xG", "xG", {"Argentina": s["home"]["xg"], "Saudi Arabia": s["away"]["xg"]}, ["c1"])]))
    wrong_number = submit(answer(findings=[finding("xG", "xG", {"Argentina": s["home"]["xg"]}, ["c1"])]))  # omits the opponent's xG
    decline = submit(answer(limitations=["Formation and sprint speed need tracking data, which this event data does not include."]))
    summary = tool_use(("get_match_summary", {"match_id": 3857300}))
    provider = ScriptedProvider([summary, right, summary, wrong_number, decline, submit(answer(findings=[finding("x", "x", {"n": 1}, ["c1"])]))])

    # upset_xg passes; run it again to see the wrong-number answer fail
    good = run_eval(db, provider, _cases(db, "upset_xg"))
    assert good["pass_rate"] == 1.0 and good["grounded_rate"] == 1.0 and good["cost_per_question_usd"] > 0
    bad = run_eval(db, provider, _cases(db, "upset_xg"))
    assert bad["pass_rate"] == 0.0 and bad["numbers_correct_rate"] == 0.0 and bad["results"][0]["tools_ok"]
    ok_decline = run_eval(db, provider, _cases(db, "decline_formation"))
    assert ok_decline["pass_rate"] == 1.0 and ok_decline["results"][0]["declined_ok"]


def test_a_decline_case_fails_if_the_model_makes_findings_instead(db):
    guess = submit(answer(findings=[finding("France played 4-3-3", "formation", {"x": 1}, ["c1"])], limitations=["x"]))
    p = ScriptedProvider([tool_use(("get_match_summary", {"match_id": 3869685})), guess, guess])
    r = run_eval(db, p, _cases(db, "decline_formation"))
    assert r["pass_rate"] == 0.0 and r["results"][0]["declined_ok"] is False
