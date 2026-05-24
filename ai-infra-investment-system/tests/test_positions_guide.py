import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PositionsGuideTests(unittest.TestCase):
    def test_guide_states_no_auto_inference(self):
        text = (ROOT / "docs" / "positions_guide.md").read_text(encoding="utf-8")
        self.assertIn("不会自动推断持仓", text)
        self.assertIn("不会自动下单", text)

    def test_example_contains_all_version_b_tickers(self):
        text = (ROOT / "docs" / "examples" / "positions.example.yaml").read_text(encoding="utf-8")
        for ticker in ["NVDA", "TSM", "AVGO", "GOOGL", "AMZN", "MU", "GEV", "VRT", "ETN", "DLR"]:
            self.assertIn(f"ticker: {ticker}", text)

    def test_local_positions_are_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("config/positions.local.yaml", text)


if __name__ == "__main__":
    unittest.main()
