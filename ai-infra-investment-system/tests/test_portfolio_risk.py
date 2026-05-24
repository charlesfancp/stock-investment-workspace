import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_portfolio_risk.py"


def load_risk_module():
    spec = importlib.util.spec_from_file_location("build_portfolio_risk", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PortfolioRiskTests(unittest.TestCase):
    def test_technical_overheat_counts_flagged_tickers(self):
        module = load_risk_module()
        row = module.technical_overheat_risk(
            [
                {"ticker": "NVDA", "risk_flags": "near_52w_high"},
                {"ticker": "AMZN", "risk_flags": "none"},
                {"ticker": "VRT", "risk_flags": "extended_more_than_30pct_above_ma200"},
            ],
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(row["value"], 2)
        self.assertEqual(row["risk_level"], "low")
        self.assertIn("NVDA", row["details"])

    def test_event_density_high_at_five_events(self):
        module = load_risk_module()
        row = module.event_density_risk(
            [{"ticker": str(index), "include_in_report": "true"} for index in range(5)],
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(row["risk_level"], "high")
        self.assertEqual(row["value"], 5)

    def test_missing_positions_are_high_risk(self):
        module = load_risk_module()
        row = module.portfolio_state_risk(
            [{"ticker": "NVDA", "position_status": "missing_position_input"}],
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(row["risk_level"], "high")
        self.assertEqual(row["status"], "needs_manual_position_input")

    def test_latest_portfolio_risk_contains_expected_rows_when_present(self):
        latest_path = ROOT / "data" / "processed" / "portfolio_risk_latest.csv"
        if not latest_path.exists():
            self.skipTest("portfolio_risk_latest.csv has not been generated yet")
        with latest_path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 7)


if __name__ == "__main__":
    unittest.main()
