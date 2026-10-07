import random
import time
import math
from datetime import datetime
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from utils import (
    rotate_image_for_tarot,
    format_now,
    load_tarot_history,
    save_tarot_history,
)
from config import TAROT_DIR, SPREADS, SPREAD_LABELS


class TarotWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("塔罗")
        self.geometry("1280x900")
        self.transient(app.root)

        self.spread_var = tb.StringVar(value=SPREAD_LABELS["single"])
        self.question_var = tb.StringVar()
        self.cooldown_seconds = 10
        self.cooldown_job = None
        self._cooldown_remaining = 0
        self._cooldown_until = 0

        self.build_ui()
        last_draw = self.app.store.state["tarot"].get("last_draw_at")
        if last_draw:
            try:
                remaining = self.cooldown_seconds - (datetime.now() - datetime.strptime(last_draw, "%Y-%m-%d %H:%M:%S")).total_seconds()
                if remaining > 0:
                    self.start_cooldown(min(self.cooldown_seconds, math.ceil(remaining)))
            except (ValueError, TypeError):
                pass

    def build_ui(self):
        main = tb.Frame(self, padding=14)
        main.pack(fill=BOTH, expand=True)

        top = tb.Frame(main)
        top.pack(fill=X)

        tb.Label(top, text="牌阵").pack(side=LEFT)

        self.spread_box = tb.Combobox(
            top,
            textvariable=self.spread_var,
            values=list(SPREAD_LABELS.values()),
            state="readonly",
            width=18,
        )
        self.spread_box.pack(side=LEFT, padx=(6, 12))

        tb.Label(top, text="问题").pack(side=LEFT)

        self.question_entry = tb.Entry(top, textvariable=self.question_var)
        self.question_entry.pack(side=LEFT, fill=X, expand=True, padx=(6, 12))
        self.question_entry.bind("<Return>", lambda event: self.draw_cards())

        self.draw_btn = tb.Button(
            top,
            text="抽牌",
            bootstyle="primary",
            command=self.draw_cards,
        )
        self.draw_btn.pack(side=LEFT, padx=(0, 8))

        tb.Button(top, text="历史", command=self.open_history).pack(side=LEFT)

        self.result_wrap = tb.Frame(main)
        self.result_wrap.pack(fill=BOTH, expand=True, pady=(16, 0))

    def _clear_results(self):
        for child in self.result_wrap.winfo_children():
            child.destroy()

    def _get_card_image(self, img_filename: str, reversed_card: bool, size=(320, 560)):
        path = TAROT_DIR / img_filename
        if path.exists():
            return rotate_image_for_tarot(str(path), reversed_card, size)
        return None

    def draw_cards(self):
        if time.monotonic() < self._cooldown_until:
            return
        question = self.question_var.get().strip()
        spread_label = self.spread_var.get()
        spread = next((k for k, v in SPREAD_LABELS.items() if v == spread_label), None)
        if spread is None:
            return

        positions = SPREADS[spread]
        single_mode = len(positions) == 1
        if len(self.app.tarot_cards) < len(positions):
            Messagebox.ok("牌库不足，请检查塔罗数据文件。", "无法抽牌")
            return
        selected = random.sample(self.app.tarot_cards, k=len(positions))

        cards = []
        self._clear_results()

        cards_row = tb.Frame(self.result_wrap)
        cards_row.pack(anchor=CENTER)

        for pos, card in zip(positions, selected):
            reversed_card = random.random() < 0.5

            desc = card.get("desc", "")
            if reversed_card:
                desc = f"逆位视角：{desc}"

            card_info = {
                "position": pos,
                "name_zh": card["name_zh"],
                "name_en": card["name_en"],
                "reversed": reversed_card,
                "img": card["img"],
                "desc": desc,
                "keywords": card.get("keywords", []),
            }
            cards.append(card_info)

            frame = tb.Labelframe(
                cards_row,
                text=pos,
                padding=10,
                width=350 if single_mode else 300,
                height=700,
            )
            frame.pack_propagate(False)

            if single_mode:
                frame.pack(padx=8, pady=4)
            else:
                frame.pack(side=LEFT, padx=8, pady=4)

            img = self._get_card_image(card_info["img"], reversed_card,
                                       (320, 560) if single_mode else (260, 455))
            if img:
                lbl = tb.Label(frame, image=img)
                lbl.image = img
                lbl.pack(pady=(0, 10))
            else:
                tb.Label(frame, text="[牌面占位]", width=20).pack(pady=(0, 12))

            tb.Label(
                frame,
                text=f"{card_info['name_zh']} {'逆位' if reversed_card else '正位'}",
                font=("Segoe UI", 12, "bold"),
                justify=CENTER,
                wraplength=360,
            ).pack(anchor=CENTER, pady=(6, 8))

            tb.Label(
                frame,
                text=card_info["desc"],
                wraplength=360,
                justify=CENTER,
            ).pack(anchor=CENTER, pady=(0, 8))

            if card_info["keywords"]:
                tb.Label(
                    frame,
                    text=" / ".join(card_info["keywords"]),
                    foreground="#888",
                    justify=CENTER,
                    wraplength=360,
                ).pack(anchor=CENTER, pady=(4, 0))

        entry = {
            "time": format_now(),
            "question": question,
            "spread": spread,
            "cards": cards,
        }

        history = load_tarot_history()
        history.append(entry)
        save_tarot_history(history)

        self.app.store.state["tarot"]["last_draw_at"] = format_now()
        self.app.store.save()

        self.start_cooldown(self.cooldown_seconds)
        self.app.flash_status("塔罗已记录。")

    def start_cooldown(self, seconds: int):
        self._cooldown_until = time.monotonic() + seconds
        self.draw_btn.configure(state=DISABLED)
        self._cooldown_remaining = seconds
        self._tick_cooldown()

    def _tick_cooldown(self):
        self.draw_btn.configure(text=f"冷却中（{self._cooldown_remaining}s）")
        if self._cooldown_remaining <= 0:
            self.draw_btn.configure(text="抽牌", state=NORMAL)
            self.cooldown_job = None
            return
        self._cooldown_remaining -= 1
        self.cooldown_job = self.after(1000, self._tick_cooldown)

    def open_history(self):
        self.app._open_or_focus("tarot_history", TarotHistoryWindow)

    def destroy(self):
        if self.cooldown_job is not None:
            self.after_cancel(self.cooldown_job)
            self.cooldown_job = None
        super().destroy()


class TarotHistoryWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("塔罗历史")
        self.geometry("760x520")
        self.build_ui()
        self.refresh()

    def build_ui(self):
        main = tb.Frame(self, padding=12)
        main.pack(fill=BOTH, expand=True)

        self.listbox = tb.Treeview(
            main,
            columns=("time", "spread", "question"),
            show="headings",
        )
        self.listbox.heading("time", text="时间")
        self.listbox.heading("spread", text="牌阵")
        self.listbox.heading("question", text="提问")
        self.listbox.pack(fill=BOTH, expand=True)

        btn_row = tb.Frame(main)
        btn_row.pack(fill=X, pady=(8, 0))

        tb.Button(
            btn_row,
            text="清空历史",
            bootstyle="danger",
            command=self.clear_history,
        ).pack(side=LEFT)

        tb.Button(
            btn_row,
            text="查看详情",
            command=self.view_selected,
        ).pack(side=RIGHT)

    def refresh(self):
        self.history = load_tarot_history()
        for item in self.listbox.get_children():
            self.listbox.delete(item)

        for i, entry in enumerate(self.history):
            self.listbox.insert(
                "",
                END,
                iid=str(i),
                values=(entry["time"], entry["spread"], entry["question"]),
            )

    def view_selected(self):
        sel = self.listbox.selection()
        if not sel:
            return

        entry = self.history[int(sel[0])]
        lines = [
            f"时间：{entry['time']}",
            f"牌阵：{entry['spread']}",
            f"问题：{entry['question']}",
            "",
        ]

        for card in entry["cards"]:
            lines.append(
                f"{card['position']}：{card['name_zh']} {'逆位' if card['reversed'] else '正位'}"
            )
            lines.append(card["desc"])
            if card.get("keywords"):
                lines.append("关键词：" + " / ".join(card["keywords"]))
            lines.append("")

        Messagebox.ok("\n".join(lines), "塔罗详情")

    def clear_history(self):
        confirmed = Messagebox.yesno(
            "确定要清空全部塔罗历史吗？此操作不可撤销。",
            "确认清空",
        )
        if confirmed == "Yes":
            save_tarot_history([])
            self.refresh()
