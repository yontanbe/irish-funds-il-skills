"""מנוע החישוב של irish-funds-il-skills.

ספריית תקן בלבד, בלי התקנות. כל הפונקציות טהורות: מקבלות נתונים ומחזירות נתונים.
הכלי נועד למחקר וללימוד בלבד ואינו ייעוץ השקעות.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DISCLAIMER = (
    "הכלי נועד למחקר וללימוד עצמי בלבד. הוא אינו ייעוץ השקעות, אינו שיווק השקעות "
    "ואינו תחליף לייעוץ שמתחשב בנתונים ובצרכים של כל אדם. כל החלטה היא באחריותכם."
)


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


def load_data() -> dict:
    """טוען את שלושת קובצי הדאטה למילון אחד."""
    return {
        "funds": _load("funds.json"),
        "questionnaire": _load("questionnaire.json"),
        "portfolios": _load("portfolios.json"),
    }


def funds_by_number(funds_data: dict) -> dict:
    return {f["tase_number"]: f for f in funds_data["funds"]}


def total_cost_pct(fund: dict) -> float:
    """עלות שנתית כוללת באחוזים: דמי ניהול ועוד עמלות נוספות כמו SWAP."""
    return round(fund["fee_pct"] + fund["extra_fee_pct"], 4)


# ---------- שאלון סיכון ----------

def score_risk(answers: dict, questionnaire: dict) -> dict:
    """מחשב פרופיל סיכון מתשובות השאלון.

    answers: מילון של מזהה שאלה למזהה תשובה. חובה לענות על כל השאלות.
    """
    score = 0
    max_score = 0
    for q in questionnaire["questions"]:
        if q["id"] not in answers:
            raise ValueError(f"חסרה תשובה לשאלה: {q['id']}")
        chosen = [o for o in q["options"] if o["id"] == answers[q["id"]]]
        if not chosen:
            raise ValueError(f"תשובה לא מוכרת לשאלה {q['id']}: {answers[q['id']]}")
        score += chosen[0]["points"]
        max_score += max(o["points"] for o in q["options"])

    pct = score * 100 // max_score
    profile = questionnaire["profiles"][0]
    for p in questionnaire["profiles"]:
        if pct >= p["min_pct"]:
            profile = p

    equity_pct = profile["equity_pct"]
    warnings = []
    for cap in questionnaire["caps"]:
        if answers[cap["question"]] == cap["option"] and equity_pct > cap["max_equity_pct"]:
            equity_pct = cap["max_equity_pct"]
            warnings.append(cap["warning"])
    for w in questionnaire["warnings"]:
        if answers[w["question"]] == w["option"]:
            warnings.append(w["warning"])

    return {
        "score": score,
        "max_score": max_score,
        "pct": pct,
        "profile_id": profile["id"],
        "profile_name": profile["name"],
        "equity_pct": equity_pct,
        "tech_pct_of_equity": profile["tech_pct_of_equity"],
        "warnings": warnings,
    }


# ---------- בניית תיק ----------

def _template(portfolios: dict, template_id: str) -> dict:
    for t in portfolios["templates"]:
        if t["id"] == template_id:
            return t
    raise ValueError(f"תבנית לא מוכרת: {template_id}")


def _option(template: dict, options: dict, key: str) -> str:
    spec = template["options"][key]
    value = (options or {}).get(key, spec["default"])
    if value not in spec["choices"]:
        raise ValueError(f"ערך לא מוכר לאפשרות {key}: {value}")
    return value


def _equity_legs(template: dict, tech_pct: int, options: dict) -> tuple[list, list]:
    """מחזיר רגליים מנייתיות במשקל של רבעי אחוז (סכום 400) והערות."""
    notes = []
    tid = template["id"]
    if tid == "olami-ehad":
        fund = _option(template, options, "global_fund")
        return [{"slot": "global", "label": "עולמי", "fund": fund, "w4": 400}], notes

    if tid == "triathlon":
        if tech_pct % 5 != 0 or not 0 <= tech_pct <= 50:
            raise ValueError("משקל הטכנולוגיה חייב להיות כפולה של 5 בין 0 ל-50")
        f = template["funds"]
        rest = 100 - tech_pct
        legs = [{"slot": "tech", "label": "טכנולוגיה, נאסדק 100", "fund": f["tech"], "w4": 4 * tech_pct}]

        sp = _option(template, options, "sp_variant")
        if sp == "regular":
            legs.append({"slot": "sp", "label": "S&P 500 רגיל", "fund": f["sp_regular"], "w4": 2 * rest})
        elif sp == "equal":
            legs.append({"slot": "sp", "label": "S&P 500 משקל שווה", "fund": f["sp_equal"], "w4": 2 * rest})
        elif sp == "hedged":
            h = template["hedged_slot"]
            legs.append({"slot": h["id"], "label": h["label"], "fund": None, "w4": 2 * rest})
            notes.append(h["note"])
        else:  # combined
            legs.append({"slot": "sp", "label": "S&P 500 רגיל", "fund": f["sp_regular"], "w4": rest})
            legs.append({"slot": "sp_equal", "label": "S&P 500 משקל שווה", "fund": f["sp_equal"], "w4": rest})

        gl = _option(template, options, "global_variant")
        if gl == "all":
            legs.append({"slot": "global", "label": "כל העולם", "fund": f["global_all"], "w4": 2 * rest})
        else:
            split = template["ex_us_split"]
            legs.append({"slot": "europe", "label": "אירופה", "fund": f["ex_us_europe"],
                         "w4": 2 * rest * split["europe"] // 100})
            legs.append({"slot": "emerging", "label": "שווקים מתפתחים", "fund": f["ex_us_emerging"],
                         "w4": 2 * rest * split["emerging"] // 100})
            notes.append(template["ex_us_note"])
        return legs, notes

    legs = [{"slot": l["slot"], "label": l["label"], "fund": l["fund"], "w4": 4 * l["weight"]}
            for l in template["legs"]]
    return legs, notes


def build_portfolio(template_id: str, equity_pct: int, tech_pct: int, portfolios: dict,
                    options: dict | None = None) -> dict:
    """בונה תיק לדוגמה. המשקלים הם אחוזים שלמים שסכומם תמיד 100."""
    if not isinstance(equity_pct, int) or not 0 <= equity_pct <= 100:
        raise ValueError("החלק המנייתי חייב להיות מספר שלם בין 0 ל-100")
    template = _template(portfolios, template_id)
    legs, notes = _equity_legs(template, tech_pct, options or {})
    assert sum(l["w4"] for l in legs) == 400, "משקלי הרגליים חייבים להסתכם ל-100 אחוז"

    # עיגול בשיטת השארית הגדולה, בחשבון שלמים בלבד
    raw = [l["w4"] * equity_pct for l in legs]
    weights = [r // 400 for r in raw]
    leftover = equity_pct - sum(weights)
    order = sorted(range(len(legs)), key=lambda i: (-(raw[i] % 400), i))
    for i in order[:leftover]:
        weights[i] += 1

    lines = [{"slot": l["slot"], "label": l["label"], "fund": l["fund"], "weight": w}
             for l, w in zip(legs, weights) if w > 0]
    solid = 100 - equity_pct
    if solid > 0:
        s = portfolios["solid_slot"]
        lines.append({"slot": s["id"], "label": s["label"], "fund": None, "weight": solid})
        notes.append(s["note"])
    return {"template_id": template_id, "template_name": template["name"],
            "equity_pct": equity_pct, "lines": lines, "notes": notes}


def portfolio_stats(lines: list, funds_data: dict) -> dict:
    """עלות משוקללת וחשיפה לארה"ב, רק על השורות שיש להן קרן מהדאטה."""
    by_num = funds_by_number(funds_data)
    covered = 0
    cost = 0.0
    us = 0.0
    for line in lines:
        fund = by_num.get(line["fund"]) if line["fund"] else None
        if not fund:
            continue
        covered += line["weight"]
        cost += line["weight"] * total_cost_pct(fund)
        us += line["weight"] * fund["us_share"]
    if covered == 0:
        return {"covered_weight": 0, "weighted_cost_pct": 0.0, "us_share_pct": 0.0}
    return {
        "covered_weight": covered,
        "weighted_cost_pct": round(cost / covered, 4),
        "us_share_pct": round(us / covered * 100, 1),
    }


# ---------- איזון ובדיקת תיק קיים ----------

def rebalance(holdings: dict, lines: list, deposit: float = 0.0) -> list:
    """כמה לקנות או למכור בכל שורה כדי לחזור למשקלי היעד.

    holdings: מילון של מפתח לסכום בשקלים. המפתח הוא מספר הקרן, או שם המשבצת
    כשאין קרן (למשל solid).
    """
    if deposit < 0:
        raise ValueError("הפקדה לא יכולה להיות שלילית")
    for key, amount in holdings.items():
        if amount < 0:
            raise ValueError(f"סכום שלילי עבור {key}")
    total = sum(holdings.values()) + deposit
    out = []
    for line in lines:
        key = line["fund"] or line["slot"]
        current = float(holdings.get(key, 0.0))
        target = round(total * line["weight"] / 100, 2)
        out.append({"key": key, "label": line["label"], "current": current,
                    "target": target, "delta": round(target - current, 2)})
    return out


def checkup(holdings: dict, funds_data: dict) -> dict:
    """בודק תיק קיים שהמשתמש הזין: משקלים, עלות, ריכוזיות וכפילויות."""
    by_num = funds_by_number(funds_data)
    for key, amount in holdings.items():
        if amount < 0:
            raise ValueError(f"סכום שלילי עבור {key}")
    total = sum(holdings.values())
    if total <= 0:
        raise ValueError("התיק ריק")

    rows, warnings, unknown = [], [], []
    cost = us = known = tech = satellite = synthetic = 0.0
    seen_index: dict = {}
    for key, amount in holdings.items():
        if amount == 0:
            continue
        weight = amount / total * 100
        fund = by_num.get(str(key))
        if not fund:
            unknown.append(str(key))
            rows.append({"key": str(key), "name": "לא בדאטה", "weight_pct": round(weight, 1)})
            continue
        known += weight
        cost += weight * total_cost_pct(fund)
        us += weight * fund["us_share"]
        if fund["category"] == "us_tech":
            tech += weight
        if fund["category"] in ("sector", "country"):
            satellite += weight
        if fund["replication"] == "synthetic":
            synthetic += weight
        seen_index.setdefault(fund["index"], []).append(fund["tase_number"])
        rows.append({"key": fund["tase_number"], "name": fund["name"], "weight_pct": round(weight, 1)})

    if unknown:
        warnings.append("ניירות שלא נמצאים בדאטה ולא נכללו בחישובים: " + ", ".join(unknown))
    if known and us / known > 0.8:
        warnings.append("יותר מ-80 אחוז מהחלק המוכר חשוף לארה\"ב. זו ריכוזיות במדינה אחת.")
    if tech > 30:
        warnings.append("יותר מ-30 אחוז בנאסדק 100. המדד חופף מאוד ל-S&P 500 ומגדיל תנודתיות.")
    if satellite > 10:
        warnings.append("יותר מ-10 אחוז בקרנות ענף או מדינה. אלה תוספות לתיק ולא בסיס.")
    for index, numbers in seen_index.items():
        if len(numbers) > 1:
            warnings.append(f"שתי קרנות על אותו מדד ({index}): {', '.join(numbers)}. אין בזה פיזור נוסף.")

    return {
        "total": round(total, 2),
        "rows": rows,
        "known_weight_pct": round(known, 1),
        "weighted_cost_pct": round(cost / known, 4) if known else 0.0,
        "us_share_pct": round(us / known * 100, 1) if known else 0.0,
        "synthetic_weight_pct": round(synthetic, 1),
        "warnings": warnings,
    }


# ---------- מחשבון דמי ניהול ----------

def fee_drag(initial: float, monthly: float, years: int, gross_return_pct: float, fee_pct: float) -> dict:
    """כמה כסף דמי הניהול אוכלים לאורך זמן. הנחת תשואה היא של המשתמש, לא תחזית."""
    if years <= 0 or initial < 0 or monthly < 0 or fee_pct < 0:
        raise ValueError("קלט לא תקין")

    def grow(annual_pct: float) -> float:
        rate = (1 + annual_pct / 100) ** (1 / 12) - 1
        value = initial
        for _ in range(years * 12):
            value = value * (1 + rate) + monthly
        return value

    without_fee = grow(gross_return_pct)
    with_fee = grow(gross_return_pct - fee_pct)
    return {
        "deposited": round(initial + monthly * years * 12, 2),
        "without_fee": round(without_fee, 2),
        "with_fee": round(with_fee, 2),
        "lost_to_fees": round(without_fee - with_fee, 2),
    }
