"""ממשק שורת פקודה פשוט.

דוגמאות:
  python3 -m engine.cli funds
  python3 -m engine.cli quiz
  python3 -m engine.cli build --template triathlon --answers answers.json --sp equal --global ex_us
  python3 -m engine.cli checkup --holdings '{"1159250": 60000, "1159243": 40000}'
  python3 -m engine.cli fees --initial 0 --monthly 2000 --years 20 --return 7 --fee 0.8
"""
from __future__ import annotations

import argparse
import json
import sys

from . import core


def _print_portfolio(result: dict, data: dict) -> None:
    by_num = core.funds_by_number(data["funds"])
    print(f"\nתיק לדוגמה: {result['template_name']}")
    for line in result["lines"]:
        fund = by_num.get(line["fund"]) if line["fund"] else None
        tail = f"{fund['name']} | מספר נייר {fund['tase_number']}" if fund else "בוחרים לבד"
        print(f"  {line['weight']:>3}%  {line['label']}  |  {tail}")
    stats = core.portfolio_stats(result["lines"], data["funds"])
    if stats["covered_weight"]:
        print(f"\nעלות שנתית משוקללת על החלק המנייתי: {stats['weighted_cost_pct']}%")
        print(f"חשיפה משוערת לארה\"ב בחלק המנייתי: {stats['us_share_pct']}%")
    for note in result["notes"]:
        print(f"הערה: {note}")


def cmd_funds(args, data):
    for f in data["funds"]["funds"]:
        print(f"{f['tase_number']}  {f['name']}  |  {f['index']}  |  "
              f"עלות {core.total_cost_pct(f)}%  |  {'פיזית' if f['replication'] == 'physical' else 'סינתטית'}")
    print("\n" + data["funds"]["meta"]["note"])


def _ask(questionnaire: dict) -> dict:
    answers = {}
    for q in questionnaire["questions"]:
        print(f"\n{q['text']}\n({q['help']})")
        for i, o in enumerate(q["options"], 1):
            print(f"  {i}. {o['text']}")
        while True:
            raw = input("מספר התשובה: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(q["options"]):
                answers[q["id"]] = q["options"][int(raw) - 1]["id"]
                break
            print("נא להקליד מספר מהרשימה.")
    return answers


def _show_risk(risk: dict) -> None:
    print(f"\nפרופיל: {risk['profile_name']} | חלק מנייתי לדוגמה: {risk['equity_pct']}%")
    for w in risk["warnings"]:
        print(f"שימו לב: {w}")


def cmd_quiz(args, data):
    answers = _ask(data["questionnaire"])
    risk = core.score_risk(answers, data["questionnaire"])
    _show_risk(risk)
    for t in data["portfolios"]["templates"]:
        result = core.build_portfolio(t["id"], risk["equity_pct"], risk["tech_pct_of_equity"], data["portfolios"])
        _print_portfolio(result, data)


def cmd_build(args, data):
    with open(args.answers, encoding="utf-8") as fh:
        answers = json.load(fh)
    risk = core.score_risk(answers, data["questionnaire"])
    _show_risk(risk)
    options = {}
    if args.sp:
        options["sp_variant"] = args.sp
    if args.global_variant:
        options["global_variant"] = args.global_variant
    if args.global_fund:
        options["global_fund"] = args.global_fund
    result = core.build_portfolio(args.template, risk["equity_pct"], risk["tech_pct_of_equity"],
                                  data["portfolios"], options)
    _print_portfolio(result, data)


def cmd_checkup(args, data):
    holdings = {str(k): float(v) for k, v in json.loads(args.holdings).items()}
    result = core.checkup(holdings, data["funds"])
    for row in result["rows"]:
        print(f"  {row['weight_pct']:>5}%  {row['key']}  {row['name']}")
    print(f"\nעלות שנתית משוקללת: {result['weighted_cost_pct']}%")
    print(f"חשיפה משוערת לארה\"ב: {result['us_share_pct']}%")
    for w in result["warnings"]:
        print(f"שימו לב: {w}")


def cmd_fees(args, data):
    r = core.fee_drag(args.initial, args.monthly, args.years, args.ret, args.fee)
    print(f"הופקד: {r['deposited']:,.0f}")
    print(f"בלי דמי ניהול: {r['without_fee']:,.0f}")
    print(f"עם דמי ניהול של {args.fee}%: {r['with_fee']:,.0f}")
    print(f"ההפרש: {r['lost_to_fees']:,.0f}")
    print("זו הדגמה חשבונית לפי ההנחות שהזנתם ולא תחזית.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="irish-funds", description="כלי מחקר לקרנות איריות בתל אביב")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("funds", help="רשימת הקרנות")
    sub.add_parser("quiz", help="שאלון אינטראקטיבי ותיקים לדוגמה")
    b = sub.add_parser("build", help="בניית תיק מקובץ תשובות")
    b.add_argument("--template", required=True)
    b.add_argument("--answers", required=True)
    b.add_argument("--sp", choices=["regular", "equal", "hedged", "combined"])
    b.add_argument("--global", dest="global_variant", choices=["all", "ex_us"])
    b.add_argument("--global-fund", dest="global_fund")
    c = sub.add_parser("checkup", help="בדיקת תיק קיים")
    c.add_argument("--holdings", required=True, help="JSON של מספר נייר לסכום בשקלים")
    f = sub.add_parser("fees", help="מחשבון דמי ניהול")
    f.add_argument("--initial", type=float, default=0)
    f.add_argument("--monthly", type=float, default=0)
    f.add_argument("--years", type=int, required=True)
    f.add_argument("--return", dest="ret", type=float, required=True)
    f.add_argument("--fee", type=float, required=True)

    args = parser.parse_args(argv)
    data = core.load_data()
    try:
        {"funds": cmd_funds, "quiz": cmd_quiz, "build": cmd_build,
         "checkup": cmd_checkup, "fees": cmd_fees}[args.cmd](args, data)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"שגיאה: {exc}", file=sys.stderr)
        return 1
    print("\n" + core.DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
