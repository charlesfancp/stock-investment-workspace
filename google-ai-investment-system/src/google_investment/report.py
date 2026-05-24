from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .charts import ChartResult
from .data_loader import MISSING, MetricRecord, ValuationSnapshot
from .decision_log import DecisionLogEntry, build_run_id, generated_at_now
from .price_sensitivity import PriceSensitivity, build_price_sensitivity
from .scoring import Scorecard, recommendation_from_score
from .valuation_scenarios import ValuationScenarioMatrix


def render_report(
    records: list[MetricRecord],
    scorecard: Scorecard,
    config: dict[str, Any],
    as_of: date,
    valuation: ValuationSnapshot | None = None,
    charts: list[ChartResult] | None = None,
    io_event: dict[str, Any] | None = None,
    analyst_data: dict[str, Any] | None = None,
    scenario_matrix: ValuationScenarioMatrix | None = None,
) -> str:
    score_recommendation = recommendation_from_score(scorecard.total_score, config)
    confidence = "低" if scorecard.total_score < 55 else "中" if scorecard.total_score < 72 else "待人工复核"
    stale_after_days = int(config.get("stale_after_days", 92))
    usable_records = [record for record in records if record.is_usable(as_of, stale_after_days)]
    missing_valuation = valuation is None or not valuation.is_complete(as_of, stale_after_days)
    recommendation = action_with_valuation_gate(score_recommendation, missing_valuation, valuation)
    core_judgment = build_core_judgment(scorecard.total_score, usable_records, missing_valuation)
    action_note = "估值数据缺失，不具备真实交易资格" if missing_valuation else "估值数据完整，真实交易仍须人工确认"
    core_evidence = build_core_evidence(usable_records)
    valuation_status = build_valuation_status(valuation, as_of, stale_after_days)
    log_entry = build_decision_log_entry(
        as_of=as_of,
        records=records,
        scorecard=scorecard,
        action=recommendation,
        confidence=confidence,
        key_evidence=core_evidence,
        valuation=valuation,
    )

    lines = [
        "# Alphabet / Google AI 投资季度跟踪报告",
        "",
        f"- 生成日期：{as_of.isoformat()}",
        "- 覆盖对象：Alphabet Inc.（GOOG / GOOGL 需核实交易市场、股价、市值和股本口径后才能进入结论）",
        f"- 核心判断：{core_judgment}",
        f"- 综合评分：{scorecard.total_score:.1f} / {scorecard.max_score:.0f}",
        f"- 系统动作建议：{recommendation}（置信度：{confidence}；{action_note}）",
        f"- 估值状态：{valuation_status}",
        "",
        "## 综合评分",
        "",
        "| 维度 | 得分 | 状态 | 扣分或提示 |",
        "| --- | ---: | --- | --- |",
    ]
    for item in scorecard.dimensions:
        lines.append(
            f"| {item.label} | {item.score:.1f} / {item.max_score:.0f} | {item.status} | {'；'.join(item.reasons)} |"
        )

    lines.extend(
        [
            "",
            "## 趋势图表",
            "",
        ]
    )
    lines.extend(render_chart_section(charts or []))

    if io_event:
        lines.extend(render_io_event_section(io_event))
    if analyst_data:
        lines.extend(render_analyst_section(analyst_data))

    lines.extend(
        [
            "",
            "## 四个框架判断",
            "",
            "| 框架 | 当前判断 | 需要补充的证据 |",
            "| --- | --- | --- |",
            "| Goldman | Cloud 增速和 margin 已核实为强信号，但估值快照缺失，不能确认重估空间 | 当前价格、PE、FCF yield、R/R |",
            "| Damodaran | 经营数字可进入模型，但缺少市场价格和股本/市值快照，暂不能做完整估值 | 当前价格、市值、股本、资本成本、终值假设 |",
            "| Dan Niles | AI capex 压力已可见，FCF 仍需连续跟踪；估值缺失导致无法判断是否过热 | CapEx 指引、FCF、估值扩张、Cloud 降速风险 |",
            "| Ackman/Berkshire | Search 与 Cloud 质量信号较强，但买入价和长期 R/R 尚未核实 | 合理买入价、FCF yield、回购纪律、监管风险 |",
            "",
            "## 情景与概率",
            "",
            "| 情景 | 概率 | 判断 | 触发条件 |",
            "| --- | ---: | --- | --- |",
            "| 基准 | 50% | 继续跟踪，等待估值快照补齐 | 价格、PE、FCF yield、来源和抓取日期完整 |",
            "| 乐观 | 25% | Search 稳定、Cloud 利润率改善、AI 投入转化为 FCF 增量 | 云收入和利润率超预期，AI 产品提升商业化，FCF 质量改善 |",
            "| 风险 | 25% | AI capex 回报不清、监管压力或广告增长放缓压低估值 | FCF 走弱、capex 上修、反垄断处罚或搜索份额明显下滑 |",
            "",
            "## 触发条件",
            "",
            "| 动作 | 条件 |",
            "| --- | --- |",
            "| 加仓 | 估值数据、来源和日期完整，R/R 不低于 1.5，且 Cloud 与 Search 指标继续高于阈值 |",
            "| 减仓 | Cloud 增速低于合格线、Cloud margin 回落、Search 增速弱化，或估值与增长质量不匹配 |",
            "| 退出 | Search 护城河受损、Cloud 增速低于危险线、FCF 持续恶化或监管永久削弱商业模式 |",
            "",
            "## 估值快照",
            "",
            "| 字段 | 当前值 |",
            "| --- | --- |",
        ]
    )
    lines.extend(render_valuation_rows(valuation, as_of, stale_after_days))

    lines.extend(
        [
            "",
            "## R/R 与仓位资格",
            "",
        ]
    )
    lines.extend(render_rr_section(valuation, as_of, stale_after_days))
    lines.extend(render_price_sensitivity_section(build_price_sensitivity(valuation)))
    if scenario_matrix is not None:
        lines.extend(render_valuation_scenario_matrix_section(scenario_matrix))

    lines.extend(
        [
            "",
            "## 风险信号",
            "",
            "- Search 份额或商业化效率下滑。",
            "- Cloud 增长放缓或经营利润率回落。",
            "- AI 资本开支上升但收入和 FCF 转化不清晰。",
            f"- {valuation_risk_signal(valuation, as_of, stale_after_days)}",
            "- 反垄断、数据隐私、默认搜索协议等监管风险扩大。",
            "- 回购价格纪律变差或股本口径不清。",
            "",
            "## 下季度跟踪清单",
            "",
            "- Alphabet 官方财报、10-Q、IR 材料和业绩会纪要。",
            "- Search 收入增长、利润率、流量获取成本和份额变化。",
            "- Google Cloud 收入增长、经营利润、积压订单或等效指标。",
            "- AI capex、折旧、FCF、AI 产品商业化证据。",
            "- 最新股价、市值、股本、回购、估值倍数和 R/R。",
            "",
            "## 数据来源与核实状态",
            "",
            "| 指标 | 数值 | 单位 | 报告期 | 来源 | 发布日期 | 抓取日期 | 口径 | 核实状态 | 时效 | 备注 |",
            "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for record in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.metric,
                    display(record.value),
                    display(record.unit),
                    display(record.period),
                    display(record.source_name),
                    display(record.published_date),
                    display(record.accessed_date),
                    display(record.methodology),
                    display(record.verified_status),
                    record.stale_status(as_of, stale_after_days),
                    display(record.notes),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 决策日志字段",
            "",
            "| 字段 | 当前值 |",
            "| --- | --- |",
            f"| 日期 | {as_of.isoformat()} |",
            "| 标的 | Alphabet Inc. |",
            f"| 当前价格或估值 | {display(valuation.current_price) if valuation else MISSING} |",
            f"| 当前判断 | {core_judgment} |",
            f"| 建议动作 | {recommendation}，但{action_note} |",
            "| 概率 | 基准 50%，乐观 25%，风险 25% |",
            f"| 核心证据 | {core_evidence} |",
            f"| 反方证据 | {build_contrary_evidence(valuation)} |",
            "| 关键假设 | Search 护城河、Cloud 利润率、AI ROI 和估值口径均待继续验证 |",
            "| 触发条件 | 见上方加仓、减仓、退出触发条件 |",
            "| 止损或退出条件 | 护城河受损、FCF 恶化、监管永久削弱商业模式 |",
            "| 下次复盘日期 | 下季度财报发布后 5 个工作日内 |",
            "| 后续实际结果 | 待记录 |",
            "",
            "## 决策日志待写入字段",
            "",
            "| 字段 | 当前值 |",
            "| --- | --- |",
        ]
    )
    for field, value in log_entry.as_row().items():
        lines.append(f"| {field} | {display(value)} |")
    lines.append("")
    return "\n".join(lines)


def display(value: str) -> str:
    return MISSING if value.strip() == "" else value


def render_chart_section(charts: list[ChartResult]) -> list[str]:
    if not charts:
        return ["历史数据不足，暂不生成趋势图"]
    lines: list[str] = []
    for chart in charts:
        if chart.generated:
            lines.extend([f"### {chart.title}", "", f"![{chart.title}](charts/{chart.filename})", ""])
        else:
            lines.append(f"- {chart.title}：{chart.message}")
    return lines


def render_io_event_section(io_event: dict[str, Any]) -> list[str]:
    lines = [
        "",
        "## Google I/O 2026 事件影响",
        "",
        f"- 状态：{display(str(io_event.get('status', MISSING)))}",
        f"- 判断：{display(str(io_event.get('summary', MISSING)))}",
        "- 结论纪律：I/O 事件事实不直接解锁买入、加仓、R/R 或仓位建议。",
        "",
        "| 方向 | 关键事实 | 投资含义 |",
        "| --- | --- | --- |",
    ]
    for item in io_event.get("items", []):
        lines.append(
            f"| {display(str(item.get('label', MISSING)))} | "
            f"{display(str(item.get('metric', MISSING)))} | "
            f"{display(str(item.get('detail', MISSING)))} |"
        )
    lines.extend(["", "### 后续跟踪", ""])
    for item in io_event.get("watchlist", []):
        lines.append(f"- {display(str(item))}")
    return lines


def render_analyst_section(analysts: dict[str, Any]) -> list[str]:
    lines = [
        "",
        "## 投行与共识目标价",
        "",
        f"- 状态：{display(str(analysts.get('status', MISSING)))}",
        f"- 摘要：{display(str(analysts.get('summary', MISSING)))}",
        f"- 外部基准参考：{display(str(analysts.get('base_target_reference', MISSING)))}",
        f"- 外部风险参考：{display(str(analysts.get('risk_target_reference', MISSING)))}",
        f"- 外部乐观参考：{display(str(analysts.get('bull_target_reference', MISSING)))}",
        "- 结论纪律：二手新闻和聚合目标价只作为外部参考，不直接写入 valuation_snapshot.csv，不自动解锁 R/R。",
        "",
        "| 机构 | 评级 | 动作 | 目标价 | 前值 | 来源 | 日期 | 备注 |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for item in analysts.get("items", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    display(str(item.get("firm", MISSING))),
                    display(str(item.get("rating", MISSING))),
                    display(str(item.get("action", MISSING))),
                    display(str(item.get("target_price", MISSING))),
                    display(str(item.get("previous_target", MISSING))),
                    display(str(item.get("source_name", MISSING))),
                    display(str(item.get("source_date", MISSING))),
                    display(str(item.get("notes", MISSING))),
                ]
            )
            + " |"
        )
    return lines


def action_with_valuation_gate(
    score_recommendation: str,
    missing_valuation: bool,
    valuation: ValuationSnapshot | None = None,
    min_rr: float = 1.5,
) -> str:
    if missing_valuation:
        return "继续跟踪 / 待核实"
    if valuation is not None and (valuation.rr_ratio is None or valuation.rr_ratio < min_rr):
        return "持有 / 不加仓"
    return score_recommendation


def build_core_judgment(total_score: float, usable_records: list[MetricRecord], missing_valuation: bool) -> str:
    if not usable_records:
        return "继续跟踪。当前报告为系统 MVP 输出，尚无可进入结论区的已核实官方数据。"
    if missing_valuation:
        return (
            "继续跟踪。2026Q1 官方经营数据已部分核实，Search 与 Cloud 信号强，"
            "但估值数据缺失，不能生成 R/R、仓位建议或高置信度买入/加仓结论。"
        )
    if total_score < 55:
        return "减仓观察。评分显示投资逻辑偏弱，需人工复核是否由基本面恶化还是数据缺口导致。"
    return "待人工复核后再形成正式投资结论。"


def build_core_evidence(usable_records: list[MetricRecord]) -> str:
    highlights = []
    wanted = {
        "search_revenue_growth_yoy_pct": "Search & other 增长",
        "cloud_revenue_growth_yoy_pct": "Cloud 收入增长",
        "cloud_operating_margin_pct": "Cloud operating margin",
        "fcf_margin_pct": "FCF margin",
        "capex_to_revenue_pct": "CapEx / revenue",
    }
    for record in usable_records:
        label = wanted.get(record.metric)
        if label:
            highlights.append(f"{label} {record.value}{record.unit}（{record.source_name}，{record.published_date}）")
    return "；".join(highlights) if highlights else "数据缺失，待绑定官方来源"


def build_valuation_status(valuation: ValuationSnapshot | None, as_of: date, stale_after_days: int) -> str:
    if valuation is None:
        return "估值数据缺失：未找到 valuation_snapshot.csv 可用记录"
    missing = valuation.required_missing_fields
    stale = valuation.stale_status(as_of, stale_after_days)
    numeric_missing = [
        field
        for field in ["current_price", "pe_ratio", "fcf_yield_pct", "target_price_base", "downside_price"]
        if valuation.numeric_value(field) is None
    ]
    problems = []
    if missing:
        problems.append("缺少 " + "、".join(missing))
    if numeric_missing:
        problems.append("数值不可用 " + "、".join(numeric_missing))
    if stale != "未过期":
        problems.append(f"时效={stale}")
    return "估值数据完整" if not problems else "估值数据缺失：" + "；".join(problems)


def valuation_risk_signal(valuation: ValuationSnapshot | None, as_of: date, stale_after_days: int) -> str:
    if valuation is None or not valuation.is_complete(as_of, stale_after_days):
        return "估值数据缺失或过期，导致 R/R 与仓位建议不可用。"
    if valuation.rr_ratio is not None and valuation.rr_ratio < 1:
        return f"估值吸引力不足：R/R {valuation.rr_ratio} 低于 1，当前不具备加仓吸引力。"
    if valuation.rr_ratio is not None and valuation.rr_ratio < 1.5:
        return f"估值吸引力一般：R/R {valuation.rr_ratio} 低于 1.5 门槛。"
    return "估值快照完整且 R/R 达到最低门槛，但真实交易仍须人工确认。"


def render_valuation_rows(
    valuation: ValuationSnapshot | None,
    as_of: date,
    stale_after_days: int,
) -> list[str]:
    if valuation is None:
        return [
            "| current_price | 数据缺失 |",
            "| pe_ratio | 数据缺失 |",
            "| fcf_yield_pct | 数据缺失 |",
            "| source_url | 数据缺失 |",
            "| captured_at | 数据缺失 |",
            "| 时效 | 数据缺失 |",
        ]
    rows = [
        ("date", valuation.date),
        ("ticker", valuation.ticker),
        ("current_price", valuation.current_price),
        ("target_price_base", valuation.target_price_base),
        ("downside_price", valuation.downside_price),
        ("upside_pct", f"{valuation.upside_pct}%" if valuation.upside_pct is not None else MISSING),
        ("downside_pct", f"{valuation.downside_pct}%" if valuation.downside_pct is not None else MISSING),
        ("rr_ratio", str(valuation.rr_ratio) if valuation.rr_ratio is not None else MISSING),
        ("market_cap_usd_bn", valuation.market_cap_usd_bn),
        ("diluted_shares_bn", valuation.diluted_shares_bn),
        ("pe_ratio", valuation.pe_ratio),
        ("fcf_yield_pct", valuation.fcf_yield_pct),
        ("ev_to_fcf", valuation.ev_to_fcf),
        ("net_cash_usd_bn", valuation.net_cash_usd_bn),
        ("source_url", valuation.source_url),
        ("source_date", valuation.source_date),
        ("captured_at", valuation.captured_at),
        ("valuation_methodology", valuation.valuation_methodology),
        ("时效", valuation.stale_status(as_of, stale_after_days)),
        ("notes", valuation.notes),
    ]
    return [f"| {field} | {display(value)} |" for field, value in rows]


def render_rr_section(
    valuation: ValuationSnapshot | None,
    as_of: date,
    stale_after_days: int,
) -> list[str]:
    if valuation is None:
        return [
            "- R/R 状态：未解锁。",
            "- 缺口：估值快照缺失。",
            "- 动作限制：不允许输出买入、加仓或核心仓建议。",
        ]
    missing = valuation.required_missing_fields
    stale = valuation.stale_status(as_of, stale_after_days)
    if not valuation.is_complete(as_of, stale_after_days):
        gaps = missing[:]
        for field in ["current_price", "target_price_base", "downside_price", "pe_ratio", "fcf_yield_pct"]:
            if valuation.numeric_value(field) is None and field not in gaps:
                gaps.append(field)
        if stale != "未过期":
            gaps.append(f"时效={stale}")
        return [
            "- R/R 状态：未解锁。",
            f"- 缺口：{'、'.join(gaps) if gaps else '数据缺失'}。",
            "- 动作限制：不允许输出买入、加仓或核心仓建议。",
            "- 估值口径要求：目标价和下行价必须来自人工估值假设，并标注“模型假设，不是已验证事实”。",
        ]
    return [
        "- R/R 状态：已解锁，仍需人工确认真实交易动作。",
        f"- 上行空间：{valuation.upside_pct}%。",
        f"- 下行空间：{valuation.downside_pct}%。",
        f"- R/R：{valuation.rr_ratio}。",
        f"- 计算口径：上行=(基准目标价 {valuation.target_price_base} - 当前价格 {valuation.current_price}) / 当前价格；"
        f"下行=(当前价格 {valuation.current_price} - 风险下行价 {valuation.downside_price}) / 当前价格；"
        "R/R=上行空间/下行空间。",
        f"- 估值方法：{valuation.valuation_methodology}。目标价区间为模型假设，不是已验证事实。",
    ]


def render_price_sensitivity_section(sensitivity: PriceSensitivity) -> list[str]:
    lines = [
        "",
        "## 价格敏感性与动作区间",
        "",
        f"- 摘要：{sensitivity.summary}",
        f"- 买入复核区：{format_price(sensitivity.buy_below, suffix=' 以下')}",
        f"- 持有区间：{sensitivity.hold_range}",
        f"- 减仓复盘区：{format_price(sensitivity.reduce_review_above, suffix=' 以上')}",
        f"- 计算口径：{sensitivity.methodology}",
    ]
    if not sensitivity.available:
        return lines
    lines.extend(
        [
            "",
            "| 假设股价 | 上行空间 | 下行空间 | R/R | 动作区间 | 备注 |",
            "| ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in sensitivity.rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"${row.price:.2f}",
                    pct(row.upside_pct),
                    pct(row.downside_pct),
                    f"{row.rr_ratio:.2f}" if row.rr_ratio is not None else MISSING,
                    row.decision,
                    row.note,
                ]
            )
            + " |"
        )
    return lines


def render_valuation_scenario_matrix_section(matrix: ValuationScenarioMatrix) -> list[str]:
    lines = [
        "",
        "## 估值情景矩阵",
        "",
        f"- 摘要：{matrix.summary}",
        "- 结论纪律：情景目标价和下行价是模型假设或外部参考衍生，不是已验证事实；矩阵只用于复核当前持有结论是否稳健。",
    ]
    if matrix.gaps:
        lines.append(f"- 数据缺口：{'；'.join(matrix.gaps)}")
    if not matrix.available:
        return lines
    lines.extend(
        [
            "",
            "| 情景 | 概率 | 目标价 | 下行价 | 买入复核价 | R/R=1 价格 | 减仓复盘价 | 当前价 R/R | 当前动作 | 来源日期 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in matrix.rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.label,
                    f"{row.probability:.0f}%",
                    f"${row.target_price:.2f}",
                    f"${row.downside_price:.2f}",
                    f"${row.buy_below:.2f}",
                    f"${row.fair_price:.2f}",
                    f"${row.reduce_review_above:.2f}",
                    f"{row.current_rr:.2f}" if row.current_rr is not None else MISSING,
                    row.current_decision,
                    row.source_date,
                ]
            )
            + " |"
        )
    lines.extend(["", "### 情景口径", ""])
    for row in matrix.rows:
        lines.append(f"- {row.label}：{row.methodology}")
    return lines


def format_price(value: float | None, suffix: str = "") -> str:
    return MISSING if value is None else f"${value:.2f}{suffix}"


def pct(value: float | None) -> str:
    return MISSING if value is None else f"{value:.1f}%"


def build_decision_log_entry(
    as_of: date,
    records: list[MetricRecord],
    scorecard: Scorecard,
    action: str,
    confidence: str,
    key_evidence: str,
    valuation: ValuationSnapshot | None,
) -> DecisionLogEntry:
    period = next((record.period for record in records if record.period.strip() not in {"", MISSING}), MISSING)
    ticker = valuation.ticker if valuation else MISSING
    current_price = valuation.current_price if valuation else MISSING
    return DecisionLogEntry(
        run_id=build_run_id(
            {
                "date": as_of.isoformat(),
                "period": period,
                "ticker": ticker,
                "action": action,
                "score": f"{scorecard.total_score:.1f}",
            }
        ),
        generated_at=generated_at_now(),
        date=as_of.isoformat(),
        period=period,
        ticker=ticker,
        current_price=current_price,
        score=f"{scorecard.total_score:.1f}",
        action=action,
        confidence=confidence,
        key_evidence=key_evidence,
        contrary_evidence=build_contrary_evidence(valuation),
        add_trigger="估值数据、来源和日期完整，R/R 不低于 1.5，且 Cloud 与 Search 指标继续高于阈值",
        reduce_trigger="Cloud 增速低于合格线、Cloud margin 回落、Search 增速弱化，或估值与增长质量不匹配",
        exit_trigger="Search 护城河受损、Cloud 增速低于危险线、FCF 持续恶化或监管永久削弱商业模式",
        next_review_date="下季度财报发布后 5 个工作日内",
    )


def build_contrary_evidence(valuation: ValuationSnapshot | None) -> str:
    if valuation is None:
        return "估值数据缺失或未核实；监管、竞争和 AI ROI 反方证据仍待补齐"
    issues = []
    if valuation.rr_ratio is None:
        issues.append("R/R 不可计算")
    elif valuation.rr_ratio < 1.0:
        issues.append(f"R/R 低于 1（当前 {valuation.rr_ratio}）")
    elif valuation.rr_ratio < 1.5:
        issues.append(f"R/R 低于 1.5 门槛（当前 {valuation.rr_ratio}）")
    fcf_yield = valuation.numeric_value("fcf_yield_pct")
    if fcf_yield is not None and fcf_yield < 2.0:
        issues.append(f"FCF yield 偏低（当前 {valuation.fcf_yield_pct}%）")
    pe = valuation.numeric_value("pe_ratio")
    if pe is not None and pe > 25:
        issues.append(f"PE 偏高（当前 {valuation.pe_ratio}x）")
    issues.append("AI CapEx ROI 仍需后续财报验证")
    issues.append("监管、竞争和 Search AI monetization 风险仍需跟踪")
    return "；".join(issues)


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
