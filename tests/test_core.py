import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from income import calculate_income, count_workdays, validate_income, validate_schedule
from storage import DataStore, read_json, write_json
from utils import load_tarot_cards
from config import TAROT_DIR
from salary_panel import available_coins, work_status


class IncomeTests(unittest.TestCase):
    def setUp(self):
        self.income = {"monthly_net_salary": 2600 * 5 / 6, "weekly_work_hours": 40,
                       "employment_start": "2026-01-05 09:00:00",
                       "work_start": "09:00", "work_end": "17:00"}

    def stats(self, time):
        return calculate_income(self.income, datetime.fromisoformat(time))

    def test_only_working_hours_accrue(self):
        for time, today, rate in (("08:00", 0, 0), ("09:00", 0, 100/28800),
                                  ("13:00", 50, 100/28800), ("17:00", 100, 0), ("23:59", 100, 0)):
            with self.subTest(time=time):
                result = self.stats(f"2026-01-05 {time}:00")
                self.assertAlmostEqual(result["today"], today)
                self.assertAlmostEqual(result["rate"], rate)

    def test_display_rate_matches_increment(self):
        a = self.stats("2026-01-05 10:00:00")
        b = self.stats("2026-01-05 10:00:01")
        self.assertAlmostEqual(b["today"]-a["today"], a["rate"])

    def test_weekend_is_paused(self):
        result = self.stats("2026-01-10 13:00:00")
        self.assertEqual(result["today"], 0)
        self.assertEqual(result["rate"], 0)
        self.assertEqual(result["daily_target"], 0)
        self.assertAlmostEqual(result["joined"], 500)

    def test_no_income_before_employment(self):
        self.income["employment_start"] = "2026-01-07 13:00:00"
        before = self.stats("2026-01-07 12:00:00")
        self.assertEqual([before[key] for key in ("today", "month", "year", "joined")], [0]*4)
        after = self.stats("2026-01-07 17:00:00")
        self.assertEqual([after[key] for key in ("today", "month", "year", "joined")], [50]*4)

    def test_month_boundary(self):
        self.income["employment_start"] = "2026-01-30 13:00:00"
        result = self.stats("2026-02-02 13:00:00")
        self.assertEqual(result["month"], 50)
        self.assertEqual(result["joined"], 100)

    def test_year_boundary(self):
        self.income["employment_start"] = "2025-12-31 13:00:00"
        result = self.stats("2026-01-01 13:00:00")
        self.assertEqual(result["year"], 50)
        self.assertEqual(result["joined"], 100)

    def test_custom_schedule(self):
        self.income.update(work_start="10:30", work_end="18:30")
        self.assertEqual(self.stats("2026-01-05 10:00:00")["today"], 0)
        self.assertEqual(self.stats("2026-01-05 14:30:00")["today"], 50)

    def test_invalid_settings(self):
        for salary in (float("nan"), float("inf"), 0, -10):
            with self.subTest(salary=salary), self.assertRaises(ValueError):
                validate_income(salary, 40, "2026-01-01 00:00:00")
        for schedule in (("17:00", "09:00"), ("09:00", "09:00"), ("25:00", "17:00")):
            with self.subTest(schedule=schedule), self.assertRaises(ValueError):
                validate_schedule(*schedule)

    def test_workday_count(self):
        from datetime import timedelta
        start = datetime(2024, 1, 1).date()
        for offset in range(7):
            begin = start + timedelta(days=offset)
            for days in (0, 1, 6, 7, 31, 366, 5000):
                expected = sum((begin + timedelta(days=i)).weekday() < 5 for i in range(days))
                self.assertEqual(count_workdays(begin, begin + timedelta(days=days)), expected)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/"nested"/"state.json"

    def test_round_trip_preserves_extensions_and_defaults(self):
        write_json(self.path, {"income": {"monthly_net_salary": 3200}, "extension": {"items": [1, 2]}})
        store = DataStore(self.path)
        self.assertEqual(store.state["income"]["monthly_net_salary"], 3200)
        self.assertEqual(store.state["income"]["work_start"], "09:00")
        store.save()
        self.assertEqual(DataStore(self.path).state["extension"], {"items": [1, 2]})

    def test_corruption_is_backed_up(self):
        self.path.parent.mkdir()
        self.path.write_text('{"income": broken', encoding="utf-8")
        original = self.path.read_bytes()
        store = DataStore(self.path)
        store.save()
        backups = list(self.path.parent.glob("*.invalid-*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(json.loads(self.path.read_text())["income"]["monthly_net_salary"], 2600)

    def test_failed_replace_does_not_truncate_original(self):
        write_json(self.path, {"value": 1})
        with patch("storage.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                write_json(self.path, {"value": 2})
        self.assertEqual(read_json(self.path, {}), {"value": 1})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_unserializable_data_does_not_destroy_original(self):
        write_json(self.path, {"value": 1})
        for value in (float("nan"), object()):
            with self.assertRaises((TypeError, ValueError)):
                write_json(self.path, {"value": value})
        self.assertEqual(read_json(self.path, {}), {"value": 1})

    def test_permission_failure_is_not_reset(self):
        write_json(self.path, {"value": 1})
        with patch("pathlib.Path.open", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                read_json(self.path, {})

    def test_defaults_are_not_shared(self):
        first = DataStore(self.path)
        first.state["pet"]["inventory"].append({"name": "test"})
        other = DataStore(self.path.with_name("other.json"))
        self.assertEqual(other.state["pet"]["inventory"], [])

    def test_invalid_field_shapes_are_preserved_before_repair(self):
        write_json(self.path, {"quotes": {"favorites": {}}, "income": {"employment_start": "broken"}})
        original = self.path.read_bytes()
        store = DataStore(self.path)
        self.assertEqual(store.state["quotes"]["favorites"], [])
        self.assertEqual(store.state["income"]["employment_start"], "2026-04-01 00:00:00")
        backup = next(self.path.parent.glob("*.invalid-*.bak"))
        self.assertEqual(backup.read_bytes(), original)


class TarotDataTests(unittest.TestCase):
    def test_bundled_deck_and_assets_are_complete(self):
        cards = load_tarot_cards()
        self.assertEqual(len(cards), 78)
        self.assertEqual(len({card["name_en"] for card in cards}), 78)
        self.assertEqual(len({card["img"] for card in cards}), 78)
        for card in cards:
            with self.subTest(card=card["name_en"]):
                self.assertTrue(card["name_zh"])
                self.assertTrue((TAROT_DIR/card["img"]).is_file())


class SalaryDisplayTests(unittest.TestCase):
    def test_only_completed_cents_can_be_collected(self):
        self.assertEqual(available_coins(1.239, 1), .23)
        self.assertEqual(available_coins(.009, 0), 0)
        self.assertEqual(available_coins(1.24, 1.24), 0)

    def test_salary_changes_never_create_negative_pending(self):
        self.assertEqual(available_coins(3, 8), 0)
        self.assertEqual(available_coins(-1, 8), 0)

    def test_work_states_and_countdowns(self):
        income = {"employment_start": "2026-01-01 00:00:00", "work_start": "09:00", "work_end": "17:00"}
        self.assertEqual(work_status(income, datetime(2026, 10, 7, 8))[0], "等待上班")
        self.assertEqual(work_status(income, datetime(2026, 10, 7, 12)), ("正在回收", "距离下班 05:00:00"))
        self.assertEqual(work_status(income, datetime(2026, 10, 7, 17))[0], "今日收工")
        self.assertEqual(work_status(income, datetime(2026, 10, 10, 12))[0], "休息日")


if __name__ == "__main__":
    unittest.main()
