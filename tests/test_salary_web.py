from concurrent.futures import ThreadPoolExecutor
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

    def test_payday_short_month_leap_year_and_year_rollover(self):
        self.api._store.state["payroll"]["payday"] = 31
        for now, expected in [(datetime(2028, 2, 2), "2028-02-29"), (datetime(2027, 2, 2), "2027-02-28"), (datetime(2026, 12, 31), "2026-12-31")]:
            self.now = now
            self.assertEqual(self.api.snapshot()["next_payday"], expected)
        self.api._store.state["payroll"]["receipts"]["2026-12"] = {"amount_cents": 100, "received_on": "2026-12-31"}
        self.assertEqual(self.api.snapshot()["next_payday"], "2027-01-31")

    def test_receipt_persists_cents_and_rejects_duplicate_and_invalid(self):
        payload = {"period": "2026-10", "received_on": "2026-10-07", "amount": "2600.12"}
        self.assertTrue(self.api.confirm_receipt(payload)["ok"])
        self.assertEqual(DataStore(self.path).state["payroll"]["receipts"]["2026-10"]["amount_cents"], 260012)
        self.assertFalse(self.api.confirm_receipt(payload)["ok"])
        before = copy.deepcopy(self.api._store.state)
        for changes in ({"period": "2026-11"}, {"received_on": "2026-10-08"}, {"amount": "nan"}, {"amount": "1.001"}, {"period": "bad"}):
            self.assertFalse(self.api.confirm_receipt(payload | changes)["ok"])
            self.assertEqual(self.api._store.state, before)

    def test_concurrent_receipt_requests_commit_once(self):
        payload = {"period": "2026-10", "received_on": "2026-10-07", "amount": "2600"}
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(self.api.confirm_receipt, [payload]*4))
        self.assertEqual(sum(result["ok"] for result in results), 1)
        self.assertEqual(len(DataStore(self.path).state["payroll"]["receipts"]), 1)

    def test_receipt_disk_failure_has_no_memory_effect(self):
        before = copy.deepcopy(self.api._store.state)
        with patch.object(self.api._store, "save", side_effect=OSError("disk")):
            self.assertFalse(self.api.confirm_receipt({"period": "2026-10", "received_on": "2026-10-07", "amount": "2600"})["ok"])
        self.assertEqual(self.api._store.state, before)

    def test_invalid_payday_and_valid_preference_persist(self):
        payload = {"monthly_net_salary": "3000", "work_start": "09:00", "work_end": "17:00", "employment_start": "2026-01-01 00:00:00"}
        for day in (0, 32, True, "1.5"):
            self.assertFalse(self.api.save_settings(payload | {"payday": day})["ok"])
        self.assertTrue(self.api.save_settings(payload | {"payday": "31", "animations": False})["ok"])
        self.assertEqual(DataStore(self.path).state["payroll"]["payday"], 31)
        self.assertFalse(DataStore(self.path).state["payroll"]["animations"])

    def test_edit_move_keeps_baseline_and_revoke_persists(self):
        payload = {"period": "2026-10", "received_on": "2026-10-07", "amount": "2600"}
        self.assertTrue(self.api.confirm_receipt(payload)["ok"])
        self.api._store.state["income"]["monthly_net_salary"] = 3000
        self.assertTrue(self.api.edit_receipt("2026-10", payload | {"period": "2026-09", "amount": "2700.12"})["ok"])
        records = DataStore(self.path).state["payroll"]["receipts"]
        self.assertNotIn("2026-10", records)
        self.assertEqual(records["2026-09"]["amount_cents"], 270012)
        self.assertEqual(records["2026-09"]["expected_cents"], 260000)
        self.assertTrue(self.api.revoke_receipt("2026-09")["ok"])
        self.assertFalse(DataStore(self.path).state["payroll"]["receipts"])
        self.assertFalse(self.api.revoke_receipt("2026-09")["ok"])

    def test_edit_collision_and_failures_keep_original(self):
        payload = {"period": "2026-10", "received_on": "2026-10-07", "amount": "2600"}
        self.api.confirm_receipt(payload)
        self.api.confirm_receipt(payload | {"period": "2026-09"})
        before = copy.deepcopy(self.api._store.state)
        for original, change in [("2026-10", {"period": "2026-09"}), ("2026-08", {}), ("2026-10", {"amount": "nan"})]:
            self.assertFalse(self.api.edit_receipt(original, payload | change)["ok"])
            self.assertEqual(self.api._store.state, before)
        with patch.object(self.api._store, "save", side_effect=OSError("disk")):
            self.assertFalse(self.api.edit_receipt("2026-10", payload | {"amount": "2700"})["ok"])
            self.assertFalse(self.api.revoke_receipt("2026-10")["ok"])
        self.assertEqual(self.api._store.state, before)
        self.assertEqual(DataStore(self.path).state, before)

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
