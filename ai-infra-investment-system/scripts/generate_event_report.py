#!/usr/bin/env python3
"""Generate an event watch report.

Events can trigger research review, but they never directly create trade orders.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVENT_CALENDAR_PATH = ROOT / "data" / "processed" / "event_calendar_latest.csv"
REPORT_DIR = ROOT / "reports" / "event"


def read_events(path: Path = EVENT_CALENDAR_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def markdown_table(rows: list[list[str]]) -> str:
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def source_label(event: dict[str, str]) -> str:
    source = event.get("source") or "数据缺失"
    source_url = event.get("source_url")
    if source_url not in (None, "", "null"):
        return f"[{source}]({source_url})"
    return source


def confirmed_event_rows(events: list[dict[str, str]]) -> list[list[str]]:
    rows = [["日期", "ticker", "类型", "事件", "来源", "复核文件", "复核重点"], ["---", "---", "---", "---", "---", "---", "---"]]
    confirmed = [event for event in events if event.get("include_in_report") == "true"]
    if not confirmed:
        rows.append(["数据缺失", "数据缺失", "数据缺失", "未来 14 天 confirmed 事件缺失", "数据缺失", "无"])
        return rows
    for event in confirmed:
        review_focus = "人工复核重点" if event.get("source_tier") == "tier_1" else "辅助复核"
        review_file = event.get("review_file") or "待建立"
        if review_file not in ("", "null", "待建立"):
            review_file = f"[{Path(review_file).name}](../../{review_file})"
        rows.append(
            [
                event.get("event_date") or "数据缺失",
                event.get("ticker") or "组合",
                event.get("event_type") or "数据缺失",
                event.get("title") or "数据缺失",
                source_label(event),
                review_file,
                review_focus,
            ]
        )
    return rows


def non_reportable_reason(event: dict[str, str]) -> str:
    missing_parts = []
    if event.get("event_date") in (None, "", "null"):
        missing_parts.append("日期")
    if event.get("source") in (None, "", "null"):
        missing_parts.append("来源")
    if event.get("source_tier") in (None, "", "null"):
        missing_parts.append("可信等级")
    if missing_parts:
        return "/".join(missing_parts)
    try:
        days_until = int(event.get("days_until") or 0)
    except ValueError:
        return "日期格式待复核"
    if days_until < 0:
        return "事件已过，待人工复核归档"
    if days_until > 14:
        return "已确认，尚未进入未来14天正式窗口"
    return "待复核"


def needs_source_rows(events: list[dict[str, str]]) -> list[list[str]]:
    rows = [["ticker", "类型", "事件", "状态", "未进入原因"], ["---", "---", "---", "---", "---"]]
    pending = [event for event in events if event.get("include_in_report") != "true"]
    if not pending:
        rows.append(["无", "无", "无", "无", "无"])
        return rows
    for event in pending:
        rows.append(
            [
                event.get("ticker") or "组合",
                event.get("event_type") or "数据缺失",
                event.get("title") or "数据缺失",
                event.get("status") or "needs_source",
                non_reportable_reason(event),
            ]
        )
    return rows


def generate_report() -> tuple[Path, str]:
    events = read_events()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    confirmed_count = sum(1 for event in events if event.get("include_in_report") == "true")
    non_reportable_count = len(events) - confirmed_count

    lines = [
        f"# AI 基础设施事件预警 - {today}",
        "",
        f"- 生成时间：{generated_at}",
        "- 系统定位：事件预警只触发人工复核，不自动生成交易指令。",
        f"- confirmed 事件：{confirmed_count}",
        f"- 未进入 14 天正式窗口事件：{non_reportable_count}",
        "",
        "## 1. 未来 14 天 confirmed 事件",
        "",
        markdown_table(confirmed_event_rows(events)),
        "",
        "## 2. 未进入 14 天正式窗口事件",
        "",
        markdown_table(needs_source_rows(events)),
        "",
        "## 3. 使用规则",
        "",
        "- tier_1 事件进入人工复核重点。",
        "- tier_2 事件可做辅助复核。",
        "- 缺少日期、来源或可信等级的事件不进入正式判断。",
        "- 事件本身不构成买入、卖出、加仓或减仓建议。",
        "",
        "> 本报告仅作投研整理，不构成投资建议。",
    ]

    report_text = "\n".join(lines) + "\n"
    report_path = REPORT_DIR / f"{today.replace('-', '')}_event_report.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    (REPORT_DIR / "latest_event_report.md").write_text(report_text, encoding="utf-8")
    return report_path, report_text


def main() -> int:
    report_path, _ = generate_report()
    print(f"Wrote {report_path}")
    print(f"Wrote {REPORT_DIR / 'latest_event_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
