from __future__ import annotations

import csv
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "kuaishou_ir"
ANNOUNCEMENTS_PATH = ROOT / "data" / "processed" / "announcements.csv"
IR_URL = "https://ir.kuaishou.com/"
KEYWORDS = ["可灵", "Kling", "AI", "分拆", "融资", "重组", "资本开支", "ARR", "估值", "外部投资者"]
CONTENT_PATH_MARKERS = ["/news-releases/", "/events/"]
FIELDNAMES = ["date", "title", "source", "link", "summary", "is_major_event", "keywords", "credibility", "fetched_at"]


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            title = " ".join("".join(self._text).split())
            if title:
                self.links.append((title, self._href))
            self._href = None
            self._text = []


def existing_keys() -> set[tuple[str, str]]:
    if not ANNOUNCEMENTS_PATH.exists():
        return set()
    with ANNOUNCEMENTS_PATH.open("r", encoding="utf-8", newline="") as f:
        return {(row.get("title", ""), row.get("link", "")) for row in csv.DictReader(f)}


def append_rows(rows: list[dict[str, str]]) -> None:
    ANNOUNCEMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = ANNOUNCEMENTS_PATH.exists()
    with ANNOUNCEMENTS_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


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


def is_content_link(title: str, url: str) -> bool:
    if url.startswith("mailto:") or "#" in url:
        return False
    if title.lower() in {"view all", "webcast", "english", "简", "繁", "home"}:
        return False
    return any(marker in url for marker in CONTENT_PATH_MARKERS)


def main() -> None:
    now = datetime.now(timezone.utc).astimezone()
    fetched_at = now.isoformat(timespec="seconds")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    request = Request(IR_URL, headers={"User-Agent": "investment-research-tracker/0.1"})
    try:
        with urlopen(request, timeout=6) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"IR fetch skipped: {type(exc).__name__}: {exc}")
        sys.exit(1)
    raw_path = RAW_DIR / f"{now.strftime('%Y%m%d-%H%M%S')}-kuaishou-ir.html"
    raw_path.write_text(html, encoding="utf-8")

    parser = LinkExtractor()
    parser.feed(html)
    seen = existing_keys()
    rows: list[dict[str, str]] = []
    for title, href in parser.links:
        if not title or not href:
            continue
        full_url = urljoin(IR_URL, href)
        if not is_content_link(title, full_url):
            continue
        matched = match_keywords(title)
        key = (title, full_url)
        if key in seen:
            continue
        rows.append(
            {
                "date": now.date().isoformat(),
                "title": title,
                "source": "Kuaishou IR",
                "link": full_url,
                "summary": title,
                "is_major_event": str(bool(matched)),
                "keywords": ";".join(matched),
                "credibility": "高",
                "fetched_at": fetched_at,
            }
        )
        seen.add(key)

    append_rows(rows)
    print(f"Saved raw page to {raw_path}")
    print(f"Appended {len(rows)} IR row(s) to {ANNOUNCEMENTS_PATH}")


if __name__ == "__main__":
    main()
