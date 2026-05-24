import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "generate_daily_report.py"


def load_report_module():
    spec = importlib.util.spec_from_file_location("generate_daily_report", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DailyReportTests(unittest.TestCase):
    def test_markdown_table_formats_rows(self):
        module = load_report_module()
        table = module.markdown_table([["a", "b"], ["---", "---"], ["1", "2"]])
        self.assertIn("| a | b |", table)
        self.assertIn("| 1 | 2 |", table)

    def test_report_mentions_no_auto_trading_when_generated(self):
        latest_path = ROOT / "reports" / "daily" / "latest_daily_report.md"
        if not latest_path.exists():
            self.skipTest("daily report has not been generated yet")
        text = latest_path.read_text(encoding="utf-8")
        self.assertIn("不是自动交易系统", text)
        self.assertIn("不自动下单", text)

    def test_counts_reversal_triggers(self):
        module = load_report_module()
        portfolio_count, ticker_count = module.count_reversal_triggers()
        self.assertGreaterEqual(portfolio_count, 1)
        self.assertGreaterEqual(ticker_count, 10)

    def test_event_table_hides_missing_events(self):
        module = load_report_module()
        text = module.event_table([])
        self.assertIn("数据缺失", text)

    def test_daily_report_mentions_recent_thesis_changes_when_present(self):
        latest_path = ROOT / "reports" / "daily" / "latest_daily_report.md"
        if not latest_path.exists():
            self.skipTest("daily report has not been generated yet")
        text = latest_path.read_text(encoding="utf-8")
        self.assertIn("最近 thesis 变化", text)


if __name__ == "__main__":
    unittest.main()
