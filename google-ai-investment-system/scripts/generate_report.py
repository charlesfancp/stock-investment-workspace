from __future__ import annotations

import sys
import json
from datetime import date
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from google_investment.data_loader import (
    latest_by_metric,
    latest_valuation_snapshot,
    load_metric_records,
    load_valuation_scenarios,
    load_valuation_snapshots,
    valuation_metric_records,
)
from google_investment.charts import generate_charts
from google_investment.decision_log import append_decision_log
from google_investment.report import (
    action_with_valuation_gate,
    build_core_evidence,
    build_decision_log_entry,
    render_report,
    write_report,
)
from google_investment.scoring import recommendation_from_score, score_records
from google_investment.valuation_scenarios import build_valuation_scenario_matrix

from build_dashboard_data import build_dashboard_data


def main() -> int:
    config_path = PROJECT_ROOT / "configs" / "thresholds.yaml"
    input_path = PROJECT_ROOT / "data" / "raw" / "alphabet_quarterly_manual.csv"
    valuation_path = PROJECT_ROOT / "data" / "raw" / "valuation_snapshot.csv"
    valuation_scenarios_path = PROJECT_ROOT / "data" / "raw" / "valuation_scenarios.csv"
    output_path = PROJECT_ROOT / "reports" / "latest_report.md"
    charts_dir = PROJECT_ROOT / "reports" / "charts"
    decision_log_path = PROJECT_ROOT / "decision_log" / "decision_log.csv"
    dashboard_data_path = PROJECT_ROOT / "dashboard" / "data.json"

    as_of = date.today()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    records = load_metric_records(input_path)
    valuations = load_valuation_snapshots(valuation_path)
    valuation = latest_valuation_snapshot(valuations)
    valuation_scenarios = load_valuation_scenarios(valuation_scenarios_path)
    scoring_records = records + valuation_metric_records(valuation)
    scorecard = score_records(latest_by_metric(scoring_records), config, as_of)
    stale_after_days = int(config.get("stale_after_days", 92))
    charts = generate_charts(records, valuations, charts_dir, as_of, stale_after_days)
    dashboard_payload = build_dashboard_data(PROJECT_ROOT, as_of)
    scenario_matrix = build_valuation_scenario_matrix(
        valuation,
        valuation_scenarios,
        as_of,
        stale_after_days,
    )
    report = render_report(
        scoring_records,
        scorecard,
        config,
        as_of,
        valuation,
        charts,
        dashboard_payload.get("io_event"),
        dashboard_payload.get("analysts"),
        scenario_matrix,
    )
    write_report(output_path, report)
    confidence = "低" if scorecard.total_score < 55 else "中" if scorecard.total_score < 72 else "待人工复核"
    missing_valuation = valuation is None or not valuation.is_complete(as_of, stale_after_days)
    action = action_with_valuation_gate(recommendation_from_score(scorecard.total_score, config), missing_valuation, valuation)
    log_result = append_decision_log(
        decision_log_path,
        build_decision_log_entry(
            as_of=as_of,
            records=scoring_records,
            scorecard=scorecard,
            action=action,
            confidence=confidence,
            key_evidence=build_core_evidence(
                [record for record in scoring_records if record.is_usable(as_of, stale_after_days)]
            ),
            valuation=valuation,
        ),
    )
    print(f"已生成报告：{output_path}")
    print(f"{log_result.message}：{decision_log_path}")
    dashboard_data_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_data_path.write_text(
        json.dumps(dashboard_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已更新面板数据：{dashboard_data_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
