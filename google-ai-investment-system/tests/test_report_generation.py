from __future__ import annotations

from datetime import date

from google_investment.data_loader import MetricRecord
from google_investment.report import render_report
from google_investment.scoring import recommendation_from_score, score_records


CONFIG = {
    "stale_after_days": 92,
    "score_dimensions": {
        "search_moat": {
            "label": "Search 护城河",
            "max_score": 25,
            "metrics": ["search_revenue_growth_yoy_pct", "search_operating_margin_pct"],
        },
        "cloud_second_curve": {
            "label": "Cloud 第二曲线",
            "max_score": 35,
            "metrics": ["cloud_revenue_growth_yoy_pct"],
        },
    },
    "recommendations": {"buy": 82, "add": 72, "hold": 55, "reduce": 40},
}


def record(metric: str, value: str = "10", verified_status: str = "已核实") -> MetricRecord:
    return MetricRecord(
        metric=metric,
        value=value,
        unit="%",
        period="2026Q1",
        source_name="Alphabet Form 10-Q",
        source_url="https://abc.xyz/investor/",
        published_date="2026-05-01",
        accessed_date="2026-05-10",
        methodology="官方财报口径",
        verified_status=verified_status,
        notes="",
    )


def test_score_uses_only_verified_complete_fresh_records() -> None:
    records = {
        "search_revenue_growth_yoy_pct": record("search_revenue_growth_yoy_pct"),
        "search_operating_margin_pct": record("search_operating_margin_pct", verified_status="待核实"),
        "cloud_revenue_growth_yoy_pct": record("cloud_revenue_growth_yoy_pct", value="数据缺失"),
    }

    scorecard = score_records(records, CONFIG, date(2026, 5, 18))

    assert scorecard.total_score == 8.8
    assert recommendation_from_score(scorecard.total_score, CONFIG) == "退出"


def test_report_contains_required_sections_and_missing_data_label() -> None:
    records = [record("search_revenue_growth_yoy_pct", value="数据缺失", verified_status="待核实")]
    scorecard = score_records({records[0].metric: records[0]}, CONFIG, date(2026, 5, 18))

    report = render_report(records, scorecard, CONFIG, date(2026, 5, 18))

    for heading in [
        "核心判断",
        "综合评分",
        "四个框架判断",
        "情景与概率",
        "触发条件",
        "风险信号",
        "价格敏感性与动作区间",
        "下季度跟踪清单",
        "数据来源与核实状态",
        "决策日志字段",
    ]:
        assert heading in report
    assert "数据缺失" in report
    assert "GOOG / GOOGL 需核实" in report
