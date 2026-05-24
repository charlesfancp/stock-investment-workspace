import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "fetch_prices.py"


def load_fetch_prices_module():
    spec = importlib.util.spec_from_file_location("fetch_prices", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PriceFetchTests(unittest.TestCase):
    def test_portfolio_tickers_match_version_b(self):
        fetch_prices = load_fetch_prices_module()
        self.assertEqual(
            fetch_prices.read_portfolio_tickers(),
            ["NVDA", "TSM", "AVGO", "GOOGL", "AMZN", "MU", "GEV", "VRT", "ETN", "DLR"],
        )

    def test_benchmark_tickers_match_config(self):
        fetch_prices = load_fetch_prices_module()
        self.assertEqual(fetch_prices.read_benchmark_tickers(), ["QQQ", "SOXX", "SMH"])

    def test_csv_schema_contains_required_fields(self):
        fetch_prices = load_fetch_prices_module()
        self.assertEqual(
            fetch_prices.FIELDNAMES,
            [
                "ticker",
                "price",
                "market_cap",
                "pe_ttm",
                "pe_forward",
                "week_52_high",
                "week_52_low",
                "change_percent",
                "ma_20",
                "ma_50",
                "ma_200",
                "source",
                "source_date",
                "fetched_at",
                "error",
            ],
        )

    def test_parse_chart_response_uses_last_two_closes_for_change_percent(self):
        fetch_prices = load_fetch_prices_module()
        data = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "regularMarketPrice": 110,
                            "chartPreviousClose": 50,
                            "regularMarketTime": 1_700_000_000,
                        },
                        "timestamp": [1_699_900_000, 1_700_000_000],
                        "indicators": {"quote": [{"close": [100, 110]}]},
                    }
                ]
            }
        }
        row = fetch_prices.parse_chart_response("TEST", data, "2026-01-01T00:00:00Z")
        self.assertEqual(row["change_percent"], 10.0)

    def test_fetch_ticker_retries_transient_failure(self):
        fetch_prices = load_fetch_prices_module()
        calls = {"count": 0}

        def flaky_fetch_json(_url):
            calls["count"] += 1
            if calls["count"] == 1:
                raise TimeoutError("temporary timeout")
            return {
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "regularMarketPrice": 110,
                                "chartPreviousClose": 100,
                                "regularMarketTime": 1_700_000_000,
                            },
                            "timestamp": [1_699_900_000, 1_700_000_000],
                            "indicators": {"quote": [{"close": [100, 110]}]},
                        }
                    ]
                }
            }

        original_fetch_json = fetch_prices.fetch_json
        fetch_prices.fetch_json = flaky_fetch_json
        try:
            row = fetch_prices.fetch_ticker("TEST", "2026-01-01T00:00:00Z", attempts=2)
        finally:
            fetch_prices.fetch_json = original_fetch_json

        self.assertEqual(calls["count"], 2)
        self.assertEqual(row["price"], 110.0)
        self.assertIsNone(row["error"])

    def test_latest_output_contains_all_portfolio_tickers_when_present(self):
        latest_path = ROOT / "data" / "processed" / "prices_latest.csv"
        if not latest_path.exists():
            self.skipTest("prices_latest.csv has not been generated yet")

        fetch_prices = load_fetch_prices_module()
        with latest_path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual([row["ticker"] for row in rows], fetch_prices.read_portfolio_tickers())


if __name__ == "__main__":
    unittest.main()
