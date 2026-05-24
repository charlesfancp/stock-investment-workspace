import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_rebalance.py"


def load_rebalance_module():
    spec = importlib.util.spec_from_file_location("check_rebalance", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RebalanceCheckTests(unittest.TestCase):
    def test_missing_position_does_not_trigger_review(self):
        module = load_rebalance_module()
        rows = module.build_rows(
            [
                {
                    "ticker": "NVDA",
                    "target_weight": "20",
                    "current_weight": "null",
                    "weight_drift": "null",
                    "position_status": "missing_position_input",
                }
            ],
            2,
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(rows[0]["rebalance_status"], "insufficient_data")
        self.assertEqual(rows[0]["review_required"], "false")

    def test_over_threshold_drift_triggers_manual_review(self):
        module = load_rebalance_module()
        rows = module.build_rows(
            [
                {
                    "ticker": "NVDA",
                    "target_weight": "20",
                    "current_weight": "23.1",
                    "weight_drift": "3.1",
                    "position_status": "ready",
                }
            ],
            2,
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(rows[0]["rebalance_status"], "manual_review_overweight")
        self.assertEqual(rows[0]["review_required"], "true")
        self.assertEqual(rows[0]["abs_weight_drift"], 3.1)

    def test_within_threshold_does_not_trigger_review(self):
        module = load_rebalance_module()
        rows = module.build_rows(
            [
                {
                    "ticker": "TSM",
                    "target_weight": "17",
                    "current_weight": "15.5",
                    "weight_drift": "-1.5",
                    "position_status": "ready",
                }
            ],
            2,
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(rows[0]["rebalance_status"], "within_threshold")
        self.assertEqual(rows[0]["review_required"], "false")


if __name__ == "__main__":
    unittest.main()
