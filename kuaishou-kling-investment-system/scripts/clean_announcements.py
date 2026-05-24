from __future__ import annotations

import re
from pathlib import Path

from common import read_csv, write_csv


ROOT = Path(__file__).resolve().parents[1]
ANNOUNCEMENTS_PATH = ROOT / "data" / "processed" / "announcements.csv"
FIELDNAMES = ["date", "title", "source", "link", "summary", "is_major_event", "keywords", "credibility", "fetched_at"]
KEYWORDS = ["可灵", "Kling", "AI", "分拆", "融资", "重组", "资本开支", "ARR", "估值", "外部投资者"]
IR_CONTENT_PATH_MARKERS = ["/news-releases/", "/events/"]


def match_keywords(text: str) -> list[str]:
    matched: list[str] = []
    for keyword in KEYWORDS:
        if keyword == "AI":
            if re.search(r"(?<![A-Za-z])AI(?![A-Za-z])", text, flags=re.IGNORECASE):
                matched.append(keyword)
            continue
        if keyword.lower() in text.lower():
            matched.append(keyword)
    return matched


def keep_row(row: dict[str, str]) -> bool:
    if row.get("source") != "Kuaishou IR":
        return True
    link = row.get("link", "")
    title = row.get("title", "").strip().lower()
    if "#" in link or link.startswith("mailto:"):
        return False
    if title in {"view all", "webcast", "english", "简", "繁", "home"}:
        return False
    return any(marker in link for marker in IR_CONTENT_PATH_MARKERS)


def main() -> None:
    rows = []
    seen: set[tuple[str, str]] = set()
    for row in read_csv(ANNOUNCEMENTS_PATH):
        if not keep_row(row):
            continue
        key = (row.get("title", ""), row.get("link", ""))
        if key in seen:
            continue
        seen.add(key)
        matched = match_keywords(" ".join([row.get("title", ""), row.get("summary", "")]))
        row["keywords"] = ";".join(matched)
        row["is_major_event"] = str(bool(matched))
        rows.append(row)
    write_csv(ANNOUNCEMENTS_PATH, rows, FIELDNAMES, append=False)
    print(f"Kept {len(rows)} cleaned announcement row(s)")


if __name__ == "__main__":
    main()
