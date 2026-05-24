import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "thesis_log.py"


def load_thesis_log_module():
    spec = importlib.util.spec_from_file_location("thesis_log", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ThesisLogReaderTests(unittest.TestCase):
    def test_empty_log_returns_no_changes(self):
        module = load_thesis_log_module()
        rows = module.read_thesis_changes(ROOT / "reviews" / "thesis_change_log.md")
        self.assertEqual(rows, [])

    def test_parses_manual_change_row(self):
        module = load_thesis_log_module()
        text = """# log
| 日期 | ticker | 事件/来源 | 原 thesis 状态 | 新 thesis 状态 | 变化原因 | 证据等级 | 确认人 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-05-20 | NVDA | earnings | thesis_unchanged | thesis_strengthened | data center beat | tier_1 | human | maintain_watch |
"""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as file:
            file.write(text)
            path = Path(file.name)
        try:
            rows = module.read_thesis_changes(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "NVDA")
        self.assertEqual(rows[0]["新 thesis 状态"], "thesis_strengthened")

    def test_table_states_no_manual_changes(self):
        module = load_thesis_log_module()
        self.assertIn("暂无人工确认", module.thesis_changes_table([]))


if __name__ == "__main__":
    unittest.main()
