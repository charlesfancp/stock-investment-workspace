import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ThesisChangeLogTests(unittest.TestCase):
    def test_log_has_required_columns(self):
        text = (ROOT / "reviews" / "thesis_change_log.md").read_text(encoding="utf-8")
        for column in ["日期", "ticker", "原 thesis 状态", "新 thesis 状态", "证据等级", "确认人", "后续动作"]:
            self.assertIn(column, text)

    def test_log_states_scripts_must_not_auto_modify_thesis(self):
        text = (ROOT / "reviews" / "thesis_change_log.md").read_text(encoding="utf-8")
        self.assertIn("脚本不得自动改写 thesis", text)

    def test_risk_control_has_thesis_change_redline(self):
        text = (ROOT / "docs" / "risk_control.md").read_text(encoding="utf-8")
        self.assertIn("脚本不得自动改写", text)
        self.assertIn("thesis_broken_confirmed", text)


if __name__ == "__main__":
    unittest.main()
