import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "score_tickers.py"


def load_score_module():
    spec = importlib.util.spec_from_file_location("score_tickers", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScoringTests(unittest.TestCase):
    def test_portfolio_weights_sum_to_100(self):
        score_tickers = load_score_module()
        portfolio = score_tickers.read_portfolio()
        self.assertEqual(len(portfolio), 10)
        self.assertEqual(sum(item["target_weight"] for item in portfolio.values()), 100)

    def test_technical_score_handles_missing_data(self):
        score_tickers = load_score_module()
        self.assertIsNone(score_tickers.technical_score(None, 1, 1, 1))

    def test_technical_score_rewards_uptrend(self):
        score_tickers = load_score_module()
        self.assertGreater(score_tickers.technical_score(120, 110, 100, 90), 80)

    def test_reads_reversal_triggers_for_nvda(self):
        score_tickers = load_score_module()
        triggers = score_tickers.read_reversal_trigger_names("NVDA")
        self.assertIn("gross_margin_down_two_quarters", triggers)
        self.assertIn("blackwell_or_rubin_delay", triggers)

    def test_fundamentals_schema_changes_evidence_coverage(self):
        score_tickers = load_score_module()
        row = score_tickers.score_row(
            "NVDA",
            {"target_weight": 20},
            {"price": "120", "ma_20": "110", "ma_50": "100", "ma_200": "90", "week_52_high": "130"},
            {"fundamentals_status": "missing_required_fields", "data_gaps": "period;source_tier"},
            {"valuation_status": "missing_required_fields", "data_gaps": "pe_forward;source_tier"},
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(row["evidence_coverage"], "technicals_plus_evidence_schema")
        self.assertIn("fundamentals:period", row["data_gaps"])
        self.assertIn("valuation:pe_forward", row["data_gaps"])

    def test_latest_scores_contains_all_portfolio_tickers_when_present(self):
        scores_path = ROOT / "data" / "processed" / "scores_latest.csv"
        if not scores_path.exists():
            self.skipTest("scores_latest.csv has not been generated yet")

        score_tickers = load_score_module()
        with scores_path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(list(score_tickers.read_portfolio().keys()), [row["ticker"] for row in rows])


if __name__ == "__main__":
    unittest.main()
