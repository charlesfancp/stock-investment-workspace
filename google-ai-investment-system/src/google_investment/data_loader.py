from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


MISSING = "数据缺失"
VERIFIED = "已核实"


@dataclass(frozen=True)
class MetricRecord:
    metric: str
    value: str
    unit: str
    period: str
    source_name: str
    source_url: str
    published_date: str
    accessed_date: str
    methodology: str
    verified_status: str
    notes: str

    @property
    def numeric_value(self) -> float | None:
        if self.value.strip() in {"", MISSING}:
            return None
        try:
            return float(self.value)
        except ValueError:
            return None

    def missing_fields(self) -> list[str]:
        required = {
            "value": self.value,
            "period": self.period,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "published_date": self.published_date,
            "accessed_date": self.accessed_date,
            "methodology": self.methodology,
            "verified_status": self.verified_status,
        }
        return [field for field, value in required.items() if value.strip() in {"", MISSING}]

    def age_days(self, as_of: date) -> int | None:
        parsed = parse_date(self.accessed_date) or parse_date(self.published_date)
        if parsed is None:
            return None
        return (as_of - parsed).days

    def stale_status(self, as_of: date, stale_after_days: int) -> str:
        age = self.age_days(as_of)
        if age is None:
            return MISSING
        return "过期" if age > stale_after_days else "未过期"

    def is_usable(self, as_of: date, stale_after_days: int) -> bool:
        return (
            not self.missing_fields()
            and self.numeric_value is not None
            and self.verified_status == VERIFIED
            and self.stale_status(as_of, stale_after_days) == "未过期"
        )


@dataclass(frozen=True)
class ValuationSnapshot:
    date: str
    ticker: str
    current_price: str
    market_cap_usd_bn: str
    diluted_shares_bn: str
    pe_ratio: str
    fcf_yield_pct: str
    ev_to_fcf: str
    net_cash_usd_bn: str
    source_url: str
    source_date: str
    captured_at: str
    notes: str
    target_price_base: str = MISSING
    downside_price: str = MISSING
    valuation_methodology: str = MISSING

    @property
    def required_missing_fields(self) -> list[str]:
        required = {
            "current_price": self.current_price,
            "pe_ratio": self.pe_ratio,
            "fcf_yield_pct": self.fcf_yield_pct,
            "source_url": self.source_url,
            "captured_at": self.captured_at,
            "target_price_base": self.target_price_base,
            "downside_price": self.downside_price,
            "valuation_methodology": self.valuation_methodology,
        }
        return [field for field, value in required.items() if value.strip() in {"", MISSING}]

    def numeric_value(self, field: str) -> float | None:
        value = getattr(self, field)
        if value.strip() in {"", MISSING}:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def age_days(self, as_of: date) -> int | None:
        parsed = parse_date(self.captured_at) or parse_date(self.source_date)
        if parsed is None:
            return None
        return (as_of - parsed).days

    def stale_status(self, as_of: date, stale_after_days: int) -> str:
        age = self.age_days(as_of)
        if age is None:
            return MISSING
        return "过期" if age > stale_after_days else "未过期"

    def is_complete(self, as_of: date, stale_after_days: int) -> bool:
        numeric_fields = ["current_price", "pe_ratio", "fcf_yield_pct", "target_price_base", "downside_price"]
        return (
            not self.required_missing_fields
            and all(self.numeric_value(field) is not None for field in numeric_fields)
            and self.stale_status(as_of, stale_after_days) == "未过期"
        )

    @property
    def upside_pct(self) -> float | None:
        current = self.numeric_value("current_price")
        target = self.numeric_value("target_price_base")
        if current is None or target is None or current <= 0:
            return None
        return round((target - current) / current * 100, 1)

    @property
    def downside_pct(self) -> float | None:
        current = self.numeric_value("current_price")
        downside = self.numeric_value("downside_price")
        if current is None or downside is None or current <= 0:
            return None
        return round((current - downside) / current * 100, 1)

    @property
    def rr_ratio(self) -> float | None:
        upside = self.upside_pct
        downside = self.downside_pct
        if upside is None or downside is None or downside <= 0:
            return None
        return round(upside / downside, 2)


@dataclass(frozen=True)
class ValuationScenario:
    scenario: str
    label: str
    probability: str
    target_price: str
    downside_price: str
    source_name: str
    source_url: str
    source_date: str
    captured_at: str
    methodology: str
    verified_status: str
    notes: str

    def numeric_value(self, field: str) -> float | None:
        value = getattr(self, field)
        if value.strip() in {"", MISSING}:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @property
    def required_missing_fields(self) -> list[str]:
        required = {
            "scenario": self.scenario,
            "probability": self.probability,
            "target_price": self.target_price,
            "downside_price": self.downside_price,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "source_date": self.source_date,
            "captured_at": self.captured_at,
            "methodology": self.methodology,
            "verified_status": self.verified_status,
        }
        return [field for field, value in required.items() if value.strip() in {"", MISSING}]

    def age_days(self, as_of: date) -> int | None:
        parsed = parse_date(self.captured_at) or parse_date(self.source_date)
        if parsed is None:
            return None
        return (as_of - parsed).days

    def stale_status(self, as_of: date, stale_after_days: int) -> str:
        age = self.age_days(as_of)
        if age is None:
            return MISSING
        return "过期" if age > stale_after_days else "未过期"

    def is_usable(self, as_of: date, stale_after_days: int) -> bool:
        return (
            not self.required_missing_fields
            and self.numeric_value("probability") is not None
            and self.numeric_value("target_price") is not None
            and self.numeric_value("downside_price") is not None
            and self.verified_status == VERIFIED
            and self.stale_status(as_of, stale_after_days) == "未过期"
        )


def parse_date(value: str) -> date | None:
    if value.strip() in {"", MISSING}:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def load_metric_records(path: Path) -> list[MetricRecord]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            MetricRecord(
                metric=row.get("metric", MISSING) or MISSING,
                value=row.get("value", MISSING) or MISSING,
                unit=row.get("unit", MISSING) or MISSING,
                period=row.get("period", MISSING) or MISSING,
                source_name=row.get("source_name", MISSING) or MISSING,
                source_url=row.get("source_url", MISSING) or MISSING,
                published_date=row.get("published_date", MISSING) or MISSING,
                accessed_date=row.get("accessed_date", MISSING) or MISSING,
                methodology=row.get("methodology", MISSING) or MISSING,
                verified_status=row.get("verified_status", MISSING) or MISSING,
                notes=row.get("notes", "") or "",
            )
            for row in reader
        ]


def load_valuation_snapshots(path: Path) -> list[ValuationSnapshot]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            ValuationSnapshot(
                date=row.get("date", MISSING) or MISSING,
                ticker=row.get("ticker", MISSING) or MISSING,
                current_price=row.get("current_price", MISSING) or MISSING,
                market_cap_usd_bn=row.get("market_cap_usd_bn", MISSING) or MISSING,
                diluted_shares_bn=row.get("diluted_shares_bn", MISSING) or MISSING,
                pe_ratio=row.get("pe_ratio", MISSING) or MISSING,
                fcf_yield_pct=row.get("fcf_yield_pct", MISSING) or MISSING,
                ev_to_fcf=row.get("ev_to_fcf", MISSING) or MISSING,
                net_cash_usd_bn=row.get("net_cash_usd_bn", MISSING) or MISSING,
                source_url=row.get("source_url", MISSING) or MISSING,
                source_date=row.get("source_date", MISSING) or MISSING,
                captured_at=row.get("captured_at", MISSING) or MISSING,
                notes=row.get("notes", "") or "",
                target_price_base=row.get("target_price_base", MISSING) or MISSING,
                downside_price=row.get("downside_price", MISSING) or MISSING,
                valuation_methodology=row.get("valuation_methodology", MISSING) or MISSING,
            )
            for row in reader
        ]


def load_valuation_scenarios(path: Path) -> list[ValuationScenario]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            ValuationScenario(
                scenario=row.get("scenario", MISSING) or MISSING,
                label=row.get("label", MISSING) or MISSING,
                probability=row.get("probability", MISSING) or MISSING,
                target_price=row.get("target_price", MISSING) or MISSING,
                downside_price=row.get("downside_price", MISSING) or MISSING,
                source_name=row.get("source_name", MISSING) or MISSING,
                source_url=row.get("source_url", MISSING) or MISSING,
                source_date=row.get("source_date", MISSING) or MISSING,
                captured_at=row.get("captured_at", MISSING) or MISSING,
                methodology=row.get("methodology", MISSING) or MISSING,
                verified_status=row.get("verified_status", MISSING) or MISSING,
                notes=row.get("notes", "") or "",
            )
            for row in reader
        ]


def latest_valuation_snapshot(snapshots: Iterable[ValuationSnapshot]) -> ValuationSnapshot | None:
    latest: ValuationSnapshot | None = None
    latest_date: date | None = None
    for snapshot in snapshots:
        parsed = parse_date(snapshot.date) or parse_date(snapshot.captured_at) or date.min
        if latest is None or parsed >= (latest_date or date.min):
            latest = snapshot
            latest_date = parsed
    return latest


def latest_by_metric(records: Iterable[MetricRecord]) -> dict[str, MetricRecord]:
    latest: dict[str, MetricRecord] = {}
    for record in records:
        latest[record.metric] = record
    return latest


def valuation_metric_records(valuation: ValuationSnapshot | None) -> list[MetricRecord]:
    if valuation is None:
        return []
    source_name = "valuation_snapshot.csv / analyst_snapshot.csv"
    methodology = valuation.valuation_methodology
    common = {
        "period": valuation.date,
        "source_name": source_name,
        "source_url": valuation.source_url,
        "published_date": valuation.source_date,
        "accessed_date": valuation.captured_at,
        "methodology": methodology,
        "verified_status": VERIFIED,
        "notes": "由估值快照派生；目标价和下行价为模型假设，不是已验证事实",
    }
    rows = [
        ("forward_pe", valuation.pe_ratio, "x"),
        ("fcf_yield_pct", valuation.fcf_yield_pct, "%"),
        ("rr_ratio", str(valuation.rr_ratio) if valuation.rr_ratio is not None else MISSING, "x"),
    ]
    return [
        MetricRecord(
            metric=metric,
            value=value,
            unit=unit,
            **common,
        )
        for metric, value, unit in rows
    ]
