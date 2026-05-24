from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYST_VIEWS_PATH = ROOT / "data" / "processed" / "analyst_views.csv"
FIELDNAMES = [
    "date",
    "institution",
    "analyst",
    "rating",
    "target_price_hkd",
    "previous_target_hkd",
    "action",
    "confidence",
    "source",
    "source_url",
    "source_date",
    "source_language",
    "chinese_summary",
    "key_points",
    "fetched_at",
]


CURATED_VIEWS = [
    {
        "date": "2026-03-27",
        "institution": "摩根大通",
        "analyst": "",
        "rating": "持有",
        "target_price_hkd": "48.00",
        "previous_target_hkd": "89.00",
        "action": "下调评级",
        "confidence": "高",
        "source": "Investing.com 分析师一致预期",
        "source_url": "https://www.investing.com/equities/kuaishou-technology-consensus-estimates",
        "source_date": "2026-03-27",
        "source_language": "英文",
        "chinese_summary": "摩根大通将快手评级下调至持有，目标价 48 港元，明显低于此前 89 港元，属于当前大行观点中的偏谨慎一端。",
        "key_points": "评级转弱;目标价大幅下调;需重点核查其对核心业务、AI投入和估值倍数的假设",
    },
    {
        "date": "2026-03-26",
        "institution": "花旗",
        "analyst": "",
        "rating": "买入",
        "target_price_hkd": "72.00",
        "previous_target_hkd": "95.00",
        "action": "维持评级",
        "confidence": "高",
        "source": "Investing.com 分析师一致预期",
        "source_url": "https://www.investing.com/equities/kuaishou-technology-consensus-estimates",
        "source_date": "2026-03-26",
        "source_language": "英文",
        "chinese_summary": "花旗维持买入评级，但将目标价降至 72 港元；观点仍偏正面，但已反映更保守的盈利或估值假设。",
        "key_points": "维持买入;目标价下调;仍高于当前系统基准买入区",
    },
    {
        "date": "2026-04-01",
        "institution": "美银证券",
        "analyst": "",
        "rating": "买入",
        "target_price_hkd": "77.00",
        "previous_target_hkd": "",
        "action": "维持评级",
        "confidence": "中高",
        "source": "Yahoo Finance / AASTOCKS 转引",
        "source_url": "https://hk.finance.yahoo.com/news/%E5%A4%A7%E8%A1%8C-%E7%BE%8E%E9%8A%80%E8%AD%89%E5%88%B8%E9%99%8D%E5%BF%AB%E6%89%8B-01024-hk-%E7%9B%AE%E6%A8%99%E5%83%B9%E8%87%B377%E5%85%83-025231633.html/",
        "source_date": "2026-04",
        "source_language": "中文",
        "chinese_summary": "美银证券维持买入评级，目标价 77 港元；其关注点包括 2026 年 AI 资本开支增加，以及可灵 ARR 已从 2.4 亿美元提升至约 3 亿美元。",
        "key_points": "维持买入;AI资本开支上升;可灵ARR约3亿美元;目标价接近系统基准目标",
    },
    {
        "date": "2026-02-14",
        "institution": "高盛",
        "analyst": "",
        "rating": "买入",
        "target_price_hkd": "87.00",
        "previous_target_hkd": "",
        "action": "维持评级",
        "confidence": "中高",
        "source": "证券时报转引",
        "source_url": "https://www.stcn.com/article/detail/3643088.html",
        "source_date": "2026-02",
        "source_language": "中文",
        "chinese_summary": "高盛重申买入评级，目标价 87 港元；核心判断是可灵价值被低估，预计 2026 年可灵 AI 收入约 2.8 亿美元、同比增长超过 90%。",
        "key_points": "可灵价值被低估;目标价87港元;看重AI视频商业化;偏乐观",
    },
    {
        "date": "2026-04-15",
        "institution": "中银国际",
        "analyst": "",
        "rating": "买入",
        "target_price_hkd": "60.00",
        "previous_target_hkd": "",
        "action": "下调目标价",
        "confidence": "中",
        "source": "Longbridge 转引",
        "source_url": "https://longbridge.com/zh-CN/news/280564965",
        "source_date": "2026-04",
        "source_language": "中文",
        "chinese_summary": "中银国际维持买入评级但下调目标价至 60 港元；理由包含宏观、竞争和监管压力对核心业务收入预测的影响，同时仍预期 2026 财年调整后净利润增长。",
        "key_points": "维持买入;目标价60港元;核心业务收入假设更谨慎;利润仍有增长预期",
    },
    {
        "date": "2026-03-03",
        "institution": "华安证券",
        "analyst": "",
        "rating": "买入",
        "target_price_hkd": "86.00",
        "previous_target_hkd": "",
        "action": "首次评级",
        "confidence": "中",
        "source": "东方财富 PDF 转引",
        "source_url": "https://pdf.dfcfw.com/pdf/H3_AP202603031820221870_1.pdf?1772550491000.pdf=",
        "source_date": "2026-03-03",
        "source_language": "中文",
        "chinese_summary": "华安证券首次给予买入评级，6 个月目标价 86 港元；采用 SOTP 估值，其中主业贡献约 70 港元，可灵 AI 贡献约 16 港元。",
        "key_points": "SOTP估值;主业70港元;可灵16港元;目标价86港元",
    },
]


def existing_keys() -> set[tuple[str, str, str]]:
    if not ANALYST_VIEWS_PATH.exists():
        return set()
    with ANALYST_VIEWS_PATH.open("r", encoding="utf-8", newline="") as f:
        return {(row.get("date", ""), row.get("institution", ""), row.get("source_url", "")) for row in csv.DictReader(f)}


def append_rows(rows: list[dict[str, str]]) -> None:
    ANALYST_VIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = ANALYST_VIEWS_PATH.exists()
    with ANALYST_VIEWS_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    fetched_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    seen = existing_keys()
    rows = []
    for view in CURATED_VIEWS:
        key = (view["date"], view["institution"], view["source_url"])
        if key in seen:
            continue
        row = {field: view.get(field, "") for field in FIELDNAMES}
        row["fetched_at"] = fetched_at
        rows.append(row)
    append_rows(rows)
    print(f"Appended {len(rows)} analyst view row(s) to {ANALYST_VIEWS_PATH}")


if __name__ == "__main__":
    main()
