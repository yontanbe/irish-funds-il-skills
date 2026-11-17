"""בדיקות לשאלון הסיכון."""
import itertools

import pytest

from engine import score_risk


def _answers(q, pick):
    return {x["id"]: x["options"][pick(x)]["id"] for x in q["questions"]}


def test_most_cautious_answers_give_conservative(data):
    q = data["questionnaire"]
    r = score_risk(_answers(q, lambda x: 0), q)
    assert r["profile_id"] == "conservative"
    assert r["equity_pct"] == 30
    assert r["score"] == sum(x["options"][0]["points"] for x in q["questions"])


def test_boldest_answers_give_aggressive(data):
    q = data["questionnaire"]
    r = score_risk(_answers(q, lambda x: -1), q)
    assert r["profile_id"] == "aggressive"
    assert r["equity_pct"] == 100
    assert r["pct"] == 100
    assert r["warnings"] == []


def test_short_horizon_caps_equity_even_for_bold_investor(data):
    q = data["questionnaire"]
    a = _answers(q, lambda x: -1)
    a["horizon"] = "lt3"
    r = score_risk(a, q)
    assert r["equity_pct"] == 30
    assert any("3 שנים" in w for w in r["warnings"])


def test_medium_horizon_caps_at_50(data):
    q = data["questionnaire"]
    a = _answers(q, lambda x: -1)
    a["horizon"] = "3to5"
    assert score_risk(a, q)["equity_pct"] == 50


def test_panic_seller_is_capped_at_50(data):
    q = data["questionnaire"]
    a = _answers(q, lambda x: -1)
    a["drop"] = "sell_all"
    r = score_risk(a, q)
    assert r["equity_pct"] <= 50
    assert any("נועל הפסד" in w for w in r["warnings"])


def test_no_emergency_fund_gives_warning(data):
    q = data["questionnaire"]
    a = _answers(q, lambda x: -1)
    a["emergency"] = "none"
    assert any("כרית ביטחון" in w for w in score_risk(a, q)["warnings"])


def test_example_file_is_balanced(data, root):
    import json
    answers = json.loads((root / "examples" / "answers-balanced.json").read_text(encoding="utf-8"))
    r = score_risk(answers, data["questionnaire"])
    assert r["profile_id"] == "balanced"
    assert r["equity_pct"] == 70


def test_missing_answer_raises(data):
    q = data["questionnaire"]
    a = _answers(q, lambda x: 0)
    del a["goal"]
    with pytest.raises(ValueError, match="חסרה תשובה"):
        score_risk(a, q)


def test_unknown_answer_raises(data):
    q = data["questionnaire"]
    a = _answers(q, lambda x: 0)
    a["goal"] = "moon"
    with pytest.raises(ValueError, match="לא מוכרת"):
        score_risk(a, q)


def test_every_possible_answer_combination(data):
    """עובר על כל הצירופים האפשריים ובודק שהתוצאה תמיד חוקית ושכל הפרופילים מושגים."""
    q = data["questionnaire"]
    allowed_equity = {p["equity_pct"] for p in q["profiles"]} | {c["max_equity_pct"] for c in q["caps"]}
    ids = [x["id"] for x in q["questions"]]
    seen_profiles = set()
    count = 0
    for combo in itertools.product(*[[o["id"] for o in x["options"]] for x in q["questions"]]):
        r = score_risk(dict(zip(ids, combo)), q)
        assert r["equity_pct"] in allowed_equity
        assert 0 <= r["pct"] <= 100
        seen_profiles.add(r["profile_id"])
        count += 1
    assert count == 5 * 4 ** 6
    assert seen_profiles == {p["id"] for p in q["profiles"]}


def test_bolder_answer_never_lowers_equity(data):
    """מונוטוניות: תשובה נועזת יותר לשאלה אחת לא מורידה את החלק המנייתי."""
    q = data["questionnaire"]
    ids = [x["id"] for x in q["questions"]]
    option_ids = [[o["id"] for o in x["options"]] for x in q["questions"]]
    for combo in itertools.product(*[range(len(o)) for o in option_ids]):
        base = score_risk({i: option_ids[k][c] for k, (i, c) in enumerate(zip(ids, combo))}, q)["equity_pct"]
        for k in range(len(ids)):
            if combo[k] + 1 < len(option_ids[k]):
                bumped = list(combo)
                bumped[k] += 1
                up = score_risk({i: option_ids[j][c] for j, (i, c) in enumerate(zip(ids, bumped))}, q)["equity_pct"]
                assert up >= base
