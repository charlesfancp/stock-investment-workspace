import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_event_calendar.py"


def load_event_module():
    spec = importlib.util.spec_from_file_location("build_event_calendar", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EventCalendarTests(unittest.TestCase):
    def test_missing_source_is_not_reportable(self):
        module = load_event_module()
        row = module.normalize_event(
            {
                "ticker": "NVDA",
                "event_type": "earnings",
                "event_date": "2026-05-20",
                "title": "Earnings",
                "source": None,
                "source_tier": None,
                "status": "needs_source",
            },
            datetime(2026, 5, 14, tzinfo=timezone.utc),
            "2026-05-14T00:00:00Z",
        )
        self.assertFalse(row["include_in_report"])

    def test_tier_1_future_event_is_reportable(self):
        module = load_event_module()
        row = module.normalize_event(
            {
                "ticker": "NVDA",
                "event_type": "earnings",
                "event_date": "2026-05-20",
                "title": "Earnings",
                "source": "Company IR",
                "source_url": "https://example.com",
                "source_tier": "tier_1",
                "status": "confirmed",
                "review_file": "reviews/event_reviews/test.md",
            },
            datetime(2026, 5, 14, tzinfo=timezone.utc),
            "2026-05-14T00:00:00Z",
        )
        self.assertTrue(row["include_in_report"])
        self.assertEqual(row["days_until"], 6)
        self.assertEqual(row["source_url"], "https://example.com")
        self.assertEqual(row["review_file"], "reviews/event_reviews/test.md")

    def test_confirmed_event_outside_window_keeps_confirmed_status(self):
        module = load_event_module()
        row = module.normalize_event(
            {
                "ticker": "AVGO",
                "event_type": "earnings",
                "event_date": "2026-06-03",
                "title": "Earnings",
                "source": "Company IR",
                "source_url": "https://example.com",
                "source_tier": "tier_1",
                "status": "confirmed",
            },
            datetime(2026, 5, 16, tzinfo=timezone.utc),
            "2026-05-16T00:00:00Z",
        )
        self.assertFalse(row["include_in_report"])
        self.assertEqual(row["status"], "confirmed")

    def test_latest_event_calendar_contains_all_seed_events_when_present(self):
        latest_path = ROOT / "data" / "processed" / "event_calendar_latest.csv"
        if not latest_path.exists():
            self.skipTest("event_calendar_latest.csv has not been generated yet")
        rows = latest_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(rows), 11)


if __name__ == "__main__":
    unittest.main()
