#!/usr/bin/env python3
"""Check portfolio weight drift for manual rebalance review.

This script generates research alerts only. It never calculates order sizes or places trades.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "config" / "portfolio.yaml"
PORTFOLIO_STATE_PATH = ROOT / "data" / "processed" / "portfolio_state_latest.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "rebalance_check_latest.csv"
DEFAULT_THRESHOLD_PP = 2.0

FIELDNAMES = [
    "ticker",
    "target_weight",
    "current_weight",
    "weight_drift",
    "abs_weight_drift",
    "threshold_pp",
    "rebalance_status",
    "review_required",
    "reason",
    "position_status",
    "fetched_at",
]


def parse_number(value: str | float | None) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_rebalance_threshold(path: Path = PORTFOLIO_PATH) -> float:
    if not path.exists():
        return DEFAULT_THRESHOLD_PP
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^\s*drift_threshold_percentage_points:\s*([0-9.]+)\s*$", text, flags=re.MULTILINE)
    if not match:
        return DEFAULT_THRESHOLD_PP
    threshold = parse_number(match.group(1))
    if threshold is None or threshold <= 0:
        return DEFAULT_THRESHOLD_PP
    return threshold


def read_portfolio_state(path: Path = PORTFOLIO_STATE_PATH) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing portfolio state input: {path}")
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def classify_row(row: dict[str, str], threshold_pp: float, fetched_at: str) -> dict[str, Any]:
    target_weight = parse_number(row.get("target_weight"))
    current_weight = parse_number(row.get("current_weight"))
    weight_drift = parse_number(row.get("weight_drift"))
    position_status = row.get("position_status") or "unknown"

    if current_weight is None or weight_drift is None or position_status != "ready":
        return {
            "ticker": row.get("ticker"),
            "target_weight": target_weight,
            "current_weight": current_weight,
            "weight_drift": weight_drift,
            "abs_weight_drift": None,
            "threshold_pp": threshold_pp,
            "rebalance_status": "insufficient_data",
            "review_required": "false",
            "reason": "真实持仓或价格数据缺失，无法计算再平衡偏离",
            "position_status": position_status,
            "fetched_at": fetched_at,
        }

    abs_drift = abs(weight_drift)
    if abs_drift >= threshold_pp:
        status = "manual_review_overweight" if weight_drift > 0 else "manual_review_underweight"
        reason = f"当前权重较目标权重偏离 {weight_drift:.2f} 个百分点，达到人工复核阈值"
        review_required = "true"
    else:
        status = "within_threshold"
        reason = "当前权重偏离未达到人工再平衡复核阈值"
        review_required = "false"

    return {
        "ticker": row.get("ticker"),
        "target_weight": target_weight,
        "current_weight": current_weight,
        "weight_drift": weight_drift,
        "abs_weight_drift": abs_drift,
        "threshold_pp": threshold_pp,
        "rebalance_status": status,
        "review_required": review_required,
        "reason": reason,
        "position_status": position_status,
        "fetched_at": fetched_at,
    }


def build_rows(
    portfolio_state: list[dict[str, str]],
    threshold_pp: float,
    fetched_at: str,
) -> list[dict[str, Any]]:
    return [classify_row(row, threshold_pp, fetched_at) for row in portfolio_state]


def csv_value(value: Any) -> Any:
    if value is None:
        return "null"
    if isinstance(value, float):
        return round(value, 4)
    return value


def write_csv(rows: list[dict[str, Any]], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in FIELDNAMES})


def main() -> int:
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = build_rows(read_portfolio_state(), read_rebalance_threshold(), fetched_at)
    write_csv(rows)
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
