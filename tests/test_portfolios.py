"""בדיקות לבניית התיקים."""
import itertools

import pytest

from engine import build_portfolio, funds_by_number, portfolio_stats

TECH = [10, 15, 20, 25]


def _option_combos(template):
    specs = template.get("options", {})
    keys = list(specs)
    for values in itertools.product(*[list(specs[k]["choices"]) for k in keys]):
        yield dict(zip(keys, values))


def test_every_template_option_and_equity_level_sums_to_100(data):
    """כל תבנית, כל צירוף אפשרויות, כל אחוז מנייתי מ-0 עד 100: הסכום תמיד 100."""
    numbers = set(funds_by_number(data["funds"]))
    checked = 0
    for t in data["portfolios"]["templates"]:
        for options in _option_combos(t):
            for tech in TECH:
                for equity in range(0, 101):
                    p = build_portfolio(t["id"], equity, tech, data["portfolios"], options)
                    weights = [l["weight"] for l in p["lines"]]
                    assert sum(weights) == 100
                    assert all(isinstance(w, int) and w > 0 for w in weights)
                    solid = [l for l in p["lines"] if l["slot"] == "solid"]
                    assert (solid[0]["weight"] if solid else 0) == 100 - equity
                    for l in p["lines"]:
                        assert l["fund"] is None or l["fund"] in numbers
                    checked += 1
    assert checked > 5000


def test_olami_ehad_is_one_fund(data):
    p = build_portfolio("olami-ehad", 100, 10, data["portfolios"])
    assert p["lines"] == [{"slot": "global", "label": "עולמי", "fund": "1209220", "weight": 100}]


def test_olami_ehad_respects_fund_choice(data):
    p = build_portfolio("olami-ehad", 100, 10, data["portfolios"], {"global_fund": "1159235"})
    assert p["lines"][0]["fund"] == "1159235"


def test_three_regions_at_full_equity(data):
    p = build_portfolio("shlosha-ezorim", 100, 10, data["portfolios"])
    assert [(l["fund"], l["weight"]) for l in p["lines"]] == [("1159250", 60), ("1159094", 25), ("1159169", 15)]


def test_balanced_profile_adds_solid_part(data):
    p = build_portfolio("shlosha-ezorim", 70, 15, data["portfolios"])
    assert [(l["slot"], l["weight"]) for l in p["lines"]] == [("us", 42), ("europe", 18), ("emerging", 10), ("solid", 30)]
    assert any("כספית" in n for n in p["notes"])


def test_triathlon_default_aggressive(data):
    p = build_portfolio("triathlon", 100, 25, data["portfolios"])
    by_slot = {l["slot"]: l for l in p["lines"]}
    assert by_slot["tech"]["weight"] == 25
    assert by_slot["sp"]["fund"] == "1159250"
    assert by_slot["global"]["fund"] == "1209220"
    assert by_slot["sp"]["weight"] + by_slot["global"]["weight"] == 75
    assert abs(by_slot["sp"]["weight"] - by_slot["global"]["weight"]) <= 1


def test_triathlon_equal_weight_uses_equal_weight_fund(data):
    p = build_portfolio("triathlon", 100, 20, data["portfolios"], {"sp_variant": "equal"})
    assert {l["slot"]: l["fund"] for l in p["lines"]}["sp"] == "1207208"


def test_triathlon_hedged_leaves_empty_slot_with_note(data):
    p = build_portfolio("triathlon", 100, 20, data["portfolios"], {"sp_variant": "hedged"})
    hedged = [l for l in p["lines"] if l["slot"] == "sp_hedged"][0]
    assert hedged["fund"] is None
    assert hedged["weight"] == 40
    assert any("מנוטרל" in n for n in p["notes"])


def test_triathlon_combined_splits_sp_leg_in_two(data):
    p = build_portfolio("triathlon", 100, 20, data["portfolios"], {"sp_variant": "combined"})
    by_slot = {l["slot"]: l for l in p["lines"]}
    assert by_slot["sp"]["fund"] == "1159250" and by_slot["sp_equal"]["fund"] == "1207208"
    assert by_slot["sp"]["weight"] == by_slot["sp_equal"]["weight"] == 20


def test_triathlon_ex_us_global_leg_holds_no_us_fund(data):
    by_num = funds_by_number(data["funds"])
    p = build_portfolio("triathlon", 100, 20, data["portfolios"], {"global_variant": "ex_us"})
    by_slot = {l["slot"]: l for l in p["lines"]}
    assert by_slot["europe"]["weight"] == 24 and by_slot["emerging"]["weight"] == 16
    assert by_num[by_slot["europe"]["fund"]]["us_share"] == 0
    assert by_num[by_slot["emerging"]["fund"]]["us_share"] == 0
    assert any("יפן" in n for n in p["notes"])


def test_ex_us_lowers_us_exposure(data):
    all_world = build_portfolio("triathlon", 100, 20, data["portfolios"], {"global_variant": "all"})
    ex_us = build_portfolio("triathlon", 100, 20, data["portfolios"], {"global_variant": "ex_us"})
    assert (portfolio_stats(ex_us["lines"], data["funds"])["us_share_pct"]
            < portfolio_stats(all_world["lines"], data["funds"])["us_share_pct"])


def test_stats_for_single_fund_match_fund_data(data):
    p = build_portfolio("olami-ehad", 100, 10, data["portfolios"])
    s = portfolio_stats(p["lines"], data["funds"])
    assert s == {"covered_weight": 100, "weighted_cost_pct": 0.15, "us_share_pct": 62.0}


def test_stats_ignore_slots_without_fund(data):
    p = build_portfolio("olami-ehad", 50, 10, data["portfolios"])
    s = portfolio_stats(p["lines"], data["funds"])
    assert s["covered_weight"] == 50 and s["weighted_cost_pct"] == 0.15


def test_zero_equity_is_all_solid(data):
    p = build_portfolio("triathlon", 0, 10, data["portfolios"])
    assert p["lines"] == [{"slot": "solid", "label": "רכיב סולידי", "fund": None, "weight": 100}]
    assert portfolio_stats(p["lines"], data["funds"])["covered_weight"] == 0


@pytest.mark.parametrize("kwargs", [
    {"template_id": "nope", "equity_pct": 50, "tech_pct": 10},
    {"template_id": "triathlon", "equity_pct": 101, "tech_pct": 10},
    {"template_id": "triathlon", "equity_pct": -1, "tech_pct": 10},
    {"template_id": "triathlon", "equity_pct": 50.5, "tech_pct": 10},
    {"template_id": "triathlon", "equity_pct": 50, "tech_pct": 12},
    {"template_id": "triathlon", "equity_pct": 50, "tech_pct": 55},
])
def test_bad_input_raises(data, kwargs):
    with pytest.raises(ValueError):
        build_portfolio(portfolios=data["portfolios"], **kwargs)


def test_bad_option_raises(data):
    with pytest.raises(ValueError):
        build_portfolio("triathlon", 50, 10, data["portfolios"], {"sp_variant": "leveraged"})
    with pytest.raises(ValueError):
        build_portfolio("olami-ehad", 50, 10, data["portfolios"], {"global_fund": "0000000"})
