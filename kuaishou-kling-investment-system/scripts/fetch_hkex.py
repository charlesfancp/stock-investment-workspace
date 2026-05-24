from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "hkex_announcements"
ANNOUNCEMENTS_PATH = ROOT / "data" / "processed" / "announcements.csv"
STOCK_CODE = "01024"
KEYWORDS = ["可灵", "Kling", "AI", "分拆", "融资", "重组", "资本开支", "ARR", "估值", "外部投资者"]
FIELDNAMES = ["date", "title", "source", "link", "summary", "is_major_event", "keywords", "credibility", "fetched_at"]
ACTIVE_STOCKS_URL = "https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json"
TITLE_SEARCH_URL = "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh"


def fetch_text(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 8) -> str:
    command = [
        "curl",
        "-L",
        "-s",
        "--max-time",
        str(timeout),
        "-A",
        "Mozilla/5.0 investment-research-tracker/0.2",
    ]
    for key, value in (headers or {}).items():
        command.extend(["-H", f"{key}: {value}"])
    if data is not None:
        command.extend(["--data", data.decode("utf-8")])
    command.append(url)
    process = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise TimeoutError(process.stderr.strip() or f"curl exited {process.returncode}")
    return process.stdout


def normalize_code(code: str) -> str:
    return "".join(ch for ch in code if ch.isdigit()).zfill(5)


def yyyymmdd(value: datetime) -> str:
    return value.strftime("%Y%m%d")


def decode_html(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]*>", " ", value))).strip()


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


def get_stock_info(code: str) -> dict[str, str]:
    normalized = normalize_code(code)
    raw = fetch_text(ACTIVE_STOCKS_URL)
    stocks = json.loads(raw)
    found = next((stock for stock in stocks if stock.get("c") == normalized), None)
    if not found:
        raise ValueError(f"HKEX active stock list did not contain {normalized}")
    return {
        "id": str(found["i"]),
        "code": str(found["c"]),
        "short_name": str(found.get("n", "")),
        "security_id": str(found.get("s", "")),
    }


def parse_release_datetime(raw: str) -> tuple[str, str]:
    text = decode_html(raw)
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})", text)
    if not match:
        today = datetime.now(timezone.utc).astimezone().date().isoformat()
        return today, text
    dd, mm, yyyy, hh, minute = match.groups()
    return f"{yyyy}-{mm}-{dd}", f"{yyyy}-{mm}-{dd} {hh}:{minute}"


def strip_label(text: str) -> str:
    return (
        text.replace("Stock Code:", "")
        .replace("股份代號:", "")
        .replace("Stock Short Name:", "")
        .replace("股份簡稱:", "")
        .strip()
    )


def parse_announcements(html: str) -> list[dict[str, str]]:
    rows = re.findall(r"<tr[\s\S]*?</tr>", html, flags=re.IGNORECASE)
    items: list[dict[str, str]] = []
    for row in rows:
        if "stock-short-code" not in row:
            continue
        cells = re.findall(r"<td[\s\S]*?</td>", row, flags=re.IGNORECASE)
        if len(cells) < 4:
            continue
        release_date, release_time = parse_release_datetime(cells[0])
        code = strip_label(decode_html(cells[1]))
        name = strip_label(decode_html(cells[2]))
        document_cell = cells[3]
        category_match = re.search(r'<div class="headline">([\s\S]*?)</div>', document_cell, flags=re.IGNORECASE)
        link_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', document_cell, flags=re.IGNORECASE)
        size_match = re.search(r'attachment_filesize">([^<]+)', document_cell, flags=re.IGNORECASE)
        if not link_match:
            continue
        href = link_match.group(1)
        link = href if href.startswith("http") else f"https://www1.hkexnews.hk{href}"
        title = decode_html(link_match.group(2))
        category = decode_html(category_match.group(1) if category_match else "")
        file_size = decode_html(size_match.group(1) if size_match else "")
        items.append(
            {
                "date": release_date,
                "release_time": release_time,
                "stock_code": code,
                "stock_name": name,
                "category": category,
                "title": title,
                "link": link,
                "file_size": file_size,
            }
        )
    return items


def search_hkex_announcements(stock_id: str, months: int = 12) -> tuple[str, list[dict[str, str]]]:
    now = datetime.now(timezone.utc).astimezone()
    start = now - timedelta(days=31 * months)
    params = {
        "lang": "ZH",
        "category": "0",
        "market": "SEHK",
        "searchType": "0",
        "documentType": "",
        "t1code": "-2",
        "t2Gcode": "-2",
        "t2code": "-2",
        "stockId": stock_id,
        "from": yyyymmdd(start),
        "to": yyyymmdd(now),
        "title": "",
    }
    body = urlencode(params).encode("utf-8")
    html = fetch_text(
        TITLE_SEARCH_URL,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh",
        },
    )
    return html, parse_announcements(html)


def main() -> None:
    now = datetime.now(timezone.utc).astimezone()
    fetched_at = now.isoformat(timespec="seconds")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    try:
        stock = get_stock_info(STOCK_CODE)
        html, items = search_hkex_announcements(stock["id"])
    except Exception as exc:
        print(f"HKEX title search skipped: {type(exc).__name__}: {exc}")
        sys.exit(1)

    raw_path = RAW_DIR / f"{now.strftime('%Y%m%d-%H%M%S')}-01024-title-search.html"
    raw_path.write_text(html, encoding="utf-8")

    seen = existing_keys()
    rows: list[dict[str, str]] = []
    for item in items:
        matched = match_keywords(" ".join([item["title"], item["category"]]))
        title = item["title"]
        link = item["link"]
        key = (title, link)
        if key in seen:
            continue
        rows.append(
            {
                "date": item["date"],
                "title": title,
                "source": "HKEXnews",
                "link": link,
                "summary": f"{item['category']} | {item['release_time']} | {item['stock_code']} {item['stock_name']} | {item['file_size']}",
                "is_major_event": str(bool(matched)),
                "keywords": ";".join(matched),
                "credibility": "高",
                "fetched_at": fetched_at,
            }
        )
        seen.add(key)

    append_rows(rows)
    print(f"HKEX stockId={stock['id']} code={stock['code']} name={stock['short_name']}")
    print(f"Saved title-search HTML to {raw_path}")
    print(f"Parsed {len(items)} HKEX announcement row(s)")
    print(f"Appended {len(rows)} new HKEX row(s) to {ANNOUNCEMENTS_PATH}")


if __name__ == "__main__":
    main()
