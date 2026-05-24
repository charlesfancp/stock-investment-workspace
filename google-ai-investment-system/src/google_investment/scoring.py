from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .data_loader import MISSING, MetricRecord


@dataclass(frozen=True)
class DimensionScore:
    key: str
    label: str
    score: float
    max_score: float
    status: str
    reasons: list[str]


@dataclass(frozen=True)
class Scorecard:
    dimensions: list[DimensionScore]

    @property
    def total_score(self) -> float:
        return round(sum(item.score for item in self.dimensions), 1)

    @property
    def max_score(self) -> float:
        return sum(item.max_score for item in self.dimensions)


def score_records(
    records_by_metric: dict[str, MetricRecord],
    config: dict[str, Any],
    as_of: date,
) -> Scorecard:
    stale_after_days = int(config.get("stale_after_days", 92))
    dimensions: list[DimensionScore] = []
    for key, dimension in config["score_dimensions"].items():
        metrics = dimension["metrics"]
        max_score = float(dimension["max_score"])
        if key == "search_moat":
            dimensions.append(score_search_moat(records_by_metric, metrics, max_score, dimension["label"], as_of, stale_after_days))
            continue
        if key == "cloud_second_curve":
            dimensions.append(score_cloud_second_curve(records_by_metric, metrics, max_score, dimension["label"], as_of, stale_after_days))
            continue
        if key == "ai_roi_fcf":
            dimensions.append(score_ai_roi_fcf(records_by_metric, metrics, max_score, dimension["label"], as_of, stale_after_days))
            continue
        if key == "valuation_position":
            dimensions.append(score_valuation_position(records_by_metric, metrics, max_score, dimension["label"], as_of, stale_after_days))
            continue
        usable = []
        reasons: list[str] = []
        for metric in metrics:
            record = records_by_metric.get(metric)
            if record is None:
                reasons.append(f"{metric}: {MISSING}")
                continue
            if record.is_usable(as_of, stale_after_days):
                usable.append(record)
                continue
            problems = []
            if record.missing_fields():
                problems.append("字段缺失")
            if record.verified_status != "已核实":
                problems.append(f"核实状态={record.verified_status}")
            stale_status = record.stale_status(as_of, stale_after_days)
            if stale_status != "未过期":
                problems.append(f"时效={stale_status}")
            if record.numeric_value is None:
                problems.append("数值不可用")
            reasons.append(f"{metric}: {'、'.join(problems)}")
        score = round(max_score * len(usable) / len(metrics), 1) if metrics else 0.0
        status = "可用" if len(usable) == len(metrics) else "保守扣分"
        dimensions.append(
            DimensionScore(
                key=key,
                label=dimension["label"],
                score=score,
                max_score=max_score,
                status=status,
                reasons=reasons or ["全部关键字段已核实且未过期"],
            )
        )
    return Scorecard(dimensions)


def usable_numeric(
    records_by_metric: dict[str, MetricRecord],
    metric: str,
    as_of: date,
    stale_after_days: int,
) -> tuple[MetricRecord | None, float | None]:
    record = records_by_metric.get(metric)
    if record is None or not record.is_usable(as_of, stale_after_days) or record.numeric_value is None:
        return record, None
    return record, record.numeric_value


def score_search_moat(
    records_by_metric: dict[str, MetricRecord],
    metrics: list[str],
    max_score: float,
    label: str,
    as_of: date,
    stale_after_days: int,
) -> DimensionScore:
    per_metric = max_score / len(metrics)
    score = 0.0
    reasons: list[str] = []
    for metric in metrics:
        record, value = usable_numeric(records_by_metric, metric, as_of, stale_after_days)
        if value is None:
            reasons.append(f"{metric}: {MISSING}")
            continue
        if metric == "search_revenue_growth_yoy_pct":
            if value >= 15:
                score += per_metric
                reasons.append("Search 增速强")
            elif value >= 10:
                score += per_metric * 0.7
                reasons.append("Search 增速合格")
            elif value >= 8:
                score += per_metric * 0.4
                reasons.append("Search 增速接近危险线")
            else:
                reasons.append("Search 增速危险")
        elif metric == "search_operating_margin_pct":
            if value >= 40:
                score += per_metric
                reasons.append("Google Services margin 代理显示利润质量强")
            elif value >= 30:
                score += per_metric * 0.7
                reasons.append("Google Services margin 代理显示利润质量合格")
            else:
                score += per_metric * 0.3
                reasons.append("Google Services margin 代理偏弱")
        elif metric == "search_market_share_pct":
            if value >= 88:
                score += per_metric
                reasons.append("搜索份额仍高")
            elif value >= 80:
                score += per_metric * 0.7
                reasons.append("搜索份额仍可接受")
            else:
                score += per_metric * 0.3
                reasons.append("搜索份额承压")
        else:
            score += per_metric
            reasons.append(f"{metric}: 已核实")
    rounded = round(score, 1)
    status = "强" if rounded >= max_score * 0.8 else "可用" if rounded >= max_score * 0.6 else "偏弱"
    return DimensionScore("search_moat", label, rounded, max_score, status, reasons)


def score_cloud_second_curve(
    records_by_metric: dict[str, MetricRecord],
    metrics: list[str],
    max_score: float,
    label: str,
    as_of: date,
    stale_after_days: int,
) -> DimensionScore:
    per_metric = max_score / len(metrics)
    score = 0.0
    reasons: list[str] = []
    for metric in metrics:
        record, value = usable_numeric(records_by_metric, metric, as_of, stale_after_days)
        if value is None:
            reasons.append(f"{metric}: {MISSING}")
            continue
        if metric == "cloud_revenue_growth_yoy_pct":
            if value >= 45:
                score += per_metric
                reasons.append("Cloud 增速强")
            elif value >= 35:
                score += per_metric * 0.7
                reasons.append("Cloud 增速合格")
            elif value >= 30:
                score += per_metric * 0.4
                reasons.append("Cloud 增速接近危险线")
            else:
                reasons.append("Cloud 增速危险")
        elif metric == "cloud_operating_margin_pct":
            if value >= 28:
                score += per_metric
                reasons.append("Cloud margin 强")
            elif value >= 25:
                score += per_metric * 0.7
                reasons.append("Cloud margin 合格")
            elif value >= 20:
                score += per_metric * 0.4
                reasons.append("Cloud margin 接近危险线")
            else:
                reasons.append("Cloud margin 危险")
        elif metric == "cloud_backlog_growth_yoy_pct":
            has_method_change = record and ("口径变化" in record.methodology or "口径变化" in record.notes)
            if has_method_change:
                score += per_metric * 0.45
                reasons.append("Cloud backlog 原始增速强但口径变化，折扣计分")
            elif value >= 45:
                score += per_metric
                reasons.append("Cloud backlog 增速强")
            elif value >= 25:
                score += per_metric * 0.7
                reasons.append("Cloud backlog 增速合格")
            else:
                score += per_metric * 0.3
                reasons.append("Cloud backlog 增速偏弱")
        else:
            score += per_metric
            reasons.append(f"{metric}: 已核实")
    rounded = round(score, 1)
    status = "强" if rounded >= max_score * 0.8 else "可用" if rounded >= max_score * 0.6 else "偏弱"
    return DimensionScore("cloud_second_curve", label, rounded, max_score, status, reasons)


def score_ai_roi_fcf(
    records_by_metric: dict[str, MetricRecord],
    metrics: list[str],
    max_score: float,
    label: str,
    as_of: date,
    stale_after_days: int,
) -> DimensionScore:
    per_metric = max_score / len(metrics)
    score = 0.0
    reasons: list[str] = []
    for metric in metrics:
        record, value = usable_numeric(records_by_metric, metric, as_of, stale_after_days)
        if value is None:
            reasons.append(f"{metric}: {MISSING}")
            continue
        if metric == "fcf_margin_pct":
            if value >= 15:
                score += per_metric
                reasons.append("FCF margin 强")
            elif value >= 8:
                score += per_metric * 0.6
                reasons.append("FCF margin 可用但受 CapEx 压制")
            else:
                score += per_metric * 0.2
                reasons.append("FCF margin 偏弱")
        elif metric == "capex_to_revenue_pct":
            if value <= 15:
                score += per_metric
                reasons.append("CapEx/revenue 温和")
            elif value <= 25:
                score += per_metric * 0.6
                reasons.append("CapEx/revenue 偏高")
            elif value <= 35:
                score += per_metric * 0.2
                reasons.append("CapEx/revenue 很高，压制 FCF")
            else:
                reasons.append("CapEx/revenue 危险")
        elif metric == "ai_capex_roi_comment_score":
            score += per_metric * max(0, min(value, 100)) / 100
            reasons.append(f"AI ROI 内部评分 {value:.0f}/100")
        else:
            score += per_metric
            reasons.append(f"{metric}: 已核实")
    rounded = round(score, 1)
    status = "强" if rounded >= max_score * 0.8 else "可用" if rounded >= max_score * 0.55 else "偏弱"
    return DimensionScore("ai_roi_fcf", label, rounded, max_score, status, reasons)


def score_valuation_position(
    records_by_metric: dict[str, MetricRecord],
    metrics: list[str],
    max_score: float,
    label: str,
    as_of: date,
    stale_after_days: int,
) -> DimensionScore:
    per_metric = max_score / len(metrics)
    score = 0.0
    reasons: list[str] = []
    for metric in metrics:
        record = records_by_metric.get(metric)
        if record is None or not record.is_usable(as_of, stale_after_days) or record.numeric_value is None:
            reasons.append(f"{metric}: {MISSING}")
            continue
        value = record.numeric_value
        if metric == "forward_pe":
            if value <= 25:
                score += per_metric
                reasons.append("forward_pe: 估值合理")
            elif value <= 35:
                score += per_metric * 0.6
                reasons.append("forward_pe: 估值偏高")
            else:
                score += per_metric * 0.2
                reasons.append("forward_pe: 估值较高")
        elif metric == "fcf_yield_pct":
            if value >= 3:
                score += per_metric
                reasons.append("fcf_yield_pct: 现金流收益率有吸引力")
            elif value >= 2:
                score += per_metric * 0.6
                reasons.append("fcf_yield_pct: 现金流收益率一般")
            else:
                score += per_metric * 0.2
                reasons.append("fcf_yield_pct: 现金流收益率偏低")
        elif metric == "rr_ratio":
            if value >= 1.5:
                score += per_metric
                reasons.append("rr_ratio: R/R 达到最低门槛")
            elif value >= 1:
                score += per_metric * 0.5
                reasons.append("rr_ratio: R/R 不足")
            else:
                reasons.append("rr_ratio: R/R 低于 1")
        else:
            score += per_metric
            reasons.append(f"{metric}: 已核实")
    rounded = round(score, 1)
    status = "可用" if rounded >= max_score * 0.7 else "估值吸引力不足"
    return DimensionScore("valuation_position", label, rounded, max_score, status, reasons)


def recommendation_from_score(total_score: float, thresholds: dict[str, Any]) -> str:
    levels = thresholds["recommendations"]
    if total_score >= float(levels["buy"]):
        return "买入"
    if total_score >= float(levels["add"]):
        return "加仓"
    if total_score >= float(levels["hold"]):
        return "持有"
    if total_score >= float(levels["reduce"]):
        return "减仓"
    return "退出"
