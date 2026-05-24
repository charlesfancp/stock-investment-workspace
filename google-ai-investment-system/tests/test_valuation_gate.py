from __future__ import annotations

from datetime import date

from google_investment.data_loader import ValuationSnapshot
from google_investment.report import action_with_valuation_gate, build_valuation_status, render_report
from google_investment.scoring import DimensionScore, Scorecard


CONFIG = {
    "stale_after_days": 92,
    "recommendations": {"buy": 82, "add": 72, "hold": 55, "reduce": 40},
}


def valuation(**overrides: str) -> ValuationSnapshot:
    values = {
        "date": "2026-05-18",
        "ticker": "GOOGL",
        "current_price": "390",
        "market_cap_usd_bn": "4800",
        "diluted_shares_bn": "12.2",
        "pe_ratio": "28",
        "fcf_yield_pct": "2.1",
        "ev_to_fcf": "45",
        "net_cash_usd_bn": "100",
        "source_url": "https://example.com/valuation",
        "source_date": "2026-05-18",
        "captured_at": "2026-05-18",
        "notes": "测试估值快照",
        "target_price_base": "480",
        "downside_price": "330",
        "valuation_methodology": "测试：基准目标价与风险下行价",
    }
    values.update(overrides)
    return ValuationSnapshot(**values)


def high_scorecard() -> Scorecard:
    return Scorecard(
        [
            DimensionScore("search_moat", "Search 护城河", 25, 25, "可用", ["测试"]),
            DimensionScore("cloud_second_curve", "Cloud 第二曲线", 35, 35, "可用", ["测试"]),
            DimensionScore("ai_roi_fcf", "AI ROI / FCF", 25, 25, "可用", ["测试"]),
            DimensionScore("valuation_position", "估值与仓位", 15, 15, "可用", ["测试"]),
        ]
    )


def test_missing_valuation_blocks_buy_or_add_action() -> None:
    assert action_with_valuation_gate("买入", missing_valuation=True) == "继续跟踪 / 待核实"
    assert action_with_valuation_gate("加仓", missing_valuation=True) == "继续跟踪 / 待核实"


def test_low_rr_blocks_buy_or_add_even_when_valuation_complete() -> None:
    snapshot = valuation(current_price="400", target_price_base="420", downside_price="340")

    assert action_with_valuation_gate("买入", missing_valuation=False, valuation=snapshot) == "持有 / 不加仓"
    assert action_with_valuation_gate("加仓", missing_valuation=False, valuation=snapshot) == "持有 / 不加仓"


def test_stale_valuation_is_marked_expired() -> None:
    snapshot = valuation(captured_at="2026-01-01", source_date="2026-01-01")

    assert snapshot.stale_status(date(2026, 5, 18), 92) == "过期"
    assert "时效=过期" in build_valuation_status(snapshot, date(2026, 5, 18), 92)


def test_missing_source_url_prevents_high_confidence_conclusion() -> None:
    snapshot = valuation(source_url="数据缺失")

    report = render_report([], high_scorecard(), CONFIG, date(2026, 5, 18), snapshot)

    assert "估值数据缺失" in report
    assert "继续跟踪 / 待核实" in report
    assert "买入" not in report.split("## 综合评分", maxsplit=1)[0]


def test_rr_requires_target_and_downside_prices() -> None:
    snapshot = valuation(target_price_base="数据缺失", downside_price="数据缺失")

    assert snapshot.rr_ratio is None
    assert not snapshot.is_complete(date(2026, 5, 18), 92)
    assert "target_price_base" in build_valuation_status(snapshot, date(2026, 5, 18), 92)


def test_rr_is_calculated_from_manual_valuation_inputs() -> None:
    snapshot = valuation(current_price="400", target_price_base="500", downside_price="350")

    assert snapshot.upside_pct == 25.0
    assert snapshot.downside_pct == 12.5
    assert snapshot.rr_ratio == 2.0
    assert snapshot.is_complete(date(2026, 5, 18), 92)


def test_report_shows_rr_calculation_when_valuation_is_complete() -> None:
    snapshot = valuation(current_price="400", target_price_base="500", downside_price="350")

    report = render_report([], high_scorecard(), CONFIG, date(2026, 5, 18), snapshot)

    assert "## R/R 与仓位资格" in report
    assert "R/R 状态：已解锁" in report
    assert "R/R：2.0" in report
    assert "模型假设，不是已验证事实" in report
