import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_fundamentals.py"


def load_fundamentals_module():
    spec = importlib.util.spec_from_file_location("build_fundamentals", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FundamentalsTests(unittest.TestCase):
    def test_missing_required_fields_are_labeled(self):
        module = load_fundamentals_module()
        row = module.normalize_row({"ticker": "NVDA", "period": None}, "2026-01-01T00:00:00Z")
        self.assertEqual(row["fundamentals_status"], "missing_required_fields")
        self.assertIn("revenue_growth_yoy", row["data_gaps"])
        self.assertIn("source_tier", row["data_gaps"])

    def test_ready_row_has_no_gaps(self):
        module = load_fundamentals_module()
        row = module.normalize_row(
            {
                "ticker": "NVDA",
                "period": "FY2026Q1",
                "revenue_growth_yoy": "50",
                "gross_margin": "70",
                "operating_margin": "60",
                "free_cash_flow": "1000",
                "capex": "500",
                "guidance": "raised",
                "source": "Company IR",
                "source_url": "https://example.com/nvda",
                "source_tier": "tier_1",
                "source_type": "original",
                "source_date": "2026-05-20",
                "verified_status": "verified",
            },
            "2026-05-21T00:00:00Z",
        )
        self.assertEqual(row["fundamentals_status"], "ready")
        self.assertEqual(row["data_gaps"], "none")
        self.assertEqual(row["freshness_status"], "current")
        self.assertEqual(row["conclusion_eligible"], "true")

    def test_unverified_or_stale_row_is_not_ready(self):
        module = load_fundamentals_module()
        row = module.normalize_row(
            {
                "ticker": "NVDA",
                "period": "FY2026Q1",
                "revenue_growth_yoy": "50",
                "gross_margin": "70",
                "operating_margin": "60",
                "free_cash_flow": "1000",
                "capex": "500",
                "guidance": "raised",
                "source": "Company IR",
                "source_url": "https://example.com/nvda",
                "source_tier": "tier_3",
                "source_type": "original",
                "source_date": "2025-01-01",
                "verified_status": "pending",
            },
            "2026-05-21T00:00:00Z",
        )
        self.assertEqual(row["fundamentals_status"], "missing_required_fields")
        self.assertEqual(row["conclusion_eligible"], "false")
        self.assertIn("invalid_or_low_tier_source", row["data_gaps"])
        self.assertIn("not_verified", row["data_gaps"])
        self.assertIn("freshness:stale", row["data_gaps"])

    def test_latest_fundamentals_contains_all_portfolio_tickers_when_present(self):
        latest_path = ROOT / "data" / "processed" / "fundamentals_latest.csv"
        if not latest_path.exists():
            self.skipTest("fundamentals_latest.csv has not been generated yet")
        with latest_path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 10)


if __name__ == "__main__":
    unittest.main()
