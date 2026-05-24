import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "generate_event_report.py"


def load_event_report_module():
    spec = importlib.util.spec_from_file_location("generate_event_report", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EventReportTests(unittest.TestCase):
    def test_confirmed_tier_1_event_is_review_focus(self):
        module = load_event_report_module()
        rows = module.confirmed_event_rows(
            [
                {
                    "include_in_report": "true",
                    "event_date": "2026-05-20",
                    "ticker": "NVDA",
                    "event_type": "earnings",
                    "title": "NVIDIA earnings",
                    "source": "NVIDIA Investor Relations",
                    "source_tier": "tier_1",
                    "review_file": "reviews/event_reviews/2026-05-20_NVDA_earnings.md",
                }
            ]
        )
        table = module.markdown_table(rows)
        self.assertIn("人工复核重点", table)
        self.assertIn("NVDA", table)
        self.assertIn("2026-05-20_NVDA_earnings.md", table)

    def test_pending_event_lists_missing_parts(self):
        module = load_event_report_module()
        rows = module.needs_source_rows(
            [
                {
                    "include_in_report": "false",
                    "ticker": "TSM",
                    "event_type": "earnings",
                    "title": "Next earnings release",
                    "status": "needs_source",
                    "event_date": "null",
                    "source": "null",
                    "source_tier": "null",
                }
            ]
        )
        table = module.markdown_table(rows)
        self.assertIn("日期/来源/可信等级", table)

    def test_latest_event_report_mentions_no_trade_when_present(self):
        latest_path = ROOT / "reports" / "event" / "latest_event_report.md"
        if not latest_path.exists():
            self.skipTest("event report has not been generated yet")
        text = latest_path.read_text(encoding="utf-8")
        self.assertIn("不自动生成交易指令", text)


if __name__ == "__main__":
    unittest.main()
