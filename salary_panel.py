"""Pixel salary dashboard. All effects are presentation, never payroll mutations."""
import math
import random
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont

import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk

BG = "#101d2a"
EDGE = "#2a4355"
MINT = "#80efba"
GOLD = "#ffcc68"
TEXT = "#eaf2ed"
MUTED = "#90a9b7"


def available_coins(today, collected):
    """Whole cents only; settings changes cannot create negative balances."""
    earned = math.floor(max(0, today) * 100 + 1e-8)
    banked = min(earned, round(max(0, collected) * 100))
    return (earned - banked) / 100


def work_status(income, now):
    if now < datetime.strptime(income["employment_start"], "%Y-%m-%d %H:%M:%S"):
        return "等待入职", "你的回收旅程即将开始"
    if now.weekday() >= 5:
        return "休息日", "装置休眠中 · 今天好好休息"
    begin = datetime.combine(now.date(), datetime.strptime(income["work_start"], "%H:%M").time())
    end = datetime.combine(now.date(), datetime.strptime(income["work_end"], "%H:%M").time())
    if now < begin:
        seconds = int((begin - now).total_seconds())
        status, prefix = "等待上班", "距离开工"
    elif now < end:
        seconds = int((end - now).total_seconds())
        status, prefix = "正在回收", "距离下班"
    else:
        return "今日收工", "金币流已暂停 · 明天继续"
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return status, f"{prefix} {hours:02d}:{minutes:02d}:{seconds:02d}"


class SalaryPanel(tb.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.stats = {"today": 0.0, "rate": 0.0}
        self.status, self.countdown = "等待上班", ""
        self.previous = self.target = 0.0
        self.transition = time.monotonic()
        self.goal_reached = False
        self._feedback_kind = "idle"
        self.particles = []
        self._job = None
        self.settings = app.store.state["salary_display"]
        self.canvas = tk.Canvas(self, height=288, background=BG, highlightthickness=0)
        self.canvas.pack(fill="x")
        self.number_canvas = tk.Canvas(self.canvas, background=BG, highlightthickness=0)
        self._number_font = None
        asset = Path(__file__).resolve().parent / "assets/salary/coin.png"
        with Image.open(asset) as image:
            self.coin_image = ImageTk.PhotoImage(image.resize((32, 32), Image.Resampling.NEAREST), master=self.canvas)
        self.canvas.bind("<Configure>", lambda event: self._render())
        self.canvas.bind("<Button-1>", self._canvas_click)
        self.canvas.bind("<Motion>", self._hover)
        controls = tb.Frame(self)
        controls.pack(fill="x", pady=(8, 0))
        self.collect_button = tb.Button(controls, text="收取金币", bootstyle="success", command=self.collect)
        self.collect_button.pack(side="left")
        tb.Button(controls, text="设置小目标", bootstyle="secondary", command=self.open_goal).pack(side="left", padx=8)
        self.quiet_var = tk.BooleanVar(value=self.settings["quiet"])
        tb.Checkbutton(controls, text="安静模式", variable=self.quiet_var, command=self.toggle_quiet).pack(side="right")
        self.feedback = tb.Label(self, text="点击钱罐收取今日金币 · 工资按工时估算", font=("Microsoft YaHei", 9), wraplength=450)
        self.feedback.pack(anchor="w", pady=(7, 0))
        self._tick()

    def update_stats(self, stats, now=None):
        now = datetime.now() if now is None else now
        self.settings = self.app.store.state["salary_display"]
        date = now.strftime("%Y-%m-%d")
        if self.settings["collection_date"] != date:
            self.settings["collection_date"] = date
            self.settings["collected_today"] = 0.0
            self.goal_reached = False
            self._feedback_kind = "idle"
            self.feedback.configure(text="点击钱罐收取今日金币 · 工资按工时估算")
        self.stats = stats
        self.status, self.countdown = work_status(self.app.store.state["income"], now)
        self.previous = self.displayed_amount()
        self.target = max(0, stats["today"])
        self.transition = time.monotonic()
        reached = self.target >= self.settings["goal_amount"]
        if reached and not self.goal_reached:
            self.feedback.configure(text="小目标达成！今天的努力值得被看见。")
            self._feedback_kind = "goal"
            if not self.settings["quiet"]:
                self._burst()
        elif not reached and self._feedback_kind == "goal":
            self.feedback.configure(text="点击钱罐收取今日金币 · 工资按工时估算")
            self._feedback_kind = "idle"
        self.goal_reached = reached
        pending = available_coins(self.target, self.settings["collected_today"])
        self.collect_button.configure(text=f"收取 €{pending:.2f}", state="normal" if pending >= .01 else "disabled")
        self._render()

    def displayed_amount(self):
        if self.settings["quiet"]:
            return self.target
        progress = min(1, max(0, (time.monotonic() - self.transition) / .35))
        return self.previous + (self.target - self.previous) * (1 - (1 - progress) ** 3)

    def collect(self):
        # Refresh from the wage engine rather than trusting the animated value.
        self.update_stats(self.app.get_income_stats())
        pending = available_coins(self.target, self.settings["collected_today"])
        if pending < .01:
            self.feedback.configure(text="暂时没有新的金币，钱罐会等你。")
            return
        self.settings["collected_today"] = math.floor(self.target * 100 + 1e-8) / 100
        self.app.store.save()
        self.feedback.configure(text=f"已把 €{pending:.2f} 装进今日钱罐！这是展示收集，不影响工资累计。")
        self._feedback_kind = "collection"
        if not self.settings["quiet"]:
            self._burst()
        self.collect_button.configure(text="已收入钱罐", state="disabled")
        self._render()

    def toggle_quiet(self):
        self.settings["quiet"] = bool(self.quiet_var.get())
        self.particles.clear()
        self.app.store.save()
        self._render()

    def open_goal(self):
        dialog = tb.Toplevel(self.app.root)
        dialog.title("今天的小目标")
        dialog.geometry("360x235")
        dialog.transient(self.app.root)
        dialog.grab_set()
        frame = tb.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)
        tb.Label(frame, text="给今天一个看得见的目标", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w")
        tb.Label(frame, text="例如 €5 的咖啡，或 €20 的小奖励。", wraplength=310).pack(anchor="w", pady=(8, 12))
        amount = tk.StringVar(value=str(self.settings["goal_amount"]))
        entry = tb.Entry(frame, textvariable=amount)
        entry.pack(fill="x")
        def save():
            try:
                value = float(amount.get())
                if not math.isfinite(value) or not .01 <= value <= 1000000:
                    raise ValueError
            except ValueError:
                Messagebox.ok("请输入 €0.01 至 €1,000,000 之间的目标金额。", "目标金额无效", parent=dialog)
                return
            self.settings["goal_amount"] = round(value, 2)
            self.app.store.save()
            self.goal_reached = False
            self.update_stats(self.app.get_income_stats())
            dialog.destroy()
        tb.Button(frame, text="就定这个目标", bootstyle="success", command=save).pack(fill="x", pady=(14, 0))
        entry.bind("<Return>", lambda event: save())
        entry.focus_set()

    def _hover(self, event):
        self.canvas.configure(cursor="hand2" if event.x > self.canvas.winfo_width() - 115 and 140 < event.y < 236 else "")

    def _canvas_click(self, event):
        if event.x > self.canvas.winfo_width() - 115 and 140 < event.y < 236:
            self.collect()

    def _burst(self):
        self.particles = [(random.random(), random.uniform(-1, 1), time.monotonic()) for _ in range(18)]

    def _tick(self):
        if self.winfo_ismapped():
            self._render()
        animating = not self.settings["quiet"] and (self.stats["rate"] > 0 or self.particles or time.monotonic() - self.transition < .35)
        self._job = self.after(33 if animating and self.winfo_ismapped() else 250, self._tick)

    def _draw_amount(self, width):
        old = f"{self.previous:,.2f}"
        new = f"{self.target:,.2f}"
        size = min(34, max(18, int((width-72) / max(8, len(new)) / .85)))
        if self._number_font is None:
            self._number_font = tkfont.Font(root=self.number_canvas, family="Consolas", size=size)
        else:
            self._number_font.configure(size=size)
        step = self._number_font.measure("0")
        height = self._number_font.metrics("linespace")
        progress = 1 if self.settings["quiet"] else min(1, max(0, (time.monotonic()-self.transition)/.35))
        eased = 1-(1-progress)**3
        old, new = old.rjust(max(len(old), len(new))), new.rjust(max(len(old), len(new)))
        c = self.number_canvas
        c.configure(background=BG)
        c.delete("all")
        c.create_text(0, 32, text="€", anchor="w", font=self._number_font, fill=MINT)
        for index, (before, after) in enumerate(zip(old, new)):
            x = step*(index+1.6)
            if before == after or progress >= 1:
                c.create_text(x, 32, text=after, anchor="w", font=self._number_font, fill=MINT)
            else:
                c.create_text(x, 32-height*eased, text=before, anchor="w", font=self._number_font, fill=MINT)
                c.create_text(x, 32+height*(1-eased), text=after, anchor="w", font=self._number_font, fill=MINT)
        self.canvas.create_window(20, 40, window=c, width=width-40, height=64, anchor="nw")

    def _render(self):
        c = self.canvas
        width = max(400, c.winfo_width())
        c.delete("all")
        def rect(x, y, w, h, color, outline=""):
            c.create_rectangle(x, y, x+w, y+h, fill=color, outline=outline)
        def label(x, y, text, size=10, color=MUTED, anchor="w", family="Microsoft YaHei"):
            c.create_text(x, y, text=text, font=(family, size), fill=color, anchor=anchor)
        rect(1, 1, width-3, 285, BG, EDGE)
        for x, y in ((0, 0), (width-8, 0), (0, 280), (width-8, 280)):
            rect(x, y, 8, 8, MINT)
        label(18, 21, "WESI / 价值回收站", 10, TEXT)
        active = self.stats["rate"] > 0
        rect(width-110, 16, 6, 6, MINT if active else MUTED)
        label(width-95, 20, self.status, 9, MINT if active else MUTED)
        # The rolling counter is always bounded by the wage engine's target.
        self._draw_amount(width)
        label(22, 111, "今日估算收益", 9)
        label(width-20, 111, self.countdown, 9, anchor="e")
        rect(20, 133, width-40, 1, EDGE)
        # Pixel machine and conveyor: authored canvas art, not bank transactions.
        rect(30, 155, 62, 51, EDGE)
        rect(35, 149, 52, 6, MUTED)
        rect(36, 160, 50, 24, "#172e3d")
        for i in range(5):
            phase = int(time.monotonic()*3) % 5 if active and not self.settings["quiet"] else -1
            rect(42+i*8, 168, 5, 10, MINT if i <= phase else EDGE)
        rect(44, 191, 33, 8, GOLD)
        for x in (37, 77):
            rect(x, 206, 8, 7, MUTED)
        jar_x = width-83
        rect(98, 184, max(1, jar_x-112), 4, EDGE)
        for x in range(104, int(jar_x-10), 16):
            rect(x, 181, 3, 10, "#355063")
        if active:
            t = time.monotonic() % 3 / 3 if not self.settings["quiet"] else .5
            c.create_image(108+(jar_x-125)*t, 173, image=self.coin_image)
        rect(jar_x, 158, 50, 8, MUTED)
        rect(jar_x-6, 166, 62, 44, EDGE)
        rect(jar_x, 172, 50, 32, "#1c3543")
        banked = min(self.target, self.settings["collected_today"])
        fill = min(26, int(26*banked/max(.01, self.settings["goal_amount"])))
        if fill:
            rect(jar_x+5, 201-fill, 40, fill, GOLD)
        rect(jar_x+17, 156, 16, 3, BG)
        c.create_image(jar_x+25, 185, image=self.coin_image)
        label(31, 226, "工资引擎", 8)
        label(jar_x+25, 226, f"钱罐 €{banked:.2f}", 8, GOLD, anchor="center")
        goal = self.settings["goal_amount"]
        ratio = min(1, self.target/goal)
        label(20, 249, f"今日小目标  €{goal:.2f}", 9, TEXT)
        label(width-20, 249, "已达成" if ratio >= 1 else f"{ratio:.0%}", 9, GOLD, anchor="e")
        count = max(1, int((width-40)/13))
        for i in range(count):
            rect(20+i*13, 268, 10, 7, GOLD if i < int(ratio*count) else EDGE)
        now = time.monotonic()
        self.particles = [p for p in self.particles if now-p[2] < .9]
        for position, drift, born in self.particles:
            age = now-born
            x = jar_x+25 + (position-.5)*120*age
            y = 170 - 95*age + 130*age*age + drift*10
            rect(x, y, 4, 4, GOLD if drift > 0 else MINT)

    def destroy(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()
