from __future__ import annotations

from dataclasses import dataclass

from .data_loader import MISSING, ValuationSnapshot


@dataclass(frozen=True)
class PriceSensitivityRow:
    price: float
    upside_pct: float | None
    downside_pct: float | None
    rr_ratio: float | None
    decision: str
    note: str


@dataclass(frozen=True)
class PriceSensitivity:
    available: bool
    summary: str
    methodology: str
    buy_below: float | None
    hold_range: str
    reduce_review_above: float | None
    rows: list[PriceSensitivityRow]


def build_price_sensitivity(
    valuation: ValuationSnapshot | None,
    min_buy_rr: float = 1.5,
    reduce_review_rr: float = 0.5,
) -> PriceSensitivity:
    if valuation is None:
        return unavailable("估值快照缺失，不能生成价格敏感性表。")

    current = valuation.numeric_value("current_price")
    target = valuation.numeric_value("target_price_base")
    downside = valuation.numeric_value("downside_price")
    if current is None or target is None or downside is None or target <= downside:
        return unavailable("current_price、target_price_base 或 downside_price 不完整，不能生成价格敏感性表。")

    buy_below = rr_threshold_price(target, downside, min_buy_rr)
    fair_price = rr_threshold_price(target, downside, 1.0)
    reduce_review_above = rr_threshold_price(target, downside, reduce_review_rr)
    prices = price_points(current, target, downside, buy_below, fair_price, reduce_review_above)
    rows = [
        build_row(price, target, downside, buy_below, fair_price, reduce_review_above)
        for price in prices
    ]
    return PriceSensitivity(
        available=True,
        summary=(
            f"R/R >= {min_buy_rr:.1f} 的复核买入价约为 ${buy_below:.2f} 以下；"
            f"${fair_price:.2f} 以上 R/R 低于 1；${reduce_review_above:.2f} 以上进入减仓复盘区。"
        ),
        methodology=(
            f"基准目标价 ${target:.2f}、风险下行价 ${downside:.2f} 沿用 valuation_snapshot.csv；"
            "上行=(基准目标价-假设价格)/假设价格；下行=(假设价格-风险下行价)/假设价格；"
            "R/R=上行/下行。目标价和下行价为模型假设，不是已验证事实。"
        ),
        buy_below=round(buy_below, 2),
        hold_range=f"${buy_below:.2f} - ${reduce_review_above:.2f}",
        reduce_review_above=round(reduce_review_above, 2),
        rows=rows,
    )


def unavailable(summary: str) -> PriceSensitivity:
    return PriceSensitivity(
        available=False,
        summary=summary,
        methodology="估值快照完整后自动生成；缺失时不得用猜测价格支撑买入、加仓或减仓结论。",
        buy_below=None,
        hold_range=MISSING,
        reduce_review_above=None,
        rows=[],
    )


def rr_threshold_price(target: float, downside: float, rr: float) -> float:
    return (target + rr * downside) / (1 + rr)


def price_points(
    current: float,
    target: float,
    downside: float,
    buy_below: float,
    fair_price: float,
    reduce_review_above: float,
) -> list[float]:
    raw = [
        downside,
        round_to_nearest(downside * 1.05, 5),
        round_to_nearest(downside * 1.10, 5),
        buy_below,
        fair_price,
        current,
        reduce_review_above,
        round_to_nearest((reduce_review_above + target) / 2, 5),
        target,
    ]
    bounded = [price for price in raw if price > 0]
    return sorted({round(price, 2) for price in bounded})


def build_row(
    price: float,
    target: float,
    downside: float,
    buy_below: float,
    fair_price: float,
    reduce_review_above: float,
) -> PriceSensitivityRow:
    upside = round((target - price) / price * 100, 1)
    downside_pct = round((price - downside) / price * 100, 1)
    rr_ratio = round(upside / downside_pct, 2) if downside_pct > 0 else None
    decision, note = decision_for_price(price, buy_below, fair_price, reduce_review_above, downside)
    return PriceSensitivityRow(
        price=price,
        upside_pct=upside,
        downside_pct=downside_pct,
        rr_ratio=rr_ratio,
        decision=decision,
        note=note,
    )


def decision_for_price(
    price: float,
    buy_below: float,
    fair_price: float,
    reduce_review_above: float,
    downside: float,
) -> tuple[str, str]:
    price_2 = round(price, 2)
    downside_2 = round(downside, 2)
    buy_below_2 = round(buy_below, 2)
    fair_price_2 = round(fair_price, 2)
    reduce_review_above_2 = round(reduce_review_above, 2)
    if price_2 <= downside_2:
        return "风险价以下 / 先复核", "价格低于风险情景，下行假设可能需要重估，不自动加仓。"
    if price_2 <= buy_below_2:
        return "可买入复核", "R/R 达到 1.5 门槛；仍需确认 Search、Cloud、FCF 和监管风险未恶化。"
    if price_2 <= fair_price_2:
        return "持有 / 等待", "R/R 在 1.0-1.5，估值有边际但未达到加仓门槛。"
    if price_2 < reduce_review_above_2:
        return "持有 / 不加仓", "R/R 低于 1，当前价格对目标价和下行价不够有利。"
    return "减仓复盘", "R/R 低于 0.5，需复核仓位、目标价和新增证据。"


def round_to_nearest(value: float, step: int) -> float:
    return round(value / step) * step
