#!/usr/bin/env python3
"""Build portfolio state from manually confirmed positions and latest prices."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "config" / "portfolio.yaml"
POSITIONS_PATH = ROOT / "config" / "positions.yaml"
PRICES_PATH = ROOT / "data" / "processed" / "prices_latest.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "portfolio_state_latest.csv"

FIELDNAMES = [
    "ticker",
    "target_weight",
    "shares",
    "average_cost",
    "price",
    "market_value",
    "current_weight",
    "weight_drift",
    "position_status",
    "source_date",
    "fetched_at",
]


def parse_number(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


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
    if not holdings:
        raise ValueError(f"No holdings found in {path}")
    return holdings


def read_positions(path: Path = POSITIONS_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    positions: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        ticker_match = re.match(r"^\s*-\s+ticker:\s*([A-Z.]+)\s*$", line)
        if ticker_match:
            current = {"ticker": ticker_match.group(1)}
            positions[current["ticker"]] = current
            continue
        if current is None:
            continue
        for key in ("shares", "average_cost"):
            match = re.match(rf"^\s*{key}:\s*(.+?)\s*$", line)
            if match:
                current[key] = parse_number(match.group(1))
    return positions


def read_prices(path: Path = PRICES_PATH) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing price input: {path}")
    with path.open(encoding="utf-8", newline="") as file:
        return {row["ticker"]: row for row in csv.DictReader(file)}


def build_rows(
    portfolio: dict[str, dict[str, Any]],
    positions: dict[str, dict[str, Any]],
    prices: dict[str, dict[str, str]],
    fetched_at: str,
) -> list[dict[str, Any]]:
    preliminary: list[dict[str, Any]] = []
    for ticker, holding in portfolio.items():
        position = positions.get(ticker, {})
        price_row = prices.get(ticker, {})
        shares = position.get("shares")
        average_cost = position.get("average_cost")
        price = parse_number(price_row.get("price"))
        market_value = shares * price if shares is not None and price is not None else None
        if shares is None:
            status = "missing_position_input"
        elif price is None:
            status = "missing_price"
        else:
            status = "ready"
        preliminary.append(
            {
                "ticker": ticker,
                "target_weight": holding.get("target_weight"),
                "shares": shares,
                "average_cost": average_cost,
                "price": price,
                "market_value": market_value,
                "source_date": price_row.get("source_date") or None,
                "fetched_at": fetched_at,
                "position_status": status,
            }
        )

    total_market_value = sum(row["market_value"] or 0 for row in preliminary)
    for row in preliminary:
        if total_market_value > 0 and row["market_value"] is not None:
            row["current_weight"] = row["market_value"] / total_market_value * 100
            row["weight_drift"] = row["current_weight"] - (row["target_weight"] or 0)
        else:
            row["current_weight"] = None
            row["weight_drift"] = None
    return preliminary


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
    rows = build_rows(read_portfolio(), read_positions(), read_prices(), fetched_at)
    write_csv(rows)
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
