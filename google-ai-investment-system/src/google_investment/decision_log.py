from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


FIELDS = [
    "run_id",
    "generated_at",
    "date",
    "period",
    "ticker",
    "current_price",
    "score",
    "action",
    "confidence",
    "key_evidence",
    "contrary_evidence",
    "add_trigger",
    "reduce_trigger",
    "exit_trigger",
    "next_review_date",
    "change_reason",
]

DEDUP_FIELDS = ["date", "period", "ticker", "action", "score"]


@dataclass(frozen=True)
class DecisionLogEntry:
    run_id: str
    generated_at: str
    date: str
    period: str
    ticker: str
    current_price: str
    score: str
    action: str
    confidence: str
    key_evidence: str
    contrary_evidence: str
    add_trigger: str
    reduce_trigger: str
    exit_trigger: str
    next_review_date: str
    change_reason: str = ""

    def as_row(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in FIELDS}


@dataclass(frozen=True)
class DecisionLogWriteResult:
    status: str
    message: str


def append_decision_log(path: Path, entry: DecisionLogEntry) -> DecisionLogWriteResult:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = dedupe_rows(read_decision_log(path))
    entry_row = entry.as_row()
    if any(is_same_decision(row, entry_row) for row in rows):
        write_decision_log(path, rows)
        return DecisionLogWriteResult("skipped", "决策日志已存在，未重复写入")

    change_reason = detect_change_reason(rows, entry_row)
    if change_reason:
        entry_row["change_reason"] = change_reason
    rows.append(entry_row)
    write_decision_log(path, rows)
    return DecisionLogWriteResult("appended", "已更新决策日志")


def read_decision_log(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_row(row) for row in reader]


def write_decision_log(path: Path, rows: list[dict[str, str]]) -> None:
    rows = dedupe_rows(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(normalize_row(row) for row in rows)


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {field: row.get(field, "") or "" for field in FIELDS}
    if not normalized["run_id"]:
        normalized["run_id"] = build_run_id(normalized)
    if not normalized["generated_at"]:
        normalized["generated_at"] = normalized["date"]
    return normalized


def is_same_decision(existing: dict[str, str], incoming: dict[str, str]) -> bool:
    return all(existing.get(field, "") == incoming.get(field, "") for field in DEDUP_FIELDS)


def detect_change_reason(rows: list[dict[str, str]], incoming: dict[str, str]) -> str:
    for row in reversed(rows):
        same_context = (
            row.get("date") == incoming.get("date")
            and row.get("period") == incoming.get("period")
            and row.get("ticker") == incoming.get("ticker")
        )
        if same_context and (
            row.get("action") != incoming.get("action") or row.get("score") != incoming.get("score")
        ):
            return "判断变化"
    return incoming.get("change_reason", "")


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        normalized = normalize_row(row)
        key = tuple(normalized.get(field, "") for field in DEDUP_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def build_run_id(row: dict[str, str]) -> str:
    parts = [row.get(field, "") for field in DEDUP_FIELDS]
    return "|".join(parts)


def generated_at_now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()
