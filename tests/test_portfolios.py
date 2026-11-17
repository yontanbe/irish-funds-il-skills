"""בדיקות לבניית התיקים: שלושת המבנים, כל הגרסאות, והשוואת חלופות."""
import itertools

import pytest

from engine import alternatives, build_portfolio, funds_by_number, portfolio_stats, total_cost_pct


def _option_combos(template):
    specs = template.get("options", {})
    keys = list(specs)
    for values in itertools.product(*[list(specs[k]["choices"]) for k in keys]):
        yield dict(zip(keys, values))


def test_every_template_option_and_equity_level_sums_to_100(data):
    """כל מבנה, כל צירוף גרסאות, כל אחוז מנייתי מ-0 עד 100: הסכום תמיד 100."""
    numbers = set(funds_by_number(data["funds"]))
    checked = 0
    for t in data["portfolios"]["templates"]:
        for options in _option_combos(t):
            for equity in range(0, 101):
                p = build_portfolio(t["id"], equity, data["portfolios"], options)
                weights = [l["weight"] for l in p["lines"]]
                assert sum(weights) == 100
                assert all(isinstance(w, int) and w > 0 for w in weights)
                non_equity = sum(l["weight"] for l in p["lines"] if l["slot"] in ("solid", "bond", "il_general_bond"))
                assert non_equity == 100 - equity
                for l in p["lines"]:
                    assert l["fund"] is None or l["fund"] in numbers
                checked += 1
    assert checked == (3 + 6 + 4 * 6 * 3) * 101


# ---------- תיק 1 ----------

def test_portfolio_1_is_one_global_fund(data):
    p = build_portfolio("olami-ehad", 100, data["portfolios"])
    assert p["lines"] == [{"slot": "global", "label": "מניות עולם", "fund": "1209220", "weight": 100}]


def test_portfolio_1_respects_fund_choice_and_adds_solid(data):
    p = build_portfolio("olami-ehad", 70, data["portfolios"], {"global_fund": "1159235"})
    assert [(l["slot"], l["fund"], l["weight"]) for l in p["lines"]] == [("global", "1159235", 70), ("solid", None, 30)]


# ---------- תיק 2 ----------

def test_portfolio_2_global_equity_plus_global_bond(data):
    p = build_portfolio("olami-ve-agach", 70, data["portfolios"])
    assert [(l["slot"], l["fund"], l["weight"]) for l in p["lines"]] == [("global", "1209220", 70), ("bond", "1159102", 30)]
    assert any("מגודרת לדולר" in n for n in p["notes"])
    assert portfolio_stats(p["lines"], data["funds"])["covered_weight"] == 100


def test_portfolio_2_israeli_bond_is_an_empty_slot(data):
    p = build_portfolio("olami-ve-agach", 50, data["portfolios"], {"bond_variant": "il_general"})
    bond = p["lines"][1]
    assert (bond["slot"], bond["fund"], bond["weight"]) == ("il_general_bond", None, 50)
    assert any("אינו קרן אירית" in n for n in p["notes"])


def test_portfolio_2_at_full_equity_explains_missing_bond(data):
    p = build_portfolio("olami-ve-agach", 100, data["portfolios"])
    assert len(p["lines"]) == 1
    assert any("אין רכיב אגח" in n for n in p["notes"])


# ---------- תיק 3 ----------

def test_triathlon_is_three_equal_legs(data):
    p = build_portfolio("triathlon", 99, data["portfolios"])
    by_slot = {l["slot"]: l for l in p["lines"]}
    assert (by_slot["tech"]["weight"], by_slot["sp"]["weight"], by_slot["global"]["weight"]) == (33, 33, 33)
    assert (by_slot["tech"]["fund"], by_slot["sp"]["fund"], by_slot["global"]["fund"]) == ("1159193", "1159250", "1209220")


def test_triathlon_at_100_gives_34_33_33(data):
    p = build_portfolio("triathlon", 100, data["portfolios"])
    assert [l["weight"] for l in p["lines"]] == [34, 33, 33]


@pytest.mark.parametrize("variant,fund", [
    ("sp_tech_ishares", "1159193"), ("us_tech_invesco", "1185180"),
    ("nasdaq_ishares", "1159243"), ("nasdaq_invesco", "1186063")])
def test_triathlon_tech_variants(data, variant, fund):
    p = build_portfolio("triathlon", 90, data["portfolios"], {"tech_variant": variant})
    assert {l["slot"]: l["fund"] for l in p["lines"]}["tech"] == fund


@pytest.mark.parametrize("variant,fund", [
    ("regular_ishares", "1159250"), ("regular_invesco", "1183441"), ("equal", "1207208")])
def test_triathlon_sp_fund_variants(data, variant, fund):
    p = build_portfolio("triathlon", 90, data["portfolios"], {"sp_variant": variant})
    assert {l["slot"]: l["fund"] for l in p["lines"]}["sp"] == fund


def test_triathlon_combined_splits_sp_leg_in_two(data):
    p = build_portfolio("triathlon", 90, data["portfolios"], {"sp_variant": "combined"})
    by_slot = {l["slot"]: l for l in p["lines"]}
    assert by_slot["sp"]["fund"] == "1159250" and by_slot["sp_equal"]["fund"] == "1207208"
    assert by_slot["sp"]["weight"] == by_slot["sp_equal"]["weight"] == 15


@pytest.mark.parametrize("variant,slot,needle", [("value", "value", "5133681"), ("hedged", "sp_hedged", "מנוטרלת לשקל")])
def test_triathlon_non_irish_sp_variants_leave_empty_slot(data, variant, slot, needle):
    p = build_portfolio("triathlon", 90, data["portfolios"], {"sp_variant": variant})
    line = [l for l in p["lines"] if l["slot"] == slot][0]
    assert line["fund"] is None and line["weight"] == 30
    assert any(needle in n for n in p["notes"])


def test_triathlon_global_variants(data):
    by_num = funds_by_number(data["funds"])
    ishares = build_portfolio("triathlon", 90, data["portfolios"], {"global_variant": "all_ishares"})
    assert {l["slot"]: l["fund"] for l in ishares["lines"]}["global"] == "1159235"
    ex_us = build_portfolio("triathlon", 90, data["portfolios"], {"global_variant": "ex_us"})
    by_slot = {l["slot"]: l for l in ex_us["lines"]}
    assert (by_slot["europe"]["weight"], by_slot["emerging"]["weight"]) == (18, 12)
    assert by_num[by_slot["europe"]["fund"]]["us_share"] == 0
    assert by_num[by_slot["emerging"]["fund"]]["us_share"] == 0
    assert any("יפן" in n for n in ex_us["notes"])


def test_triathlon_always_warns_about_overlap(data):
    for options in _option_combos(data["portfolios"]["templates"][2]):
        p = build_portfolio("triathlon", 80, data["portfolios"], options)
        assert any("חופפות" in n for n in p["notes"])


def test_ex_us_lowers_us_exposure(data):
    all_world = build_portfolio("triathlon", 100, data["portfolios"])
    ex_us = build_portfolio("triathlon", 100, data["portfolios"], {"global_variant": "ex_us"})
    assert (portfolio_stats(ex_us["lines"], data["funds"])["us_share_pct"]
            < portfolio_stats(all_world["lines"], data["funds"])["us_share_pct"])


# ---------- השוואת חלופות ----------

def test_alternatives_show_ishares_against_invesco_for_sp500(data):
    alts = alternatives("1159250", data["funds"])
    assert [(a["tase_number"], a["issuer"], a["cost_pct"], a["diff_pct"]) for a in alts] == [
        ("1183441", "Invesco", 0.12, 0.05)]
    back = alternatives("1183441", data["funds"])
    assert back[0]["tase_number"] == "1159250" and back[0]["diff_pct"] == -0.05


def test_alternatives_for_global_fund_list_both_other_global_funds(data):
    alts = alternatives("1209220", data["funds"])
    assert [a["tase_number"] for a in alts] == ["1185164", "1159235"]
    assert [a["diff_pct"] for a in alts] == [-0.07, 0.05]


def test_alternatives_are_sorted_cheapest_first_and_diffs_are_consistent(data):
    by_num = funds_by_number(data["funds"])
    for f in data["funds"]["funds"]:
        alts = alternatives(f["tase_number"], data["funds"])
        costs = [a["cost_pct"] for a in alts]
        assert costs == sorted(costs)
        for a in alts:
            assert a["tase_number"] != f["tase_number"]
            assert by_num[a["tase_number"]]["peer_group"] == f["peer_group"]
            assert a["diff_pct"] == pytest.approx(a["cost_pct"] - total_cost_pct(f), abs=1e-9)


def test_every_default_fund_in_every_template_has_an_alternative(data):
    """בכל מבנה, בגרסת ברירת המחדל, לכל קרן מנייתית יש חלופה להשוואת מחיר."""
    for t in data["portfolios"]["templates"]:
        p = build_portfolio(t["id"], 70, data["portfolios"])
        for line in p["lines"]:
            if line["fund"] and line["slot"] != "bond":
                assert alternatives(line["fund"], data["funds"]), line


def test_alternatives_unknown_fund_raises(data):
    with pytest.raises(ValueError):
        alternatives("0000000", data["funds"])


# ---------- סטטיסטיקה וקלט שגוי ----------

def test_stats_for_single_fund_match_fund_data(data):
    p = build_portfolio("olami-ehad", 100, data["portfolios"])
    assert portfolio_stats(p["lines"], data["funds"]) == {
        "covered_weight": 100, "weighted_cost_pct": 0.15, "us_share_pct": 62.0}


def test_stats_us_share_ignores_bonds_and_empty_slots(data):
    p = build_portfolio("olami-ve-agach", 60, data["portfolios"])
    s = portfolio_stats(p["lines"], data["funds"])
    assert s["us_share_pct"] == 62.0
    assert s["weighted_cost_pct"] == 0.13


def test_zero_equity(data):
    p = build_portfolio("triathlon", 0, data["portfolios"])
    assert [(l["slot"], l["weight"]) for l in p["lines"]] == [("solid", 100)]
    p2 = build_portfolio("olami-ve-agach", 0, data["portfolios"])
    assert [(l["slot"], l["fund"], l["weight"]) for l in p2["lines"]] == [("bond", "1159102", 100)]


@pytest.mark.parametrize("template,equity,options", [
    ("nope", 50, {}),
    ("shlosha-ezorim", 50, {}),
    ("triathlon", 101, {}),
    ("triathlon", -1, {}),
    ("triathlon", 50.5, {}),
    ("triathlon", True, {}),
    ("triathlon", 50, {"sp_variant": "leveraged"}),
    ("triathlon", 50, {"bond_variant": "global_agg"}),
    ("olami-ehad", 50, {"global_fund": "0000000"}),
    ("olami-ehad", 50, {"sp_variant": "equal"}),
])
def test_bad_input_raises(data, template, equity, options):
    with pytest.raises(ValueError):
        build_portfolio(template, equity, data["portfolios"], options)
