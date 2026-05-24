from __future__ import annotations

from datetime import date

from google_investment.data_loader import ValuationScenario, ValuationSnapshot
from google_investment.valuation_scenarios import build_valuation_scenario_matrix


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


def scenario(name: str, target: str, downside: str, probability: str = "50") -> ValuationScenario:
    return ValuationScenario(
        scenario=name,
        label=name,
        probability=probability,
        target_price=target,
        downside_price=downside,
        source_name="valuation_snapshot.csv",
        source_url="https://example.com",
        source_date="2026-05-20",
        captured_at="2026-05-20",
        methodology="模型假设",
        verified_status="已核实",
        notes="",
    )


def test_scenario_matrix_scores_current_price_by_scenario() -> None:
    matrix = build_valuation_scenario_matrix(
        valuation(),
        [
            scenario("risk", "360", "300", "25"),
            scenario("base", "428.96", "334.22", "50"),
            scenario("bull", "475", "350", "25"),
        ],
        date(2026, 5, 22),
        92,
    )

    decisions = {row.scenario: row.current_decision for row in matrix.rows}

    assert matrix.available is True
    assert decisions["risk"] == "减仓复盘"
    assert decisions["base"] == "持有 / 不加仓"
    assert decisions["bull"] == "可买入复核"
    assert matrix.rows[1].buy_below == 372.12


def test_scenario_matrix_reports_missing_current_price() -> None:
    missing_price = ValuationSnapshot(
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

    matrix = build_valuation_scenario_matrix(missing_price, [scenario("base", "428.96", "334.22")], date(2026, 5, 22), 92)

    assert matrix.available is False
    assert matrix.gaps == ["current_price"]
