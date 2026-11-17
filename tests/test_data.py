"""בדיקות תקינות לקובצי הדאטה."""
import re
from datetime import date

REQUIRED = {"tase_number", "name", "issuer", "index", "category", "replication", "accumulating",
            "fee_pct", "extra_fee_pct", "fee_range", "tax_link", "us_share", "confidence", "notes", "sources",
            "asset_class", "peer_group", "isin", "yahoo_ticker", "ticker_confidence"}
CATEGORIES = {"us_large", "us_equal_weight", "us_tech", "us_small", "us_sector", "global_all", "global_developed",
              "emerging", "europe", "sector", "country", "thematic",
              "bond_global", "bond_us_gov", "bond_corp", "bond_em"}


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
        assert f["replication"] in {"physical", "synthetic", "unknown"}
        assert f["asset_class"] in {"equity", "bond"}
        assert (f["asset_class"] == "bond") == f["category"].startswith("bond_")
        assert f["tax_link"] in {"cpi", "usd", "unknown"}
        assert f["confidence"] in {"high", "medium"}
        assert f["issuer"] in {"iShares", "Invesco"}
        assert f["accumulating"] is True
        assert f["us_share"] is None or 0.0 <= f["us_share"] <= 1.0
        if f["asset_class"] == "bond":
            assert f["us_share"] is None
        if f["replication"] == "unknown":
            assert "לא אומתה" in f["notes"]


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
    assert {"us_large", "us_equal_weight", "us_tech", "us_sector", "global_all", "emerging", "europe", "bond_global"} <= cats


def test_full_coverage_of_both_issuers(data):
    funds = data["funds"]["funds"]
    assert len(funds) == 43
    assert sum(f["issuer"] == "iShares" for f in funds) == 26
    assert sum(f["issuer"] == "Invesco" for f in funds) == 17
    assert sum(f["asset_class"] == "bond" for f in funds) == 11


def test_isin_and_ticker_fields_are_well_formed(data):
    import re as _re
    for f in data["funds"]["funds"]:
        assert f["isin"] is None or _re.fullmatch(r"IE[0-9A-Z]{10}", f["isin"])
        assert (f["yahoo_ticker"] is None) == (f["ticker_confidence"] is None)
        assert f["ticker_confidence"] in {None, "verified", "likely"}


def test_main_indices_have_both_issuers_to_compare(data):
    """לכל מדד מרכזי יש לפחות שתי קרנות, כדי שתמיד אפשר להציג השוואת מחיר."""
    groups = {}
    for f in data["funds"]["funds"]:
        groups.setdefault(f["peer_group"], set()).add(f["issuer"])
    for group in ["sp500", "nasdaq100", "global_all", "us_tech_sector", "emerging", "europe"]:
        assert groups[group] == {"iShares", "Invesco"}, group


def test_non_irish_references_are_marked(data):
    refs = data["funds"]["non_irish_references"]
    assert refs and all("לא אירית" in r["note"] for r in refs)
    irish = {f["tase_number"] for f in data["funds"]["funds"]}
    assert not irish & {r["tase_number"] for r in refs}


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
    assert profiles[-1]["equity_pct"] == 100


def test_caps_and_warnings_point_to_real_options(data):
    q = data["questionnaire"]
    options = {x["id"]: {o["id"] for o in x["options"]} for x in q["questions"]}
    for rule in q["caps"] + q["warnings"]:
        assert rule["option"] in options[rule["question"]]
        assert rule["warning"]


def test_templates_are_the_three_requested_structures(data):
    t = data["portfolios"]["templates"]
    assert [(x["number"], x["id"]) for x in t] == [(1, "olami-ehad"), (2, "olami-ve-agach"), (3, "triathlon")]


def test_templates_reference_existing_funds(data):
    numbers = {f["tase_number"] for f in data["funds"]["funds"]}
    by_num = {f["tase_number"]: f for f in data["funds"]["funds"]}
    for t in data["portfolios"]["templates"]:
        for number in t.get("funds", {}).values():
            assert number in numbers
        if "global_fund" in t.get("options", {}):
            assert set(t["options"]["global_fund"]["choices"]) <= numbers
    two = data["portfolios"]["templates"][1]
    assert by_num[two["bond_fund"]]["category"] == "bond_global"
    tri = data["portfolios"]["templates"][2]
    assert sum(tri["ex_us_split"].values()) == 100
    for key in tri["options"]["tech_variant"]["choices"]:
        assert by_num[tri["funds"][key]]["peer_group"] in {"us_tech_sector", "nasdaq100"}


def test_every_slot_explains_itself(data):
    for slot in data["portfolios"]["slots"].values():
        assert slot["label"] and "בוחרים לבד" in slot["note"]


def test_option_defaults_are_valid_choices(data):
    for t in data["portfolios"]["templates"]:
        for spec in t.get("options", {}).values():
            assert spec["default"] in spec["choices"]
