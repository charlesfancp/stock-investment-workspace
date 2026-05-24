from __future__ import annotations

from pathlib import Path

from google_investment.decision_log import DecisionLogEntry, append_decision_log, read_decision_log


def entry(**overrides: str) -> DecisionLogEntry:
    values = {
        "run_id": "2026-05-18|2026Q1|数据缺失|继续跟踪 / 待核实|48.3",
        "generated_at": "2026-05-18T12:00:00",
        "date": "2026-05-18",
        "period": "2026Q1",
        "ticker": "数据缺失",
        "current_price": "数据缺失",
        "score": "48.3",
        "action": "继续跟踪 / 待核实",
        "confidence": "低",
        "key_evidence": "Search 与 Cloud 经营数据已核实",
        "contrary_evidence": "估值数据缺失",
        "add_trigger": "估值完整且 R/R 达标",
        "reduce_trigger": "Cloud 或 Search 转弱",
        "exit_trigger": "护城河受损",
        "next_review_date": "下季度财报发布后 5 个工作日内",
        "change_reason": "",
    }
    values.update(overrides)
    return DecisionLogEntry(**values)


def test_duplicate_decision_log_is_not_appended(tmp_path: Path) -> None:
    path = tmp_path / "decision_log.csv"

    first = append_decision_log(path, entry())
    second = append_decision_log(path, entry(generated_at="2026-05-18T12:01:00"))

    rows = read_decision_log(path)
    assert first.status == "appended"
    assert second.status == "skipped"
    assert second.message == "决策日志已存在，未重复写入"
    assert len(rows) == 1


def test_existing_duplicate_rows_are_compacted(tmp_path: Path) -> None:
    path = tmp_path / "decision_log.csv"
    append_decision_log(path, entry())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(path.read_text(encoding="utf-8").splitlines()[-1] + "\n")

    result = append_decision_log(path, entry(generated_at="2026-05-18T12:02:00"))

    rows = read_decision_log(path)
    assert result.status == "skipped"
    assert len(rows) == 1


def test_action_or_score_change_appends_with_change_reason(tmp_path: Path) -> None:
    path = tmp_path / "decision_log.csv"

    append_decision_log(path, entry())
    changed = entry(
        run_id="2026-05-18|2026Q1|数据缺失|待人工复核|55.0",
        score="55.0",
        action="待人工复核",
    )
    result = append_decision_log(path, changed)

    rows = read_decision_log(path)
    assert result.status == "appended"
    assert len(rows) == 2
    assert rows[-1]["change_reason"] == "判断变化"


def test_missing_valuation_log_action_stays_follow_up() -> None:
    row = entry().as_row()

    assert row["action"] == "继续跟踪 / 待核实"
