from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from common import latest_by_nonempty, load_yaml, read_csv, row_float


ROOT = Path(__file__).resolve().parents[1]
ANNOUNCEMENTS_PATH = ROOT / "data" / "processed" / "announcements.csv"
MARKET_PRICES_PATH = ROOT / "data" / "processed" / "market_prices.csv"
VALUATION_HISTORY_PATH = ROOT / "data" / "processed" / "valuation_history.csv"
ANALYST_VIEWS_PATH = ROOT / "data" / "processed" / "analyst_views.csv"
POSITION_RECORDS_PATH = ROOT / "data" / "processed" / "position_records.csv"
ALERT_RULES_PATH = ROOT / "config" / "alert_rules.yaml"
REPORTS_DIR = ROOT / "reports" / "daily"
ALLOWED_ACTIONS = {"买入", "加仓", "持有", "减仓", "卖出"}


def latest_price(rows: list[dict[str, str]]) -> dict[str, str] | None:
    return latest_by_nonempty(rows, "close_hkd")


def latest_valuation_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    latest_as_of = rows[-1].get("as_of")
    latest = [row for row in rows if row.get("as_of") == latest_as_of]
    return latest or rows[-3:]


def decide_action(price: float | None, major_events: list[dict[str, str]], rules: dict[str, Any]) -> str:
    if price is None:
        return "持有"
    price_rules = rules.get("price_alerts", {})
    has_major_event = bool(major_events)
    if price < float(price_rules.get("stop_loss", 44)) and not has_major_event:
        return "卖出"
    if price < float(price_rules.get("strong_buy_below", 50)):
        return "买入"
    if float(price_rules.get("buy_zone_low", 50)) <= price <= float(price_rules.get("buy_zone_high", 58)):
        return "加仓"
    if price >= float(price_rules.get("trim_above", 80)):
        return "减仓"
    if price >= float(price_rules.get("caution_above", 70)) and not has_major_event:
        return "减仓"
    return "持有"


def main() -> None:
    today = date.today().isoformat()
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    announcements = read_csv(ANNOUNCEMENTS_PATH)
    prices = read_csv(MARKET_PRICES_PATH)
    valuations = latest_valuation_rows(read_csv(VALUATION_HISTORY_PATH))
    analyst_views = sorted(read_csv(ANALYST_VIEWS_PATH), key=lambda row: row.get("date", ""), reverse=True)[:5]
    position_records = read_csv(POSITION_RECORDS_PATH)
    latest_position = position_records[-1] if position_records else None
    rules = load_yaml(ALERT_RULES_PATH)

    todays_announcements = [row for row in announcements if row.get("date") == today]
    major_events = [row for row in todays_announcements if row.get("is_major_event", "").lower() in {"true", "1", "yes"}]
    price_row = latest_price(prices)
    price = row_float(price_row, "close_hkd") if price_row else None
    action = decide_action(price, major_events, rules)
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Invalid action: {action}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{today}-daily-brief.md"
    lines = [
        f"# 快手-可灵每日跟踪",
        "",
        f"- 日期：{today}",
        f"- 生成时间：{now}",
        f"- 系统动作：{action}",
        "",
        "## 1. 今日重大公告",
    ]
    if major_events:
        for item in major_events:
            lines.append(f"- {item.get('date', '')} | {item.get('title', '')} | 来源：{item.get('source', '')} | 链接：{item.get('link', '')}")
    else:
        lines.append("- 无已记录重大公告。")

    lines.extend(["", "## 2. 股价与成交"])
    if price_row:
        lines.append(f"- 最新股价：{price_row.get('close_hkd')} 港元")
        lines.append(f"- 涨跌幅：{price_row.get('change_pct') or 'N/A'}")
        lines.append(f"- 成交量：{price_row.get('volume') or 'N/A'}")
        lines.append(f"- 来源：{price_row.get('source') or 'N/A'}，数据日期：{price_row.get('date') or 'N/A'}")
    else:
        lines.append("- 尚无市场价格数据，请更新 `data/processed/market_prices.csv`。")

    lines.extend(["", "## 3. 可灵相关信息"])
    kling_items = [row for row in todays_announcements if any(k in (row.get("keywords") or row.get("title") or "") for k in ["可灵", "Kling", "融资", "分拆", "估值", "外部投资者", "ARR"])]
    if kling_items:
        lines.extend(f"- {row.get('title', '')}（可信度：{row.get('credibility') or '待评估'}）" for row in kling_items)
    else:
        lines.append("- 今日无已记录可灵相关变化。")

    lines.extend(["", "## 4. 核心业务相关信息", "- 今日无已结构化记录。"])
    lines.extend(["", "## 5. 估值变化"])
    if valuations:
        lines.append("| 情景 | 目标价 | 上行/下行 |")
        lines.append("| --- | ---: | ---: |")
        for row in valuations:
            upside = row.get("upside_downside_pct")
            upside_text = "N/A" if not upside else f"{float(upside):.1f}%"
            lines.append(f"| {row.get('scenario_label') or row.get('scenario')} | {float(row.get('target_price_hkd', 0)):.2f} 港元 | {upside_text} |")
    else:
        lines.append("- 尚无估值历史，请先运行 `python models/valuation_engine.py`。")

    lines.extend(["", "## 6. 顶级分析师判断"])
    if analyst_views:
        for view in analyst_views:
            target = f"{float(view.get('target_price_hkd', 0)):.2f} 港元" if view.get("target_price_hkd") else "N/A"
            lines.append(f"- {view.get('institution')}：{view.get('rating')}，目标价 {target}。{view.get('chinese_summary')}")
    else:
        lines.append("- 尚无结构化分析师观点。")

    lines.extend(["", "## 7. 建仓测算与复盘基准"])
    if latest_position:
        lines.append(
            "- 最新记录：{lots} 手 / {shares} 股，价格 {price} 港元，预算 {budget} 港元，预计占用 {gross} 港元，剩余 {cash} 港元。".format(
                lots=latest_position.get("lots", "N/A"),
                shares=latest_position.get("shares", "N/A"),
                price=latest_position.get("price_hkd", "N/A"),
                budget=latest_position.get("budget_hkd", "N/A"),
                gross=latest_position.get("gross_amount_hkd", "N/A"),
                cash=latest_position.get("cash_left_hkd", "N/A"),
            )
        )
        if latest_position.get("note"):
            lines.append(f"- 备注：{latest_position['note']}")
        lines.append("- 费用说明：不含佣金、印花税、平台费和滑点。")
    else:
        lines.append("- 尚无建仓测算记录。")

    lines.extend(
        [
            "",
            "## 8. 今日动作建议",
            f"- {action}",
            "",
            "## 9. 需要人工确认的信息",
            "- 是否存在未录入的港交所公告或快手 IR 材料。",
            "- 今日可灵相关传闻来源是否可靠。",
            "- 是否有大行目标价或评级变化。",
            "- 股价数据是否已更新至最新交易日。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
