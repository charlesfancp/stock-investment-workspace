from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANNOUNCEMENTS_PATH = ROOT / "data" / "processed" / "announcements.csv"
EVENT_MEMOS_DIR = ROOT / "reports" / "event_memos"
KEYWORDS = ["可灵", "Kling", "融资", "分拆", "估值", "外部投资者"]


def slugify(text: str) -> str:
    text = re.sub(r"\s+", "-", text.strip().lower())
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff-]+", "", text)
    return text[:60] or "event"


def read_announcements() -> list[dict[str, str]]:
    if not ANNOUNCEMENTS_PATH.exists():
        return []
    with ANNOUNCEMENTS_PATH.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    EVENT_MEMOS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    generated = 0
    for row in read_announcements():
        text = " ".join([row.get("title", ""), row.get("summary", ""), row.get("keywords", "")])
        if not any(keyword in text for keyword in KEYWORDS):
            continue
        event_date = row.get("date") or now[:10]
        path = EVENT_MEMOS_DIR / f"{event_date}-{slugify(row.get('title', 'event'))}.md"
        if path.exists():
            continue
        lines = [
            "# 事件 memo",
            "",
            f"- 生成时间：{now}",
            f"- 事件日期：{event_date}",
            "",
            "## 1. 事件摘要",
            row.get("summary") or row.get("title") or "待补充。",
            "",
            "## 2. 信息来源",
            f"- 来源：{row.get('source') or 'N/A'}",
            f"- 链接：{row.get('link') or 'N/A'}",
            "",
            "## 3. 可信度评级",
            row.get("credibility") or "待人工确认",
            "",
            "## 4. 对原投资假设的影响",
            "- 待人工判断。",
            "",
            "## 5. 对估值模型的影响",
            "- 暂不自动修改估值假设。",
            "",
            "## 6. 是否触发动作",
            "- 持有",
            "",
            "## 7. 需要进一步验证的问题",
            "- 该信息是否来自官方公告或高可信来源。",
            "- 是否涉及融资估值、快手保留权益、ARR 或利润影响。",
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        generated += 1
    print(f"Generated {generated} event memo(s)")


if __name__ == "__main__":
    main()
