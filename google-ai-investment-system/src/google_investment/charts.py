from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .data_loader import MetricRecord, ValuationSnapshot


@dataclass(frozen=True)
class ChartResult:
    key: str
    title: str
    filename: str
    generated: bool
    message: str


CHART_SPECS = {
    "cloud_revenue_growth": {
        "title": "Google Cloud 收入增速趋势",
        "filename": "cloud_revenue_growth.png",
        "metrics": ["cloud_revenue_growth_yoy_pct"],
        "labels": ["Cloud 收入增速"],
        "ylabel": "%",
    },
    "cloud_operating_margin": {
        "title": "Google Cloud 经营利润率趋势",
        "filename": "cloud_operating_margin.png",
        "metrics": ["cloud_operating_margin_pct"],
        "labels": ["Cloud operating margin"],
        "ylabel": "%",
    },
    "search_other_growth": {
        "title": "Search & Other 收入增速趋势",
        "filename": "search_other_growth.png",
        "metrics": ["search_revenue_growth_yoy_pct"],
        "labels": ["Search & Other 增速"],
        "ylabel": "%",
    },
    "capex_vs_fcf": {
        "title": "CapEx 与 FCF margin 对比",
        "filename": "capex_vs_fcf.png",
        "metrics": ["capex_to_revenue_pct", "fcf_margin_pct"],
        "labels": ["CapEx / revenue", "FCF margin"],
        "ylabel": "%",
    },
}


def generate_charts(
    records: list[MetricRecord],
    valuations: list[ValuationSnapshot],
    output_dir: Path,
    as_of: date,
    stale_after_days: int,
) -> list[ChartResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in [spec["filename"] for spec in CHART_SPECS.values()] + ["fcf_yield_trend.png"]:
        stale_file = output_dir / filename
        if stale_file.exists():
            stale_file.unlink()

    results = [
        generate_metric_chart(key, spec, records, output_dir, as_of, stale_after_days)
        for key, spec in CHART_SPECS.items()
    ]
    results.append(generate_fcf_yield_chart(valuations, output_dir, as_of, stale_after_days))
    return results


def generate_metric_chart(
    key: str,
    spec: dict[str, object],
    records: list[MetricRecord],
    output_dir: Path,
    as_of: date,
    stale_after_days: int,
) -> ChartResult:
    metrics = list(spec["metrics"])
    points = points_for_metrics(records, metrics, as_of, stale_after_days)
    title = str(spec["title"])
    filename = str(spec["filename"])
    if len(points) < 2:
        return ChartResult(key, title, filename, False, "历史数据不足，暂不生成趋势图")

    labels = [str(label) for label in spec["labels"]]
    series = [[point[metric] for point in points] for metric in metrics]
    draw_line_chart(
        output_dir / filename,
        title=title,
        x_labels=[point["period"] for point in points],
        series=series,
        labels=labels,
        ylabel=str(spec["ylabel"]),
    )
    return ChartResult(key, title, filename, True, f"已生成 {filename}")


def generate_fcf_yield_chart(
    valuations: list[ValuationSnapshot],
    output_dir: Path,
    as_of: date,
    stale_after_days: int,
) -> ChartResult:
    usable = [
        snapshot
        for snapshot in valuations
        if snapshot.is_complete(as_of, stale_after_days) and snapshot.numeric_value("fcf_yield_pct") is not None
    ]
    usable.sort(key=lambda item: item.date)
    title = "FCF yield 趋势"
    filename = "fcf_yield_trend.png"
    if len(usable) < 2:
        return ChartResult("fcf_yield_trend", title, filename, False, "历史数据不足，暂不生成趋势图")

    draw_line_chart(
        output_dir / filename,
        title=title,
        x_labels=[snapshot.date for snapshot in usable],
        series=[[snapshot.numeric_value("fcf_yield_pct") or 0.0 for snapshot in usable]],
        labels=["FCF yield"],
        ylabel="%",
    )
    return ChartResult("fcf_yield_trend", title, filename, True, f"已生成 {filename}")


def points_for_metrics(
    records: list[MetricRecord],
    metrics: list[str],
    as_of: date,
    stale_after_days: int,
) -> list[dict[str, float | str]]:
    by_period: dict[str, dict[str, float | str]] = {}
    for record in records:
        if record.metric not in metrics or not record.is_usable(as_of, stale_after_days):
            continue
        value = record.numeric_value
        if value is None:
            continue
        by_period.setdefault(record.period, {"period": record.period})
        by_period[record.period][record.metric] = value
    complete = [point for point in by_period.values() if all(metric in point for metric in metrics)]
    return sorted(complete, key=lambda point: str(point["period"]))


def draw_line_chart(
    output_path: Path,
    title: str,
    x_labels: list[str],
    series: list[list[float]],
    labels: list[str],
    ylabel: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    configure_chinese_font(plt, font_manager)

    plt.figure(figsize=(8, 4.8))
    for values, label in zip(series, labels, strict=True):
        plt.plot(x_labels, values, marker="o", linewidth=2, label=label)
    plt.title(title)
    plt.xlabel("报告期")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.25)
    if len(labels) > 1:
        plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def configure_chinese_font(plt, font_manager) -> None:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            font_name = font_manager.FontProperties(fname=str(path)).get_name()
            plt.rcParams["font.sans-serif"] = [font_name]
            plt.rcParams["axes.unicode_minus"] = False
            return
