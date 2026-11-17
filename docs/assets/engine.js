/* מנוע החישוב בצד הדפדפן. מראה של engine/core.py, נבדק מולו בבדיקות. */
(function (root) {
  "use strict";

  function totalCostPct(fund) {
    return Math.round((fund.fee_pct + fund.extra_fee_pct) * 10000) / 10000;
  }

  function fundsByNumber(fundsData) {
    var map = {};
    fundsData.funds.forEach(function (f) { map[f.tase_number] = f; });
    return map;
  }

  function scoreRisk(answers, questionnaire) {
    var score = 0, maxScore = 0;
    questionnaire.questions.forEach(function (q) {
      if (!(q.id in answers)) throw new Error("חסרה תשובה לשאלה: " + q.id);
      var chosen = q.options.filter(function (o) { return o.id === answers[q.id]; });
      if (!chosen.length) throw new Error("תשובה לא מוכרת לשאלה " + q.id);
      score += chosen[0].points;
      maxScore += Math.max.apply(null, q.options.map(function (o) { return o.points; }));
    });
    var pct = Math.floor(score * 100 / maxScore);
    var profile = questionnaire.profiles[0];
    questionnaire.profiles.forEach(function (p) { if (pct >= p.min_pct) profile = p; });
    var equityPct = profile.equity_pct;
    var warnings = [];
    questionnaire.caps.forEach(function (cap) {
      if (answers[cap.question] === cap.option && equityPct > cap.max_equity_pct) {
        equityPct = cap.max_equity_pct;
        warnings.push(cap.warning);
      }
    });
    questionnaire.warnings.forEach(function (w) {
      if (answers[w.question] === w.option) warnings.push(w.warning);
    });
    return {
      score: score, max_score: maxScore, pct: pct,
      profile_id: profile.id, profile_name: profile.name,
      equity_pct: equityPct, tech_pct_of_equity: profile.tech_pct_of_equity,
      warnings: warnings
    };
  }

  function option(template, options, key) {
    var spec = template.options[key];
    var value = (options && key in options) ? options[key] : spec.default;
    if (!(value in spec.choices)) throw new Error("ערך לא מוכר לאפשרות " + key);
    return value;
  }

  function equityLegs(template, techPct, options) {
    var notes = [], legs = [];
    if (template.id === "olami-ehad") {
      legs.push({ slot: "global", label: "עולמי", fund: option(template, options, "global_fund"), w4: 400 });
      return { legs: legs, notes: notes };
    }
    if (template.id === "triathlon") {
      if (techPct % 5 !== 0 || techPct < 0 || techPct > 50) {
        throw new Error("משקל הטכנולוגיה חייב להיות כפולה של 5 בין 0 ל-50");
      }
      var f = template.funds, rest = 100 - techPct;
      legs.push({ slot: "tech", label: "טכנולוגיה, נאסדק 100", fund: f.tech, w4: 4 * techPct });
      var sp = option(template, options, "sp_variant");
      if (sp === "regular") {
        legs.push({ slot: "sp", label: "S&P 500 רגיל", fund: f.sp_regular, w4: 2 * rest });
      } else if (sp === "equal") {
        legs.push({ slot: "sp", label: "S&P 500 משקל שווה", fund: f.sp_equal, w4: 2 * rest });
      } else if (sp === "hedged") {
        var h = template.hedged_slot;
        legs.push({ slot: h.id, label: h.label, fund: null, w4: 2 * rest });
        notes.push(h.note);
      } else {
        legs.push({ slot: "sp", label: "S&P 500 רגיל", fund: f.sp_regular, w4: rest });
        legs.push({ slot: "sp_equal", label: "S&P 500 משקל שווה", fund: f.sp_equal, w4: rest });
      }
      var gl = option(template, options, "global_variant");
      if (gl === "all") {
        legs.push({ slot: "global", label: "כל העולם", fund: f.global_all, w4: 2 * rest });
      } else {
        var split = template.ex_us_split;
        legs.push({ slot: "europe", label: "אירופה", fund: f.ex_us_europe, w4: Math.floor(2 * rest * split.europe / 100) });
        legs.push({ slot: "emerging", label: "שווקים מתפתחים", fund: f.ex_us_emerging, w4: Math.floor(2 * rest * split.emerging / 100) });
        notes.push(template.ex_us_note);
      }
      return { legs: legs, notes: notes };
    }
    template.legs.forEach(function (l) {
      legs.push({ slot: l.slot, label: l.label, fund: l.fund, w4: 4 * l.weight });
    });
    return { legs: legs, notes: notes };
  }

  function buildPortfolio(templateId, equityPct, techPct, portfolios, options) {
    if (!Number.isInteger(equityPct) || equityPct < 0 || equityPct > 100) {
      throw new Error("החלק המנייתי חייב להיות מספר שלם בין 0 ל-100");
    }
    var template = portfolios.templates.filter(function (t) { return t.id === templateId; })[0];
    if (!template) throw new Error("תבנית לא מוכרת: " + templateId);
    var res = equityLegs(template, techPct, options || {});
    var legs = res.legs, notes = res.notes;
    var raw = legs.map(function (l) { return l.w4 * equityPct; });
    var weights = raw.map(function (r) { return Math.floor(r / 400); });
    var leftover = equityPct - weights.reduce(function (a, b) { return a + b; }, 0);
    var order = legs.map(function (_, i) { return i; }).sort(function (a, b) {
      return (raw[b] % 400) - (raw[a] % 400) || a - b;
    });
    order.slice(0, leftover).forEach(function (i) { weights[i] += 1; });
    var lines = [];
    legs.forEach(function (l, i) {
      if (weights[i] > 0) lines.push({ slot: l.slot, label: l.label, fund: l.fund, weight: weights[i] });
    });
    var solid = 100 - equityPct;
    if (solid > 0) {
      var s = portfolios.solid_slot;
      lines.push({ slot: s.id, label: s.label, fund: null, weight: solid });
      notes.push(s.note);
    }
    return { template_id: templateId, template_name: template.name, equity_pct: equityPct, lines: lines, notes: notes };
  }

  function portfolioStats(lines, fundsData) {
    var byNum = fundsByNumber(fundsData), covered = 0, cost = 0, us = 0;
    lines.forEach(function (line) {
      var fund = line.fund ? byNum[line.fund] : null;
      if (!fund) return;
      covered += line.weight;
      cost += line.weight * totalCostPct(fund);
      us += line.weight * fund.us_share;
    });
    if (!covered) return { covered_weight: 0, weighted_cost_pct: 0, us_share_pct: 0 };
    return {
      covered_weight: covered,
      weighted_cost_pct: Math.round(cost / covered * 10000) / 10000,
      us_share_pct: Math.round(us / covered * 1000) / 10
    };
  }

  function feeDrag(initial, monthly, years, grossReturnPct, feePct) {
    if (!(years > 0) || initial < 0 || monthly < 0 || feePct < 0) throw new Error("קלט לא תקין");
    function grow(annualPct) {
      var rate = Math.pow(1 + annualPct / 100, 1 / 12) - 1, value = initial;
      for (var i = 0; i < years * 12; i++) value = value * (1 + rate) + monthly;
      return value;
    }
    var withoutFee = grow(grossReturnPct), withFee = grow(grossReturnPct - feePct);
    function r2(x) { return Math.round(x * 100) / 100; }
    return {
      deposited: r2(initial + monthly * years * 12),
      without_fee: r2(withoutFee), with_fee: r2(withFee),
      lost_to_fees: r2(withoutFee - withFee)
    };
  }

  var api = {
    totalCostPct: totalCostPct, fundsByNumber: fundsByNumber, scoreRisk: scoreRisk,
    buildPortfolio: buildPortfolio, portfolioStats: portfolioStats, feeDrag: feeDrag
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.IrishFunds = api;
})(typeof window !== "undefined" ? window : globalThis);
