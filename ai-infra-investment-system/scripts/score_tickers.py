#!/usr/bin/env python3
"""Generate first-pass research scores for the AI infrastructure portfolio.

This version keeps action decisions conservative and labels missing evidence
from technical, fundamental, valuation, catalyst, and risk modules explicitly.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "config" / "portfolio.yaml"
PRICES_PATH = ROOT / "data" / "processed" / "prices_latest.csv"
FUNDAMENTALS_PATH = ROOT / "data" / "processed" / "fundamentals_latest.csv"
VALUATION_PATH = ROOT / "data" / "processed" / "valuation_latest.csv"
SCORES_PATH = ROOT / "data" / "processed" / "scores_latest.csv"
REVERSAL_TRIGGERS_PATH = ROOT / "config" / "reversal_triggers.yaml"

FIELDNAMES = [
    "ticker",
    "score",
    "action",
    "target_weight",
    "price",
    "main_reason",
    "risk_flags",
    "source_date",
    "fetched_at",
    "technical_score",
    "fundamentals_status",
    "valuation_status",
    "evidence_coverage",
    "data_gaps",
    "reversal_status",
    "reversal_triggers",
]

MISSING_EVIDENCE_MODULES = [
    "industry_momentum",
    "catalysts",
    "risk_penalty",
]


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
        weight_match = re.match(r"^\s*target_weight:\s*([0-9.]+)\s*$", line)
        if weight_match:
            current["target_weight"] = float(weight_match.group(1))
            continue
        role_match = re.match(r"^\s*role:\s*(.+?)\s*$", line)
        if role_match:
            current["role"] = role_match.group(1)
    if not holdings:
        raise ValueError(f"No holdings found in {path}")
    return holdings


def read_stop_loss(ticker: str) -> float | None:
    path = ROOT / "thesis" / f"{ticker}.yaml"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    match = re.search(r"stop_loss:\s*\n\s*price:\s*([0-9.]+|null)", text)
    if not match or match.group(1) == "null":
        return None
    return float(match.group(1))


def parse_number(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_prices(path: Path = PRICES_PATH) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing price input: {path}")
    with path.open(encoding="utf-8", newline="") as file:
        return {row["ticker"]: row for row in csv.DictReader(file)}


def read_fundamentals(path: Path = FUNDAMENTALS_PATH) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as file:
        return {row["ticker"]: row for row in csv.DictReader(file)}


def read_valuation(path: Path = VALUATION_PATH) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as file:
        return {row["ticker"]: row for row in csv.DictReader(file)}


def read_reversal_trigger_names(ticker: str, path: Path = REVERSAL_TRIGGERS_PATH) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    names: list[str] = []
    in_ticker = False
    for line in text.splitlines():
        ticker_match = re.match(r"^  ([A-Z.]+):\s*$", line)
        if ticker_match:
            in_ticker = ticker_match.group(1) == ticker
            continue
        if in_ticker:
            if re.match(r"^  [A-Z.]+:\s*$", line):
                break
            trigger_match = re.match(r"^\s+-\s+trigger:\s*([a-zA-Z0-9_]+)\s*$", line)
            if trigger_match:
                names.append(trigger_match.group(1))
    return names


def technical_score(price: float | None, ma20: float | None, ma50: float | None, ma200: float | None) -> int | None:
    if price is None or ma20 is None or ma50 is None or ma200 is None:
        return None

    score = 50
    score += 12 if price >= ma20 else -12
    score += 16 if price >= ma50 else -16
    score += 22 if price >= ma200 else -22

    if ma20 >= ma50 >= ma200:
        score += 10
    elif ma20 < ma50 < ma200:
        score -= 10

    return max(0, min(100, score))


def risk_flags(price: float | None, high_52w: float | None, ma200: float | None, stop_loss: float | None) -> list[str]:
    flags: list[str] = []
    if price is None:
        flags.append("price_missing")
        return flags
    if high_52w and high_52w > 0 and price / high_52w >= 0.95:
        flags.append("near_52w_high")
    if ma200 and ma200 > 0 and price / ma200 - 1 >= 0.30:
        flags.append("extended_more_than_30pct_above_ma200")
    if stop_loss and price <= stop_loss:
        flags.append("stop_loss_review")
    return flags


def action_for(price: float | None, ma20: float | None, ma50: float | None, ma200: float | None, flags: list[str]) -> str:
    if price is None or ma20 is None or ma50 is None or ma200 is None:
        return "数据不足/观察"
    if "stop_loss_review" in flags:
        return "止损复核"
    if price < ma200 or (price < ma50 and price < ma20):
        return "减仓观察"
    if "near_52w_high" in flags or "extended_more_than_30pct_above_ma200" in flags:
        return "持有/不加仓"
    return "持有/观察"


def reason_for(action: str, tech_score: int | None, gaps: list[str]) -> str:
    if tech_score is None:
        return "价格或均线数据缺失，无法形成技术面评分。"
    if action == "止损复核":
        return "价格触及 thesis 中的止损复核条件，需要人工确认投资假设是否破坏。"
    gap_text = "、".join(gaps) if gaps else "无"
    if action == "减仓观察":
        return f"价格跌破关键均线，先进入技术面降级观察；证据缺口：{gap_text}。"
    if action == "持有/不加仓":
        return f"趋势仍强，但价格接近高位或相对长期均线过热；证据缺口：{gap_text}。"
    return f"技术面未触发降级，但仍不能替代完整投研判断；证据缺口：{gap_text}。"


def fundamentals_gap(fundamental_row: dict[str, str]) -> tuple[str, list[str]]:
    if not fundamental_row:
        return "missing_table_row", ["fundamentals"]
    status = fundamental_row.get("fundamentals_status") or "missing_required_fields"
    if status == "ready":
        return status, []
    gaps = fundamental_row.get("data_gaps")
    if gaps in (None, "", "null"):
        return status, ["fundamentals"]
    return status, [f"fundamentals:{gap}" for gap in gaps.split(";") if gap]


def valuation_gap(valuation_row: dict[str, str]) -> tuple[str, list[str]]:
    if not valuation_row:
        return "missing_table_row", ["valuation_rr"]
    status = valuation_row.get("valuation_status") or "missing_required_fields"
    if status == "ready":
        return status, []
    gaps = valuation_row.get("data_gaps")
    if gaps in (None, "", "null"):
        return status, ["valuation_rr"]
    return status, [f"valuation:{gap}" for gap in gaps.split(";") if gap]


def evidence_coverage_for(fundamentals_status: str, valuation_status: str) -> str:
    if fundamentals_status == "ready" and valuation_status == "ready":
        return "technicals_plus_fundamentals_valuation"
    if fundamentals_status == "missing_table_row" and valuation_status == "missing_table_row":
        return "technicals_only"
    return "technicals_plus_evidence_schema"


def score_row(
    ticker: str,
    holding: dict[str, Any],
    price_row: dict[str, str],
    fundamental_row: dict[str, str],
    valuation_row: dict[str, str],
    scored_at: str,
) -> dict[str, Any]:
    price = parse_number(price_row.get("price"))
    ma20 = parse_number(price_row.get("ma_20"))
    ma50 = parse_number(price_row.get("ma_50"))
    ma200 = parse_number(price_row.get("ma_200"))
    high_52w = parse_number(price_row.get("week_52_high"))
    stop_loss = read_stop_loss(ticker)
    tech = technical_score(price, ma20, ma50, ma200)
    flags = risk_flags(price, high_52w, ma200, stop_loss)
    fundamentals_status, fundamental_gaps = fundamentals_gap(fundamental_row)
    valuation_status, valuation_gaps = valuation_gap(valuation_row)
    gaps = MISSING_EVIDENCE_MODULES.copy() + fundamental_gaps + valuation_gaps
    action = action_for(price, ma20, ma50, ma200, flags)

    return {
        "ticker": ticker,
        "score": tech,
        "action": action,
        "target_weight": holding.get("target_weight"),
        "price": price,
        "main_reason": reason_for(action, tech, gaps),
        "risk_flags": ";".join(flags) if flags else "none",
        "source_date": price_row.get("source_date") or "null",
        "fetched_at": scored_at,
        "technical_score": tech,
        "fundamentals_status": fundamentals_status,
        "valuation_status": valuation_status,
        "evidence_coverage": evidence_coverage_for(fundamentals_status, valuation_status),
        "data_gaps": ";".join(gaps),
        "reversal_status": "pending_evidence",
        "reversal_triggers": ";".join(read_reversal_trigger_names(ticker)) or "none",
    }


def csv_value(value: Any) -> Any:
    return "null" if value is None else value


def write_scores(rows: list[dict[str, Any]], path: Path = SCORES_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in FIELDNAMES})


def main() -> int:
    portfolio = read_portfolio()
    prices = read_prices()
    fundamentals = read_fundamentals()
    valuation = read_valuation()
    scored_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = [
        score_row(ticker, holding, prices.get(ticker, {}), fundamentals.get(ticker, {}), valuation.get(ticker, {}), scored_at)
        for ticker, holding in portfolio.items()
    ]
    write_scores(rows)
    print(f"Wrote {SCORES_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
