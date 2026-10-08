"""Local-only pywebview salary dashboard bridge."""
import calendar
import copy
import threading
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
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
            payroll = copy.deepcopy(self._store.state["payroll"])
            due = date(now.year, now.month, min(payroll["payday"], calendar.monthrange(now.year, now.month)[1]))
            period_key = now.strftime("%Y-%m")
            if now.date() > due or period_key in payroll["receipts"]:
                year, month = (now.year+1, 1) if now.month == 12 else (now.year, now.month+1)
                due = date(year, month, min(payroll["payday"], calendar.monthrange(year, month)[1]))
            last_day = calendar.monthrange(now.year, now.month)[1]
            return {
                "payroll": payroll, "next_payday": due.isoformat(), "payday_days": (due-now.date()).days,
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
                payday = payload.get("payday", self._store.state["payroll"]["payday"])
                if isinstance(payday, bool) or str(payday) not in [str(n) for n in range(1, 32)]:
                    raise ValueError("Invalid payday")
                animations = payload.get("animations", self._store.state["payroll"]["animations"])
                if not isinstance(animations, bool):
                    raise ValueError("Invalid animation preference")
                salary = float(payload["monthly_net_salary"])
                begin, end = validate_schedule(payload["work_start"], payload["work_end"])
                hours = ((end.hour*60+end.minute)-(begin.hour*60+begin.minute))/60*5
                validate_income(salary, hours, payload["employment_start"])
                updated = copy.deepcopy(self._store.state)
                updated["payroll"].update(payday=int(payday), animations=animations)
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

    def confirm_receipt(self, payload):
        return self._save_receipt(payload)

    def edit_receipt(self, original_period, payload):
        if not isinstance(original_period, str):
            return {"ok": False, "error": "原到账月份无效。"}
        return self._save_receipt(payload, original_period)

    def _save_receipt(self, payload, original_period=None):
        """Validate and persist before changing memory, including month moves."""
        with self._lock:
            try:
                period = payload["period"]
                period_date = datetime.strptime(period + "-01", "%Y-%m-%d").date()
                received = date.fromisoformat(payload["received_on"])
                now = self._clock().date()
                if period_date.strftime("%Y-%m") != period or period_date > now or received > now:
                    raise ValueError("Future/invalid date")
                amount = Decimal(str(payload["amount"]))
                if not amount.is_finite() or not Decimal("0.01") <= amount <= Decimal("1000000000") or amount != amount.quantize(Decimal("0.01")):
                    raise ValueError("Invalid amount")
                receipts = self._store.state["payroll"]["receipts"]
                if original_period is not None and original_period not in receipts:
                    return {"ok": False, "error": "原到账记录不存在，请刷新后重试。"}
                if period in receipts and period != original_period:
                    return {"ok": False, "error": "这个工资月份已经记录到账，请勿重复确认。"}
                updated = copy.deepcopy(self._store.state)
                original = receipts.get(original_period, {})
                if original_period is not None:
                    del updated["payroll"]["receipts"][original_period]
                updated["payroll"]["receipts"][period] = {
                    **original,
                    **({"expected_cents": int(Decimal(str(updated["income"]["monthly_net_salary"])).quantize(Decimal("0.01")) * 100)} if original_period is None else {}),
                    "amount_cents": int(amount * 100), "received_on": received.isoformat(),
                    "recorded_at": original.get("recorded_at", self._clock().isoformat(timespec="seconds")),
                    "updated_at": self._clock().isoformat(timespec="seconds"),
                }
                self._store.save(updated)
                self._store.state = updated
                return {"ok": True, "snapshot": self.snapshot()}
            except (ValueError, TypeError, KeyError, InvalidOperation, OverflowError):
                return {"ok": False, "error": "请输入有效的工资月份、非未来到账日期和正数金额（最多两位小数）。"}
            except OSError:
                return {"ok": False, "error": "到账记录保存失败，请检查目录权限后重试。"}

    def revoke_receipt(self, period):
        with self._lock:
            if not isinstance(period, str) or period not in self._store.state["payroll"]["receipts"]:
                return {"ok": False, "error": "到账记录不存在，请刷新后重试。"}
            updated = copy.deepcopy(self._store.state)
            del updated["payroll"]["receipts"][period]
            try:
                self._store.save(updated)
            except OSError:
                return {"ok": False, "error": "撤销保存失败，记录仍然保留，请重试。"}
            self._store.state = updated
            return {"ok": True, "snapshot": self.snapshot()}

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
