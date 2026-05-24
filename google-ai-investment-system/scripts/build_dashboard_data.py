from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from google_investment.data_loader import (
    MISSING,
    latest_by_metric,
    latest_valuation_snapshot,
    load_metric_records,
    load_valuation_scenarios,
    load_valuation_snapshots,
    valuation_metric_records,
)
from google_investment.decision_log import read_decision_log
from google_investment.report import (
    action_with_valuation_gate,
    build_core_evidence,
    build_core_judgment,
    build_valuation_status,
)
from google_investment.price_sensitivity import build_price_sensitivity
from google_investment.scoring import recommendation_from_score, score_records
from google_investment.valuation_scenarios import (
    build_valuation_scenario_matrix,
    scenario_matrix_missing_inputs,
)


def main() -> int:
    output_path = PROJECT_ROOT / "dashboard" / "data.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = build_dashboard_data(PROJECT_ROOT, date.today())
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成面板数据：{output_path}")
    return 0


def build_dashboard_data(project_root: Path, as_of: date) -> dict:
    config = yaml.safe_load((project_root / "configs" / "thresholds.yaml").read_text(encoding="utf-8"))
    stale_after_days = int(config.get("stale_after_days", 92))
    records = load_metric_records(project_root / "data" / "raw" / "alphabet_quarterly_manual.csv")
    valuations = load_valuation_snapshots(project_root / "data" / "raw" / "valuation_snapshot.csv")
    valuation = latest_valuation_snapshot(valuations)
    valuation_scenarios = load_valuation_scenarios(project_root / "data" / "raw" / "valuation_scenarios.csv")
    scoring_records = records + valuation_metric_records(valuation)
    scorecard = score_records(latest_by_metric(scoring_records), config, as_of)
    usable_records = [record for record in scoring_records if record.is_usable(as_of, stale_after_days)]
    missing_valuation = valuation is None or not valuation.is_complete(as_of, stale_after_days)
    action = action_with_valuation_gate(recommendation_from_score(scorecard.total_score, config), missing_valuation, valuation)
    confidence = "低" if scorecard.total_score < 55 else "中" if scorecard.total_score < 72 else "待人工复核"

    facts = load_facts(project_root / "evidence" / "facts.csv")
    scenario_matrix = build_valuation_scenario_matrix(
        valuation,
        valuation_scenarios,
        as_of,
        stale_after_days,
    )

    return {
        "updated_at": as_of.isoformat(),
        "asset": "Alphabet Inc.",
        "tickers": ["GOOG", "GOOGL"],
        "decision": build_core_judgment(scorecard.total_score, usable_records, missing_valuation),
        "action": action,
        "confidence": confidence,
        "trading_eligible": not missing_valuation,
        "trading_eligibility_note": (
            "估值数据缺失，不具备买入/加仓资格" if missing_valuation else "估值数据完整，仍需人工确认"
        ),
        "score": {
            "total": scorecard.total_score,
            "max": scorecard.max_score,
            "dimensions": [
                {
                    "key": item.key,
                    "label": item.label,
                    "score": item.score,
                    "max_score": item.max_score,
                    "status": item.status,
                    "reasons": item.reasons,
                }
                for item in scorecard.dimensions
            ],
        },
        "thesis": {
            "search": "Search & Other 增长已由官方公告核实，但仍需继续跟踪 AI 分流、TAC 和份额变化。",
            "cloud": "Google Cloud 增速和 operating margin 为当前最强正向证据，仍需观察 backlog 口径变化后的可比性。",
            "ai_fcf": "CapEx / revenue 较高，FCF margin 需要连续跟踪，AI ROI 尚未形成高置信结论。",
            "variant": "经营信号强于估值结论；当前非共识必须等真实估值快照后才能落到 R/R。",
        },
        "scenarios": [
            {
                "name": "基准",
                "probability": 50,
                "target_price": MISSING,
                "trigger": "估值快照补齐，Cloud 和 Search 继续高于合格线。",
            },
            {
                "name": "乐观",
                "probability": 25,
                "target_price": MISSING,
                "trigger": "Cloud 高增速与高 margin 延续，AI 产品商业化改善 FCF。",
            },
            {
                "name": "风险",
                "probability": 25,
                "target_price": MISSING,
                "trigger": "Search 被 AI 分流、Cloud 降速、CapEx 挤压 FCF 或监管冲击。",
            },
        ],
        "valuation": valuation_block(valuation, as_of, stale_after_days),
        "rr_gate": rr_gate_block(valuation, as_of, stale_after_days),
        "price_sensitivity": price_sensitivity_block(valuation),
        "valuation_scenarios": valuation_scenario_matrix_block(scenario_matrix),
        "market": latest_market_snapshots(project_root / "data" / "raw" / "market_snapshot.csv"),
        "analysts": analyst_block(project_root / "data" / "raw" / "analyst_snapshot.csv"),
        "position": latest_position(project_root / "data" / "raw" / "position_snapshot.csv"),
        "missing_inputs": missing_inputs(valuation) + scenario_matrix_missing_inputs(scenario_matrix),
        "evidence": facts,
        "io_event": io_event_block(facts),
        "risks": [
            "Search 被 AI 分流",
            "Cloud 增速降速",
            "Cloud margin 下行",
            "CapEx 挤压 FCF",
            "估值过高或估值数据缺失",
            "监管永久削弱商业模式",
        ],
        "triggers": {
            "add": "估值数据、来源和日期完整，R/R 不低于 1.5，且 Cloud 与 Search 指标继续高于阈值。",
            "reduce": "Cloud 增速低于合格线、Cloud margin 回落、Search 增速弱化，或估值与增长质量不匹配。",
            "exit": "Search 护城河受损、Cloud 增速低于危险线、FCF 持续恶化或监管永久削弱商业模式。",
        },
        "decision_log": read_decision_log(project_root / "decision_log" / "decision_log.csv"),
        "decision_plans": read_decision_plans(project_root / "decision_log" / "decision_plans.csv"),
        "reviews": [
            {"window": "30 天", "focus": "估值快照是否补齐，是否具备 R/R 计算资格。"},
            {"window": "60 天", "focus": "Cloud 增速、margin、backlog 口径变化后的收入可见度。"},
            {"window": "90 天", "focus": "下季度财报后复核 AI CapEx、FCF 和 Search 韧性。"},
        ],
        "key_evidence": build_core_evidence(usable_records),
    }


def valuation_block(valuation, as_of: date, stale_after_days: int) -> dict:
    if valuation is None:
        return {"status": "估值数据缺失", "trading_eligible": False}
    return {
        "date": valuation.date,
        "ticker": valuation.ticker,
        "current_price": valuation.current_price,
        "target_price_base": valuation.target_price_base,
        "downside_price": valuation.downside_price,
        "upside_pct": f"{valuation.upside_pct}%" if valuation.upside_pct is not None else MISSING,
        "downside_pct": f"{valuation.downside_pct}%" if valuation.downside_pct is not None else MISSING,
        "rr": str(valuation.rr_ratio) if valuation.rr_ratio is not None else MISSING,
        "market_cap_usd_bn": valuation.market_cap_usd_bn,
        "diluted_shares_bn": valuation.diluted_shares_bn,
        "pe_ratio": valuation.pe_ratio,
        "fcf_yield_pct": valuation.fcf_yield_pct,
        "ev_to_fcf": valuation.ev_to_fcf,
        "net_cash_usd_bn": valuation.net_cash_usd_bn,
        "source_url": valuation.source_url,
        "source_date": valuation.source_date,
        "captured_at": valuation.captured_at,
        "valuation_methodology": valuation.valuation_methodology,
        "stale_status": valuation.stale_status(as_of, stale_after_days),
        "status": build_valuation_status(valuation, as_of, stale_after_days),
        "trading_eligible": valuation.is_complete(as_of, stale_after_days),
        "position": "估值数据缺失，不具备买入/加仓资格"
        if not valuation.is_complete(as_of, stale_after_days)
        else "待人工确认",
    }


def rr_gate_block(valuation, as_of: date, stale_after_days: int) -> dict:
    required = [
        ("current_price", "当前价格"),
        ("target_price_base", "基准目标价"),
        ("downside_price", "风险下行价"),
        ("pe_ratio", "PE"),
        ("fcf_yield_pct", "FCF yield"),
        ("source_url", "来源链接"),
        ("captured_at", "抓取/录入日期"),
        ("valuation_methodology", "估值方法"),
    ]
    if valuation is None:
        items = [
            {"field": field, "label": label, "value": MISSING, "status": "缺失"}
            for field, label in required
        ]
        return {
            "unlocked": False,
            "title": "R/R 未解锁",
            "message": "估值快照缺失，不能计算上行、下行、R/R 或仓位建议。",
            "items": items,
            "calculation": "数据缺失",
            "methodology_note": "目标价和下行价必须来自人工估值假设，并明确标注模型假设，不是已验证事实。",
        }

    items = []
    for field, label in required:
        value = getattr(valuation, field)
        numeric_required = field in {"current_price", "target_price_base", "downside_price", "pe_ratio", "fcf_yield_pct"}
        numeric_missing = numeric_required and valuation.numeric_value(field) is None
        missing = value.strip() in {"", MISSING} or numeric_missing
        items.append(
            {
                "field": field,
                "label": label,
                "value": MISSING if missing else value,
                "status": "缺失" if missing else "已录入",
            }
        )

    stale = valuation.stale_status(as_of, stale_after_days)
    complete = valuation.is_complete(as_of, stale_after_days)
    if stale != "未过期":
        items.append({"field": "freshness", "label": "时效", "value": stale, "status": "缺失"})

    calculation = (
        f"上行 {valuation.upside_pct}%；下行 {valuation.downside_pct}%；R/R {valuation.rr_ratio}"
        if valuation.rr_ratio is not None
        else "数据缺失"
    )
    return {
        "unlocked": complete,
        "title": "R/R 已解锁" if complete else "R/R 未解锁",
        "message": "估值快照完整，可生成 R/R，仍需人工确认交易动作。"
        if complete
        else "估值快照仍不完整，动作继续锁定为“继续跟踪 / 待核实”。",
        "items": items,
        "calculation": calculation,
        "methodology_note": (
            f"估值方法：{valuation.valuation_methodology}"
            if complete
            else "目标价和下行价必须来自人工估值假设，并明确标注模型假设，不是已验证事实。"
        ),
    }


def price_sensitivity_block(valuation) -> dict:
    sensitivity = build_price_sensitivity(valuation)
    return {
        "available": sensitivity.available,
        "summary": sensitivity.summary,
        "methodology": sensitivity.methodology,
        "buy_below": f"${sensitivity.buy_below:.2f}" if sensitivity.buy_below is not None else MISSING,
        "hold_range": sensitivity.hold_range,
        "reduce_review_above": (
            f"${sensitivity.reduce_review_above:.2f}" if sensitivity.reduce_review_above is not None else MISSING
        ),
        "rows": [
            {
                "price": f"${row.price:.2f}",
                "upside_pct": f"{row.upside_pct:.1f}%" if row.upside_pct is not None else MISSING,
                "downside_pct": f"{row.downside_pct:.1f}%" if row.downside_pct is not None else MISSING,
                "rr": f"{row.rr_ratio:.2f}" if row.rr_ratio is not None else MISSING,
                "decision": row.decision,
                "note": row.note,
            }
            for row in sensitivity.rows
        ],
    }


def valuation_scenario_matrix_block(matrix) -> dict:
    return {
        "available": matrix.available,
        "summary": matrix.summary,
        "current_price": f"${matrix.current_price:.2f}" if matrix.current_price is not None else MISSING,
        "gaps": matrix.gaps,
        "rows": [
            {
                "scenario": row.scenario,
                "label": row.label,
                "probability": f"{row.probability:.0f}%",
                "target_price": f"${row.target_price:.2f}",
                "downside_price": f"${row.downside_price:.2f}",
                "buy_below": f"${row.buy_below:.2f}",
                "fair_price": f"${row.fair_price:.2f}",
                "reduce_review_above": f"${row.reduce_review_above:.2f}",
                "current_rr": f"{row.current_rr:.2f}" if row.current_rr is not None else MISSING,
                "current_upside_pct": (
                    f"{row.current_upside_pct:.1f}%" if row.current_upside_pct is not None else MISSING
                ),
                "current_downside_pct": (
                    f"{row.current_downside_pct:.1f}%" if row.current_downside_pct is not None else MISSING
                ),
                "current_decision": row.current_decision,
                "status": row.status,
                "methodology": row.methodology,
                "source_name": row.source_name,
                "source_date": row.source_date,
                "notes": row.notes,
            }
            for row in matrix.rows
        ],
    }


def load_facts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        facts = []
        for row in reader:
            if row.get("fact_id") == "FACT-PLACEHOLDER":
                continue
            facts.append(
                {
                    "id": row.get("fact_id", ""),
                    "metric": row.get("metric", ""),
                    "value": row.get("value", ""),
                    "unit": row.get("unit", ""),
                    "period": row.get("period", ""),
                    "source_id": row.get("source_id", ""),
                    "published_date": row.get("published_date", ""),
                    "accessed_date": row.get("accessed_date", ""),
                    "methodology": row.get("methodology", ""),
                    "verified_status": row.get("verified_status", ""),
                    "stale_status": row.get("stale_status", ""),
                    "used_in_conclusion": row.get("used_in_conclusion", ""),
                    "notes": row.get("notes", ""),
                }
            )
        return facts


def read_decision_plans(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-12:]


def io_event_block(facts: list[dict[str, str]]) -> dict:
    io_facts = [fact for fact in facts if fact.get("id", "").startswith("FACT-IO2026-")]
    if not io_facts:
        return {
            "title": "Google I/O 2026 事件影响",
            "status": "待核实",
            "summary": "尚未绑定官方来源，不进入投资判断。",
            "items": [],
            "watchlist": [],
        }

    by_metric = {fact["metric"]: fact for fact in io_facts}

    def value(metric: str) -> str:
        fact = by_metric.get(metric)
        if not fact:
            return MISSING
        unit = fact["unit"]
        if unit == "text":
            return fact["value"]
        if unit == "USD bn":
            return f"${fact['value']} {unit.replace('USD ', '')}"
        if unit == "USD/month":
            return f"${fact['value']}/month"
        if unit == "x":
            return f"{fact['value']}x"
        if unit == "x YoY":
            return f"{fact['value']}x YoY"
        if unit == "relative price ceiling":
            return "可比前沿模型一半以下"
        return f"{fact['value']} {unit}"

    items = [
        {
            "label": "模型层",
            "metric": "Gemini 3.5 Flash / Pro / Omni",
            "detail": (
                f"Flash 输出速度约为其他前沿模型的 {value('gemini35_flash_speed_vs_frontier')}，价格为"
                f"{value('gemini35_flash_price_vs_frontier')}；Gemini 3.5 Pro 仍需下月发布核实；Omni Flash 已发布。"
            ),
        },
        {
            "label": "Agent 生态",
            "metric": "Spark / Antigravity / Daily Brief",
            "detail": "Spark、Antigravity 2.0、Managed Agents 和 Daily Brief 已由官方公告核实，商业化仍需验证付费转化。",
        },
        {
            "label": "基础设施",
            "metric": f"CapEx {value('expected_2026_capex_low')} - {value('expected_2026_capex_high')}",
            "detail": (
                f"TPU 8t 原始算力约 {value('tpu8t_compute_vs_previous')}，可跨 {value('tpu8_distributed_scale')} 分布式训练；"
                "这是 Cloud/AI 护城河证据，也会加重 FCF 压力。"
            ),
        },
        {
            "label": "产品渗透",
            "metric": f"AI Mode {value('search_ai_mode_mau')}；Gemini App {value('gemini_app_mau')}",
            "detail": (
                f"AI Overviews {value('search_ai_overviews_mau')}，Gemini App 日请求同比约 "
                f"{value('gemini_app_daily_requests_growth')}；需跟踪 Search 广告 monetization。"
            ),
        },
        {
            "label": "商业化",
            "metric": f"AI Ultra {value('ai_ultra_price')}",
            "detail": "订阅层级和企业成本优势是正向线索，但还没有用户数、留存、毛利和 FCF 兑现数据。",
        },
    ]
    return {
        "title": "Google I/O 2026 事件影响",
        "status": "已核实；未进入买入/加仓结论",
        "summary": "I/O 强化了 Google 的全栈 AI 叙事：模型、Agent、TPU、Search 和订阅同时推进；当前应提高跟踪优先级，但不能替代估值和 FCF 证据。",
        "items": items,
        "watchlist": [
            "Gemini 3.5 Pro 下月是否按期发布，以及外部基准是否确认竞争力。",
            "AI Mode / AI Overviews 是否保护 Search 查询量和广告变现。",
            "AI Ultra、Spark、Antigravity 是否披露付费用户、留存或企业采用。",
            "1800-1900 亿美元 capex 是否继续挤压 FCF，Cloud 收入和利润能否对冲。",
            "TPU 8t/8i 是否带来 Cloud 外部客户收入、毛利率或单位成本改善。",
        ],
    }


def latest_position(path: Path) -> dict[str, str]:
    if not path.exists():
        return {"status": "仓位数据缺失"}
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {"status": "仓位数据缺失"}
    row = rows[-1]
    row["status"] = "仓位数据缺失" if row.get("shares") in {"", MISSING, None} else "已录入"
    return row


def latest_market_snapshots(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    latest: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = row.get("ticker", "")
        if not ticker:
            continue
        latest[ticker] = row
    return list(latest.values())


def analyst_block(path: Path) -> dict:
    if not path.exists():
        return {
            "status": "投行数据缺失",
            "summary": "尚未录入公开可核实的分析师目标价。",
            "items": [],
            "base_target_reference": MISSING,
            "risk_target_reference": MISSING,
            "bull_target_reference": MISSING,
        }
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    verified = [row for row in rows if row.get("verified_status") == "已核实"]
    numeric_targets = []
    for row in verified:
        try:
            numeric_targets.append(float(row.get("target_price", "")))
        except ValueError:
            continue
    if not numeric_targets:
        return {
            "status": "投行数据缺失",
            "summary": "分析师目标价不可用。",
            "items": verified,
            "base_target_reference": MISSING,
            "risk_target_reference": MISSING,
            "bull_target_reference": MISSING,
        }
    sorted_targets = sorted(numeric_targets)
    base = percentile(sorted_targets, 0.5)
    risk = sorted_targets[0]
    bull = sorted_targets[-1]
    return {
        "status": "已录入；仅作外部估值参考",
        "summary": (
            f"公开可核实样本 {len(verified)} 条，目标价区间 ${risk:.0f}-${bull:.0f}，"
            f"样本中位数约 ${base:.0f}。二手新闻和聚合数据不能替代自有估值模型。"
        ),
        "items": verified,
        "base_target_reference": f"{base:.0f}",
        "risk_target_reference": f"{risk:.0f}",
        "bull_target_reference": f"{bull:.0f}",
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0
    if len(values) == 1:
        return values[0]
    idx = pct * (len(values) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(values) - 1)
    weight = idx - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def missing_inputs(valuation) -> list[str]:
    items = []
    if valuation is None or valuation.required_missing_fields:
        items.append("估值快照：current_price、target_price_base、downside_price、PE、FCF yield、source_url、captured_at、valuation_methodology")
    if valuation is None or valuation.rr_ratio is None:
        items.append("R/R：需要 current_price、target_price_base、downside_price")
    items.append("仓位快照：shares、avg_cost、position_weight_pct，如无真实持仓可留空但不能生成仓位动作")
    items.append("AI ROI：需要 AI 产品收入/付费用户或管理层明确披露口径")
    return items


if __name__ == "__main__":
    raise SystemExit(main())
