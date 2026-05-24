import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_portfolio_state.py"


def load_state_module():
    spec = importlib.util.spec_from_file_location("build_portfolio_state", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PortfolioStateTests(unittest.TestCase):
    def test_missing_positions_are_labeled(self):
        module = load_state_module()
        rows = module.build_rows(
            {"NVDA": {"target_weight": 20}},
            {"NVDA": {"shares": None, "average_cost": None}},
            {"NVDA": {"price": "100", "source_date": "2026-01-01"}},
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(rows[0]["position_status"], "missing_position_input")
        self.assertIsNone(rows[0]["current_weight"])

    def test_weights_calculate_when_positions_exist(self):
        module = load_state_module()
        rows = module.build_rows(
            {"NVDA": {"target_weight": 60}, "TSM": {"target_weight": 40}},
            {"NVDA": {"shares": 1, "average_cost": 80}, "TSM": {"shares": 1, "average_cost": 80}},
            {
                "NVDA": {"price": "120", "source_date": "2026-01-01"},
                "TSM": {"price": "80", "source_date": "2026-01-01"},
            },
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(rows[0]["current_weight"], 60)
        self.assertEqual(rows[1]["current_weight"], 40)

    def test_latest_state_contains_all_portfolio_tickers_when_present(self):
        latest_path = ROOT / "data" / "processed" / "portfolio_state_latest.csv"
        if not latest_path.exists():
            self.skipTest("portfolio_state_latest.csv has not been generated yet")
        with latest_path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 10)


if __name__ == "__main__":
    unittest.main()
