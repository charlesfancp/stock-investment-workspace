from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from common import read_csv


ROOT = Path(__file__).resolve().parents[1]
ANNOUNCEMENTS_PATH = ROOT / "data" / "processed" / "announcements.csv"
REPORTS_DIR = ROOT / "reports" / "weekly"
BEAR_KEYWORDS = {
    "核心业务放缓": ["放缓", "低于预期", "增长下降", "利润下滑"],
    "AI 成本超预期": ["资本开支", "capex", "算力", "成本", "亏损"],
    "可灵质量问题": ["ARR", "留存", "退款", "价格下调", "质量"],
    "融资低于预期": ["融资", "估值", "低于", "折价"],
    "竞品冲击": ["OpenAI", "Google", "字节", "阿里", "竞品", "视频模型"],
    "监管风险": ["监管", "内容安全", "版权", "处罚"],
    "股价透支": ["目标价下调", "评级下调", "减持"],
}


def week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def main() -> None:
    today = date.today()
    start = week_start(today)
    year, week, _ = today.isocalendar()
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    announcements = [
        row
        for row in read_csv(ANNOUNCEMENTS_PATH)
        if start.isoformat() <= row.get("date", "") <= today.isoformat()
    ]
    evidence: list[tuple[str, dict[str, str]]] = []
    for row in announcements:
        text = " ".join([row.get("title", ""), row.get("summary", ""), row.get("keywords", "")]).lower()
        for bucket, keywords in BEAR_KEYWORDS.items():
            if any(keyword.lower() in text for keyword in keywords):
                evidence.append((bucket, row))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{year}-W{week:02d}-bear-case-review.md"
    latest_path = REPORTS_DIR / "latest_bear_case_review.md"
    lines = [
        "# 反证清单",
        "",
        f"- 周期：{start.isoformat()} 至 {today.isoformat()}",
        f"- 生成时间：{now}",
        "",
        "## 最强反方证据",
    ]
    if evidence:
        for bucket, row in evidence[:20]:
            lines.append(f"- {bucket}：{row.get('date')} | {row.get('title')} | 来源：{row.get('source')}")
    else:
        lines.append("- 本周结构化记录中未发现强反方证据。")

    lines.extend(
        [
            "",
            "## 对投资评级的影响",
            "- 暂不自动下调。需要人工确认是否存在未结构化的公告、券商报告或行业新闻。",
            "",
            "## 是否需要减仓",
            "- 若后续确认融资低于预期、利润下修或 AI 成本超预期，触发减仓复核。",
            "",
            "## 触发条件",
            "- 核心业务利润低于模型假设 20% 以上。",
            "- 可灵融资估值低于 80 亿美元。",
            "- 快手保留可灵权益低于 80%。",
            "- AI 资本开支显著高于当前假设并压低利润。",
            "- 股价高于基准目标但融资条款未确认。",
            "",
            "## 待人工确认",
            "- 是否有未录入的官方公告。",
            "- 是否有大行下调评级或目标价。",
            "- 是否有竞品发布造成可灵商业化假设受损。",
        ]
    )
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")
    print(f"Wrote {latest_path}")


if __name__ == "__main__":
    main()
