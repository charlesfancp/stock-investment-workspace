from __future__ import annotations

from datetime import date

from google_investment.data_loader import MetricRecord


def make_record(**overrides: str) -> MetricRecord:
    values = {
        "metric": "fcf_margin_pct",
        "value": "25",
        "unit": "%",
        "period": "2026Q1",
        "source_name": "Alphabet Form 10-Q",
        "source_url": "https://abc.xyz/investor/",
        "published_date": "2026-05-01",
        "accessed_date": "2026-05-10",
        "methodology": "官方财报口径",
        "verified_status": "已核实",
        "notes": "",
    }
    values.update(overrides)
    return MetricRecord(**values)


def test_missing_field_blocks_usable_record() -> None:
    record = make_record(source_url="数据缺失")

    assert "source_url" in record.missing_fields()
    assert not record.is_usable(date(2026, 5, 18), 92)


def test_unverified_record_is_not_usable() -> None:
    record = make_record(verified_status="待核实")

    assert not record.is_usable(date(2026, 5, 18), 92)


def test_data_older_than_three_months_is_stale() -> None:
    record = make_record(accessed_date="2026-01-01", published_date="2026-01-01")

    assert record.stale_status(date(2026, 5, 18), 92) == "过期"
    assert not record.is_usable(date(2026, 5, 18), 92)
