import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_valuation.py"


def load_valuation_module():
    spec = importlib.util.spec_from_file_location("build_valuation", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValuationTests(unittest.TestCase):
    def test_missing_required_fields_are_labeled(self):
        module = load_valuation_module()
        row = module.normalize_row({"ticker": "NVDA", "market_cap": None}, "2026-01-01T00:00:00Z")
        self.assertEqual(row["valuation_status"], "missing_required_fields")
        self.assertIn("pe_forward", row["data_gaps"])
        self.assertIn("source_tier", row["data_gaps"])

    def test_future_source_date_is_not_ready(self):
        module = load_valuation_module()
        row = module.normalize_row(
            {
                "ticker": "NVDA",
                "market_cap": "1000000",
                "pe_forward": "30",
                "fcf_yield": "2.5",
                "valuation_percentile": "80",
                "source": "Exchange data",
                "source_url": "https://example.com/nvda",
                "source_tier": "tier_1",
                "source_type": "secondary",
                "source_date": "2026-05-16",
                "verified_status": "verified",
            },
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(row["valuation_status"], "missing_required_fields")
        self.assertIn("freshness:future_source_date", row["data_gaps"])
        self.assertEqual(row["freshness_status"], "future_source_date")
        self.assertEqual(row["conclusion_eligible"], "false")

    def test_current_verified_row_is_ready(self):
        module = load_valuation_module()
        row = module.normalize_row(
            {
                "ticker": "NVDA",
                "market_cap": "1000000",
                "pe_forward": "30",
                "fcf_yield": "2.5",
                "valuation_percentile": "80",
                "source": "Exchange data",
                "source_url": "https://example.com/nvda",
                "source_tier": "tier_1",
                "source_type": "secondary",
                "source_date": "2026-05-16",
                "verified_status": "verified",
            },
            "2026-05-19T00:00:00Z",
        )
        self.assertEqual(row["valuation_status"], "ready")
        self.assertEqual(row["data_gaps"], "none")
        self.assertEqual(row["freshness_status"], "current")
        self.assertEqual(row["conclusion_eligible"], "true")

    def test_stale_valuation_row_is_not_ready(self):
        module = load_valuation_module()
        row = module.normalize_row(
            {
                "ticker": "NVDA",
                "market_cap": "1000000",
                "pe_forward": "30",
                "fcf_yield": "2.5",
                "valuation_percentile": "80",
                "source": "Exchange data",
                "source_url": "https://example.com/nvda",
                "source_tier": "tier_1",
                "source_type": "secondary",
                "source_date": "2026-01-01",
                "verified_status": "verified",
            },
            "2026-05-19T00:00:00Z",
        )
        self.assertEqual(row["valuation_status"], "missing_required_fields")
        self.assertEqual(row["freshness_status"], "stale")
        self.assertIn("freshness:stale", row["data_gaps"])

    def test_latest_valuation_contains_all_portfolio_tickers_when_present(self):
        latest_path = ROOT / "data" / "processed" / "valuation_latest.csv"
        if not latest_path.exists():
            self.skipTest("valuation_latest.csv has not been generated yet")
        with latest_path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 10)


if __name__ == "__main__":
    unittest.main()
