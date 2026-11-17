"""בדיקות לאיזון, לבדיקת תיק קיים ולמחשבון דמי הניהול."""
import pytest

from engine import build_portfolio, checkup, fee_drag, rebalance, total_cost_pct, funds_by_number


def test_total_cost_adds_swap_fee(data):
    by_num = funds_by_number(data["funds"])
    assert total_cost_pct(by_num["1159250"]) == 0.07
    assert total_cost_pct(by_num["1183441"]) == 0.12


def test_rebalance_targets_and_deltas(data):
    target = build_portfolio("shlosha-ezorim", 100, 10, data["portfolios"])
    rows = rebalance({"1159250": 70000, "1159094": 20000, "1159169": 10000}, target["lines"])
    assert [(r["key"], r["target"], r["delta"]) for r in rows] == [
        ("1159250", 60000.0, -10000.0), ("1159094", 25000.0, 5000.0), ("1159169", 15000.0, 5000.0)]
    assert sum(r["delta"] for r in rows) == 0


def test_rebalance_with_deposit_sums_to_deposit(data):
    target = build_portfolio("shlosha-ezorim", 100, 10, data["portfolios"])
    rows = rebalance({"1159250": 70000, "1159094": 20000, "1159169": 10000}, target["lines"], deposit=5000)
    assert round(sum(r["delta"] for r in rows), 2) == 5000
    assert round(sum(r["target"] for r in rows), 2) == 105000


def test_rebalance_from_empty_portfolio_follows_weights(data):
    target = build_portfolio("olami-plus-mitpatchim", 100, 10, data["portfolios"])
    rows = rebalance({}, target["lines"], deposit=10000)
    assert [r["delta"] for r in rows] == [8500.0, 1500.0]


def test_rebalance_handles_solid_slot_by_slot_name(data):
    target = build_portfolio("olami-ehad", 70, 10, data["portfolios"])
    rows = rebalance({"1209220": 50000, "solid": 50000}, target["lines"])
    assert {r["key"]: r["delta"] for r in rows} == {"1209220": 20000.0, "solid": -20000.0}


def test_rebalance_rejects_negative_values(data):
    target = build_portfolio("olami-ehad", 100, 10, data["portfolios"])
    with pytest.raises(ValueError):
        rebalance({"1209220": -1}, target["lines"])
    with pytest.raises(ValueError):
        rebalance({"1209220": 1}, target["lines"], deposit=-5)


def test_checkup_weights_cost_and_us_share(data):
    r = checkup({"1159250": 50000, "1159094": 50000}, data["funds"])
    assert r["total"] == 100000
    assert [row["weight_pct"] for row in r["rows"]] == [50.0, 50.0]
    assert r["weighted_cost_pct"] == 0.095
    assert r["us_share_pct"] == 50.0
    assert r["warnings"] == []


def test_checkup_flags_us_and_tech_concentration(data):
    r = checkup({"1159250": 60000, "1159243": 40000}, data["funds"])
    assert any("80 אחוז" in w for w in r["warnings"])
    assert any("נאסדק" in w for w in r["warnings"])


def test_checkup_flags_duplicate_index(data):
    r = checkup({"1159250": 50000, "1183441": 50000}, data["funds"])
    assert any("אותו מדד" in w for w in r["warnings"])
    assert r["synthetic_weight_pct"] == 50.0


def test_checkup_flags_sector_overweight(data):
    r = checkup({"1209220": 80000, "1248376": 20000}, data["funds"])
    assert any("ענף או מדינה" in w for w in r["warnings"])


def test_checkup_reports_unknown_fund_and_excludes_it(data):
    r = checkup({"1209220": 90000, "5129275": 10000}, data["funds"])
    assert any("5129275" in w for w in r["warnings"])
    assert r["known_weight_pct"] == 90.0
    assert r["weighted_cost_pct"] == 0.15


def test_checkup_rejects_empty_and_negative(data):
    with pytest.raises(ValueError):
        checkup({}, data["funds"])
    with pytest.raises(ValueError):
        checkup({"1209220": -5}, data["funds"])


def test_fee_drag_zero_fee_loses_nothing():
    r = fee_drag(10000, 1000, 10, 6, 0)
    assert r["lost_to_fees"] == 0
    assert r["deposited"] == 130000


def test_fee_drag_matches_closed_form_for_lump_sum():
    r = fee_drag(100000, 0, 20, 7, 0.5)
    assert r["without_fee"] == pytest.approx(100000 * 1.07 ** 20, abs=0.05)
    assert r["with_fee"] == pytest.approx(100000 * 1.065 ** 20, abs=0.05)


def test_fee_drag_higher_fee_costs_more():
    cheap = fee_drag(0, 2000, 20, 7, 0.07)
    pricey = fee_drag(0, 2000, 20, 7, 0.8)
    assert pricey["lost_to_fees"] > cheap["lost_to_fees"] > 0
    assert pricey["with_fee"] < cheap["with_fee"]


def test_fee_drag_rejects_bad_input():
    for args in [(0, 100, 0, 7, 0.1), (-1, 100, 10, 7, 0.1), (0, -1, 10, 7, 0.1), (0, 100, 10, 7, -0.1)]:
        with pytest.raises(ValueError):
            fee_drag(*args)
