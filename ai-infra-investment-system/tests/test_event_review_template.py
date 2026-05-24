import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EventReviewTemplateTests(unittest.TestCase):
    def test_template_contains_required_conclusion_fields(self):
        text = (ROOT / "docs" / "event_review_template.md").read_text(encoding="utf-8")
        self.assertIn("事件结论：", text)
        self.assertIn("对原始 thesis 的影响：", text)
        self.assertIn("是否触发假设破坏：", text)
        self.assertIn("人工确认状态：", text)

    def test_template_does_not_allow_auto_trade(self):
        text = (ROOT / "docs" / "event_review_template.md").read_text(encoding="utf-8")
        self.assertIn("不自动触发交易", text)
        self.assertIn("不能写交易指令", text)

    def test_nvda_placeholder_links_to_template(self):
        text = (ROOT / "docs" / "nvda_event_review_2026-05-20.md").read_text(encoding="utf-8")
        self.assertIn("pending_event", text)
        self.assertIn("docs/event_review_template.md", text)


if __name__ == "__main__":
    unittest.main()
