from __future__ import annotations

from google_investment.data_loader import ValuationSnapshot
from google_investment.price_sensitivity import build_price_sensitivity


def valuation() -> ValuationSnapshot:
    return ValuationSnapshot(
        date="2026-05-20",
        ticker="GOOGL",
        current_price="387.66",
        target_price_base="428.96",
        downside_price="334.22",
        market_cap_usd_bn="4696.89",
        diluted_shares_bn="数据缺失",
        pe_ratio="29.57",
        fcf_yield_pct="1.37",
        ev_to_fcf="数据缺失",
        net_cash_usd_bn="数据缺失",
        source_url="https://stockanalysis.com/stocks/googl/forecast/",
        source_date="2026-05-20",
        captured_at="2026-05-20",
        valuation_methodology="外部目标价参考",
        notes="",
    )


def test_price_sensitivity_builds_thresholds_and_rows() -> None:
    sensitivity = build_price_sensitivity(valuation())

    assert sensitivity.available is True
    assert sensitivity.buy_below == 372.12
    assert sensitivity.reduce_review_above == 397.38
    assert any(row.decision == "可买入复核" for row in sensitivity.rows)
    assert any(row.decision == "持有 / 不加仓" for row in sensitivity.rows)
    assert any(row.decision == "减仓复盘" for row in sensitivity.rows)


def test_price_sensitivity_requires_complete_prices() -> None:
    incomplete = ValuationSnapshot(
        date="2026-05-20",
        ticker="GOOGL",
        current_price="数据缺失",
        target_price_base="428.96",
        downside_price="334.22",
        market_cap_usd_bn="4696.89",
        diluted_shares_bn="数据缺失",
        pe_ratio="29.57",
        fcf_yield_pct="1.37",
        ev_to_fcf="数据缺失",
        net_cash_usd_bn="数据缺失",
        source_url="https://example.com",
        source_date="2026-05-20",
        captured_at="2026-05-20",
        valuation_methodology="外部目标价参考",
        notes="",
    )

    sensitivity = build_price_sensitivity(incomplete)

    assert sensitivity.available is False
    assert sensitivity.rows == []
