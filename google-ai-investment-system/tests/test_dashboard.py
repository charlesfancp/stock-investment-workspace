from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_data_json_exists_and_is_valid() -> None:
    data_path = PROJECT_ROOT / "dashboard" / "data.json"

    assert data_path.exists()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    assert data["asset"] == "Alphabet Inc."
    assert "decision" in data
    assert "evidence" in data
    assert "position" in data
    assert "market" in data
    assert "rr_gate" in data
    assert "price_sensitivity" in data
    assert "valuation_scenarios" in data
    assert "io_event" in data
    assert "analysts" in data
    assert "missing_inputs" in data


def test_build_dashboard_data_generates_valid_json() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_dashboard_data.py"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    data_path = PROJECT_ROOT / "dashboard" / "data.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))

    assert "已生成面板数据" in result.stdout
    assert data["action"] == "持有 / 不加仓"
    assert data["rr_gate"]["unlocked"] is True
    assert data["rr_gate"]["title"] == "R/R 已解锁"
    assert data["price_sensitivity"]["available"] is True
    assert data["price_sensitivity"]["buy_below"] == "$372.12"
    assert data["price_sensitivity"]["reduce_review_above"] == "$397.38"
    assert data["valuation_scenarios"]["available"] is True
    assert len(data["valuation_scenarios"]["rows"]) == 3
    assert data["valuation_scenarios"]["rows"][0]["current_decision"] == "减仓复盘"
    assert data["io_event"]["status"] == "已核实；未进入买入/加仓结论"
    assert data["analysts"]["status"] == "已录入；仅作外部估值参考"


def test_readme_contains_dashboard_open_command() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "python scripts/serve_dashboard.py" in readme
    assert "http://127.0.0.1:8765/" in readme
    assert "position_snapshot.csv" in readme
    assert "market_snapshot.csv" in readme


def test_position_snapshot_template_exists() -> None:
    position_path = PROJECT_ROOT / "data" / "raw" / "position_snapshot.csv"

    assert position_path.exists()
    header = position_path.read_text(encoding="utf-8").splitlines()[0]
    assert "shares" in header
    assert "position_weight_pct" in header


def test_port_in_use_detects_bound_socket() -> None:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from serve_dashboard import port_in_use

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]

        assert port_in_use(port) is True
