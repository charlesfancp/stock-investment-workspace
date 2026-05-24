from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "market_prices"
MARKET_PRICES_PATH = ROOT / "data" / "processed" / "market_prices.csv"
FIELDNAMES = ["date", "symbol", "close_hkd", "change_pct", "volume", "turnover_hkd", "source", "source_date", "fetched_at"]


def existing_dates() -> set[str]:
    if not MARKET_PRICES_PATH.exists():
        return set()
    with MARKET_PRICES_PATH.open("r", encoding="utf-8", newline="") as f:
        return {row.get("date", "") for row in csv.DictReader(f)}


def main() -> None:
    symbol = "1024.HK"
    now = datetime.now(timezone.utc).astimezone()
    fetched_at = now.isoformat(timespec="seconds")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"

    request = Request(url, headers={"User-Agent": "investment-research-tracker/0.1"})
    try:
        with urlopen(request, timeout=12) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"Market price fetch skipped: {type(exc).__name__}: {exc}")
        sys.exit(1)
    data = json.loads(raw_text)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{now.strftime('%Y%m%d-%H%M%S')}-{symbol}.json"
    raw_path.write_text(raw_text, encoding="utf-8")

    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    closes = result["indicators"].get("adjclose", [{}])[0].get("adjclose") or quote.get("close", [])
    volumes = quote.get("volume", [])
    seen = existing_dates()
    rows: list[dict[str, str]] = []
    previous_close = None

    for ts, close, volume in zip(timestamps, closes, volumes):
        if close is None:
            continue
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        if day in seen:
            previous_close = close
            continue
        change_pct = ""
        if previous_close:
            change_pct = f"{(close / previous_close - 1) * 100:.2f}"
        rows.append(
            {
                "date": day,
                "symbol": symbol,
                "close_hkd": f"{close:.3f}",
                "change_pct": change_pct,
                "volume": str(volume or ""),
                "turnover_hkd": "",
                "source": "Yahoo Finance chart API",
                "source_date": day,
                "fetched_at": fetched_at,
            }
        )
        previous_close = close

    file_exists = MARKET_PRICES_PATH.exists()
    with MARKET_PRICES_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"Saved raw market data to {raw_path}")
    print(f"Appended {len(rows)} market price row(s) to {MARKET_PRICES_PATH}")


if __name__ == "__main__":
    main()
