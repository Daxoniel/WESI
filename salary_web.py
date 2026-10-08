"""Local-only pywebview salary dashboard bridge."""
import calendar
import copy
import threading
from datetime import datetime
from pathlib import Path

from config import DATA_FILE
from income import calculate_income, validate_income, validate_schedule
from storage import DataStore


class SalaryAPI:
    def __init__(self, path=DATA_FILE, clock=datetime.now):
        self._store = DataStore(path)
        self._clock = clock
        self._lock = threading.RLock()
        self._window = None
        self._classic = False

    def snapshot(self):
        with self._lock:
            income = copy.deepcopy(self._store.state["income"])
            now = self._clock()
            stats = calculate_income(income, now)
            start, end = validate_schedule(income["work_start"], income["work_end"])
            employed = now >= datetime.strptime(income["employment_start"], "%Y-%m-%d %H:%M:%S")
            active = stats["rate"] > 0
            if not employed:
                status, deadline, label = "等待入职", datetime.strptime(income["employment_start"], "%Y-%m-%d %H:%M:%S"), "距离入职"
            elif now.weekday() >= 5:
                status, deadline, label = "休息日", None, "享受你的时间"
            elif now.time() < start:
                status, deadline, label = "等待上班", datetime.combine(now.date(), start), "距离上班"
            elif active:
                status, deadline, label = "工作中", datetime.combine(now.date(), end), "距离下班"
            else:
                status, deadline, label = "已下班", None, "今天辛苦了"
            last_day = calendar.monthrange(now.year, now.month)[1]
            return {
                "income": income, "stats": stats, "active": active, "status": status,
                "seconds_left": max(0, int((deadline-now).total_seconds())) if deadline else None,
                "countdown_label": label, "date": now.strftime("%Y-%m-%d"),
                "month_label": f"{now.year}.{now.month:02d}.01 — {now.month:02d}.{last_day:02d}",
                "day_progress": min(1, stats["today"]/stats["daily_target"]) if stats["daily_target"] else 0,
                "month_progress": min(1, stats["month"]/income["monthly_net_salary"]),
                "weekday": now.weekday(),
            }

    def save_settings(self, payload):
        with self._lock:
            try:
                if not isinstance(payload, dict):
                    raise ValueError("设置格式无效。")
                salary = float(payload["monthly_net_salary"])
                begin, end = validate_schedule(payload["work_start"], payload["work_end"])
                hours = ((end.hour*60+end.minute)-(begin.hour*60+begin.minute))/60*5
                validate_income(salary, hours, payload["employment_start"])
                updated = copy.deepcopy(self._store.state)
                updated["income"].update(
                    monthly_net_salary=salary, weekly_work_hours=hours,
                    work_start=begin.strftime("%H:%M"), work_end=end.strftime("%H:%M"),
                    employment_start=payload["employment_start"],
                )
                # Commit memory only after durable saving succeeds.
                self._store.save(updated)
                self._store.state = updated
                return {"ok": True, "snapshot": self.snapshot()}
            except (ValueError, TypeError, KeyError, OverflowError):
                return {"ok": False, "error": "请输入有效的正数月薪、入职日期和当日上下班时间。"}
            except OSError:
                return {"ok": False, "error": "无法保存设置，请检查存档目录的写入权限。"}

    def set_pin(self, enabled):
        if not isinstance(enabled, bool):
            return False
        if self._window is not None:
            self._window.on_top = enabled
        return enabled

    def set_compact(self, enabled):
        if not isinstance(enabled, bool):
            return False
        if self._window is not None:
            self._window.resize(420 if enabled else 1040, 440 if enabled else 760)
        return enabled

    def minimize(self):
        if self._window is not None:
            self._window.minimize()

    def open_classic(self):
        # Close the web app before opening Tk: only one store writer at a time.
        self._classic = True
        if self._window is not None:
            self._window.destroy()


def launch():
    import webview
    api = SalaryAPI()
    api._window = webview.create_window(
        "WESI · 工资监控", str(Path(__file__).resolve().parent / "ui/index.html"),
        js_api=api, width=1040, height=760, min_size=(390, 410), background_color="#0c1015",
    )
    webview.start(http_server=True)
    return api._classic
