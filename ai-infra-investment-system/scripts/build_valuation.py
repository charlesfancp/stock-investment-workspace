#!/usr/bin/env python3
"""Build a structured valuation table from manually confirmed inputs."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALUATION_CONFIG_PATH = ROOT / "config" / "valuation.yaml"
OUTPUT_PATH = ROOT / "data" / "processed" / "valuation_latest.csv"

FIELDNAMES = [
    "ticker",
    "market_cap",
    "pe_ttm",
    "pe_forward",
    "ev_sales",
    "fcf_yield",
    "valuation_percentile",
    "analyst_target_price_median",
    "upside_to_target",
    "valuation_commentary",
    "source",
    "source_url",
    "source_tier",
    "source_type",
    "source_date",
    "verified_status",
    "freshness_status",
    "conclusion_eligible",
    "valuation_status",
    "data_gaps",
    "notes",
    "fetched_at",
]

REQUIRED_FIELDS = [
    "market_cap",
    "pe_forward",
    "fcf_yield",
    "valuation_percentile",
    "source",
    "source_url",
    "source_tier",
    "source_type",
    "source_date",
    "verified_status",
]

ALLOWED_SOURCE_TIERS = {"tier_1", "tier_2"}
ALLOWED_SOURCE_TYPES = {"original", "secondary", "estimate", "model"}
FRESHNESS_THRESHOLD_DAYS = 30


def parse_scalar(value: str) -> str | None:
    value = value.strip()
    if value in ("", "null"):
        return None
    return value.strip('"').strip("'")


def read_valuation(path: Path = VALUATION_CONFIG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_metrics = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("metrics:"):
            in_metrics = True
            continue
        if not in_metrics:
            continue
        ticker_match = re.match(r"^\s*-\s+ticker:\s*(.+?)\s*$", line)
        if ticker_match:
            current = {"ticker": parse_scalar(ticker_match.group(1))}
            rows.append(current)
            continue
        if current is None:
            continue
        field_match = re.match(r"^\s*([a-zA-Z_]+):\s*(.*?)\s*$", line)
        if field_match:
            current[field_match.group(1)] = parse_scalar(field_match.group(2))
    return rows


def missing_fields(row: dict[str, Any]) -> list[str]:
    return [field for field in REQUIRED_FIELDS if row.get(field) in (None, "", "null")]


def parse_source_date(value: str | None) -> datetime | None:
    if value in (None, "", "null"):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def freshness_status(source_date: str | None, fetched_at: str, threshold_days: int = FRESHNESS_THRESHOLD_DAYS) -> str:
    parsed_source_date = parse_source_date(source_date)
    if parsed_source_date is None:
        return "missing_or_invalid_source_date"
    fetched_date = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    age_days = (fetched_date.date() - parsed_source_date.date()).days
    if age_days < 0:
        return "future_source_date"
    if age_days > threshold_days:
        return "stale"
    return "current"


def data_quality_gaps(row: dict[str, Any], fetched_at: str) -> list[str]:
    gaps: list[str] = []
    if row.get("source_tier") not in (None, "", "null") and row.get("source_tier") not in ALLOWED_SOURCE_TIERS:
        gaps.append("invalid_or_low_tier_source")
    if row.get("source_type") not in (None, "", "null") and row.get("source_type") not in ALLOWED_SOURCE_TYPES:
        gaps.append("invalid_source_type")
    if row.get("verified_status") not in (None, "", "null") and row.get("verified_status") != "verified":
        gaps.append("not_verified")
    freshness = freshness_status(row.get("source_date"), fetched_at)
    if row.get("source_date") not in (None, "", "null") and freshness != "current":
        gaps.append(f"freshness:{freshness}")
    return gaps


def normalize_row(row: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    freshness = freshness_status(row.get("source_date"), fetched_at)
    gaps = [*missing_fields(row), *data_quality_gaps(row, fetched_at)]
    conclusion_eligible = "true" if not gaps else "false"
    return {
        **row,
        "freshness_status": freshness,
        "conclusion_eligible": conclusion_eligible,
        "valuation_status": "ready" if not gaps else "missing_required_fields",
        "data_gaps": ";".join(gaps) if gaps else "none",
        "fetched_at": fetched_at,
    }


def csv_value(value: Any) -> Any:
    return "null" if value is None else value


def write_csv(rows: list[dict[str, Any]], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in FIELDNAMES})


def main() -> int:
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = [normalize_row(row, fetched_at) for row in read_valuation()]
    write_csv(rows)
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
