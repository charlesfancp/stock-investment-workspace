#!/usr/bin/env python3
"""Fetch latest price data for the AI infrastructure portfolio.

This first version intentionally uses only public Yahoo Finance chart data.
Fields unavailable from that endpoint are written as null instead of estimated.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "config" / "portfolio.yaml"
BENCHMARKS_PATH = ROOT / "config" / "benchmarks.yaml"
PROCESSED_PATH = ROOT / "data" / "processed" / "prices_latest.csv"
BENCHMARKS_PROCESSED_PATH = ROOT / "data" / "processed" / "benchmarks_latest.csv"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
SOURCE = "Yahoo Finance chart API"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
MAX_FETCH_ATTEMPTS = 3

FIELDNAMES = [
    "ticker",
    "price",
    "market_cap",
    "pe_ttm",
    "pe_forward",
    "week_52_high",
    "week_52_low",
    "change_percent",
    "ma_20",
    "ma_50",
    "ma_200",
    "source",
    "source_date",
    "fetched_at",
    "error",
]


def read_portfolio_tickers(path: Path = PORTFOLIO_PATH) -> list[str]:
    text = path.read_text(encoding="utf-8")
    tickers = re.findall(r"^\s*-\s+ticker:\s*([A-Z.]+)\s*$", text, flags=re.MULTILINE)
    if not tickers:
        raise ValueError(f"No tickers found in {path}")
    return tickers


def read_benchmark_tickers(path: Path = BENCHMARKS_PATH) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    tickers = re.findall(r"^\s*-\s+ticker:\s*([A-Z.]+)\s*$", text, flags=re.MULTILINE)
    return tickers


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def yahoo_chart_url(ticker: str) -> str:
    symbol = quote(ticker)
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d"


def to_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def moving_average(values: list[float], days: int) -> float | None:
    if len(values) < days:
        return None
    window = values[-days:]
    if not window:
        return None
    return sum(window) / len(window)


def parse_chart_response(ticker: str, data: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    chart = data.get("chart", {})
    error = chart.get("error")
    if error:
        raise ValueError(error.get("description") or str(error))

    result = (chart.get("result") or [None])[0]
    if not result:
        raise ValueError("Yahoo chart returned no result")

    meta = result.get("meta") or {}
    quote_data = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    timestamps = result.get("timestamp") or []
    closes = [
        to_number(value)
        for value in quote_data.get("close", [])
        if to_number(value) is not None
    ]
    closes = [value for value in closes if value is not None]

    price = to_number(meta.get("regularMarketPrice"))
    previous_close = closes[-2] if len(closes) >= 2 else to_number(meta.get("chartPreviousClose"))
    change_percent = None
    if price is not None and previous_close not in (None, 0):
        change_percent = ((price - previous_close) / previous_close) * 100

    source_date = None
    regular_market_time = meta.get("regularMarketTime")
    if regular_market_time:
        source_date = datetime.fromtimestamp(int(regular_market_time)).date().isoformat()
    elif timestamps:
        source_date = datetime.fromtimestamp(int(timestamps[-1])).date().isoformat()

    return {
        "ticker": ticker,
        "price": round_or_none(price),
        "market_cap": None,
        "pe_ttm": None,
        "pe_forward": None,
        "week_52_high": round_or_none(to_number(meta.get("fiftyTwoWeekHigh"))),
        "week_52_low": round_or_none(to_number(meta.get("fiftyTwoWeekLow"))),
        "change_percent": round_or_none(change_percent),
        "ma_20": round_or_none(moving_average(closes, 20)),
        "ma_50": round_or_none(moving_average(closes, 50)),
        "ma_200": round_or_none(moving_average(closes, 200)),
        "source": SOURCE,
        "source_date": source_date,
        "fetched_at": fetched_at,
        "error": None,
    }


def error_row(ticker: str, fetched_at: str, exc: Exception) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "price": None,
        "market_cap": None,
        "pe_ttm": None,
        "pe_forward": None,
        "week_52_high": None,
        "week_52_low": None,
        "change_percent": None,
        "ma_20": None,
        "ma_50": None,
        "ma_200": None,
        "source": SOURCE,
        "source_date": None,
        "fetched_at": fetched_at,
        "error": f"{type(exc).__name__}: {exc}",
    }


def fetch_ticker(ticker: str, fetched_at: str, attempts: int = MAX_FETCH_ATTEMPTS) -> dict[str, Any]:
    last_error: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            data = fetch_json(yahoo_chart_url(ticker))
            return parse_chart_response(ticker, data, fetched_at)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
    assert last_error is not None
    return error_row(ticker, fetched_at, last_error)


def csv_value(value: Any) -> Any:
    return "null" if value is None else value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in FIELDNAMES})


def fetch_all(tickers: list[str]) -> list[dict[str, Any]]:
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows_by_ticker: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as executor:
        futures = {executor.submit(fetch_ticker, ticker, fetched_at): ticker for ticker in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            rows_by_ticker[ticker] = future.result()
    return [rows_by_ticker[ticker] for ticker in tickers]


def main() -> int:
    tickers = read_portfolio_tickers()
    benchmark_tickers = read_benchmark_tickers()
    rows = fetch_all(tickers)
    benchmark_rows = fetch_all(benchmark_tickers) if benchmark_tickers else []
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    snapshot_path = SNAPSHOT_DIR / f"prices_{today}.csv"
    benchmark_snapshot_path = SNAPSHOT_DIR / f"benchmarks_{today}.csv"
    write_csv(PROCESSED_PATH, rows)
    write_csv(snapshot_path, rows)
    if benchmark_rows:
        write_csv(BENCHMARKS_PROCESSED_PATH, benchmark_rows)
        write_csv(benchmark_snapshot_path, benchmark_rows)

    errors = [row for row in [*rows, *benchmark_rows] if row.get("error")]
    print(f"Wrote {PROCESSED_PATH}")
    print(f"Wrote {snapshot_path}")
    if benchmark_rows:
        print(f"Wrote {BENCHMARKS_PROCESSED_PATH}")
        print(f"Wrote {benchmark_snapshot_path}")
    if errors:
        error_tickers = ", ".join(f"{row.get('ticker')}: {row.get('error')}" for row in errors)
        print(f"Completed with {len(errors)} ticker errors: {error_tickers}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
