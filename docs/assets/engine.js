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
      equity_pct: equityPct,
      warnings: warnings
    };
  }

  var UNIT = 1200;

  function option(template, options, key) {
    var spec = template.options[key];
    var value = (options && key in options) ? options[key] : spec.default;
    if (!(value in spec.choices)) throw new Error("ערך לא מוכר לאפשרות " + key);
    return value;
  }

  function slotLeg(portfolios, slotId, w, notes) {
    var slot = portfolios.slots[slotId];
    notes.push(slot.note);
    return { slot: slotId, label: slot.label, fund: null, w: w };
  }

  function equityLegs(template, portfolios, options) {
    var notes = [], legs = [];
    if (template.id === "olami-ehad" || template.id === "olami-ve-agach") {
      legs.push({ slot: "global", label: "מניות עולם", fund: option(template, options, "global_fund"), w: UNIT });
      return { legs: legs, notes: notes };
    }
    if (template.id === "triathlon") {
      var f = template.funds, third = UNIT / 3;
      var tech = option(template, options, "tech_variant");
      legs.push({ slot: "tech", label: "טכנולוגיה", fund: f[tech], w: third });
      var sp = option(template, options, "sp_variant");
      if (sp === "regular_ishares" || sp === "regular_invesco") {
        legs.push({ slot: "sp", label: "S&P 500 רגיל", fund: f[sp], w: third });
      } else if (sp === "equal") {
        legs.push({ slot: "sp", label: "S&P 500 משקל שווה", fund: f.equal, w: third });
      } else if (sp === "combined") {
        legs.push({ slot: "sp", label: "S&P 500 רגיל", fund: f.regular_ishares, w: third / 2 });
        legs.push({ slot: "sp_equal", label: "S&P 500 משקל שווה", fund: f.equal, w: third / 2 });
      } else if (sp === "value") {
        legs.push(slotLeg(portfolios, "value", third, notes));
      } else {
        legs.push(slotLeg(portfolios, "sp_hedged", third, notes));
      }
      var gl = option(template, options, "global_variant");
      if (gl === "all_invesco" || gl === "all_ishares") {
        legs.push({ slot: "global", label: "כל העולם", fund: f[gl], w: third });
      } else {
        var split = template.ex_us_split;
        legs.push({ slot: "europe", label: "אירופה", fund: f.ex_us_europe, w: Math.floor(third * split.europe / 100) });
        legs.push({ slot: "emerging", label: "שווקים מתפתחים", fund: f.ex_us_emerging, w: Math.floor(third * split.emerging / 100) });
        notes.push(template.ex_us_note);
      }
      notes.push(template.overlap_note);
      return { legs: legs, notes: notes };
    }
    throw new Error("תבנית לא מוכרת: " + template.id);
  }

  function buildPortfolio(templateId, equityPct, portfolios, options) {
    if (!Number.isInteger(equityPct) || equityPct < 0 || equityPct > 100) {
      throw new Error("החלק המנייתי חייב להיות מספר שלם בין 0 ל-100");
    }
    var template = portfolios.templates.filter(function (t) { return t.id === templateId; })[0];
    if (!template) throw new Error("תבנית לא מוכרת: " + templateId);
    options = options || {};
    Object.keys(options).forEach(function (key) {
      if (!template.options || !(key in template.options)) throw new Error("אפשרות לא מוכרת לתבנית הזו: " + key);
    });
    var res = equityLegs(template, portfolios, options);
    var legs = res.legs, notes = res.notes;
    var raw = legs.map(function (l) { return l.w * equityPct; });
    var weights = raw.map(function (r) { return Math.floor(r / UNIT); });
    var leftover = equityPct - weights.reduce(function (a, b) { return a + b; }, 0);
    var order = legs.map(function (_, i) { return i; }).sort(function (a, b) {
      return (raw[b] % UNIT) - (raw[a] % UNIT) || a - b;
    });
    order.slice(0, leftover).forEach(function (i) { weights[i] += 1; });
    var lines = [];
    legs.forEach(function (l, i) {
      if (weights[i] > 0) lines.push({ slot: l.slot, label: l.label, fund: l.fund, weight: weights[i] });
    });
    var rest = 100 - equityPct, leg;
    if (templateId === "olami-ve-agach") {
      var bond = option(template, options, "bond_variant");
      if (rest === 0) {
        notes.push(template.no_bond_note);
      } else if (bond === "global_agg") {
        lines.push({ slot: "bond", label: "אגח עולמי כללי", fund: template.bond_fund, weight: rest });
        notes.push(template.bond_note);
      } else {
        leg = slotLeg(portfolios, "il_general_bond", 0, notes);
        lines.push({ slot: leg.slot, label: leg.label, fund: null, weight: rest });
      }
    } else if (rest > 0) {
      leg = slotLeg(portfolios, "solid", 0, notes);
      lines.push({ slot: leg.slot, label: leg.label, fund: null, weight: rest });
    }
    return { template_id: templateId, template_name: template.name, equity_pct: equityPct, lines: lines, notes: notes };
  }

  function alternatives(fundNumber, fundsData) {
    var byNum = fundsByNumber(fundsData), chosen = byNum[fundNumber];
    if (!chosen) throw new Error("קרן לא בדאטה: " + fundNumber);
    var base = totalCostPct(chosen), out = [];
    fundsData.funds.forEach(function (f) {
      if (f.peer_group === chosen.peer_group && f.tase_number !== fundNumber) {
        var cost = totalCostPct(f);
        out.push({ tase_number: f.tase_number, name: f.name, issuer: f.issuer, index: f.index,
          replication: f.replication, cost_pct: cost, diff_pct: Math.round((cost - base) * 10000) / 10000 });
      }
    });
    return out.sort(function (a, b) { return a.cost_pct - b.cost_pct || (a.tase_number < b.tase_number ? -1 : 1); });
  }

  function portfolioStats(lines, fundsData) {
    var byNum = fundsByNumber(fundsData), covered = 0, cost = 0, us = 0, usBase = 0;
    lines.forEach(function (line) {
      var fund = line.fund ? byNum[line.fund] : null;
      if (!fund) return;
      covered += line.weight;
      cost += line.weight * totalCostPct(fund);
      if (fund.asset_class === "equity" && fund.us_share !== null) {
        usBase += line.weight;
        us += line.weight * fund.us_share;
      }
    });
    return {
      covered_weight: covered,
      weighted_cost_pct: covered ? Math.round(cost / covered * 10000) / 10000 : 0,
      us_share_pct: usBase ? Math.round(us / usBase * 1000) / 10 : 0
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
    buildPortfolio: buildPortfolio, alternatives: alternatives, portfolioStats: portfolioStats, feeDrag: feeDrag
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.IrishFunds = api;
})(typeof window !== "undefined" ? window : globalThis);
