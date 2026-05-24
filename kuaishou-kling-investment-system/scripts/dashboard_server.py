from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))
from common import load_yaml

WEB_DIR = ROOT / "web"
PORT = int(os.environ.get("PORT", "8765"))
POSITION_RECORDS_PATH = ROOT / "data" / "processed" / "position_records.csv"
ANALYST_VIEWS_PATH = ROOT / "data" / "processed" / "analyst_views.csv"
EVIDENCE_INDEX_PATH = ROOT / "evidence" / "source_index.csv"
POSITION_FIELDNAMES = [
    "recorded_at",
    "record_type",
    "symbol",
    "price_hkd",
    "budget_hkd",
    "board_lot_shares",
    "lots",
    "shares",
    "gross_amount_hkd",
    "cash_left_hkd",
    "action",
    "base_target_hkd",
    "base_upside_pct",
    "note",
]


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def latest_price() -> dict[str, str] | None:
    rows = [row for row in read_csv(ROOT / "data" / "processed" / "market_prices.csv") if row.get("close_hkd")]
    return rows[-1] if rows else None


def latest_valuations() -> list[dict[str, str]]:
    rows = read_csv(ROOT / "data" / "processed" / "valuation_history.csv")
    if not rows:
        return []
    latest_as_of = rows[-1].get("as_of")
    return [row for row in rows if row.get("as_of") == latest_as_of]


def latest_base_valuation() -> dict[str, str] | None:
    return next((row for row in latest_valuations() if row.get("scenario") == "base"), None)


def latest_announcements(limit: int = 8) -> list[dict[str, str]]:
    rows = read_csv(ROOT / "data" / "processed" / "announcements.csv")
    rows.sort(key=lambda row: (row.get("date", ""), row.get("fetched_at", "")), reverse=True)
    return rows[:limit]


TITLE_TRANSLATIONS = {
    "Kuaishou Technology to Report 2026 First Quarter Financial Results on May 27, 2026": "快手科技将于 2026 年 5 月 27 日发布 2026 年一季度业绩",
    "Kuaishou Releases 2025 ESG Report, Deepening Green Operations and Expanding ESG Practices with AI": "快手发布 2025 ESG 报告，推进绿色运营并拓展 AI 实践",
    "Kuaishou Technology Announces Fourth Quarter and Full Year 2025 Financial Results": "快手科技发布 2025 年第四季度及全年业绩",
    "Kuaishou Technology First Quarter 2026 Financial Results Conference Call": "快手科技 2026 年一季度业绩电话会",
    "Kuaishou Technology Fourth Quarter and Full Year 2025 Financial Results Conference Call": "快手科技 2025 年第四季度及全年业绩电话会",
    "Kuaishou Technology Third Quarter 2025 Financial Results Conference Call": "快手科技 2025 年三季度业绩电话会",
}


def translate_announcement(row: dict[str, str]) -> dict[str, str]:
    title = row.get("title", "")
    translated = dict(row)
    translated["display_title"] = TITLE_TRANSLATIONS.get(title, title)
    translated["display_source"] = "快手 IR" if row.get("source") == "Kuaishou IR" else row.get("source", "")
    return translated


def report_path(name: str) -> Path:
    today_reports = sorted((ROOT / "reports" / "daily").glob("*-daily-brief.md"))
    paths = {
        "daily": today_reports[-1] if today_reports else ROOT / "reports" / "daily" / "valuation_snapshot.md",
        "valuation": ROOT / "reports" / "daily" / "valuation_snapshot.md",
        "weekly": ROOT / "reports" / "weekly" / "latest_weekly_memo.md",
        "bear": ROOT / "reports" / "weekly" / "latest_bear_case_review.md",
        "run": ROOT / "reports" / "daily" / "latest_run_log.md",
    }
    return paths.get(name, paths["daily"])


def action_from_daily(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("- 系统动作："):
            return line.split("：", 1)[1].strip()
        if line.startswith("- ") and line[2:] in {"买入", "加仓", "持有", "减仓", "卖出"}:
            return line[2:].strip()
    return "待更新"


def trade_settings() -> dict[str, object]:
    path = ROOT / "config" / "trade_settings.yaml"
    if not path.exists():
        return {"symbol": "1024.HK", "board_lot_shares": 100, "default_budget_hkd": 100000}
    return load_yaml(path)


def position_records() -> list[dict[str, str]]:
    return read_csv(POSITION_RECORDS_PATH)[-20:][::-1]


def analyst_views(limit: int = 8) -> list[dict[str, str]]:
    rows = read_csv(ANALYST_VIEWS_PATH)
    rows.sort(key=lambda row: (row.get("date", ""), row.get("target_price_hkd", "")), reverse=True)
    return rows[:limit]


def evidence_items(limit: int = 8) -> list[dict[str, str]]:
    rows = read_csv(EVIDENCE_INDEX_PATH)
    return rows[:limit]


def dashboard_rules() -> dict[str, object]:
    alerts = load_yaml(ROOT / "config" / "alert_rules.yaml")
    trade = trade_settings()
    return {
        "price_alerts": alerts.get("price_alerts", {}),
        "event_alerts": alerts.get("event_alerts", {}),
        "decision_rules": alerts.get("decision_rules", {}),
        "trade_settings": trade,
    }


def write_position_records(rows: list[dict[str, str]]) -> None:
    POSITION_RECORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with POSITION_RECORDS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=POSITION_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in POSITION_FIELDNAMES})


def calculate_position(amount: float | None = None) -> dict[str, object]:
    settings = trade_settings()
    price_row = latest_price()
    base = latest_base_valuation()
    price = float(price_row["close_hkd"]) if price_row and price_row.get("close_hkd") else 0
    budget = float(amount if amount is not None else settings.get("default_budget_hkd", 100000))
    board_lot = int(settings.get("board_lot_shares", 100))
    lot_value = price * board_lot if price else 0
    lots = int(budget // lot_value) if lot_value else 0
    shares = lots * board_lot
    gross_amount = shares * price
    cash_left = budget - gross_amount
    return {
        "symbol": settings.get("symbol", "1024.HK"),
        "price_hkd": price,
        "budget_hkd": budget,
        "board_lot_shares": board_lot,
        "lot_value_hkd": lot_value,
        "lots": lots,
        "shares": shares,
        "gross_amount_hkd": gross_amount,
        "cash_left_hkd": cash_left,
        "price_date": price_row.get("date") if price_row else "",
        "base_target_hkd": float(base["target_price_hkd"]) if base and base.get("target_price_hkd") else None,
        "base_upside_pct": float(base["upside_downside_pct"]) if base and base.get("upside_downside_pct") else None,
        "source": settings.get("source", ""),
    }


def append_position_record(amount: float | None = None, note: str = "") -> dict[str, object]:
    daily_text = read_text(report_path("daily"))
    calc = calculate_position(amount)
    base_target = calc.get("base_target_hkd")
    base_upside = calc.get("base_upside_pct")
    row = {
        "recorded_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "record_type": "simulated_buy",
        "symbol": calc["symbol"],
        "price_hkd": f"{float(calc['price_hkd']):.3f}",
        "budget_hkd": f"{float(calc['budget_hkd']):.2f}",
        "board_lot_shares": str(calc["board_lot_shares"]),
        "lots": str(calc["lots"]),
        "shares": str(calc["shares"]),
        "gross_amount_hkd": f"{float(calc['gross_amount_hkd']):.2f}",
        "cash_left_hkd": f"{float(calc['cash_left_hkd']):.2f}",
        "action": action_from_daily(daily_text),
        "base_target_hkd": "" if base_target is None else f"{float(base_target):.3f}",
        "base_upside_pct": "" if base_upside is None else f"{float(base_upside):.2f}",
        "note": note,
    }
    POSITION_RECORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = POSITION_RECORDS_PATH.exists()
    with POSITION_RECORDS_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=POSITION_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    return {"record": row, "calculation": calc}


def delete_position_record(recorded_at: str) -> dict[str, object]:
    rows = read_csv(POSITION_RECORDS_PATH)
    kept = [row for row in rows if row.get("recorded_at") != recorded_at]
    write_position_records(kept)
    return {"ok": len(kept) != len(rows), "deleted": recorded_at}


def update_position_note(recorded_at: str, note: str) -> dict[str, object]:
    rows = read_csv(POSITION_RECORDS_PATH)
    updated = False
    for row in rows:
        if row.get("recorded_at") == recorded_at:
            row["note"] = note
            updated = True
            break
    write_position_records(rows)
    return {"ok": updated, "recorded_at": recorded_at, "note": note}


def summary() -> dict[str, object]:
    daily_text = read_text(report_path("daily"))
    price = latest_price()
    valuations = latest_valuations()
    base = next((row for row in valuations if row.get("scenario") == "base"), None)
    return {
        "price": price,
        "action": action_from_daily(daily_text),
        "baseTarget": base.get("target_price_hkd") if base else None,
        "baseUpside": base.get("upside_downside_pct") if base else None,
        "valuations": valuations,
        "announcements": [translate_announcement(row) for row in latest_announcements()],
        "position": calculate_position(),
        "positionRecords": position_records(),
        "analystViews": analyst_views(),
        "evidence": evidence_items(),
        "rules": dashboard_rules(),
        "reports": {
            "daily": daily_text,
            "valuation": read_text(report_path("valuation")),
            "weekly": read_text(report_path("weekly")),
            "bear": read_text(report_path("bear")),
            "run": read_text(report_path("run")),
        },
    }


def run_script(commands: list[list[str]]) -> dict[str, object]:
    output: list[str] = []
    for command in commands:
        try:
            process = subprocess.run(
                [sys.executable, *command],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            partial = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            output.append(
                f"$ python {' '.join(command)}\n{partial.strip()}\nTimed out after {exc.timeout} seconds".strip()
            )
            return {"ok": False, "output": "\n\n".join(output)}
        output.append(f"$ python {' '.join(command)}\n{process.stdout.strip()}")
        if process.returncode != 0:
            return {"ok": False, "output": "\n\n".join(output)}
    return {"ok": True, "output": "\n\n".join(output)}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def send_json(self, status: int, data: dict[str, object]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/summary":
            self.send_json(200, summary())
            return
        if path == "/api/position/calc":
            query = urlparse(self.path).query
            amount = None
            if query.startswith("amount="):
                try:
                    amount = float(query.split("=", 1)[1])
                except ValueError:
                    amount = None
            self.send_json(200, calculate_position(amount))
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path in {"/api/position/delete", "/api/position/note"}:
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(body or "{}")
            except json.JSONDecodeError:
                payload = {}
            recorded_at = str(payload.get("recorded_at", "")).strip()
            if not recorded_at:
                self.send_json(400, {"ok": False, "error": "missing recorded_at"})
                return
            if path == "/api/position/delete":
                self.send_json(200, delete_position_record(recorded_at))
            else:
                self.send_json(200, update_position_note(recorded_at, str(payload.get("note", "")).strip()))
            return
        if path == "/api/position/record":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(body or "{}")
            except json.JSONDecodeError:
                payload = {}
            amount = payload.get("amount")
            note = str(payload.get("note", "")).strip()
            try:
                amount_value = float(amount) if amount not in {None, ""} else None
            except ValueError:
                amount_value = None
            self.send_json(200, append_position_record(amount_value, note))
            return
        routes = {
            "/api/run/daily": [["scripts/run_daily_update.py"]],
            "/api/run/weekly": [["scripts/generate_weekly_memo.py"]],
            "/api/run/bear": [["scripts/generate_bear_case_review.py"]],
            "/api/run/all": [
                ["scripts/run_daily_update.py"],
                ["scripts/generate_weekly_memo.py"],
                ["scripts/generate_bear_case_review.py"],
            ],
        }
        if path not in routes:
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        result = run_script(routes[path])
        self.send_json(200 if result["ok"] else 500, result)


def main() -> None:
    server = None
    port = PORT
    for candidate in range(PORT, PORT + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        raise OSError(f"No available port in {PORT}-{PORT + 19}")
    print(f"Dashboard: http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
