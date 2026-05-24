#!/usr/bin/env python3
"""Run the daily research pipeline.

This pipeline generates data and reports only. It never places trades.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]


class PipelineStep(NamedTuple):
    name: str
    script: str


PIPELINE_STEPS = [
    PipelineStep("fetch prices and benchmarks", "fetch_prices.py"),
    PipelineStep("build fundamentals table", "build_fundamentals.py"),
    PipelineStep("build valuation table", "build_valuation.py"),
    PipelineStep("score tickers", "score_tickers.py"),
    PipelineStep("build portfolio state", "build_portfolio_state.py"),
    PipelineStep("check rebalance drift", "check_rebalance.py"),
    PipelineStep("build event calendar", "build_event_calendar.py"),
    PipelineStep("build portfolio risk summary", "build_portfolio_risk.py"),
    PipelineStep("generate daily report", "generate_daily_report.py"),
    PipelineStep("generate weekly report", "generate_weekly_report.py"),
    PipelineStep("generate event report", "generate_event_report.py"),
]


def run_step(step: PipelineStep) -> None:
    script_path = ROOT / "scripts" / step.script
    print(f"Running: {step.name}")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Pipeline failed at step '{step.name}' with exit code {result.returncode}")


def run_pipeline(steps: list[PipelineStep] = PIPELINE_STEPS) -> None:
    print("AI infrastructure research pipeline")
    print("Mode: research reports only; no trade execution")
    for step in steps:
        run_step(step)
    print("Pipeline completed")


def main() -> int:
    try:
        run_pipeline()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
