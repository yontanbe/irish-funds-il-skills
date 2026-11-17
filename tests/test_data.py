"""בדיקות תקינות לקובצי הדאטה."""
import re
from datetime import date

REQUIRED = {"tase_number", "name", "issuer", "index", "category", "replication", "accumulating",
            "fee_pct", "extra_fee_pct", "fee_range", "tax_link", "us_share", "confidence", "notes", "sources"}
CATEGORIES = {"us_large", "us_equal_weight", "us_tech", "us_small", "global_all", "global_developed",
              "emerging", "europe", "sector", "country"}


def test_meta_has_valid_date_and_note(data):
    meta = data["funds"]["meta"]
    date.fromisoformat(meta["checked_at"])
    assert "לאמת" in meta["note"]


def test_every_fund_has_all_fields(data):
    for f in data["funds"]["funds"]:
        assert REQUIRED <= set(f), f["name"]


def test_tase_numbers_are_unique_seven_digits(data):
    numbers = [f["tase_number"] for f in data["funds"]["funds"]]
    assert len(numbers) == len(set(numbers))
    assert all(re.fullmatch(r"\d{7}", n) for n in numbers)


def test_field_values_are_in_allowed_sets(data):
    for f in data["funds"]["funds"]:
        assert f["category"] in CATEGORIES
        assert f["replication"] in {"physical", "synthetic"}
        assert f["tax_link"] in {"cpi", "usd", "unknown"}
        assert f["confidence"] in {"high", "medium"}
        assert f["issuer"] in {"iShares", "Invesco"}
        assert f["accumulating"] is True
        assert 0.0 <= f["us_share"] <= 1.0


def test_fees_are_sane_and_inside_reported_range(data):
    for f in data["funds"]["funds"]:
        low, high = f["fee_range"]
        assert 0 < low <= high < 1.0, f["name"]
        assert low <= f["fee_pct"] <= high, f["name"]
        assert 0 <= f["extra_fee_pct"] < 0.5
        if f["replication"] == "physical":
            assert f["extra_fee_pct"] == 0, "לקרן פיזית אין עמלת SWAP"


def test_conflicting_fees_are_explained_in_notes(data):
    for f in data["funds"]["funds"]:
        if f["fee_range"][0] != f["fee_range"][1]:
            assert "חלוקים" in f["notes"], f["name"]


def test_every_fund_has_https_sources(data):
    for f in data["funds"]["funds"]:
        assert f["sources"], f["name"]
        assert all(s.startswith("https://") for s in f["sources"])


def test_core_indices_are_covered(data):
    cats = {f["category"] for f in data["funds"]["funds"]}
    assert {"us_large", "us_equal_weight", "us_tech", "global_all", "emerging", "europe"} <= cats


def test_questionnaire_structure(data):
    q = data["questionnaire"]
    assert len(q["questions"]) == 7
    ids = [x["id"] for x in q["questions"]]
    assert len(ids) == len(set(ids))
    for question in q["questions"]:
        assert question["text"].endswith("?")
        assert question["help"]
        assert 3 <= len(question["options"]) <= 5
        points = [o["points"] for o in question["options"]]
        assert points == sorted(points), "התשובות מסודרות מהזהירה לנועזת"
        assert len({o["id"] for o in question["options"]}) == len(question["options"])


def test_profiles_are_ascending(data):
    profiles = data["questionnaire"]["profiles"]
    assert profiles[0]["min_pct"] == 0
    for a, b in zip(profiles, profiles[1:]):
        assert a["min_pct"] < b["min_pct"]
        assert a["equity_pct"] < b["equity_pct"]
        assert a["tech_pct_of_equity"] <= b["tech_pct_of_equity"]
    assert all(p["tech_pct_of_equity"] % 5 == 0 for p in profiles)
    assert profiles[-1]["equity_pct"] == 100


def test_caps_and_warnings_point_to_real_options(data):
    q = data["questionnaire"]
    options = {x["id"]: {o["id"] for o in x["options"]} for x in q["questions"]}
    for rule in q["caps"] + q["warnings"]:
        assert rule["option"] in options[rule["question"]]
        assert rule["warning"]


def test_templates_reference_existing_funds(data):
    numbers = {f["tase_number"] for f in data["funds"]["funds"]}
    for t in data["portfolios"]["templates"]:
        for leg in t.get("legs", []):
            assert leg["fund"] in numbers
        for number in t.get("funds", {}).values():
            assert number in numbers
        if t["id"] == "olami-ehad":
            assert set(t["options"]["global_fund"]["choices"]) <= numbers


def test_fixed_templates_sum_to_100(data):
    for t in data["portfolios"]["templates"]:
        if "legs" in t:
            assert sum(l["weight"] for l in t["legs"]) == 100
    tri = [t for t in data["portfolios"]["templates"] if t["id"] == "triathlon"][0]
    assert sum(tri["ex_us_split"].values()) == 100


def test_option_defaults_are_valid_choices(data):
    for t in data["portfolios"]["templates"]:
        for spec in t.get("options", {}).values():
            assert spec["default"] in spec["choices"]
