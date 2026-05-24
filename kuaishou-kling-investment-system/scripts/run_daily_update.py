from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ("更新行情", ["scripts/fetch_market_price.py"], False),
    ("更新快手 IR", ["scripts/fetch_kuaishou_ir.py"], False),
    ("更新港交所公告", ["scripts/fetch_hkex.py"], False),
    ("更新分析师观点", ["scripts/fetch_analyst_views.py"], False),
    ("清理公告噪音", ["scripts/clean_announcements.py"], True),
    ("更新估值模型", ["models/valuation_engine.py"], True),
    ("生成事件 memo", ["scripts/generate_event_memo.py"], True),
    ("生成每日简报", ["scripts/generate_daily_brief.py"], True),
]


def run_step(label: str, command: list[str], required: bool) -> tuple[str, int, str]:
    try:
        process = subprocess.run(
            [sys.executable, *command],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=90 if required else 30,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        output = output.strip()
        message = f"{output}\nTimed out after {exc.timeout} seconds".strip()
        if required:
            raise RuntimeError(f"{label} timed out:\n{message}")
        return label, 124, message
    if required and process.returncode != 0:
        raise RuntimeError(f"{label} failed:\n{process.stdout}")
    return label, process.returncode, process.stdout.strip()


def main() -> None:
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines = ["# 每日更新运行记录", "", f"- 运行时间：{now}", ""]
    for label, command, required in STEPS:
        status = "完成"
        try:
            _, returncode, output = run_step(label, command, required)
            if returncode != 0:
                status = "跳过/失败，不阻断"
        except RuntimeError as exc:
            lines.append(f"## {label}")
            lines.append("")
            lines.append("- 状态：失败，已停止")
            lines.append("```")
            lines.append(str(exc))
            lines.append("```")
            path = ROOT / "reports" / "daily" / "latest_run_log.md"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            raise
        lines.append(f"## {label}")
        lines.append("")
        lines.append(f"- 状态：{status}")
        if output:
            lines.append("```")
            lines.append(output)
            lines.append("```")
        lines.append("")

    path = ROOT / "reports" / "daily" / "latest_run_log.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
