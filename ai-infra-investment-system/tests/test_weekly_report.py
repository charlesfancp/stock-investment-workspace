import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "generate_weekly_report.py"


def load_weekly_module():
    spec = importlib.util.spec_from_file_location("generate_weekly_report", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WeeklyReportTests(unittest.TestCase):
    def test_action_summary_does_not_auto_trade(self):
        module = load_weekly_module()
        summary = module.action_summary([{"action": "持有/不加仓"}])
        self.assertIn("持有", summary)

    def test_counts_reversal_triggers(self):
        module = load_weekly_module()
        portfolio_count, ticker_count = module.count_reversal_triggers()
        self.assertEqual(portfolio_count, 6)
        self.assertEqual(ticker_count, 29)

    def test_latest_weekly_report_mentions_missing_benchmarks_when_present(self):
        latest_path = ROOT / "reports" / "weekly" / "latest_weekly_report.md"
        if not latest_path.exists():
            self.skipTest("weekly report has not been generated yet")
        text = latest_path.read_text(encoding="utf-8")
        self.assertIn("相对收益：数据缺失", text)
        self.assertIn("不自动交易", text)
        self.assertIn("最近 thesis 变化", text)

    def test_benchmark_rows_include_core_benchmarks(self):
        module = load_weekly_module()
        table = module.markdown_table(module.benchmark_rows({}))
        self.assertIn("QQQ", table)
        self.assertIn("SOXX", table)
        self.assertIn("SMH", table)

    def test_portfolio_state_rows_label_missing_data(self):
        module = load_weekly_module()
        table = module.markdown_table(module.portfolio_state_rows({"NVDA": {"target_weight": 20}}, {}))
        self.assertIn("数据缺失", table)
        self.assertNotIn("数据缺失%", table)
        self.assertIn("NVDA", table)

    def test_rebalance_review_rows_only_show_manual_review_items(self):
        module = load_weekly_module()
        table = module.markdown_table(
            module.rebalance_review_rows(
                {"NVDA": {"target_weight": 20}, "TSM": {"target_weight": 17}},
                {
                    "NVDA": {
                        "ticker": "NVDA",
                        "target_weight": "20",
                        "current_weight": "23",
                        "weight_drift": "3",
                        "rebalance_status": "manual_review_overweight",
                        "review_required": "true",
                        "reason": "达到人工复核阈值",
                    },
                    "TSM": {
                        "ticker": "TSM",
                        "target_weight": "17",
                        "current_weight": "16",
                        "weight_drift": "-1",
                        "rebalance_status": "within_threshold",
                        "review_required": "false",
                        "reason": "未达到人工复核阈值",
                    },
                },
            )
        )
        self.assertIn("NVDA", table)
        self.assertNotIn("TSM |", table)

    def test_portfolio_risk_rows_formats_levels(self):
        module = load_weekly_module()
        table = module.markdown_table(
            module.portfolio_risk_rows(
                [
                    {
                        "risk_area": "event_density",
                        "risk_level": "high",
                        "metric": "reportable_event_count_14d",
                        "value": "5",
                        "status": "dense_event_window",
                        "details": "NVDA;AMZN;MU;GEV;VRT",
                    }
                ]
            )
        )
        self.assertIn("event_density", table)
        self.assertIn("高", table)

    def test_event_rows_include_missing_placeholder(self):
        module = load_weekly_module()
        table = module.markdown_table(module.event_rows([]))
        self.assertIn("未来 14 天正式事件缺失", table)

    def test_weekly_report_focus_moves_to_evidence_ingestion(self):
        latest_path = ROOT / "reports" / "weekly" / "latest_weekly_report.md"
        if not latest_path.exists():
            self.skipTest("weekly report has not been generated yet")
        text = latest_path.read_text(encoding="utf-8")
        self.assertIn("补齐基本面证据", text)
        self.assertIn("接入事件证据", text)
        self.assertNotIn("建立持仓状态：当前仓位", text)


if __name__ == "__main__":
    unittest.main()
