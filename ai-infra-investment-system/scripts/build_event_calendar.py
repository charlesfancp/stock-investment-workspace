#!/usr/bin/env python3
"""Build a structured event calendar from manually maintained event inputs."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVENT_CONFIG_PATH = ROOT / "config" / "event_calendar.yaml"
OUTPUT_PATH = ROOT / "data" / "processed" / "event_calendar_latest.csv"

FIELDNAMES = [
    "ticker",
    "event_type",
    "event_date",
    "title",
    "source",
    "source_url",
    "source_tier",
    "status",
    "review_file",
    "days_until",
    "include_in_report",
    "notes",
    "fetched_at",
]


def parse_scalar(value: str) -> str | None:
    value = value.strip()
    if value in ("null", ""):
        return None
    return value.strip('"').strip("'")


def read_events(path: Path = EVENT_CONFIG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_events = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("events:"):
            in_events = True
            continue
        if line.startswith("watch_topics:"):
            break
        if not in_events:
            continue
        ticker_match = re.match(r"^\s*-\s+ticker:\s*(.+?)\s*$", line)
        if ticker_match:
            current = {"ticker": parse_scalar(ticker_match.group(1))}
            events.append(current)
            continue
        if current is None:
            continue
        field_match = re.match(r"^\s*([a-zA-Z_]+):\s*(.*?)\s*$", line)
        if field_match:
            current[field_match.group(1)] = parse_scalar(field_match.group(2))
    return events


def days_until(event_date: str | None, today: datetime) -> int | None:
    if not event_date:
        return None
    try:
        parsed = datetime.strptime(event_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (parsed.date() - today.date()).days


def include_in_report(event: dict[str, Any], days: int | None) -> bool:
    if days is None or days < 0 or days > 14:
        return False
    if not event.get("source") or not event.get("source_tier") or not event.get("event_date"):
        return False
    return event.get("source_tier") in {"tier_1", "tier_2"}


def has_required_source_fields(event: dict[str, Any]) -> bool:
    return bool(event.get("event_date") and event.get("source") and event.get("source_tier"))


def normalize_event(event: dict[str, Any], today: datetime, fetched_at: str) -> dict[str, Any]:
    delta = days_until(event.get("event_date"), today)
    included = include_in_report(event, delta)
    status = event.get("status")
    if not has_required_source_fields(event):
        status = "needs_source"
    return {
        "ticker": event.get("ticker"),
        "event_type": event.get("event_type"),
        "event_date": event.get("event_date"),
        "title": event.get("title"),
        "source": event.get("source"),
        "source_url": event.get("source_url"),
        "source_tier": event.get("source_tier"),
        "status": status,
        "review_file": event.get("review_file"),
        "days_until": delta,
        "include_in_report": included,
        "notes": event.get("notes"),
        "fetched_at": fetched_at,
    }


def csv_value(value: Any) -> Any:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_events(rows: list[dict[str, Any]], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in FIELDNAMES})


def build_calendar(today: datetime | None = None) -> list[dict[str, Any]]:
    now = today or datetime.now(timezone.utc)
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return [normalize_event(event, now, fetched_at) for event in read_events()]


def main() -> int:
    rows = build_calendar()
    write_events(rows)
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
