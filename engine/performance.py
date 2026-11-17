"""ביצועי הקרנות: מביא מחירים עדכניים בכל הרצה ומחשב תשואות.

הרצה:
  python3 -m engine.performance                    כל הקרנות, בשקלים
  python3 -m engine.performance --numbers 1159250 1183441
  python3 -m engine.performance --group sp500 --currency native
  python3 -m engine.performance --json

מקור המחירים: Yahoo Finance, מחיר חודשי מתואם של יחידת הקרן בבורסה אירופית.
המחירים לא נשמרים בריפו. כל הרצה מביאה מחדש.
תשואות עבר אינן מבטיחות תשואות עתיד.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import core

UA = "Mozilla/5.0 (compatible; irish-funds-il-skills; +https://github.com/yontanbe/irish-funds-il-skills)"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=max&interval=1mo"
SEARCH = "https://query2.finance.yahoo.com/v1/finance/search?q={q}&quotesCount=10&newsCount=0"
PERIODS = [1, 3, 5, 10]


# ---------- חישוב טהור ----------

def to_month_series(points: list) -> list:
    """מקבל רשימה של (תאריך, מחיר) ומחזיר נקודה אחת לכל חודש: האחרונה באותו חודש."""
    months: dict = {}
    for when, price in points:
        if price is None or price <= 0:
            continue
        months[(when.year, when.month)] = float(price)
    return sorted(months.items())


def convert(series: list, fx: list) -> list:
    """מכפיל מחיר בשער המטבע של אותו חודש. חודשים בלי שער נשמטים."""
    rates = dict(fx)
    return [(m, p * rates[m]) for m, p in series if m in rates]


def trailing(series: list, years: int) -> dict | None:
    """תשואה מצטברת ושנתית ממוצעת ל-years השנים האחרונות. None אם אין מספיק היסטוריה."""
    if not series:
        return None
    (ly, lm), last = series[-1]
    start_key = (ly - years, lm)
    lookup = dict(series)
    if start_key not in lookup:
        return None
    total = last / lookup[start_key] - 1
    return {"cumulative_pct": round(total * 100, 2),
            "annualized_pct": round(((1 + total) ** (1 / years) - 1) * 100, 2)}


def calendar_years(series: list) -> dict:
    """תשואה לכל שנה קלנדרית מלאה, ולשנה הנוכחית עד החודש האחרון (מסומנת YTD)."""
    year_end: dict = {}
    for (y, m), p in series:
        year_end[y] = (m, p)
    out: dict = {}
    years = sorted(year_end)
    for prev, cur in zip(years, years[1:]):
        if cur != prev + 1 or year_end[prev][0] != 12:
            continue
        label = str(cur) if year_end[cur][0] == 12 else f"{cur} YTD"
        out[label] = round((year_end[cur][1] / year_end[prev][1] - 1) * 100, 2)
    return out


def summarize(series: list) -> dict:
    result = {"as_of": f"{series[-1][0][0]}-{series[-1][0][1]:02d}" if series else None,
              "months_of_history": len(series), "years": calendar_years(series)}
    for n in PERIODS:
        result[f"{n}y"] = trailing(series, n)
    return result


# ---------- הבאת נתונים ----------

def http_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_chart(payload: dict) -> tuple[list, str]:
    """מפרק תשובת chart של Yahoo לרשימת (תאריך, מחיר מתואם) ולמטבע."""
    chart = payload.get("chart") or {}
    if chart.get("error") or not chart.get("result"):
        raise ValueError("אין נתוני מחיר לסימול הזה")
    res = chart["result"][0]
    stamps = res.get("timestamp") or []
    ind = res.get("indicators", {})
    adj = (ind.get("adjclose") or [{}])[0].get("adjclose")
    prices = adj or (ind.get("quote") or [{}])[0].get("close") or []
    points = [(datetime.fromtimestamp(t, tz=timezone.utc), p) for t, p in zip(stamps, prices)]
    currency = (res.get("meta") or {}).get("currency") or "USD"
    return points, currency


def resolve_symbol(fund: dict, fetch=None) -> tuple[str, str]:
    """מחזיר (סימול, רמת ודאות). קודם מהדאטה, אחר כך חיפוש לפי ISIN, ובסוף לפי שם."""
    fetch = fetch or http_json
    if fund.get("yahoo_ticker"):
        return fund["yahoo_ticker"], fund.get("ticker_confidence") or "likely"
    for query, level in ((fund.get("isin"), "isin"), (fund["name"], "name_search")):
        if not query:
            continue
        data = fetch(SEARCH.format(q=urllib.parse.quote(query)))
        quotes = [q for q in data.get("quotes", []) if q.get("quoteType") in ("ETF", "MUTUALFUND", "EQUITY")]
        if quotes:
            preferred = [q for q in quotes if q["symbol"].endswith(".L")] or quotes
            return preferred[0]["symbol"], level
    raise ValueError("לא נמצא סימול")


def fx_symbol(currency: str) -> str | None:
    cur = currency.upper()
    if cur == "ILS":
        return None
    if cur in ("GBP", "GBX") or currency == "GBp":
        return "GBPILS=X"
    return f"{cur}ILS=X"


def fund_performance(fund: dict, currency: str = "ils", fetch=None, fx_cache: dict | None = None) -> dict:
    """ביצועי קרן אחת. לא זורק שגיאה: במקרה של כשל מחזיר שורה עם error."""
    fetch = fetch or http_json
    row = {"tase_number": fund["tase_number"], "name": fund["name"], "peer_group": fund["peer_group"]}
    fx_cache = fx_cache if fx_cache is not None else {}
    try:
        symbol, level = resolve_symbol(fund, fetch)
        points, native = parse_chart(fetch(CHART.format(symbol=urllib.parse.quote(symbol))))
        series = to_month_series(points)
        shown = native
        if currency == "ils":
            pair = fx_symbol(native)
            if pair:
                if pair not in fx_cache:
                    fx_points, _ = parse_chart(fetch(CHART.format(symbol=urllib.parse.quote(pair))))
                    fx_cache[pair] = to_month_series(fx_points)
                series = convert(series, fx_cache[pair])
            shown = "ILS"
        if len(series) < 2:
            raise ValueError("אין מספיק היסטוריה")
        row.update(symbol=symbol, symbol_confidence=level, currency=shown, **summarize(series))
    except Exception as exc:  # כל כשל ברשת או בנתונים הופך לשורה מסומנת ולא מפיל את הדוח
        row["error"] = str(exc) or exc.__class__.__name__
    return row


def report(funds: list, currency: str = "ils", fetch=None) -> list:
    fx_cache: dict = {}
    return [fund_performance(f, currency, fetch, fx_cache) for f in funds]


# ---------- הצגה ----------

def _cell(value) -> str:
    return "אין" if value is None else f"{value:+.1f}%"


def to_markdown(rows: list) -> str:
    ok = [r for r in rows if "error" not in r]
    bad = [r for r in rows if "error" in r]
    lines = []
    if ok:
        as_of = max(r["as_of"] for r in ok)
        lines += [f"## תשואה מצטברת, נכון ל-{as_of}, מטבע: {ok[0]['currency']}", "",
                  "| קרן | מספר נייר | שנה | 3 שנים | 5 שנים | 10 שנים |", "|---|---|---|---|---|---|"]
        for r in ok:
            cells = [_cell((r[f"{n}y"] or {}).get("cumulative_pct")) for n in PERIODS]
            lines.append(f"| {r['name']} | {r['tase_number']} | " + " | ".join(cells) + " |")
        lines += ["", "## תשואה שנתית ממוצעת", "",
                  "| קרן | מספר נייר | 3 שנים | 5 שנים | 10 שנים |", "|---|---|---|---|---|"]
        for r in ok:
            cells = [_cell((r[f"{n}y"] or {}).get("annualized_pct")) for n in (3, 5, 10)]
            lines.append(f"| {r['name']} | {r['tase_number']} | " + " | ".join(cells) + " |")
        labels = sorted({y for r in ok for y in r["years"]}, key=lambda s: s.split()[0])[-6:]
        if labels:
            lines += ["", "## שנה מול שנה", "",
                      "| קרן | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
            for r in ok:
                lines.append(f"| {r['name']} | " + " | ".join(_cell(r["years"].get(y)) for y in labels) + " |")
        unverified = [r for r in ok if r["symbol_confidence"] != "verified"]
        if unverified:
            lines += ["", "סימולים שלא אומתו ידנית, כדאי לוודא שזו הקרן הנכונה: "
                      + ", ".join(f"{r['tase_number']} לפי {r['symbol']}" for r in unverified)]
    if bad:
        lines += ["", "לא התקבלו נתונים עבור: " + ", ".join(f"{r['tase_number']} ({r['error']})" for r in bad)]
    lines += ["", "המחירים הם של יחידת הקרן בבורסה אירופית, לא של המסחר בתל אביב. אין: אין מספיק היסטוריה לתקופה.",
              "תשואות עבר אינן מבטיחות תשואות עתיד. " + core.DISCLAIMER]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="irish-funds-performance", description="ביצועי קרנות איריות, נתונים טריים בכל הרצה")
    parser.add_argument("--numbers", nargs="*", help="מספרי נייר. ברירת מחדל: כל הקרנות")
    parser.add_argument("--group", help="קבוצת השוואה, למשל sp500 או global_all")
    parser.add_argument("--currency", choices=["ils", "native"], default="ils")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    funds = core.load_data()["funds"]["funds"]
    if args.numbers:
        known = {f["tase_number"] for f in funds}
        missing = [n for n in args.numbers if n not in known]
        if missing:
            print("מספרי נייר שלא בדאטה: " + ", ".join(missing), file=sys.stderr)
            return 1
        funds = [f for f in funds if f["tase_number"] in args.numbers]
    if args.group:
        funds = [f for f in funds if f["peer_group"] == args.group]
        if not funds:
            print(f"אין קרנות בקבוצה {args.group}", file=sys.stderr)
            return 1
    rows = report(funds, args.currency)
    print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else to_markdown(rows))
    return 0 if any("error" not in r for r in rows) else 2


if __name__ == "__main__":
    sys.exit(main())
