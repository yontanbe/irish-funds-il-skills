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
        "warnings": warnings,
    }


# ---------- בניית תיק ----------

UNIT = 1200  # משקלי הרגליים נמדדים ב-1/12 אחוז, כדי ששלישים וחצאים יהיו מספרים שלמים


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


def _slot_leg(portfolios: dict, slot_id: str, w: int, notes: list) -> dict:
    slot = portfolios["slots"][slot_id]
    notes.append(slot["note"])
    return {"slot": slot_id, "label": slot["label"], "fund": None, "w": w}


def _equity_legs(template: dict, portfolios: dict, options: dict) -> tuple[list, list]:
    """מחזיר את הרגליים המנייתיות (סכום המשקלים UNIT) והערות."""
    notes: list = []
    tid = template["id"]
    if tid in ("olami-ehad", "olami-ve-agach"):
        fund = _option(template, options, "global_fund")
        return [{"slot": "global", "label": "מניות עולם", "fund": fund, "w": UNIT}], notes

    if tid == "triathlon":
        f = template["funds"]
        third = UNIT // 3
        tech = _option(template, options, "tech_variant")
        legs = [{"slot": "tech", "label": "טכנולוגיה", "fund": f[tech], "w": third}]

        sp = _option(template, options, "sp_variant")
        if sp in ("regular_ishares", "regular_invesco"):
            legs.append({"slot": "sp", "label": "S&P 500 רגיל", "fund": f[sp], "w": third})
        elif sp == "equal":
            legs.append({"slot": "sp", "label": "S&P 500 משקל שווה", "fund": f["equal"], "w": third})
        elif sp == "combined":
            legs.append({"slot": "sp", "label": "S&P 500 רגיל", "fund": f["regular_ishares"], "w": third // 2})
            legs.append({"slot": "sp_equal", "label": "S&P 500 משקל שווה", "fund": f["equal"], "w": third // 2})
        elif sp == "value":
            legs.append(_slot_leg(portfolios, "value", third, notes))
        else:  # hedged
            legs.append(_slot_leg(portfolios, "sp_hedged", third, notes))

        gl = _option(template, options, "global_variant")
        if gl in ("all_invesco", "all_ishares"):
            legs.append({"slot": "global", "label": "כל העולם", "fund": f[gl], "w": third})
        else:
            split = template["ex_us_split"]
            legs.append({"slot": "europe", "label": "אירופה", "fund": f["ex_us_europe"],
                         "w": third * split["europe"] // 100})
            legs.append({"slot": "emerging", "label": "שווקים מתפתחים", "fund": f["ex_us_emerging"],
                         "w": third * split["emerging"] // 100})
            notes.append(template["ex_us_note"])
        notes.append(template["overlap_note"])
        return legs, notes

    raise ValueError(f"תבנית לא מוכרת: {tid}")


def build_portfolio(template_id: str, equity_pct: int, portfolios: dict, options: dict | None = None) -> dict:
    """בונה תיק לדוגמה. המשקלים הם אחוזים שלמים שסכומם תמיד 100."""
    if not isinstance(equity_pct, int) or isinstance(equity_pct, bool) or not 0 <= equity_pct <= 100:
        raise ValueError("החלק המנייתי חייב להיות מספר שלם בין 0 ל-100")
    template = _template(portfolios, template_id)
    options = options or {}
    for key in options:
        if key not in template.get("options", {}):
            raise ValueError(f"אפשרות לא מוכרת לתבנית הזו: {key}")
    legs, notes = _equity_legs(template, portfolios, options)
    assert sum(l["w"] for l in legs) == UNIT, "משקלי הרגליים חייבים להסתכם ל-100 אחוז"

    # עיגול בשיטת השארית הגדולה, בחשבון שלמים בלבד
    raw = [l["w"] * equity_pct for l in legs]
    weights = [r // UNIT for r in raw]
    leftover = equity_pct - sum(weights)
    order = sorted(range(len(legs)), key=lambda i: (-(raw[i] % UNIT), i))
    for i in order[:leftover]:
        weights[i] += 1

    lines = [{"slot": l["slot"], "label": l["label"], "fund": l["fund"], "weight": w}
             for l, w in zip(legs, weights) if w > 0]
    rest = 100 - equity_pct
    if template_id == "olami-ve-agach":
        bond = _option(template, options, "bond_variant")
        if rest == 0:
            notes.append(template["no_bond_note"])
        elif bond == "global_agg":
            lines.append({"slot": "bond", "label": "אגח עולמי כללי", "fund": template["bond_fund"], "weight": rest})
            notes.append(template["bond_note"])
        else:
            leg = _slot_leg(portfolios, "il_general_bond", 0, notes)
            lines.append({"slot": leg["slot"], "label": leg["label"], "fund": None, "weight": rest})
    elif rest > 0:
        leg = _slot_leg(portfolios, "solid", 0, notes)
        lines.append({"slot": leg["slot"], "label": leg["label"], "fund": None, "weight": rest})
    return {"template_id": template_id, "template_name": template["name"],
            "equity_pct": equity_pct, "lines": lines, "notes": notes}


def alternatives(fund_number: str, funds_data: dict) -> list:
    """קרנות אחרות על אותו סוג מדד, עם ההפרש בעלות השנתית מול הקרן שנבחרה.

    תמיד מציגים את זה למשתמש, כדי שיראה את הפער בין iShares ל-Invesco.
    """
    by_num = funds_by_number(funds_data)
    if fund_number not in by_num:
        raise ValueError(f"קרן לא בדאטה: {fund_number}")
    chosen = by_num[fund_number]
    base = total_cost_pct(chosen)
    out = []
    for f in funds_data["funds"]:
        if f["peer_group"] == chosen["peer_group"] and f["tase_number"] != fund_number:
            cost = total_cost_pct(f)
            out.append({"tase_number": f["tase_number"], "name": f["name"], "issuer": f["issuer"],
                        "index": f["index"], "replication": f["replication"], "cost_pct": cost,
                        "diff_pct": round(cost - base, 4)})
    return sorted(out, key=lambda r: (r["cost_pct"], r["tase_number"]))


def portfolio_stats(lines: list, funds_data: dict) -> dict:
    """עלות משוקללת על השורות שיש להן קרן, וחשיפה לארה"ב בתוך החלק המנייתי."""
    by_num = funds_by_number(funds_data)
    covered = 0
    cost = 0.0
    us = 0.0
    us_base = 0
    for line in lines:
        fund = by_num.get(line["fund"]) if line["fund"] else None
        if not fund:
            continue
        covered += line["weight"]
        cost += line["weight"] * total_cost_pct(fund)
        if fund["asset_class"] == "equity" and fund["us_share"] is not None:
            us_base += line["weight"]
            us += line["weight"] * fund["us_share"]
    return {
        "covered_weight": covered,
        "weighted_cost_pct": round(cost / covered, 4) if covered else 0.0,
        "us_share_pct": round(us / us_base * 100, 1) if us_base else 0.0,
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
    cost = us = us_base = known = tech = satellite = synthetic = bonds = 0.0
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
        if fund["asset_class"] == "bond":
            bonds += weight
        elif fund["us_share"] is not None:
            us_base += weight
            us += weight * fund["us_share"]
        if fund["peer_group"] in ("nasdaq100", "us_tech_sector", "semis"):
            tech += weight
        if fund["category"] in ("sector", "country", "thematic", "us_sector"):
            satellite += weight
        if fund["replication"] == "synthetic":
            synthetic += weight
        seen_index.setdefault(fund["peer_group"], []).append(fund["tase_number"])
        rows.append({"key": fund["tase_number"], "name": fund["name"], "weight_pct": round(weight, 1)})

    if unknown:
        warnings.append("ניירות שלא נמצאים בדאטה ולא נכללו בחישובים: " + ", ".join(unknown))
    if us_base and us / us_base > 0.8:
        warnings.append("יותר מ-80 אחוז מהחלק המנייתי המוכר חשוף לארה\"ב. זו ריכוזיות במדינה אחת.")
    if tech > 35:
        warnings.append("יותר מ-35 אחוז בקרנות טכנולוגיה. הן חופפות מאוד ל-S&P 500 ומגדילות תנודתיות.")
    if satellite - tech > 10:
        warnings.append("יותר מ-10 אחוז בקרנות ענף, מדינה או נושא שאינן טכנולוגיה. אלה תוספות לתיק ולא בסיס.")
    for group, numbers in seen_index.items():
        if len(numbers) > 1:
            warnings.append(f"שתי קרנות על אותו סוג מדד: {', '.join(numbers)}. אין בזה פיזור נוסף.")

    return {
        "total": round(total, 2),
        "rows": rows,
        "known_weight_pct": round(known, 1),
        "bond_weight_pct": round(bonds, 1),
        "weighted_cost_pct": round(cost / known, 4) if known else 0.0,
        "us_share_pct": round(us / us_base * 100, 1) if us_base else 0.0,
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
