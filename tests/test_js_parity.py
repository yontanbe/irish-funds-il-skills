"""משווה את מנוע הדפדפן (JavaScript) למנוע הפייתון על אלפי מקרים."""
import itertools
import json
import shutil
import subprocess

import pytest

from engine import build_portfolio, fee_drag, portfolio_stats, score_risk

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node לא מותקן")

RUNNER = r"""
const E = require(process.argv[1]);
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const D = input.data, out = {risk: [], portfolios: [], fees: [], errors: []};
for (const a of input.answers) out.risk.push(E.scoreRisk(a, D.questionnaire));
for (const c of input.cases) {
  const p = E.buildPortfolio(c.template, c.equity, c.tech, D.portfolios, c.options);
  out.portfolios.push({p: p, s: E.portfolioStats(p.lines, D.funds)});
}
for (const f of input.fees) out.fees.push(E.feeDrag.apply(null, f));
for (const c of input.bad) {
  try { E.buildPortfolio(c.template, c.equity, c.tech, D.portfolios, c.options); out.errors.push(false); }
  catch (e) { out.errors.push(true); }
}
process.stdout.write(JSON.stringify(out));
"""


def _run(root, payload):
    res = subprocess.run(["node", "-e", RUNNER, str(root / "docs" / "assets" / "engine.js")],
                         input=json.dumps(payload), capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def js(root, data):
    q = data["questionnaire"]
    ids = [x["id"] for x in q["questions"]]
    combos = list(itertools.product(*[[o["id"] for o in x["options"]] for x in q["questions"]]))
    answers = [dict(zip(ids, c)) for c in combos[::7]]
    cases = []
    for t in data["portfolios"]["templates"]:
        specs = t.get("options", {})
        keys = list(specs)
        for values in itertools.product(*[list(specs[k]["choices"]) for k in keys]):
            for tech in (10, 15, 20, 25):
                for equity in range(0, 101, 1):
                    cases.append({"template": t["id"], "equity": equity, "tech": tech,
                                  "options": dict(zip(keys, values))})
    fees = [[0, 2000, 20, 7, 0.07], [0, 2000, 20, 7, 0.8], [100000, 0, 30, 6.5, 0.2], [5000, 500, 1, 4, 0]]
    bad = [{"template": "nope", "equity": 50, "tech": 10, "options": {}},
           {"template": "triathlon", "equity": 101, "tech": 10, "options": {}},
           {"template": "triathlon", "equity": 50, "tech": 12, "options": {}},
           {"template": "triathlon", "equity": 50, "tech": 10, "options": {"sp_variant": "x"}}]
    payload = {"data": data, "answers": answers, "cases": cases, "fees": fees, "bad": bad}
    return payload, _run(root, payload)


def test_risk_scoring_is_identical(js, data):
    payload, out = js
    assert len(out["risk"]) == len(payload["answers"]) > 2000
    for answers, got in zip(payload["answers"], out["risk"]):
        assert got == score_risk(answers, data["questionnaire"])


def test_portfolios_and_stats_are_identical(js, data):
    payload, out = js
    assert len(out["portfolios"]) == len(payload["cases"]) > 5000
    for case, got in zip(payload["cases"], out["portfolios"]):
        expected = build_portfolio(case["template"], case["equity"], case["tech"], data["portfolios"], case["options"])
        assert got["p"] == expected, case
        stats = portfolio_stats(expected["lines"], data["funds"])
        assert got["s"]["covered_weight"] == stats["covered_weight"]
        assert got["s"]["weighted_cost_pct"] == pytest.approx(stats["weighted_cost_pct"], abs=1.01e-4)  # הבדל עיגול בספרה הרביעית בלבד
        assert got["s"]["us_share_pct"] == pytest.approx(stats["us_share_pct"], abs=0.11)  # הבדל עיגול בספרה האחרונה בלבד


def test_fee_calculator_is_identical(js):
    payload, out = js
    for args, got in zip(payload["fees"], out["fees"]):
        expected = fee_drag(*args)
        for key in expected:
            assert got[key] == pytest.approx(expected[key], abs=0.02)


def test_js_rejects_the_same_bad_input(js):
    _, out = js
    assert out["errors"] == [True, True, True, True]
