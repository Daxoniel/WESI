"""Real Tk regression checks; all writable state stays in a temporary directory."""
import copy
import json
import importlib
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.environ.get("DISPLAY"), "requires an X display (e.g. Xvfb)")
class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.environment = patch.dict(os.environ, {"WESI_DATA_DIR": cls.directory.name})
        cls.environment.start()
        # Discovery may have already imported config through the core tests.
        # Reload path consumers before creating the app, so GUI checks never
        # write to the checkout's existing personal state.
        import config
        import utils
        importlib.reload(config)
        importlib.reload(utils)
        import battle_window, tarot_window, quotes_window
        for module in (battle_window, tarot_window, quotes_window):
            importlib.reload(module)
        import main
        importlib.reload(main)
        cls.main = main
        cls.app = main.WESI()
        cls.callback_errors = []
        cls.app.root.report_callback_exception = lambda *exc: cls.callback_errors.append(exc)
        cls.app.root.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.on_close()
        cls.environment.stop()
        import config
        import utils
        importlib.reload(config)
        importlib.reload(utils)
        cls.directory.cleanup()

    def setUp(self):
        self.callback_errors.clear()
        self.app.store.state = copy.deepcopy(self.main.DEFAULT_STATE)
        self.app.store.state["income"]["employment_start"] = datetime.now().strftime("%Y-%m-%d 00:00:00")
        self.app.store.save()
        from utils import save_tarot_history
        save_tarot_history([])

    def tearDown(self):
        for window in list(self.app.windows.values()):
            if window.winfo_exists():
                window.destroy()
        if self.app.pet_forage_job is not None:
            self.app.root.after_cancel(self.app.pet_forage_job)
            self.app.pet_forage_job = None
        self.app.root.update()
        self.assertFalse(self.callback_errors, self.callback_errors)

    def pump_until(self, predicate, timeout=2):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            self.app.root.update()
            if predicate():
                return
            time.sleep(0.01)
        self.fail("GUI condition timed out")

    def test_main_window_and_refresh(self):
        self.assertTrue(self.app.root.winfo_exists())
        self.app.last_income_snapshot = None
        if self.app.income_job:
            self.app.root.after_cancel(self.app.income_job)
        self.app.update_income_ui()
        self.assertIn("+€ 0.0000", self.app.tick_label.cget("text"))
        self.assertAlmostEqual(self.app.salary_panel.target, self.app.get_income_stats()["today"], places=2)

    def test_settings_validate_and_save_work_schedule(self):
        self.app.open_settings_dialog()
        dialog = next(w for w in self.app.root.winfo_children()
                      if w.winfo_class() == "Toplevel" and w.title() == "设置")
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        entries = [w for w in descendants(dialog) if w.winfo_class() == "TEntry"]
        save = next(w for w in descendants(dialog)
                    if w.winfo_class() == "TButton" and w.cget("text") == "保存")
        before = copy.deepcopy(self.app.store.state["income"])
        entries[0].delete(0, "end")
        entries[0].insert(0, "nan")
        with patch("main.Messagebox.ok") as message:
            save.invoke()
            message.assert_called_once()
        self.assertEqual(self.app.store.state["income"], before)
        for widget, value in zip(entries, ("3000", "10:30", "18:00", "2026-01-01 00:00:00")):
            widget.delete(0, "end")
            widget.insert(0, value)
        save.invoke()
        saved = json.loads(self.app.store.path.read_text())["income"]
        self.assertEqual(saved["monthly_net_salary"], 3000)
        self.assertEqual(saved["work_start"], "10:30")
        self.assertEqual(saved["work_end"], "18:00")
        self.assertEqual(saved["weekly_work_hours"], 37.5)

    def test_tarot_draw_history_and_cooldown(self):
        from tarot_window import TarotWindow
        from utils import load_tarot_history
        window = self.app._open_or_focus("tarot", TarotWindow)
        window.draw_cards()
        history = load_tarot_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(len(history[0]["cards"]), 1)
        self.assertTrue(window.result_wrap.winfo_children())
        window.draw_cards()  # same path as the Return binding
        self.assertEqual(len(load_tarot_history()), 1)
        self.assertIs(self.app.windows["tarot"], window)  # child destruction must not clear registry
        window.destroy()
        self.assertNotIn("tarot", self.app.windows)
        reopened = self.app._open_or_focus("tarot", TarotWindow)
        reopened.draw_cards()
        self.assertEqual(len(load_tarot_history()), 1)

    def test_tarot_multi_card_and_child_lifecycle(self):
        from tarot_window import TarotWindow
        from utils import load_tarot_history, save_tarot_history
        save_tarot_history([])
        window = self.app._open_or_focus("tarot", TarotWindow)
        for spread in ("three", "choice", "relationship"):
            window._cooldown_until = 0
            if window.cooldown_job:
                window.after_cancel(window.cooldown_job)
                window.cooldown_job = None
            from config import SPREAD_LABELS
            window.spread_var.set(SPREAD_LABELS[spread])
            window.draw_cards()
            self.app.root.update()
            self.assertEqual(len(load_tarot_history()[-1]["cards"]), len(self.main.SPREADS[spread]))
            self.assertIs(self.app._open_or_focus("tarot", TarotWindow), window)

    def test_battle_hit_and_kill_are_persisted(self):
        from battle_window import BattleWindow
        window = self.app._open_or_focus("battle", BattleWindow)
        window.current_hp = 1
        self.app.store.state["battle"]["stats"]["kills"] = 2
        window.attack()
        saved = json.loads(self.app.store.path.read_text())
        self.assertEqual(saved["battle"]["stats"]["total_hits"], 1)
        self.assertEqual(saved["battle"]["stats"]["kills"], 3)
        self.assertIn("会议屠戮者", [a["name"] for a in saved["achievements"]["unlocked"]])
        window.attack()
        self.assertEqual(self.app.store.state["battle"]["stats"]["total_hits"], 1)

    def test_forage_survives_window_close_and_is_not_duplicated(self):
        from main import PetWindow
        window = self.app._open_or_focus("pet", PetWindow)
        window.start_forage()
        due = self.app.store.state["pet"]["next_forage_at"]
        self.assertTrue(due)
        window.destroy()
        reopened = self.app._open_or_focus("pet", PetWindow)
        reopened.start_forage()
        self.assertEqual(self.app.store.state["pet"]["next_forage_at"], due)
        self.app.finish_pet_forage()
        self.app.finish_pet_forage()
        saved = json.loads(self.app.store.path.read_text())
        self.assertEqual(saved["pet"]["forage_count"], 1)
        self.assertEqual(len(saved["pet"]["history"]), 1)
        self.assertIsNone(saved["pet"]["next_forage_at"])

    def test_resume_overdue_forage(self):
        self.app.store.state["pet"]["next_forage_at"] = "2020-01-01 00:00:00"
        self.app.resume_pet_forage()
        self.pump_until(lambda: self.app.store.state["pet"]["forage_count"] == 1)

    def test_quote_fetch_keeps_ui_responsive_and_falls_back(self):
        from quotes_window import QuoteWindow
        gate = threading.Event()
        def slow_api():
            gate.wait(2)
            return None
        with patch("quotes_window.get_jinrishici_quote", slow_api):
            window = self.app._open_or_focus("quotes", QuoteWindow)
            self.pump_until(lambda: window._loading)
            ticks = []
            self.app.root.after(20, lambda: ticks.append(True))
            self.pump_until(lambda: ticks)
            self.assertTrue(window._loading)
            gate.set()
            self.pump_until(lambda: not window._loading)
        self.assertTrue(window.current_quote["text"])
        self.assertIn("本地内容", window.source_label.cget("text"))
        window.favorite_current()
        window.favorite_current()
        self.assertEqual(len(self.app.store.state["quotes"]["favorites"]), 1)
        window.open_favorites()
        favorites = self.app.windows["favorites"]
        favorites.listbox.selection_set("0")
        favorites.remove_selected()
        self.assertEqual(self.app.store.state["quotes"]["favorites"], [])

    def test_invalid_theme_does_not_change_saved_settings(self):
        from main import ThemeDialog
        before = copy.deepcopy(self.app.store.state["theme"])
        dialog = ThemeDialog(self.app)
        try:
            dialog.vars["money"].set("not-a-color")
            with patch("main.Messagebox.ok") as message:
                dialog.apply_theme()
                message.assert_called_once()
            self.assertEqual(self.app.store.state["theme"], before)
        finally:
            dialog.destroy()

    def test_salary_collection_is_persisted_without_changing_wages(self):
        panel = self.app.salary_panel
        income = copy.deepcopy(self.app.store.state["income"])
        stats = {"today": 12.345, "rate": .01}
        with patch.object(self.app, "get_income_stats", return_value=stats):
            panel.collect()
            panel.collect()
        saved = json.loads(self.app.store.path.read_text())
        self.assertEqual(saved["salary_display"]["collected_today"], 12.34)
        self.assertEqual(saved["income"], income)
        self.assertEqual(panel.target, 12.345)
        self.assertEqual(str(panel.collect_button.cget("state")), "disabled")
        self.assertTrue(panel.canvas.find_all())

    def test_salary_collection_resets_on_new_day(self):
        panel = self.app.salary_panel
        settings = self.app.store.state["salary_display"]
        settings.update(collection_date="2026-10-06", collected_today=20)
        panel.update_stats({"today": 2, "rate": .01}, datetime(2026, 10, 7, 12))
        self.assertEqual(settings["collected_today"], 0)
        self.assertEqual(settings["collection_date"], "2026-10-07")
        self.assertIn("€2.00", panel.collect_button.cget("text"))

    def test_salary_quiet_mode_stops_effects_and_saves(self):
        panel = self.app.salary_panel
        panel.update_stats({"today": 4, "rate": .01})
        panel._burst()
        panel.quiet_var.set(True)
        panel.toggle_quiet()
        self.assertEqual(panel.particles, [])
        self.assertEqual(panel.displayed_amount(), 4)
        self.assertTrue(json.loads(self.app.store.path.read_text())["salary_display"]["quiet"])
        panel.quiet_var.set(False)
        panel.toggle_quiet()

    def test_salary_goal_validation_and_save(self):
        panel = self.app.salary_panel
        panel.update_stats({"today": 4, "rate": .01})
        panel.open_goal()
        dialog = next(w for w in self.app.root.winfo_children()
                      if w.winfo_class() == "Toplevel" and w.title() == "今天的小目标")
        frame = dialog.winfo_children()[0]
        entry = next(w for w in frame.winfo_children() if w.winfo_class() == "TEntry")
        button = next(w for w in frame.winfo_children() if w.winfo_class() == "TButton")
        entry.delete(0, "end")
        entry.insert(0, "nan")
        with patch("salary_panel.Messagebox.ok") as message:
            button.invoke()
            message.assert_called_once()
        self.assertEqual(panel.settings["goal_amount"], 10)
        panel.settings["goal_amount"] = 2
        panel.update_stats({"today": 4, "rate": .01})
        self.assertIn("达成", panel.feedback.cget("text"))
        entry.delete(0, "end")
        entry.insert(0, "25")
        with patch.object(self.app, "get_income_stats", return_value={"today": 4, "rate": .01}):
            button.invoke()
        self.assertEqual(json.loads(self.app.store.path.read_text())["salary_display"]["goal_amount"], 25)
        self.assertNotIn("达成", panel.feedback.cget("text"))


if __name__ == "__main__":
    unittest.main()
