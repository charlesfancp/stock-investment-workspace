#!/usr/bin/env python3
"""Generate a Chinese daily research report for the AI infrastructure portfolio."""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from thesis_log import latest_thesis_changes, thesis_changes_table

PORTFOLIO_PATH = ROOT / "config" / "portfolio.yaml"
PRICES_PATH = ROOT / "data" / "processed" / "prices_latest.csv"
SCORES_PATH = ROOT / "data" / "processed" / "scores_latest.csv"
EVENT_CALENDAR_PATH = ROOT / "data" / "processed" / "event_calendar_latest.csv"
REPORT_DIR = ROOT / "reports" / "daily"
REVERSAL_TRIGGERS_PATH = ROOT / "config" / "reversal_triggers.yaml"


def read_portfolio(path: Path = PORTFOLIO_PATH) -> dict[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    holdings: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        ticker_match = re.match(r"^\s*-\s+ticker:\s*([A-Z.]+)\s*$", line)
        if ticker_match:
            current = {"ticker": ticker_match.group(1)}
            holdings[current["ticker"]] = current
            continue
        if current is None:
            continue
        for key in ("company", "role", "target_weight"):
            match = re.match(rf"^\s*{key}:\s*(.+?)\s*$", line)
            if match:
                value: str | float = match.group(1)
                if key == "target_weight":
                    value = float(value)
                current[key] = value
    if not holdings:
        raise ValueError(f"No holdings found in {path}")
    return holdings


def read_csv_by_ticker(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    with path.open(encoding="utf-8", newline="") as file:
        return {row["ticker"]: row for row in csv.DictReader(file)}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def parse_number(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def format_number(value: str | float | None, digits: int = 2) -> str:
    number = parse_number(str(value)) if value is not None else None
    if number is None:
        return "数据缺失"
    return f"{number:.{digits}f}"


def format_percent(value: str | float | None) -> str:
    number = parse_number(str(value)) if value is not None else None
    if number is None:
        return "数据缺失"
    return f"{number:.2f}%"


def report_risk_level(score_rows: list[dict[str, str]]) -> str:
    flagged = [
        row
        for row in score_rows
        if row.get("risk_flags") not in ("", "none", "null", None)
    ]
    reduce_actions = [
        row
        for row in score_rows
        if "减仓" in row.get("action", "") or "止损" in row.get("action", "")
    ]
    if reduce_actions:
        return "高：存在减仓或止损复核信号"
    if len(flagged) >= 5:
        return "中高：多只股票接近 52 周高位或显著高于长期均线"
    if flagged:
        return "中：部分股票出现技术面过热提示"
    return "低：未见技术面风险提示"


def action_summary(score_rows: list[dict[str, str]]) -> str:
    actions = {row.get("action", "") for row in score_rows}
    if any("止损" in action for action in actions):
        return "需要人工止损复核"
    if any("减仓" in action for action in actions):
        return "需要人工减仓复核"
    if any("持有/不加仓" in action for action in actions):
        return "持有为主，过热标的不加仓"
    return "持有观察"


def markdown_table(rows: list[list[str]]) -> str:
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def reportable_events(events: list[dict[str, str]]) -> list[dict[str, str]]:
    return [event for event in events if event.get("include_in_report") == "true"]


def event_table(events: list[dict[str, str]]) -> str:
    if not events:
        return "- 未来 14 天正式事件：数据缺失或待补充来源。"
    rows = [["日期", "ticker", "类型", "事件", "来源"], ["---", "---", "---", "---", "---"]]
    for event in events:
        source = event.get("source") or "数据缺失"
        if event.get("source_url") not in (None, "", "null"):
            source = f"[{source}]({event.get('source_url')})"
        rows.append(
            [
                event.get("event_date") or "数据缺失",
                event.get("ticker") or "组合",
                event.get("event_type") or "数据缺失",
                event.get("title") or "数据缺失",
                source,
            ]
        )
    return markdown_table(rows)


def count_reversal_triggers(path: Path = REVERSAL_TRIGGERS_PATH) -> tuple[int, int]:
    if not path.exists():
        return (0, 0)
    text = path.read_text(encoding="utf-8")
    portfolio_count = 0
    ticker_count = 0
    section = None
    for line in text.splitlines():
        if line.startswith("portfolio_level:"):
            section = "portfolio"
            continue
        if line.startswith("ticker_level:"):
            section = "ticker"
            continue
        if re.match(r"^\s+-\s+trigger:\s*", line):
            if section == "portfolio":
                portfolio_count += 1
            elif section == "ticker":
                ticker_count += 1
    return portfolio_count, ticker_count


def generate_report() -> tuple[Path, str]:
    portfolio = read_portfolio()
    prices = read_csv_by_ticker(PRICES_PATH)
    scores = read_csv_by_ticker(SCORES_PATH)
    events = reportable_events(read_csv_rows(EVENT_CALENDAR_PATH))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ordered_scores = [scores.get(ticker, {"ticker": ticker, "action": "数据缺失"}) for ticker in portfolio]
    risk_level = report_risk_level(ordered_scores)
    portfolio_action = action_summary(ordered_scores)
    portfolio_trigger_count, ticker_trigger_count = count_reversal_triggers()

    lines: list[str] = [
        f"# AI 基础设施组合日报 - {today}",
        "",
        f"- 生成时间：{generated_at}",
        "- 系统定位：自动投研判断系统，不是自动交易系统。",
        "- 当前证据覆盖：行情、均线、事件日历、基本面和估值数据结构；基本面与估值数值仍待人工填充。",
        "- 交易纪律：所有买卖、加仓、减仓和清仓都必须人工确认。",
        "",
        "## 1. 组合总览",
        "",
        f"- 当前风险等级：{risk_level}",
        f"- 今日组合动作：{portfolio_action}",
        "- 是否触发自动交易：否。本系统不自动下单。",
        f"- 假设破坏清单：组合层面 {portfolio_trigger_count} 项，单票层面 {ticker_trigger_count} 项；当前状态为待接入证据。",
        "- 主要数据缺口：产业景气、公司基本面数值、估值赔率数值、事件后复核、风险事件。",
        "",
        "## 2. 单票评分表",
        "",
    ]

    table_rows = [
        ["ticker", "角色", "目标仓位", "价格", "评分", "动作", "风险提示"],
        ["---", "---", "---:", "---:", "---:", "---", "---"],
    ]
    for ticker, holding in portfolio.items():
        price = prices.get(ticker, {})
        score = scores.get(ticker, {})
        table_rows.append(
            [
                ticker,
                str(holding.get("role", "数据缺失")),
                f"{format_number(holding.get('target_weight'), 1)}%",
                format_number(price.get("price")),
                format_number(score.get("score"), 0),
                score.get("action") or "数据缺失",
                score.get("risk_flags") or "数据缺失",
            ]
        )
    lines.extend([markdown_table(table_rows), ""])

    lines.extend(
        [
            "## 3. 今日重大变化",
            "",
            "- 财报：数据缺失，尚未接入公司财报和电话会文字稿。",
            "- 新闻：数据缺失，尚未接入新闻和公司 IR。",
            "- 分析师调整：数据缺失，尚未接入目标价和评级变化。",
            "- 行业事件：数据缺失，尚未接入 CapEx、HBM、电力、数据中心等事件源。",
            "",
            "### 未来 14 天事件",
            "",
            event_table(events),
            "",
            "### 最近 thesis 变化",
            "",
            thesis_changes_table(latest_thesis_changes()),
            "",
            "## 4. 触发器检查",
            "",
        ]
    )

    trigger_rows = [["ticker", "止损/降级", "过热提示", "假设破坏状态", "证据缺口"], ["---", "---", "---", "---", "---"]]
    for ticker in portfolio:
        price = prices.get(ticker, {})
        score = scores.get(ticker, {})
        flags = score.get("risk_flags") or "数据缺失"
        downgrade = "是" if "stop_loss" in flags or "减仓" in score.get("action", "") else "否"
        overheating = "是" if "near_52w_high" in flags or "extended" in flags else "否"
        reversal_status = score.get("reversal_status") or "pending_evidence"
        gaps = score.get("data_gaps") or "数据缺失"
        trigger_rows.append([ticker, downgrade, overheating, reversal_status, gaps])
    lines.extend([markdown_table(trigger_rows), ""])

    lines.extend(
        [
            "## 5. 今日行动建议",
            "",
            f"- 组合层面：{portfolio_action}。",
            "- 单票层面：对接近 52 周高位或显著高于 200 日均线的股票，当前输出为“持有/不加仓”。",
            "- 基本面/估值层面：基本面和估值表结构已接入，但关键数值和来源仍待人工确认，不能升级为正式买入或加仓结论。",
            "- 风控层面：若后续接入 A 类来源并确认原始投资假设被破坏，应强制进入降级复核。",
            "- 假设破坏层面：当前只建立清单，尚未接入证据源，因此全部为待接入证据，不直接触发减仓或清仓。",
            "",
            "## 6. 数据来源",
            "",
        ]
    )

    sources = sorted(
        {
            f"{row.get('source', '数据缺失')}（日期：{row.get('source_date', '数据缺失')}，抓取：{row.get('fetched_at', '数据缺失')}）"
            for row in prices.values()
        }
    )
    lines.extend([f"- {source}" for source in sources])
    lines.extend(["", "> 本报告仅作投研整理，不构成投资建议。"])

    report_text = "\n".join(lines) + "\n"
    report_path = REPORT_DIR / f"{today.replace('-', '')}_daily_report.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    (REPORT_DIR / "latest_daily_report.md").write_text(report_text, encoding="utf-8")
    return report_path, report_text


def main() -> int:
    report_path, _ = generate_report()
    print(f"Wrote {report_path}")
    print(f"Wrote {REPORT_DIR / 'latest_daily_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
