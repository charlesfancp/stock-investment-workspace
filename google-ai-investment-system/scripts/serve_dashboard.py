from __future__ import annotations

import argparse
import csv
import functools
import http.server
import json
import socket
import socketserver
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
DEFAULT_PORT = 8765

from build_dashboard_data import build_dashboard_data


def main() -> int:
    parser = argparse.ArgumentParser(description="启动 Google 投资决策面板本地服务")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="本地端口，默认 8765")
    args = parser.parse_args()

    dashboard_dir = PROJECT_ROOT / "dashboard"
    if not dashboard_dir.exists():
        print(f"dashboard/ 目录不存在：{dashboard_dir}")
        return 1
    if port_in_use(args.port):
        print(f"端口 {args.port} 已被占用，请换一个端口，例如：python scripts/serve_dashboard.py --port 8766")
        return 1

    handler = functools.partial(DashboardHandler, directory=str(dashboard_dir))
    with ReusableTCPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Dashboard 服务已启动： http://127.0.0.1:{args.port}/")
        print("按 Ctrl+C 停止服务。")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard 服务已停止。")
    return 0


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        try:
            payload = self.read_json()
            if route == "/api/valuation":
                append_csv(PROJECT_ROOT / "data" / "raw" / "valuation_snapshot.csv", valuation_fields(), payload)
            elif route == "/api/position":
                append_csv(PROJECT_ROOT / "data" / "raw" / "position_snapshot.csv", position_fields(), payload)
            elif route == "/api/market":
                append_csv(PROJECT_ROOT / "data" / "raw" / "market_snapshot.csv", market_fields(), payload)
            elif route == "/api/decision-plan":
                payload.setdefault("created_at", generated_at())
                payload.setdefault("date", date.today().isoformat())
                append_csv(PROJECT_ROOT / "decision_log" / "decision_plans.csv", decision_plan_fields(), payload)
            elif route == "/api/refresh":
                refresh_full_report()
                self.send_json({"ok": True, "message": "已重新生成报告和面板数据"})
                return
            else:
                self.send_json({"ok": False, "error": "unknown endpoint"}, status=404)
                return
            refresh_dashboard_data()
            self.send_json({"ok": True})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=400)

    def read_json(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw or "{}")
        return {str(key): str(value).strip() for key, value in data.items()}

    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def append_csv(path: Path, fields: list[str], payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    row = {field: payload.get(field, "数据缺失") or "数据缺失" for field in fields}
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def refresh_dashboard_data() -> None:
    output_path = PROJECT_ROOT / "dashboard" / "data.json"
    output_path.write_text(
        json.dumps(build_dashboard_data(PROJECT_ROOT, __import__("datetime").date.today()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def refresh_full_report() -> None:
    scripts_root = PROJECT_ROOT / "scripts"
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    from generate_report import main as generate_report_main

    generate_report_main()


def generated_at() -> str:
    return datetime.now().isoformat(timespec="seconds")


def valuation_fields() -> list[str]:
    return [
        "date",
        "ticker",
        "current_price",
        "target_price_base",
        "downside_price",
        "market_cap_usd_bn",
        "diluted_shares_bn",
        "pe_ratio",
        "fcf_yield_pct",
        "ev_to_fcf",
        "net_cash_usd_bn",
        "source_url",
        "source_date",
        "captured_at",
        "valuation_methodology",
        "notes",
    ]


def position_fields() -> list[str]:
    return [
        "date",
        "ticker",
        "shares",
        "avg_cost",
        "current_price",
        "market_value_usd",
        "unrealized_pnl_pct",
        "position_weight_pct",
        "cash_available_usd",
        "source",
        "notes",
    ]


def decision_plan_fields() -> list[str]:
    return [
        "created_at",
        "date",
        "ticker",
        "decision_type",
        "planned_action",
        "trigger_price",
        "shares_or_budget",
        "target_weight_pct",
        "rr_at_decision",
        "reason",
        "confirm_conditions",
        "risk_controls",
        "review_date",
        "review_result",
        "review_notes",
    ]


def market_fields() -> list[str]:
    return [
        "date",
        "ticker",
        "share_class",
        "current_price",
        "market_cap_usd_bn",
        "pe_ratio",
        "price_change_pct",
        "regular_close_time",
        "pre_market_price",
        "source_name",
        "source_url",
        "captured_at",
        "notes",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
