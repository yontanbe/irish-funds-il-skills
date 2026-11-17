"""בדיקות לסקיל הביצועים. הרשת מוחלפת בתשובות מדומות במבנה של Yahoo Finance."""
from datetime import datetime, timezone

import pytest

from engine import performance as P


def _series(start_year, months, monthly_growth=0.01, base=100.0):
    return [((start_year + i // 12, i % 12 + 1), base * (1 + monthly_growth) ** i) for i in range(months)]


def _chart(series, currency="USD"):
    stamps = [int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp()) for (y, m), _ in series]
    prices = [p for _, p in series]
    return {"chart": {"error": None, "result": [{
        "meta": {"currency": currency}, "timestamp": stamps,
        "indicators": {"quote": [{"close": prices}], "adjclose": [{"adjclose": prices}]}}]}}


def _fake_fetch(charts, searches=None, calls=None):
    def fetch(url):
        if calls is not None:
            calls.append(url)
        if "/v1/finance/search" in url:
            for key, quotes in (searches or {}).items():
                if key in url:
                    return {"quotes": quotes}
            return {"quotes": []}
        for symbol, payload in charts.items():
            if f"/chart/{symbol}?" in url:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        return {"chart": {"error": {"code": "Not Found"}, "result": None}}
    return fetch


# ---------- חישוב ----------

def test_trailing_returns_on_known_growth():
    s = _series(2015, 131)  # עד נובמבר 2025
    assert P.trailing(s, 1) == {"cumulative_pct": 12.68, "annualized_pct": 12.68}
    assert P.trailing(s, 3)["annualized_pct"] == 12.68
    assert P.trailing(s, 5)["cumulative_pct"] == round((1.01 ** 60 - 1) * 100, 2)
    assert P.trailing(s, 10)["cumulative_pct"] == round((1.01 ** 120 - 1) * 100, 2)


def test_trailing_is_none_without_enough_history():
    s = _series(2023, 30)
    assert P.trailing(s, 1) is not None
    assert P.trailing(s, 3) is None
    assert P.trailing(s, 10) is None
    assert P.trailing([], 1) is None


def test_calendar_years_and_ytd_label():
    s = _series(2021, 47)  # ינואר 2021 עד נובמבר 2024
    years = P.calendar_years(s)
    assert list(years) == ["2022", "2023", "2024 YTD"]
    assert years["2022"] == 12.68
    assert years["2024 YTD"] == round((1.01 ** 11 - 1) * 100, 2)


def test_calendar_years_skip_year_without_december_base():
    s = [((2022, 6), 100.0), ((2023, 12), 120.0), ((2024, 12), 132.0)]
    assert P.calendar_years(s) == {"2024": 10.0}


def test_negative_year_is_reported_as_negative():
    s = [((2021, 12), 100.0), ((2022, 12), 80.0), ((2023, 12), 100.0)]
    assert P.calendar_years(s) == {"2022": -20.0, "2023": 25.0}
    assert P.trailing(s, 2) == {"cumulative_pct": 0.0, "annualized_pct": 0.0}


def test_month_series_keeps_last_point_per_month_and_drops_bad_prices():
    pts = [(datetime(2024, 1, 1, tzinfo=timezone.utc), 10.0), (datetime(2024, 1, 20, tzinfo=timezone.utc), 11.0),
           (datetime(2024, 2, 1, tzinfo=timezone.utc), None), (datetime(2024, 3, 1, tzinfo=timezone.utc), 0)]
    assert P.to_month_series(pts) == [((2024, 1), 11.0)]


def test_convert_multiplies_by_fx_and_drops_months_without_rate():
    series = [((2024, 1), 100.0), ((2024, 2), 110.0), ((2024, 3), 120.0)]
    fx = [((2024, 1), 3.5), ((2024, 3), 4.0)]
    assert P.convert(series, fx) == [((2024, 1), 350.0), ((2024, 3), 480.0)]


def test_parse_chart_reads_adjusted_prices_and_currency():
    points, currency = P.parse_chart(_chart(_series(2024, 3), "GBp"))
    assert currency == "GBp" and len(points) == 3 and points[0][0].year == 2024


def test_parse_chart_rejects_error_payload():
    with pytest.raises(ValueError):
        P.parse_chart({"chart": {"error": {"code": "Not Found"}, "result": None}})


@pytest.mark.parametrize("currency,pair", [("USD", "USDILS=X"), ("EUR", "EURILS=X"), ("GBp", "GBPILS=X"),
                                           ("GBP", "GBPILS=X"), ("ILS", None)])
def test_fx_symbol(currency, pair):
    assert P.fx_symbol(currency) == pair


# ---------- הבאת נתונים ----------

FUND = {"tase_number": "1159250", "name": "iShares Core S&P 500 UCITS ETF", "peer_group": "sp500",
        "isin": "IE00B5BMR087", "yahoo_ticker": "CSPX.L", "ticker_confidence": "verified"}


def test_fund_performance_native_currency():
    row = P.fund_performance(FUND, "native", _fake_fetch({"CSPX.L": _chart(_series(2015, 131))}))
    assert row["symbol"] == "CSPX.L" and row["symbol_confidence"] == "verified"
    assert row["currency"] == "USD" and row["as_of"] == "2025-11"
    assert row["5y"]["annualized_pct"] == 12.68
    assert row["years"]["2024"] == 12.68


def test_fund_performance_in_shekels_includes_currency_move():
    usd_flat = [((y, m), 100.0) for (y, m), _ in _series(2015, 131)]
    fx_rising = _series(2015, 131, monthly_growth=0.005, base=3.5)
    fetch = _fake_fetch({"CSPX.L": _chart(usd_flat), "USDILS%3DX": _chart(fx_rising, "ILS")})
    row = P.fund_performance(FUND, "ils", fetch)
    assert row["currency"] == "ILS"
    assert row["1y"]["cumulative_pct"] == round((1.005 ** 12 - 1) * 100, 2)


def test_fx_rate_is_fetched_once_for_many_funds():
    calls = []
    fetch = _fake_fetch({"CSPX.L": _chart(_series(2015, 131)), "USDILS%3DX": _chart(_series(2015, 131, 0.0, 3.6), "ILS")},
                        calls=calls)
    rows = P.report([FUND, dict(FUND, tase_number="1183441")], "ils", fetch)
    assert all("error" not in r for r in rows)
    assert sum("USDILS" in c for c in calls) == 1


def test_symbol_is_resolved_by_isin_then_by_name():
    fund = dict(FUND, yahoo_ticker=None, ticker_confidence=None)
    by_isin = _fake_fetch({}, {"IE00B5BMR087": [{"symbol": "SXR8.DE", "quoteType": "ETF"},
                                               {"symbol": "CSPX.L", "quoteType": "ETF"}]})
    assert P.resolve_symbol(fund, by_isin) == ("CSPX.L", "isin")
    no_isin = dict(fund, isin=None)
    by_name = _fake_fetch({}, {"iShares": [{"symbol": "CSPX.AS", "quoteType": "ETF"}]})
    assert P.resolve_symbol(no_isin, by_name) == ("CSPX.AS", "name_search")
    with pytest.raises(ValueError):
        P.resolve_symbol(no_isin, _fake_fetch({}))


def test_one_failing_fund_does_not_break_the_report():
    fetch = _fake_fetch({"CSPX.L": _chart(_series(2015, 131)), "BAD.L": OSError("network down")})
    rows = P.report([FUND, dict(FUND, tase_number="1111111", yahoo_ticker="BAD.L")], "native", fetch)
    assert "error" not in rows[0]
    assert rows[1]["error"] == "network down"


def test_markdown_report_has_three_tables_date_currency_and_disclaimers():
    fetch = _fake_fetch({"CSPX.L": _chart(_series(2015, 131)), "NEW.L": _chart(_series(2024, 20)),
                         "BAD.L": OSError("timeout")})
    funds = [FUND, dict(FUND, tase_number="1207208", name="Young Fund", yahoo_ticker="NEW.L", ticker_confidence="likely"),
             dict(FUND, tase_number="1111111", yahoo_ticker="BAD.L")]
    text = P.to_markdown(P.report(funds, "native", fetch))
    assert "## תשואה מצטברת, נכון ל-2025-11, מטבע: USD" in text
    assert "## תשואה שנתית ממוצעת" in text and "## שנה מול שנה" in text
    assert "| שנה | 3 שנים | 5 שנים | 10 שנים |" in text
    assert "| Young Fund | 1207208 | +12.7% | אין | אין | אין |" in text
    assert "1207208 לפי NEW.L" in text, "סימול שלא אומת חייב להיות מסומן"
    assert "1111111 (timeout)" in text
    assert "תשואות עבר אינן מבטיחות תשואות עתיד" in text and "אינו ייעוץ השקעות" in text


def test_cli_rejects_unknown_number_and_unknown_group(capsys):
    assert P.main(["--numbers", "0000000"]) == 1
    assert P.main(["--group", "no_such_group"]) == 1
    assert "לא בדאטה" in capsys.readouterr().err


def test_cli_end_to_end_with_mocked_network(monkeypatch, capsys):
    flat_fx = _chart(_series(2015, 131, 0.0, 3.6), "ILS")

    def fetch(url, timeout=20):
        return flat_fx if "ILS%3DX" in url else _chart(_series(2015, 131))
    monkeypatch.setattr(P, "http_json", fetch)
    assert P.main(["--group", "sp500"]) == 0
    out = capsys.readouterr().out
    assert "1159250" in out and "1183441" in out and "מטבע: ILS" in out


def test_every_ticker_in_data_is_used_as_is(data):
    for f in data["funds"]["funds"]:
        if f["yahoo_ticker"]:
            assert P.resolve_symbol(f, _fake_fetch({})) == (f["yahoo_ticker"], f["ticker_confidence"])
