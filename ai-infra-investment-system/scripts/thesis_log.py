"""Read manually maintained thesis change logs.

This module is read-only. It must not modify thesis files or the change log.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THESIS_CHANGE_LOG_PATH = ROOT / "reviews" / "thesis_change_log.md"
EXPECTED_COLUMNS = ["日期", "ticker", "事件/来源", "原 thesis 状态", "新 thesis 状态", "变化原因", "证据等级", "确认人", "后续动作"]


def parse_markdown_table_line(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def read_thesis_changes(path: Path = THESIS_CHANGE_LOG_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    current_header: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = parse_markdown_table_line(line)
        if cells == EXPECTED_COLUMNS:
            current_header = cells
            continue
        if current_header is None:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if len(cells) != len(current_header):
            continue
        row = dict(zip(current_header, cells))
        if row.get("日期") in ("", "日期"):
            continue
        rows.append(row)
    return rows


def latest_thesis_changes(limit: int = 5, path: Path = THESIS_CHANGE_LOG_PATH) -> list[dict[str, str]]:
    rows = read_thesis_changes(path)
    return rows[-limit:]


def thesis_changes_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "- 暂无人工确认的 thesis 变化。"
    table = [
        ["日期", "ticker", "新 thesis 状态", "证据等级", "后续动作"],
        ["---", "---", "---", "---", "---"],
    ]
    for row in rows:
        table.append(
            [
                row.get("日期", "数据缺失"),
                row.get("ticker", "数据缺失"),
                row.get("新 thesis 状态", "数据缺失"),
                row.get("证据等级", "数据缺失"),
                row.get("后续动作", "数据缺失"),
            ]
        )
    return "\n".join("| " + " | ".join(line) + " |" for line in table)
