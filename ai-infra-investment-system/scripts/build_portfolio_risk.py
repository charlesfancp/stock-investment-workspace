#!/usr/bin/env python3
"""Build portfolio-level risk summary from existing research outputs."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCORES_PATH = ROOT / "data" / "processed" / "scores_latest.csv"
PORTFOLIO_STATE_PATH = ROOT / "data" / "processed" / "portfolio_state_latest.csv"
REBALANCE_CHECK_PATH = ROOT / "data" / "processed" / "rebalance_check_latest.csv"
EVENT_CALENDAR_PATH = ROOT / "data" / "processed" / "event_calendar_latest.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "portfolio_risk_latest.csv"

FIELDNAMES = [
    "risk_area",
    "risk_level",
    "metric",
    "value",
    "threshold",
    "status",
    "details",
    "fetched_at",
]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def risk_level_for_count(count: int, medium_threshold: int, high_threshold: int) -> str:
    if count >= high_threshold:
        return "high"
    if count >= medium_threshold:
        return "medium"
    return "low"


def portfolio_state_risk(rows: list[dict[str, str]], fetched_at: str) -> dict[str, Any]:
    missing = [row.get("ticker") for row in rows if row.get("position_status") != "ready"]
    return {
        "risk_area": "position_data",
        "risk_level": "high" if missing else "low",
        "metric": "missing_position_count",
        "value": len(missing),
        "threshold": "0",
        "status": "needs_manual_position_input" if missing else "ready",
        "details": ";".join(missing) if missing else "none",
        "fetched_at": fetched_at,
    }


def technical_overheat_risk(rows: list[dict[str, str]], fetched_at: str) -> dict[str, Any]:
    overheated = [
        row.get("ticker")
        for row in rows
        if row.get("risk_flags") not in (None, "", "none", "null")
    ]
    return {
        "risk_area": "technical_overheat",
        "risk_level": risk_level_for_count(len(overheated), medium_threshold=3, high_threshold=5),
        "metric": "overheated_ticker_count",
        "value": len(overheated),
        "threshold": "medium>=3;high>=5",
        "status": "overheat_review" if overheated else "clear",
        "details": ";".join(overheated) if overheated else "none",
        "fetched_at": fetched_at,
    }


def event_density_risk(rows: list[dict[str, str]], fetched_at: str) -> dict[str, Any]:
    reportable = [row.get("ticker") for row in rows if row.get("include_in_report") == "true"]
    return {
        "risk_area": "event_density",
        "risk_level": risk_level_for_count(len(reportable), medium_threshold=3, high_threshold=5),
        "metric": "reportable_event_count_14d",
        "value": len(reportable),
        "threshold": "medium>=3;high>=5",
        "status": "dense_event_window" if reportable else "no_reportable_events",
        "details": ";".join(reportable) if reportable else "none",
        "fetched_at": fetched_at,
    }


def evidence_gap_risk(rows: list[dict[str, str]], status_field: str, area: str, fetched_at: str) -> dict[str, Any]:
    missing = [row.get("ticker") for row in rows if row.get(status_field) != "ready"]
    return {
        "risk_area": area,
        "risk_level": risk_level_for_count(len(missing), medium_threshold=3, high_threshold=6),
        "metric": f"{status_field}_missing_count",
        "value": len(missing),
        "threshold": "medium>=3;high>=6",
        "status": "missing_required_fields" if missing else "ready",
        "details": ";".join(missing) if missing else "none",
        "fetched_at": fetched_at,
    }


def rebalance_risk(rows: list[dict[str, str]], fetched_at: str) -> dict[str, Any]:
    review = [row.get("ticker") for row in rows if row.get("review_required") == "true"]
    insufficient = [row.get("ticker") for row in rows if row.get("rebalance_status") == "insufficient_data"]
    if review:
        level = "medium"
        status = "manual_rebalance_review"
        details = ";".join(review)
    elif insufficient:
        level = "medium"
        status = "insufficient_position_data"
        details = ";".join(insufficient)
    else:
        level = "low"
        status = "within_threshold"
        details = "none"
    return {
        "risk_area": "rebalance",
        "risk_level": level,
        "metric": "manual_review_or_insufficient_count",
        "value": len(review) if review else len(insufficient),
        "threshold": "review_required=true",
        "status": status,
        "details": details,
        "fetched_at": fetched_at,
    }


def thesis_risk(rows: list[dict[str, str]], fetched_at: str) -> dict[str, Any]:
    confirmed = [row.get("ticker") for row in rows if row.get("reversal_status") == "thesis_broken_confirmed"]
    pending = [row.get("ticker") for row in rows if row.get("reversal_status") == "thesis_broken_pending_confirmation"]
    if confirmed:
        level = "high"
        status = "confirmed_thesis_break"
        details = ";".join(confirmed)
    elif pending:
        level = "medium"
        status = "pending_thesis_break"
        details = ";".join(pending)
    else:
        level = "low"
        status = "no_confirmed_break"
        details = "none"
    return {
        "risk_area": "thesis_reversal",
        "risk_level": level,
        "metric": "thesis_break_count",
        "value": len(confirmed) + len(pending),
        "threshold": "confirmed_or_pending_break>0",
        "status": status,
        "details": details,
        "fetched_at": fetched_at,
    }


def build_rows(
    scores: list[dict[str, str]],
    portfolio_state: list[dict[str, str]],
    rebalance: list[dict[str, str]],
    events: list[dict[str, str]],
    fetched_at: str,
) -> list[dict[str, Any]]:
    return [
        portfolio_state_risk(portfolio_state, fetched_at),
        technical_overheat_risk(scores, fetched_at),
        event_density_risk(events, fetched_at),
        evidence_gap_risk(scores, "fundamentals_status", "fundamentals_coverage", fetched_at),
        evidence_gap_risk(scores, "valuation_status", "valuation_coverage", fetched_at),
        rebalance_risk(rebalance, fetched_at),
        thesis_risk(scores, fetched_at),
    ]


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
    rows = build_rows(
        read_csv_rows(SCORES_PATH),
        read_csv_rows(PORTFOLIO_STATE_PATH),
        read_csv_rows(REBALANCE_CHECK_PATH),
        read_csv_rows(EVENT_CALENDAR_PATH),
        fetched_at,
    )
    write_csv(rows)
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
