
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import dialog
from typing import Any, Dict, List, Tuple
from utils import *
from tarot_window import TarotWindow
from quotes_window import QuoteWindow, FavoritesWindow
from battle_window import BattleWindow


try:
    from PIL import Image, ImageOps, ImageTk, ImageDraw
except Exception:
    Image = None
    ImageOps = None
    ImageTk = None
    ImageDraw = None

try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    from ttkbootstrap.dialogs import Messagebox
    from ttkbootstrap.scrolled import ScrolledText
except Exception as exc:
    raise SystemExit(
        "This program requires ttkbootstrap.\n"
        "Install with: pip install ttkbootstrap pillow"
    ) from exc

from config import (
    APP_TITLE,
    PROJECT_DIR,
    DATA_DIR,
    ASSETS_DIR,
    PET_DIR,
    AVATAR_DIR,
    TAROT_DIR,
    D2DATA_DIR,
    DATA_FILE,
    QUOTES_FILE,
    TAROT_JSON_FILE,
    PET_ITEMS_FILE,
    PET_EVENTS_FILE,
    THEME_PRESETS,
    CUSTOM_COLOR_KEYS,
    QUOTE_LIBRARY,
    PET_ITEMS,
    PET_EVENTS,
    RARITY_WEIGHTS,
    SPREADS,
    DEFAULT_STATE,
)

class DataStore:
    def __init__(self, path: Path):
        self.path = path
        self.state = self.load()

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            self.save(DEFAULT_STATE)
            return json.loads(json.dumps(DEFAULT_STATE, ensure_ascii=False))
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            return deep_merge(json.loads(json.dumps(DEFAULT_STATE, ensure_ascii=False)), loaded)
        except Exception:
            self.save(DEFAULT_STATE)
            return json.loads(json.dumps(DEFAULT_STATE, ensure_ascii=False))

    def save(self, data: Optional[Dict[str, Any]] = None) -> None:
        target = data if data is not None else self.state

        def clean(obj):
            if obj is ...:
                return None
            if isinstance(obj, list):
                return [clean(x) for x in obj if x is not ...]
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items() if v is not ...}
            return obj

        target = clean(target)

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(target, f, ensure_ascii=False, indent=2)


# =========================
# Windows
# =========================
class ThemeDialog(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("主题设置")
        self.geometry("420x520")
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()
        self.vars: Dict[str, tb.StringVar] = {}
        self.build_ui()

    def build_ui(self):
        main = tb.Frame(self, padding=16)
        main.pack(fill=BOTH, expand=True)

        tb.Label(main, text="ttkbootstrap 预设主题", font=("Segoe UI", 12, "bold")).pack(anchor=W)
        self.theme_var = tb.StringVar(value=self.app.store.state["theme"]["name"])
        tb.Combobox(main, textvariable=self.theme_var, values=THEME_PRESETS, state="readonly").pack(fill=X, pady=(8, 12))

        tb.Label(main, text="自定义颜色", font=("Segoe UI", 12, "bold")).pack(anchor=W, pady=(8, 6))
        for key in CUSTOM_COLOR_KEYS:
            row = tb.Frame(main)
            row.pack(fill=X, pady=4)
            tb.Label(row, text=key, width=10).pack(side=LEFT)
            var = tb.StringVar(value=self.app.store.state["theme"]["colors"].get(key, ""))
            self.vars[key] = var
            tb.Entry(row, textvariable=var).pack(side=LEFT, fill=X, expand=True)

        button_row = tb.Frame(main)
        button_row.pack(fill=X, pady=(16, 0))
        tb.Button(button_row, text="应用", bootstyle="primary", command=self.apply_theme).pack(side=LEFT, padx=(0, 8))
        tb.Button(button_row, text="恢复默认", bootstyle="secondary", command=self.reset_theme).pack(side=LEFT, padx=(0, 8))
        tb.Button(button_row, text="关闭", bootstyle="outline-secondary", command=self.destroy).pack(side=LEFT)

    def apply_theme(self):
        self.app.store.state["theme"]["name"] = self.theme_var.get()
        for key, var in self.vars.items():
            self.app.store.state["theme"]["colors"][key] = var.get().strip() or DEFAULT_STATE["theme"]["colors"][key]
        self.app.store.save()
        self.app.apply_theme(refresh_widgets=True)

    def reset_theme(self):
        self.app.store.state["theme"] = json.loads(json.dumps(DEFAULT_STATE["theme"], ensure_ascii=False))
        self.app.store.save()
        self.app.apply_theme(refresh_widgets=True)
        self.destroy()



class PetWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("虚拟宠物")
        self.geometry("760x560")
        self.pet_img = None
        self.forage_running = False
        self.build_ui()
        self.refresh()

    def build_ui(self):
        main = tb.Frame(self, padding=12)
        main.pack(fill=BOTH, expand=True)

        top = tb.Frame(main)
        top.pack(fill=X)
        left = tb.Frame(top)
        left.pack(side=LEFT, fill=Y)
        self.pet_view = tb.Label(left, text="[宠物形象]", width=24)
        self.pet_view.pack(pady=(0, 8))
        self.pet_name_var = tb.StringVar(value=self.app.store.state["pet"]["name"])
        tb.Entry(left, textvariable=self.pet_name_var).pack(fill=X, pady=(0, 8))
        action_row = tb.Frame(left)
        action_row.pack(fill=X)
        tb.Button(action_row, text="保存名称", command=self.save_name).pack(side=LEFT, padx=(0, 6))
        tb.Button(action_row, text="导入形象", command=self.import_pet_image).pack(side=LEFT)

        right = tb.Frame(top)
        right.pack(side=LEFT, fill=BOTH, expand=True, padx=(14, 0))
        self.status_label = tb.Label(right, text="")
        self.status_label.pack(anchor=W)
        self.loot_label = tb.Label(right, text="")
        self.loot_label.pack(anchor=W, pady=(8, 12))
        control_row = tb.Frame(right)
        control_row.pack(fill=X, pady=(0, 8))
        tb.Button(control_row, text="去摸鱼", bootstyle="primary", command=self.start_forage).pack(side=LEFT, padx=(0, 8))
        tb.Button(control_row, text="导入D2词库", command=self.import_d2_words).pack(side=LEFT, padx=(0, 8))
        tb.Button(control_row, text="图鉴", command=self.open_codex).pack(side=LEFT, padx=(0, 8))
        tb.Button(control_row, text="历史", command=self.open_history).pack(side=LEFT, padx=(0, 8))
        tb.Button(control_row, text="生成宠物（预留）", bootstyle="secondary", command=self.generate_pet_stub).pack(side=LEFT)

        self.history_box = ScrolledText(main, height=14)
        self.history_box.pack(fill=BOTH, expand=True, pady=(12, 0))
        self.history_box.text.configure(state="disabled")

    def refresh(self):
        pet = self.app.store.state["pet"]
        self.status_label.configure(text=f"宠物：{pet['name']}    亲密度：{pet['affinity']}    摸鱼次数：{pet['forage_count']}")
        self.loot_label.configure(text=f"库存物品数：{len(pet['inventory'])}    相遇次数：{len(pet['encounters'])}")
        if pet.get("image_path") and Image:
            self.pet_img = make_rounded_image(pet["image_path"], (180, 180), radius=28)
            if self.pet_img:
                self.pet_view.configure(image=self.pet_img, text="")
        else:
            self.pet_view.configure(text="[宠物形象]", image="")
        self._refresh_history_box()

    def _refresh_history_box(self):
        pet = self.app.store.state["pet"]
        lines = []
        for item in reversed(pet["history"][-20:]):
            if item["kind"] == "loot":
                lines.append(f"[{item['time']}] 捡到 {item['name']} ({item['rarity']})")
            else:
                lines.append(f"[{item['time']}] 相遇：{item['story']}")
        self.history_box.text.configure(state="normal")
        self.history_box.text.delete("1.0", END)
        self.history_box.text.insert(END, "\n".join(lines) if lines else "宠物还没有开始摸鱼。")
        self.history_box.text.configure(state="disabled")

    def save_name(self):
        self.app.store.state["pet"]["name"] = self.pet_name_var.get().strip() or "Mochi"
        self.app.store.save()
        self.refresh()

    def import_pet_image(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")])
        if not path:
            return
        saved = safe_copy_image(path, PET_DIR)
        self.app.store.state["pet"]["image_path"] = saved
        self.app.store.save()
        self.refresh()

    def import_d2_words(self):
        self.app.d2_item_names = import_d2_names_from_local_json()
        self.app.flash_status(f"已导入 {len(self.app.d2_item_names)} 个本地 D2 名称。")
        self.refresh()

    def generate_pet_stub(self):
        Messagebox.ok(
            "这里预留了图像生成按钮。\n\n后续可接入 OpenAI 图像生成 API：\n输入描述词 → 调用 API → 保存本地图片 → 设为宠物形象。",
            "生成宠物（预留）",
        )

    def start_forage(self):
        if self.forage_running:
            return
        self.forage_running = True
        self.status_label.configure(text="宠物正在摸鱼中……")
        delay = random.randint(6, 14)
        self.after(delay * 1000, self.finish_forage)

    def finish_forage(self):
        self.forage_running = False
        pet = self.app.store.state["pet"]
        pet["forage_count"] += 1
        pet["affinity"] += 1
        if random.random() < 0.7:
            item = choose_weighted(self.app.pet_items)
            entry = {
                "time": format_now(),
                "kind": "loot",
                "name": item["name"],
                "rarity": item["rarity"],
                "desc": item["desc"],
            }
            pet["history"].append(entry)
            pet["inventory"].append(entry)
            self.app.flash_status(f"宠物捡到了：{item['name']}")
        else:
            story = random.choice(self.app.pet_events)
            entry = {"time": format_now(), "kind": "encounter", "story": story}
            pet["history"].append(entry)
            pet["encounters"].append(entry)
            self.app.flash_status("宠物带回了一段相遇。")
        self.app.increment_achievement_check()
        self.app.store.save()
        self.refresh()

    def open_codex(self):
        PetCodexWindow(self.app)

    def open_history(self):
        PetHistoryWindow(self.app)


class PetCodexWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("宠物图鉴")
        self.geometry("680x480")
        self.build_ui()
        self.refresh()

    def build_ui(self):
        main = tb.Frame(self, padding=12)
        main.pack(fill=BOTH, expand=True)
        self.tree = tb.Treeview(main, columns=("name", "rarity", "count", "desc"), show="headings")
        self.tree.heading("name", text="名称")
        self.tree.heading("rarity", text="稀有度")
        self.tree.heading("count", text="数量")
        self.tree.heading("desc", text="描述")
        self.tree.pack(fill=BOTH, expand=True)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        counts: Dict[str, Dict[str, Any]] = {}
        for item in self.app.store.state["pet"]["inventory"]:
            counts.setdefault(item["name"], {"rarity": item["rarity"], "count": 0, "desc": item.get("desc", "")})
            counts[item["name"]]["count"] += 1
        for name, meta in counts.items():
            self.tree.insert("", END, values=(name, meta["rarity"], meta["count"], meta["desc"]))


class PetHistoryWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("宠物历史")
        self.geometry("760x520")
        self.build_ui()
        self.refresh()

    def build_ui(self):
        main = tb.Frame(self, padding=12)
        main.pack(fill=BOTH, expand=True)
        self.text = ScrolledText(main, height=24)
        self.text.pack(fill=BOTH, expand=True)
        self.text.text.configure(state="disabled")

    def refresh(self):
        lines = []
        for item in self.app.store.state["pet"]["history"]:
            if item["kind"] == "loot":
                lines.append(f"[{item['time']}] 捡到 {item['name']} ({item['rarity']})：{item['desc']}")
            else:
                lines.append(f"[{item['time']}] 相遇：{item['story']}")
        self.text.text.configure(state="normal")
        self.text.text.delete("1.0", END)
        self.text.text.insert(END, "\n".join(lines) if lines else "暂无记录。")
        self.text.text.configure(state="disabled")


class AchievementWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("成就列表")
        self.geometry("520x460")
        self.build_ui()
        self.refresh()

    def build_ui(self):
        main = tb.Frame(self, padding=12)
        main.pack(fill=BOTH, expand=True)
        self.text = ScrolledText(main, height=20)
        self.text.pack(fill=BOTH, expand=True)
        self.text.text.configure(state="disabled")

    def refresh(self):
        unlocked = self.app.store.state["achievements"]["unlocked"]
        lines = [f"已解锁：{a['name']}  @ {a['time']}\n{a['desc']}\n" for a in unlocked]
        self.text.text.configure(state="normal")
        self.text.text.delete("1.0", END)
        self.text.text.insert(END, "\n".join(lines) if lines else "尚未解锁成就。")
        self.text.text.configure(state="disabled")


# =========================
# App
# =========================
class WESI:
    def __init__(self):
        self.store = DataStore(DATA_FILE)
        self.tarot_cards = load_tarot_cards()

        self.pet_items = load_pet_items()
        self.pet_events = load_pet_events()
        self.d2_item_names = import_d2_names_from_local_json()

        self.battle_attack_points = load_battle_attack_points()
        self.battle_base_game_weapons = load_battle_base_game_weapons()
        self.battle_damage_types = load_battle_damage_types()
        self.battle_reactions = load_battle_reactions()
        self.battle_real_weapons = load_battle_real_weapons()
        self.battle_warm_messages = load_battle_warm_messages()

        self.style = tb.Style(theme=self.store.state["theme"]["name"])
        self.root = self.style.master
        self.root.title(APP_TITLE)
        self.root.geometry(self.store.state["income"].get("window_geometry", "760x860+120+80"))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.status_locked_until = None
        self.status_default = "系统已就绪。"
        self.windows: Dict[str, Any] = {}

        self.last_income_snapshot = 0.0
        self.last_status_tick = 0
        self.status_messages = [
            "系统正在安静地回收今日价值。",
            "你不是白坐在这里，每一秒都在结算。",
            "金币流正在推进，保持呼吸。",
            "今天已经开始回本，不需要每一秒都证明自己。",
            "资本机器仍在转动，你已经从里面取回了一部分。",
        ]

        self.build_ui()
        self.apply_theme(refresh_widgets=False)
        self.update_income_ui()

    def count_workdays(self, start_date, end_date) -> int:
        count = 0
        current = start_date

        while current < end_date:
            if current.weekday() < 5:
                count += 1
            current += timedelta(days=1)

        return count

    def apply_theme(self, refresh_widgets: bool = True):
        theme = self.store.state["theme"]
        try:
            self.style.theme_use(theme["name"])
        except Exception:
            self.style.theme_use("darkly")

        colors = theme["colors"]
        self.root.configure(bg=colors["bg"])

        if refresh_widgets:
            self._refresh_color_overrides()

    def _refresh_color_overrides(self):
        colors = self.store.state["theme"]["colors"]
        money = colors.get("money", "#37f2a3")
        status = colors.get("status", "#8aa4c8")

        for label in [
            self.joined_label,
            self.year_label,
            self.month_label,
            self.today_label,
            self.rate_label,
            self.tick_label,
            self.today_recovery_label,
        ]:
            label.configure(foreground=money)

        self.status_label.configure(foreground=status)

    def build_ui(self):
        self.main = tb.Frame(self.root, padding=16)
        self.main.pack(fill=BOTH, expand=True)

        self.header_card = tb.Labelframe(self.main, text="今日价值回收", padding=14)
        self.header_card.pack(fill=X, pady=(0, 12))

        top = tb.Frame(self.header_card)
        top.pack(fill=X)

        tb.Label(
            top,
            text="WESI",
            font=("Segoe UI", 16, "bold")
        ).pack(side=LEFT)

        tb.Button(top, text="主题", command=self.open_theme_dialog).pack(side=RIGHT, padx=(8, 0))
        tb.Button(top, text="设置", command=self.open_settings_dialog).pack(side=RIGHT)

        self.today_recovery_label = tb.Label(
            self.header_card,
            text="今日回血：€0.00 / €0.00",
            font=("Segoe UI", 20, "bold")
        )
        self.today_recovery_label.pack(anchor=W, pady=(16, 8))

        self.today_progress_bar = tb.Progressbar(
            self.header_card,
            maximum=100,
            value=0,
            bootstyle="success-striped"
        )
        self.today_progress_bar.pack(fill=X, pady=(0, 8))

        self.today_progress_text = tb.Label(
            self.header_card,
            text="今日进度：0.0%    剩余：€0.00",
            font=("Segoe UI", 10)
        )
        self.today_progress_text.pack(anchor=W)

        self.money_card = tb.Labelframe(self.main, text="金币回收记录", padding=12)
        self.money_card.pack(fill=X, pady=(0, 12))

        self.rate_label = tb.Label(
            self.money_card,
            text="当前流速：€0.000000 / 秒",
            font=("Consolas", 15, "bold")
        )
        self.rate_label.pack(anchor=W, pady=(0, 8))

        self.tick_label = tb.Label(
            self.money_card,
            text="刚刚回收：+€0.00",
            font=("Consolas", 15, "bold")
        )
        self.tick_label.pack(anchor=W, pady=(0, 8))

        self.today_label = tb.Label(self.money_card, text="", font=("Consolas", 13, "bold"))
        self.today_label.pack(anchor=W, pady=2)

        self.month_label = tb.Label(self.money_card, text="", font=("Consolas", 13, "bold"))
        self.month_label.pack(anchor=W, pady=2)

        self.year_label = tb.Label(self.money_card, text="", font=("Consolas", 13, "bold"))
        self.year_label.pack(anchor=W, pady=2)

        self.joined_label = tb.Label(self.money_card, text="", font=("Consolas", 13, "bold"))
        self.joined_label.pack(anchor=W, pady=2)

        self.actions_card = tb.Labelframe(self.main, text="互动", padding=12)
        self.actions_card.pack(fill=X, pady=(0, 12))

        row1 = tb.Frame(self.actions_card)
        row1.pack(fill=X, pady=(0, 8))

        tb.Button(row1, text="进度", command=self.show_progress).pack(side=LEFT, padx=(0, 8))
        tb.Button(row1, text="发泄", bootstyle="danger", command=self.open_battle).pack(side=LEFT, padx=(0, 8))
        tb.Button(row1, text="来一句", command=self.open_quote_window).pack(side=LEFT, padx=(0, 8))
        tb.Button(row1, text="收藏", command=self.open_favorites).pack(side=LEFT)

        row2 = tb.Frame(self.actions_card)
        row2.pack(fill=X)

        tb.Button(row2, text="塔罗", command=self.open_tarot).pack(side=LEFT, padx=(0, 8))
        tb.Button(row2, text="宠物", command=self.open_pet).pack(side=LEFT, padx=(0, 8))
        tb.Button(row2, text="成就", command=self.open_achievements).pack(side=LEFT)

        self.status_card = tb.Labelframe(self.main, text="事件流", padding=12)
        self.status_card.pack(fill=BOTH, expand=True)

        self.status_label = tb.Label(
            self.status_card,
            text=self.status_default,
            wraplength=460,
            justify=LEFT,
            font=("Segoe UI", 11)
        )
        self.status_label.pack(anchor=W)

    def open_theme_dialog(self):
        dialog = ThemeDialog(self)
        dialog.lift()
        dialog.focus_force()

    def open_settings_dialog(self):
        dialog = tb.Toplevel(self.root)
        dialog.title("设置")
        dialog.geometry("440x340")
        dialog.transient(self.root)
        dialog.grab_set()

        main = tb.Frame(dialog, padding=12)
        main.pack(fill=BOTH, expand=True)

        income = self.store.state.setdefault("income", {})

        salary_var = tb.StringVar(value=str(income.get("monthly_net_salary", 2600.0)))
        weekly_hours_var = tb.StringVar(value=str(income.get("weekly_work_hours", 40.0)))
        start_var = tb.StringVar(value=income.get("employment_start", "2026-04-01 00:00:00"))

        tb.Label(main, text="月净收入 (€)").pack(anchor=W)
        tb.Entry(main, textvariable=salary_var).pack(fill=X, pady=(6, 12))

        tb.Label(main, text="每周工作时间 (h)").pack(anchor=W)
        tb.Entry(main, textvariable=weekly_hours_var).pack(fill=X, pady=(6, 12))

        tb.Label(main, text="入职时间 (YYYY-MM-DD HH:MM:SS)").pack(anchor=W)
        tb.Entry(main, textvariable=start_var).pack(fill=X, pady=(6, 12))

        def save_settings():
            try:
                salary = float(salary_var.get().strip())
                weekly_hours = float(weekly_hours_var.get().strip())
                start_text = start_var.get().strip()

                if salary <= 0 or weekly_hours <= 0:
                    raise ValueError

                parse_dt(start_text)

                self.store.state["income"]["monthly_net_salary"] = salary
                self.store.state["income"]["weekly_work_hours"] = weekly_hours
                self.store.state["income"]["employment_start"] = start_text

                self.store.save()
                self.flash_status("设置已保存。工资流速已更新。")
                dialog.destroy()

            except Exception:
                Messagebox.ok(
                    "请输入正确格式：\n\n"
                    "月净收入：数字，例如 2660\n"
                    "每周工作时间：数字，例如 40\n"
                    "入职时间：YYYY-MM-DD HH:MM:SS",
                    "输入错误"
                )

        btn_row = tb.Frame(main)
        btn_row.pack(fill=X, pady=(8, 0))

        tb.Button(btn_row, text="保存", bootstyle="success", command=save_settings).pack(side=RIGHT)
        tb.Button(btn_row, text="取消", command=dialog.destroy).pack(side=RIGHT, padx=(0, 8))

    def get_income_stats(self) -> Dict[str, Any]:
        now = datetime.now()

        income = self.store.state["income"]
        salary = float(income.get("monthly_net_salary", 2600.0))
        weekly_hours = float(income.get("weekly_work_hours", 40.0))
        start = parse_dt(income.get("employment_start", "2026-04-01 00:00:00"))

        monthly_work_hours = weekly_hours * 52 / 12
        daily_work_hours = weekly_hours / 5

        hourly_rate = salary / monthly_work_hours if monthly_work_hours > 0 else 0.0
        rate = hourly_rate / 3600
        daily_target = hourly_rate * daily_work_hours

        if now < start:
            return {
                "rate": rate,
                "joined": 0.0,
                "year": 0.0,
                "month": 0.0,
                "today": 0.0,
                "daily_target": daily_target,
            }

        today_date = now.date()

        if now.weekday() < 5:
            elapsed_seconds = (now - day_start(now)).total_seconds()
            ratio = min(elapsed_seconds / (24 * 3600), 1.0)
            today_income = daily_target * ratio
        else:
            today_income = 0.0

        month_workdays = self.count_workdays(month_start(now).date(), today_date)
        year_workdays = self.count_workdays(year_start(now).date(), today_date)
        joined_workdays = self.count_workdays(start.date(), today_date)

        return {
            "rate": rate,
            "today": today_income,
            "month": month_workdays * daily_target + today_income,
            "year": year_workdays * daily_target + today_income,
            "joined": joined_workdays * daily_target + today_income,
            "daily_target": daily_target,
        }

    def update_income_ui(self):
        stats = self.get_income_stats()

        daily_target = float(stats.get("daily_target", 100.0))
        today = stats["today"]

        progress = 0.0 if daily_target <= 0 else min(today / daily_target, 1.0)
        progress_percent = progress * 100
        remain = max(0.0, daily_target - today)

        recovered_since_last = max(0.0, today - self.last_income_snapshot)
        self.last_income_snapshot = today

        self.today_recovery_label.configure(
            text=f"今日回血：€{today:.2f} / €{daily_target:.2f}"
        )
        self.today_progress_bar.configure(value=progress_percent)
        self.today_progress_text.configure(
            text=f"今日进度：{progress_percent:.1f}%    剩余：€{remain:.2f}"
        )

        self.rate_label.configure(text=f"当前价值流速：€ {stats['rate']:.6f} / 秒")
        self.tick_label.configure(text=f"刚刚回收：+€ {recovered_since_last:.4f}")

        self.today_label.configure(text=f"今日已回收：€ {stats['today']:.2f}")
        self.month_label.configure(text=f"本月已回收：€ {stats['month']:.2f}")
        self.year_label.configure(text=f"今年已回收：€ {stats['year']:.2f}")
        self.joined_label.configure(text=f"入职以来总回收：€ {stats['joined']:.2f}")

        self._refresh_color_overrides()
        self.increment_achievement_check()
        self._tick_status_messages(stats, daily_target, remain)

        self.root.after(1000, self.update_income_ui)

    def _tick_status_messages(self, stats: Dict[str, Any], daily_target: float, remain: float):
        now_ts = time.time()

        if self.status_locked_until and now_ts < self.status_locked_until:
            return

        if now_ts - self.last_status_tick < 18:
            return

        self.last_status_tick = now_ts

        dynamic_messages = [
            f"金币流速稳定：€{stats['rate']:.6f} / 秒。",
            f"今日已经回收 €{stats['today']:.2f}，不是白来。",
            f"距离今日目标还差 €{remain:.2f}。",
            f"本月累计回收 €{stats['month']:.2f}，进度正在堆叠。",
            random.choice(self.status_messages),
        ]

        if daily_target > 0 and stats["today"] >= daily_target:
            dynamic_messages.append("今日目标已完成。剩下的时间属于你的精神余量。")

        self.status_label.configure(text=random.choice(dynamic_messages))

    def flash_status(self, message: str, seconds: int = 6):
        self.status_label.configure(text=message)
        self.status_locked_until = time.time() + seconds
        self.root.after(seconds * 1000, self._restore_status_if_ready)

    def _restore_status_if_ready(self):
        if self.status_locked_until and time.time() < self.status_locked_until:
            return
        self.status_label.configure(text=self.status_default)

    def show_progress(self):
        stats = self.get_income_stats()
        daily_target = float(stats.get("daily_target", 100.0))
        today = stats["today"]
        remain_today = max(0.0, daily_target - today)

        milestones = [1000, 5000, 10000, 50000, 100000]
        joined = stats["joined"]
        next_m = next((m for m in milestones if joined < m), milestones[-1])
        remain_total = max(0, next_m - joined)

        message = (
            f"今日回血：€{today:.2f} / €{daily_target:.2f}\n"
            f"今日剩余：€{remain_today:.2f}\n"
            f"距离累计里程碑 €{next_m:,.0f} 还差 €{remain_total:,.2f}。"
        )

        self.flash_status(message, seconds=8)

    def _open_or_focus(self, key: str, cls):
        win = self.windows.get(key)
        if win is not None:
            try:
                if win.winfo_exists():
                    win.lift()
                    win.focus_force()
                    return win
            except Exception:
                pass

        win = cls(self)
        self.windows[key] = win

        def _cleanup(_event=None, _key=key):
            self.windows.pop(_key, None)

        win.bind("<Destroy>", _cleanup)
        return win

    def open_quote_window(self):
        self._open_or_focus("quotes", QuoteWindow)

    def open_favorites(self):
        self._open_or_focus("favorites", FavoritesWindow)

    def open_battle(self):
        self._open_or_focus("battle", BattleWindow)

    def open_tarot(self):
        self._open_or_focus("tarot", TarotWindow)

    def open_pet(self):
        self._open_or_focus("pet", PetWindow)

    def open_achievements(self):
        self._open_or_focus("achievements", AchievementWindow)

    def _unlock_achievement(self, name: str, desc: str):
        unlocked = self.store.state["achievements"]["unlocked"]
        if any(a["name"] == name for a in unlocked):
            return

        unlocked.append({"name": name, "desc": desc, "time": format_now()})
        self.store.save()
        self.flash_status(f"成就解锁：{name}", seconds=8)

    def increment_achievement_check(self):
        stats = self.get_income_stats()
        joined = stats["joined"]
        battle = self.store.state["battle"]["stats"]
        pet = self.store.state["pet"]
        inventory_count = len(pet["inventory"])

        if joined >= 1000:
            self._unlock_achievement("第一桶金", "累计收入达到 €1,000。")
        if joined >= 5000:
            self._unlock_achievement("稳定输出", "累计收入达到 €5,000。")
        if joined >= 10000:
            self._unlock_achievement("资本开始说话", "累计收入达到 €10,000。")
        if battle["total_hits"] >= 10:
            self._unlock_achievement("小小发泄", "累计攻击达到 10 次。")
        if battle["kills"] >= 3:
            self._unlock_achievement("会议屠戮者", "累计击败 3 个目标。")
        if pet["forage_count"] >= 5:
            self._unlock_achievement("第一次长时间摸鱼", "宠物累计摸鱼 5 次。")
        if inventory_count >= 10:
            self._unlock_achievement("收藏开始增长", "宠物累计捡到 10 件物品。")
        if any(item.get("rarity") == "legendary" for item in pet["inventory"]):
            self._unlock_achievement("传奇一瞥", "宠物捡到过传奇物品。")

    def on_close(self):
        self.store.state["income"]["window_geometry"] = self.root.geometry()
        self.store.save()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = WESI()
    app.run()