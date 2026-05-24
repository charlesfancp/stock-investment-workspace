import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_daily_pipeline.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("run_daily_pipeline", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PipelineTests(unittest.TestCase):
    def test_pipeline_step_order(self):
        module = load_pipeline_module()
        self.assertEqual(
            [step.script for step in module.PIPELINE_STEPS],
            [
                "fetch_prices.py",
                "build_fundamentals.py",
                "build_valuation.py",
                "score_tickers.py",
                "build_portfolio_state.py",
                "check_rebalance.py",
                "build_event_calendar.py",
                "build_portfolio_risk.py",
                "generate_daily_report.py",
                "generate_weekly_report.py",
                "generate_event_report.py",
            ],
        )

    def test_pipeline_docstring_says_no_trades(self):
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("never places trades", text)


if __name__ == "__main__":
    unittest.main()
