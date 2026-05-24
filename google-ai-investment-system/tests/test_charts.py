from __future__ import annotations

from datetime import date

from google_investment.charts import generate_charts
from google_investment.data_loader import MetricRecord


def record(metric: str, value: str, period: str) -> MetricRecord:
    return MetricRecord(
        metric=metric,
        value=value,
        unit="%",
        period=period,
        source_name="Alphabet Q1 earnings release",
        source_url="https://example.com/source",
        published_date="2026-05-01",
        accessed_date="2026-05-18",
        methodology="官方口径",
        verified_status="已核实",
        notes="测试数据",
    )


def test_less_than_two_points_do_not_generate_chart(tmp_path) -> None:
    results = generate_charts(
        [record("cloud_revenue_growth_yoy_pct", "63", "2026Q1")],
        [],
        tmp_path,
        date(2026, 5, 18),
        92,
    )

    cloud = next(item for item in results if item.key == "cloud_revenue_growth")
    assert not cloud.generated
    assert cloud.message == "历史数据不足，暂不生成趋势图"
    assert not (tmp_path / "cloud_revenue_growth.png").exists()


def test_two_or_more_points_generate_chart(tmp_path) -> None:
    results = generate_charts(
        [
            record("cloud_revenue_growth_yoy_pct", "45", "2025Q4"),
            record("cloud_revenue_growth_yoy_pct", "63", "2026Q1"),
        ],
        [],
        tmp_path,
        date(2026, 5, 18),
        92,
    )

    cloud = next(item for item in results if item.key == "cloud_revenue_growth")
    assert cloud.generated
    assert (tmp_path / "cloud_revenue_growth.png").exists()


def test_missing_fields_do_not_crash_chart_generation(tmp_path) -> None:
    broken = MetricRecord(
        metric="search_revenue_growth_yoy_pct",
        value="数据缺失",
        unit="%",
        period="2026Q1",
        source_name="数据缺失",
        source_url="数据缺失",
        published_date="数据缺失",
        accessed_date="数据缺失",
        methodology="数据缺失",
        verified_status="待核实",
        notes="缺失字段测试",
    )

    results = generate_charts([broken], [], tmp_path, date(2026, 5, 18), 92)

    assert all(not item.generated for item in results)
