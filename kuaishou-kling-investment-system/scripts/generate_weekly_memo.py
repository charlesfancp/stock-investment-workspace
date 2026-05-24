from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from common import latest_by_nonempty, read_csv, row_float


ROOT = Path(__file__).resolve().parents[1]
ANNOUNCEMENTS_PATH = ROOT / "data" / "processed" / "announcements.csv"
MARKET_PRICES_PATH = ROOT / "data" / "processed" / "market_prices.csv"
VALUATION_HISTORY_PATH = ROOT / "data" / "processed" / "valuation_history.csv"
REPORTS_DIR = ROOT / "reports" / "weekly"


def latest_valuation_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    latest_as_of = rows[-1].get("as_of")
    return [row for row in rows if row.get("as_of") == latest_as_of]


def week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def classify_conclusion(price: float | None, base_target: float | None, major_count: int) -> str:
    if price is None or base_target is None:
        return "维持观察，等待行情和估值数据补齐。"
    discount = 1 - price / base_target
    if discount >= 0.25 and major_count == 0:
        return "基准偏多，价格仍低于基准估值，但需要等待可灵融资事实确认。"
    if discount >= 0.15:
        return "偏多持有，风险收益仍可接受，但加仓需要更强事件确认。"
    if price >= base_target:
        return "估值接近或高于基准目标，优先控制仓位和确认融资条款。"
    return "中性持有，等待新增事实。"


def main() -> None:
    today = date.today()
    start = week_start(today)
    year, week, _ = today.isocalendar()
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    announcements = read_csv(ANNOUNCEMENTS_PATH)
    prices = read_csv(MARKET_PRICES_PATH)
    valuations = latest_valuation_rows(read_csv(VALUATION_HISTORY_PATH))
    weekly_announcements = [row for row in announcements if start.isoformat() <= row.get("date", "") <= today.isoformat()]
    major_events = [row for row in weekly_announcements if row.get("is_major_event", "").lower() in {"true", "1", "yes"}]
    price_row = latest_by_nonempty(prices, "close_hkd")
    price = row_float(price_row, "close_hkd")
    base_row = next((row for row in valuations if row.get("scenario") == "base"), None)
    base_target = row_float(base_row, "target_price_hkd")
    conclusion = classify_conclusion(price, base_target, len(major_events))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{year}-W{week:02d}-weekly-memo.md"
    latest_path = REPORTS_DIR / "latest_weekly_memo.md"

    lines = [
        "# 快手周度投资 memo",
        "",
        f"- 周期：{start.isoformat()} 至 {today.isoformat()}",
        f"- 生成时间：{now}",
        "",
        "## 本周核心结论",
        conclusion,
        "",
        "## 本周新增事实",
    ]
    if weekly_announcements:
        for row in weekly_announcements[:20]:
            flag = "重大" if row in major_events else "普通"
            lines.append(f"- [{flag}] {row.get('date')} | {row.get('title')} | 来源：{row.get('source')}")
    else:
        lines.append("- 本周尚无结构化事实记录。")

    lines.extend(["", "## 投资假设是否变化"])
    lines.append("- 核心业务利润底：未见结构化证据显示变化。")
    lines.append("- 可灵估值假设：未见已验证融资条款更新。")
    lines.append("- 分拆概率：等待官方公告或高可信报道。")
    lines.append("- 市场风险偏好：以股价和成交变化继续观察。")

    lines.extend(["", "## 估值表"])
    if valuations:
        lines.append("| 情景 | 目标价 | 上行/下行 |")
        lines.append("| --- | ---: | ---: |")
        for row in valuations:
            upside = row.get("upside_downside_pct")
            upside_text = "N/A" if not upside else f"{float(upside):.1f}%"
            lines.append(f"| {row.get('scenario_label') or row.get('scenario')} | {float(row.get('target_price_hkd', 0)):.2f} 港元 | {upside_text} |")
    else:
        lines.append("- 尚无估值数据。")

    lines.extend(
        [
            "",
            "## 当前仓位建议",
            "- 按既定价格区间和事件触发器执行，不因单日波动改变主线。",
            "",
            "## 下周重点盯防",
            "- 可灵融资、分拆、估值或外部投资者确认。",
            "- 快手核心业务利润和 AI 成本是否出现负面变化。",
            "- 竞品视频模型价格、能力和商业化进展。",
            "- 港股流动性和快手成交量变化。",
        ]
    )
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")
    print(f"Wrote {latest_path}")


if __name__ == "__main__":
    main()
