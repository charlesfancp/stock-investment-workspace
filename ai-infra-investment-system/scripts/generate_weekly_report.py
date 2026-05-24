#!/usr/bin/env python3
"""Generate a Chinese weekly research report for the AI infrastructure portfolio."""

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
BENCHMARKS_PATH = ROOT / "data" / "processed" / "benchmarks_latest.csv"
PORTFOLIO_STATE_PATH = ROOT / "data" / "processed" / "portfolio_state_latest.csv"
REBALANCE_CHECK_PATH = ROOT / "data" / "processed" / "rebalance_check_latest.csv"
EVENT_CALENDAR_PATH = ROOT / "data" / "processed" / "event_calendar_latest.csv"
SCORES_PATH = ROOT / "data" / "processed" / "scores_latest.csv"
PORTFOLIO_RISK_PATH = ROOT / "data" / "processed" / "portfolio_risk_latest.csv"
REVERSAL_TRIGGERS_PATH = ROOT / "config" / "reversal_triggers.yaml"
REPORT_DIR = ROOT / "reports" / "weekly"

THEME_BY_TICKER = {
    "NVDA": "算力",
    "TSM": "先进制造",
    "AVGO": "ASIC/网络",
    "GOOGL": "模型/数据入口",
    "AMZN": "云地产",
    "MU": "HBM",
    "GEV": "电力/散热",
    "VRT": "电力/散热",
    "ETN": "电力/散热",
    "DLR": "带电容量",
}


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


def format_weight(value: str | float | None, digits: int = 1) -> str:
    number = parse_number(str(value)) if value is not None else None
    if number is None:
        return "数据缺失"
    return f"{number:.{digits}f}%"


def markdown_table(rows: list[list[str]]) -> str:
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def reportable_events(events: list[dict[str, str]]) -> list[dict[str, str]]:
    return [event for event in events if event.get("include_in_report") == "true"]


def event_rows(events: list[dict[str, str]]) -> list[list[str]]:
    rows = [["日期", "ticker", "类型", "事件", "来源"], ["---", "---", "---", "---", "---"]]
    if not events:
        rows.append(["数据缺失", "数据缺失", "数据缺失", "未来 14 天正式事件缺失或待补充来源", "数据缺失"])
        return rows
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
    return rows


def action_summary(score_rows: list[dict[str, str]]) -> str:
    actions = {row.get("action", "") for row in score_rows}
    if any("止损" in action for action in actions):
        return "防守：需要人工止损复核"
    if any("减仓" in action for action in actions):
        return "防守：需要人工减仓复核"
    if any("持有/不加仓" in action for action in actions):
        return "持有：强趋势但多只标的过热，暂不加仓"
    return "持有观察：等待基本面和估值证据"


def theme_rows(portfolio: dict[str, dict[str, Any]], scores: dict[str, dict[str, str]]) -> list[list[str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for ticker in portfolio:
        grouped.setdefault(THEME_BY_TICKER.get(ticker, "其他"), []).append(scores.get(ticker, {}))

    rows = [["主线", "覆盖股票", "平均技术分", "状态", "证据缺口"], ["---", "---", "---:", "---", "---"]]
    for theme, items in grouped.items():
        tickers = [
            ticker
            for ticker, mapped_theme in THEME_BY_TICKER.items()
            if mapped_theme == theme and ticker in portfolio
        ]
        numeric_scores = [parse_number(item.get("score")) for item in items]
        valid_scores = [score for score in numeric_scores if score is not None]
        average = sum(valid_scores) / len(valid_scores) if valid_scores else None
        if any((item.get("risk_flags") or "none") != "none" for item in items):
            status = "技术面强，但有过热提示"
        else:
            status = "技术面稳定，等待更多证据"
        rows.append(
            [
                theme,
                "/".join(tickers),
                format_number(average, 0),
                status,
                "基本面数值/估值数值/事件复核数据缺失",
            ]
        )
    return rows


def count_reversal_triggers(path: Path = REVERSAL_TRIGGERS_PATH) -> tuple[int, int]:
    if not path.exists():
        return (0, 0)
    text = path.read_text(encoding="utf-8")
    portfolio_count = len(re.findall(r"^  - trigger:", text, flags=re.MULTILINE))
    ticker_count = len(re.findall(r"^    - trigger:", text, flags=re.MULTILINE))
    return portfolio_count, ticker_count


def benchmark_rows(benchmarks: dict[str, dict[str, str]]) -> list[list[str]]:
    rows = [["基准", "价格", "当日涨跌", "52周高点", "52周低点", "数据日期"], ["---", "---:", "---:", "---:", "---:", "---"]]
    for ticker in ("QQQ", "SOXX", "SMH"):
        row = benchmarks.get(ticker, {})
        rows.append(
            [
                ticker,
                format_number(row.get("price")),
                format_percent(row.get("change_percent")),
                format_number(row.get("week_52_high")),
                format_number(row.get("week_52_low")),
                row.get("source_date") or "数据缺失",
            ]
        )
    return rows


def portfolio_state_rows(
    portfolio: dict[str, dict[str, Any]],
    state: dict[str, dict[str, str]],
) -> list[list[str]]:
    rows = [["ticker", "目标权重", "当前权重", "偏离", "市值", "状态"], ["---", "---:", "---:", "---:", "---:", "---"]]
    for ticker, holding in portfolio.items():
        row = state.get(ticker, {})
        rows.append(
            [
                ticker,
                format_weight(holding.get("target_weight")),
                format_weight(row.get("current_weight")) if row else "数据缺失",
                format_weight(row.get("weight_drift")) if row else "数据缺失",
                format_number(row.get("market_value")) if row else "数据缺失",
                row.get("position_status") or "数据缺失",
            ]
        )
    return rows


def rebalance_review_rows(
    portfolio: dict[str, dict[str, Any]],
    rebalance: dict[str, dict[str, str]],
) -> list[list[str]]:
    rows = [["ticker", "目标权重", "当前权重", "偏离", "状态", "原因"], ["---", "---:", "---:", "---:", "---", "---"]]
    review_rows = [
        rebalance.get(ticker, {})
        for ticker in portfolio
        if rebalance.get(ticker, {}).get("review_required") == "true"
    ]
    if not review_rows:
        rows.append(["组合", "数据缺失", "数据缺失", "数据缺失", "暂无可确认复核信号", "未发现达到阈值的权重偏离，或真实持仓数据仍缺失"])
        return rows
    for row in review_rows:
        rows.append(
            [
                row.get("ticker") or "数据缺失",
                format_weight(row.get("target_weight")),
                format_weight(row.get("current_weight")),
                format_weight(row.get("weight_drift")),
                row.get("rebalance_status") or "数据缺失",
                row.get("reason") or "数据缺失",
            ]
        )
    return rows


def risk_level_label(level: str | None) -> str:
    mapping = {"high": "高", "medium": "中", "low": "低"}
    return mapping.get(level or "", "数据缺失")


def portfolio_risk_rows(risks: list[dict[str, str]]) -> list[list[str]]:
    rows = [["风险项", "等级", "指标", "数值", "状态", "细节"], ["---", "---", "---", "---:", "---", "---"]]
    if not risks:
        rows.append(["组合风险", "数据缺失", "数据缺失", "数据缺失", "风险摘要未生成", "请先运行 build_portfolio_risk.py"])
        return rows
    for risk in risks:
        details = risk.get("details") or "数据缺失"
        if len(details) > 80:
            details = details[:77] + "..."
        rows.append(
            [
                risk.get("risk_area") or "数据缺失",
                risk_level_label(risk.get("risk_level")),
                risk.get("metric") or "数据缺失",
                str(risk.get("value") or "数据缺失"),
                risk.get("status") or "数据缺失",
                details,
            ]
        )
    return rows


def generate_report() -> tuple[Path, str]:
    portfolio = read_portfolio()
    prices = read_csv_by_ticker(PRICES_PATH)
    benchmarks = read_csv_by_ticker(BENCHMARKS_PATH) if BENCHMARKS_PATH.exists() else {}
    portfolio_state = read_csv_by_ticker(PORTFOLIO_STATE_PATH) if PORTFOLIO_STATE_PATH.exists() else {}
    rebalance_check = read_csv_by_ticker(REBALANCE_CHECK_PATH) if REBALANCE_CHECK_PATH.exists() else {}
    events = reportable_events(read_csv_rows(EVENT_CALENDAR_PATH))
    scores = read_csv_by_ticker(SCORES_PATH)
    portfolio_risks = read_csv_rows(PORTFOLIO_RISK_PATH)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ordered_scores = [scores.get(ticker, {"ticker": ticker, "action": "数据缺失"}) for ticker in portfolio]
    summary = action_summary(ordered_scores)
    portfolio_trigger_count, ticker_trigger_count = count_reversal_triggers()

    lines: list[str] = [
        f"# AI 基础设施组合周报 - {today}",
        "",
        f"- 生成时间：{generated_at}",
        "- 系统定位：自动投研判断系统，不是自动交易系统。",
        "- 当前证据覆盖：行情、均线、技术面风险提示、事件日历、基本面和估值数据结构、假设破坏清单。",
        "- 数据缺口：尚未接入组合真实持仓市值、基本面数值、估值数值、新闻、SEC filing 和 IR 复核证据。",
        "",
        "## 一、本周核心结论",
        "",
        f"- 组合判断：{summary}。",
        "- 交易结论：不自动交易；如需调整，必须人工确认。",
        "- 主要约束：当前评分仍是技术面初版评分，不能替代完整基本面判断。",
        f"- 假设破坏清单：组合层面 {portfolio_trigger_count} 项，单票层面 {ticker_trigger_count} 项；当前均为待接入证据。",
        "",
        "## 二、组合表现",
        "",
        "- 组合收益：数据缺失，尚未建立持仓市值和历史净值表。",
        "- 相对收益：数据缺失，尚未建立真实组合收益，不能计算跑赢/跑输。",
        "",
        "### 持仓状态",
        "",
        markdown_table(portfolio_state_rows(portfolio, portfolio_state)),
        "",
        markdown_table(benchmark_rows(benchmarks)),
        "",
        "## 三、组合风险摘要",
        "",
        markdown_table(portfolio_risk_rows(portfolio_risks)),
        "",
        "## 四、主线评分",
        "",
        markdown_table(theme_rows(portfolio, scores)),
        "",
        "## 五、最近 thesis 变化",
        "",
        thesis_changes_table(latest_thesis_changes()),
        "",
        "## 六、单票更新",
        "",
    ]

    table_rows = [
        ["ticker", "角色", "目标仓位", "价格", "评分", "动作", "假设破坏状态"],
        ["---", "---", "---:", "---:", "---:", "---", "---"],
    ]
    for ticker, holding in portfolio.items():
        price = prices.get(ticker, {})
        score = scores.get(ticker, {})
        table_rows.append(
            [
                ticker,
                str(holding.get("role", "数据缺失")),
                format_weight(holding.get("target_weight")),
                format_number(price.get("price")),
                format_number(score.get("score"), 0),
                score.get("action") or "数据缺失",
                score.get("reversal_status") or "pending_evidence",
            ]
        )
    lines.extend([markdown_table(table_rows), ""])

    lines.extend(
        [
            "## 七、下周事件日历",
            "",
            markdown_table(event_rows(events)),
            "",
            "- 说明：事件必须有日期、来源和可信等级；否则只保留在待补充清单，不进入正式判断。",
            "",
            "## 八、调仓建议",
            "",
            f"- 当前建议：{summary}。",
            "- 加仓：不建议仅凭技术面初版评分加仓。",
            "- 减仓：若后续 A 类来源或两个独立 B 类来源确认假设破坏，应进入减仓复核。",
            "- 再平衡：只输出人工复核信号，不计算交易数量，不自动下单。",
            "",
            markdown_table(rebalance_review_rows(portfolio, rebalance_check)),
            "",
            "- 版本判断：继续运行版本 B，等待基本面数值、估值数值和事件后复核数据接入后再判断是否升级版本 C。",
            "",
            "## 九、下周工程重点",
            "",
            "- 补齐基本面证据：收入增速、毛利率、经营现金流、CapEx、订单和 backlog，必须保留来源、报告期和抓取时间。",
            "- 补齐估值证据：PE、EV/EBITDA、FCF yield、同业估值和目标区间，缺失数据继续保留 null。",
            "- 接入事件证据：财报、SEC filing、IR、电话会和公司新闻先进入待核查队列，确认后再影响 thesis 或动作。",
            "- 扩展基准对比：加入周度收益、月度收益和 YTD 收益；没有真实组合净值前不计算跑赢/跑输。",
            "",
            "> 本报告仅作投研整理，不构成投资建议。",
        ]
    )

    report_text = "\n".join(lines) + "\n"
    report_path = REPORT_DIR / f"{today.replace('-', '')}_weekly_report.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    (REPORT_DIR / "latest_weekly_report.md").write_text(report_text, encoding="utf-8")
    return report_path, report_text


def main() -> int:
    report_path, _ = generate_report()
    print(f"Wrote {report_path}")
    print(f"Wrote {REPORT_DIR / 'latest_weekly_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
