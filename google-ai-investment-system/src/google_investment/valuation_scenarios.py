from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .data_loader import MISSING, ValuationScenario, ValuationSnapshot
from .price_sensitivity import decision_for_price, rr_threshold_price


@dataclass(frozen=True)
class ValuationScenarioRow:
    scenario: str
    label: str
    probability: float
    target_price: float
    downside_price: float
    buy_below: float
    fair_price: float
    reduce_review_above: float
    current_rr: float | None
    current_upside_pct: float | None
    current_downside_pct: float | None
    current_decision: str
    status: str
    methodology: str
    source_name: str
    source_date: str
    notes: str


@dataclass(frozen=True)
class ValuationScenarioMatrix:
    available: bool
    summary: str
    current_price: float | None
    rows: list[ValuationScenarioRow]
    gaps: list[str]


def build_valuation_scenario_matrix(
    valuation: ValuationSnapshot | None,
    scenarios: list[ValuationScenario],
    as_of: date,
    stale_after_days: int,
) -> ValuationScenarioMatrix:
    current = valuation.numeric_value("current_price") if valuation else None
    if current is None:
        return ValuationScenarioMatrix(
            available=False,
            summary="当前价格缺失，不能判断不同估值情景下的动作区间。",
            current_price=None,
            rows=[],
            gaps=["current_price"],
        )

    rows: list[ValuationScenarioRow] = []
    gaps: list[str] = []
    for scenario in scenarios:
        if not scenario.is_usable(as_of, stale_after_days):
            gaps.append(scenario_gap(scenario, as_of, stale_after_days))
            continue
        target = scenario.numeric_value("target_price")
        downside = scenario.numeric_value("downside_price")
        probability = scenario.numeric_value("probability")
        if target is None or downside is None or probability is None or target <= downside:
            gaps.append(f"{scenario.scenario}: 目标价、下行价或概率不可用")
            continue
        buy_below = rr_threshold_price(target, downside, 1.5)
        fair_price = rr_threshold_price(target, downside, 1.0)
        reduce_review_above = rr_threshold_price(target, downside, 0.5)
        upside_pct = round((target - current) / current * 100, 1)
        downside_pct = round((current - downside) / current * 100, 1)
        current_rr = round(upside_pct / downside_pct, 2) if downside_pct > 0 else None
        decision, _ = decision_for_price(current, buy_below, fair_price, reduce_review_above, downside)
        rows.append(
            ValuationScenarioRow(
                scenario=scenario.scenario,
                label=scenario.label,
                probability=probability,
                target_price=target,
                downside_price=downside,
                buy_below=round(buy_below, 2),
                fair_price=round(fair_price, 2),
                reduce_review_above=round(reduce_review_above, 2),
                current_rr=current_rr,
                current_upside_pct=upside_pct,
                current_downside_pct=downside_pct,
                current_decision=decision,
                status=scenario.stale_status(as_of, stale_after_days),
                methodology=scenario.methodology,
                source_name=scenario.source_name,
                source_date=scenario.source_date,
                notes=scenario.notes,
            )
        )

    return ValuationScenarioMatrix(
        available=bool(rows),
        summary=matrix_summary(rows, current, gaps),
        current_price=current,
        rows=rows,
        gaps=gaps,
    )


def scenario_gap(scenario: ValuationScenario, as_of: date, stale_after_days: int) -> str:
    gaps = scenario.required_missing_fields[:]
    if scenario.stale_status(as_of, stale_after_days) != "未过期":
        gaps.append(f"时效={scenario.stale_status(as_of, stale_after_days)}")
    if scenario.verified_status != "已核实":
        gaps.append(f"核实状态={scenario.verified_status}")
    return f"{scenario.scenario}: {'、'.join(gaps) if gaps else '不可用'}"


def matrix_summary(rows: list[ValuationScenarioRow], current: float, gaps: list[str]) -> str:
    if not rows:
        return "估值情景缺失或不可用，不能判断当前价格在不同假设下是否稳健。"
    decisions = {row.current_decision for row in rows}
    if decisions == {"可买入复核"}:
        stance = "当前价在所有已录入情景下都达到买入复核门槛。"
    elif "减仓复盘" in decisions and "可买入复核" in decisions:
        stance = "风险情景进入减仓复盘区、乐观情景达到买入复核区，分歧较大；基准情景仍是核心锚点，不支持直接加仓。"
    elif "减仓复盘" in decisions:
        stance = "当前价在至少一个情景下进入减仓复盘区，持有结论需要重点复核。"
    elif "可买入复核" in decisions:
        stance = "当前价只在部分情景下达到买入复核门槛，不能直接升级为加仓。"
    else:
        stance = "当前价未在已录入情景中达到统一买入复核门槛。"
    gap_note = f" 另有 {len(gaps)} 个情景不可用。" if gaps else ""
    return f"当前价 ${current:.2f}：{stance}{gap_note}"


def scenario_matrix_missing_inputs(matrix: ValuationScenarioMatrix) -> list[str]:
    if matrix.available and not matrix.gaps:
        return []
    if matrix.gaps:
        return [f"估值情景矩阵：{gap}" for gap in matrix.gaps]
    return ["估值情景矩阵：valuation_scenarios.csv 缺失或没有可用情景"]
