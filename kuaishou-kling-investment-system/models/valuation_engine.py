from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
from common import load_yaml

ROOT = Path(__file__).resolve().parents[1]
ASSUMPTIONS_PATH = ROOT / "config" / "valuation_assumptions.yaml"
MARKET_PRICES_PATH = ROOT / "data" / "processed" / "market_prices.csv"
VALUATION_HISTORY_PATH = ROOT / "data" / "processed" / "valuation_history.csv"
SNAPSHOT_PATH = ROOT / "reports" / "daily" / "valuation_snapshot.md"


SCENARIOS = {
    "bear": {"label": "熊市", "pe": "core_pe_bear", "arr": "arr_usd_mn_bear", "ps": "ps_bear", "ownership": "kuaishou_ownership_bear"},
    "base": {"label": "基准", "pe": "core_pe_base", "arr": "arr_usd_mn_base", "ps": "ps_base", "ownership": "kuaishou_ownership_base"},
    "bull": {"label": "乐观", "pe": "core_pe_bull", "arr": "arr_usd_mn_bull", "ps": "ps_bull", "ownership": "kuaishou_ownership_bull"},
}


def latest_market_price() -> float | None:
    if not MARKET_PRICES_PATH.exists():
        return None
    with MARKET_PRICES_PATH.open("r", encoding="utf-8", newline="") as f:
        rows = [row for row in csv.DictReader(f) if row.get("close_hkd")]
    if not rows:
        return None
    try:
        return float(rows[-1]["close_hkd"])
    except (TypeError, ValueError):
        return None


def pct_text(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def money(value: float) -> str:
    return f"{value:.2f}"


def calculate_rows(assumptions: dict[str, Any]) -> list[dict[str, Any]]:
    kuaishou = assumptions["kuaishou"]
    kling = assumptions["kling"]
    market = assumptions["market"]

    current_price = market.get("current_price_hkd") or latest_market_price()
    current_price = float(current_price) if current_price else None

    profit_rmb_bn = float(kuaishou["adjusted_net_profit_rmb_bn"])
    cny_hkd = float(market["cny_hkd"])
    usd_hkd = float(market["usd_hkd"])
    shares_bn = float(market["shares_outstanding_bn"])
    as_of = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    rows: list[dict[str, Any]] = []
    for scenario, keys in SCENARIOS.items():
        core_pe = float(kuaishou[keys["pe"]])
        arr_usd_mn = float(kling[keys["arr"]])
        ps = float(kling[keys["ps"]])
        ownership = float(kling[keys["ownership"]])

        core_value_hkd_bn = profit_rmb_bn * core_pe * cny_hkd
        kling_total_value_hkd_bn = arr_usd_mn / 1000 * ps * usd_hkd
        kling_owned_value_hkd_bn = kling_total_value_hkd_bn * ownership
        total_value_hkd_bn = core_value_hkd_bn + kling_owned_value_hkd_bn
        target_price_hkd = total_value_hkd_bn / shares_bn
        upside_pct = None if current_price is None else (target_price_hkd / current_price - 1) * 100

        rows.append(
            {
                "as_of": as_of,
                "scenario": scenario,
                "scenario_label": keys["label"],
                "adjusted_net_profit_rmb_bn": profit_rmb_bn,
                "core_pe": core_pe,
                "core_value_hkd_bn": core_value_hkd_bn,
                "kling_arr_usd_mn": arr_usd_mn,
                "kling_ps": ps,
                "kling_total_value_hkd_bn": kling_total_value_hkd_bn,
                "kuaishou_ownership": ownership,
                "kling_owned_value_hkd_bn": kling_owned_value_hkd_bn,
                "total_sotp_value_hkd_bn": total_value_hkd_bn,
                "shares_outstanding_bn": shares_bn,
                "target_price_hkd": target_price_hkd,
                "current_price_hkd": current_price,
                "upside_downside_pct": upside_pct,
                "source": assumptions.get("metadata", {}).get("source", "manual"),
                "source_date": assumptions.get("metadata", {}).get("source_date", ""),
            }
        )
    return rows


def append_history(rows: list[dict[str, Any]]) -> None:
    VALUATION_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = VALUATION_HISTORY_PATH.exists()
    with VALUATION_HISTORY_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def write_snapshot(rows: list[dict[str, Any]]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    current_price = rows[0]["current_price_hkd"]
    lines = [
        "# 估值快照",
        "",
        f"- 生成时间：{rows[0]['as_of']}",
        f"- 当前股价：{money(current_price) + ' 港元' if current_price else 'N/A（请更新 data/processed/market_prices.csv 或 config/valuation_assumptions.yaml）'}",
        "- 货币单位：除每股价格外，价值单位均为十亿港元。",
        "",
        "| 情景 | 核心业务价值 | 可灵总价值 | 快手持有可灵价值 | SOTP 总价值 | 目标价 | 上行/下行 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {scenario_label} | {core} | {kling_total} | {kling_owned} | {total} | {target} | {upside} |".format(
                scenario_label=row["scenario_label"],
                core=money(row["core_value_hkd_bn"]),
                kling_total=money(row["kling_total_value_hkd_bn"]),
                kling_owned=money(row["kling_owned_value_hkd_bn"]),
                total=money(row["total_sotp_value_hkd_bn"]),
                target=money(row["target_price_hkd"]),
                upside=pct_text(row["upside_downside_pct"]),
            )
        )
    lines.extend(
        [
            "",
            "## 假设来源",
            "",
            f"- 来源：{rows[0]['source']}",
            f"- 来源日期：{rows[0]['source_date']}",
            "- 未经核实的传闻不得进入本估值模型。",
        ]
    )
    SNAPSHOT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    assumptions = load_yaml(ASSUMPTIONS_PATH)
    rows = calculate_rows(assumptions)
    append_history(rows)
    write_snapshot(rows)
    print(f"Wrote {VALUATION_HISTORY_PATH}")
    print(f"Wrote {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
