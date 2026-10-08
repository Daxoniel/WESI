import copy
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from salary_web import SalaryAPI
from storage import DataStore


class SalaryAPITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/"state.json"
        self.now = datetime(2026, 10, 7, 13)
        self.api = SalaryAPI(self.path, clock=lambda: self.now)
        self.api._store.state["income"].update(employment_start="2026-10-07 09:00:00")

    def test_snapshot_uses_existing_engine_and_does_not_collect_coins(self):
        from income import calculate_income
        before = copy.deepcopy(self.api._store.state)
        data = self.api.snapshot()
        self.assertEqual(data["stats"], calculate_income(before["income"], self.now))
        self.assertEqual(data["status"], "工作中")
        self.assertEqual(data["seconds_left"], 4*3600)
        self.assertEqual(data["day_progress"], .5)
        self.assertEqual(data["month_label"], "2026.10.01 — 10.31")
        self.assertEqual(self.api._store.state, before)

    def test_rest_and_before_employment_states(self):
        self.now = datetime(2026, 10, 10, 13)
        self.assertEqual(self.api.snapshot()["status"], "休息日")
        self.assertIsNone(self.api.snapshot()["seconds_left"])
        self.now = datetime(2026, 10, 7, 8)
        self.assertEqual(self.api.snapshot()["status"], "等待入职")
        self.now = datetime(2026, 10, 8, 8)
        self.assertEqual(self.api.snapshot()["status"], "等待上班")
        self.now = datetime(2026, 10, 8, 18)
        self.assertEqual(self.api.snapshot()["status"], "已下班")

    def test_settings_save_and_legacy_fields_survive(self):
        self.api._store.state["pet"]["name"] = "Keep me"
        result = self.api.save_settings({"monthly_net_salary": "3000", "work_start": "10:00", "work_end": "18:00", "employment_start": "2026-01-01 00:00:00"})
        self.assertTrue(result["ok"])
        saved = DataStore(self.path).state
        self.assertEqual(saved["income"]["monthly_net_salary"], 3000)
        self.assertEqual(saved["pet"]["name"], "Keep me")

    def test_invalid_settings_do_not_mutate_state(self):
        before = copy.deepcopy(self.api._store.state)
        valid = {"monthly_net_salary": "3000", "work_start": "10:00", "work_end": "18:00", "employment_start": "2026-01-01 00:00:00"}
        for patch_value in ({"monthly_net_salary": "nan"}, {"work_end": "08:00"}, {"employment_start": "bad"}):
            self.assertFalse(self.api.save_settings(valid | patch_value)["ok"])
            self.assertEqual(self.api._store.state, before)

    def test_save_failure_preserves_memory(self):
        before = copy.deepcopy(self.api._store.state)
        with patch.object(self.api._store, "save", side_effect=OSError("read only")):
            result = self.api.save_settings({"monthly_net_salary": 3000, "work_start": "09:00", "work_end": "17:00", "employment_start": "2026-01-01 00:00:00"})
        self.assertFalse(result["ok"])
        self.assertEqual(self.api._store.state, before)

    def test_native_controls_and_exclusive_classic_handoff(self):
        window = self.api._window = Mock()
        self.assertTrue(self.api.set_pin(True))
        self.assertTrue(window.on_top)
        self.api.set_compact(True)
        window.resize.assert_called_with(420, 440)
        self.api.open_classic()
        self.assertTrue(self.api._classic)
        window.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
