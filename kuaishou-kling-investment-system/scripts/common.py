from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def simple_yaml_load(text: str) -> dict[str, Any]:
    raw_lines = [line.rstrip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for index, line in enumerate(raw_lines):
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        while indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if stripped.startswith("- "):
            if isinstance(parent, list):
                parent.append(parse_scalar(stripped[2:]))
            continue
        key, _, value = stripped.partition(":")
        if value.strip():
            parent[key] = parse_scalar(value)
            continue
        next_line = next((candidate for candidate in raw_lines[index + 1 :] if len(candidate) - len(candidate.lstrip(" ")) > indent), "")
        node: dict[str, Any] | list[Any] = [] if next_line.strip().startswith("- ") else {}
        parent[key] = node
        stack.append((indent, node))
    return root


def load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(text) or {}
    return simple_yaml_load(text)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str], append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not append or not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def row_float(row: dict[str, str] | None, key: str) -> float | None:
    if not row:
        return None
    try:
        value = row.get(key, "")
        return float(value) if value not in {"", None} else None
    except ValueError:
        return None


def latest_by_nonempty(rows: list[dict[str, str]], key: str) -> dict[str, str] | None:
    valid = [row for row in rows if row.get(key)]
    return valid[-1] if valid else None
