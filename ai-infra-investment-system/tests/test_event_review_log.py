import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EventReviewLogTests(unittest.TestCase):
    def test_review_index_links_nvda_review(self):
        text = (ROOT / "reviews" / "event_reviews" / "index.md").read_text(encoding="utf-8")
        self.assertIn("2026-05-20_NVDA_earnings.md", text)
        self.assertIn("pending_event", text)

    def test_nvda_review_has_fixed_conclusion_block(self):
        text = (ROOT / "reviews" / "event_reviews" / "2026-05-20_NVDA_earnings.md").read_text(encoding="utf-8")
        self.assertIn("事件结论：", text)
        self.assertIn("人工确认状态：", text)
        self.assertIn("no_action_review_only", text)


if __name__ == "__main__":
    unittest.main()
