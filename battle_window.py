import random
from typing import List

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets.scrolled import ScrolledText
from ttkbootstrap.dialogs import Messagebox

try:
    from PIL import Image
except Exception:
    Image = None

from config import AVATAR_DIR
from utils import safe_copy_image, make_rounded_image, format_now


class BattleWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app

        self.overrideredirect(True)
        self.attributes("-alpha", 0.94)
        self.geometry("420x520+700+120")

        self.target_var = tb.StringVar(value=app.store.state["battle"]["default_target"])
        self.avatar_path = self._find_avatar_for_target(self.target_var.get())

        self.current_hp_max = random.randint(40, 90)
        self.current_hp = self.current_hp_max

        self.log_lines: List[str] = []
        self.avatar_img = None

        self.build_ui()
        self.refresh()
        self.bind_drag()

        self.app.store.state["battle"]["stats"]["sessions"] += 1
        self.app.store.save()

    # =========================
    # helpers
    # =========================
    def _find_avatar_for_target(self, name: str) -> str:
        for target in self.app.store.state["battle"]["targets"]:
            if target["name"] == name:
                return target.get("avatar", "")
        return ""

    def bind_drag(self):
        self._drag_x = 0
        self._drag_y = 0

        def start_drag(event):
            self._drag_x = event.x_root
            self._drag_y = event.y_root

        def drag(event):
            dx = event.x_root - self._drag_x
            dy = event.y_root - self._drag_y
            self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")
            self._drag_x = event.x_root
            self._drag_y = event.y_root

        self.bind("<ButtonPress-1>", start_drag)
        self.bind("<B1-Motion>", drag)

    # =========================
    # UI
    # =========================
    def build_ui(self):
        self.main = tb.Frame(self, padding=14, bootstyle="dark")
        self.main.pack(fill=BOTH, expand=True)

        top = tb.Frame(self.main)
        top.pack(fill=X)

        self.avatar_label = tb.Label(top, width=12)
        self.avatar_label.pack(side=LEFT, padx=(0, 12))

        info = tb.Frame(top)
        info.pack(side=LEFT, fill=X, expand=True)

        tb.Label(info, text="发泄战斗", font=("Segoe UI", 14, "bold")).pack(anchor=W)

        target_row = tb.Frame(info)
        target_row.pack(fill=X, pady=(6, 6))

        tb.Entry(target_row, textvariable=self.target_var).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        tb.Button(target_row, text="更新对象", command=self.update_target).pack(side=LEFT)

        avatar_row = tb.Frame(info)
        avatar_row.pack(fill=X)

        tb.Button(avatar_row, text="上传头像", command=self.upload_avatar).pack(side=LEFT, padx=(0, 6))
        tb.Button(avatar_row, text="关闭", bootstyle="outline-secondary", command=self.destroy).pack(side=LEFT)

        self.hp_label = tb.Label(self.main, text="")
        self.hp_label.pack(anchor=W, pady=(12, 4))

        self.hp_bar = tb.Progressbar(
            self.main,
            maximum=self.current_hp_max,
            value=self.current_hp,
            bootstyle="danger-striped"
        )
        self.hp_bar.pack(fill=X)

        self.latest_label = tb.Label(
            self.main,
            text="准备攻击。",
            wraplength=380,
            justify=LEFT,
            font=("Segoe UI", 11, "bold")
        )
        self.latest_label.pack(anchor=W, pady=(14, 12))

        self.damage_label = tb.Label(
            self.main,
            text="",
            font=("Consolas", 16, "bold"),
            bootstyle="warning"
        )
        self.damage_label.pack(anchor=W)

        tb.Button(self.main, text="攻击", bootstyle="danger", command=self.attack)\
            .pack(fill=X, pady=(14, 12))

        tb.Label(self.main, text="最近战斗日志", bootstyle="secondary").pack(anchor=W)

        self.log_box = ScrolledText(self.main, height=10)
        self.log_box.pack(fill=BOTH, expand=True, pady=(6, 0))
        self.log_box.text.configure(state="disabled")

    # =========================
    # logic
    # =========================
    def refresh(self):
        self.hp_label.configure(
            text=f"{self.target_var.get()}  HP: {self.current_hp} / {self.current_hp_max}"
        )
        self.hp_bar.configure(maximum=self.current_hp_max, value=self.current_hp)

        if self.avatar_path and Image:
            self.avatar_img = make_rounded_image(self.avatar_path, (96, 96), radius=22)
            if self.avatar_img:
                self.avatar_label.configure(image=self.avatar_img, text="")
                return

        self.avatar_label.configure(text="(头像)", image="")

    def update_target(self):
        target = self.target_var.get().strip() or "Boss"
        self.target_var.set(target)

        self.app.store.state["battle"]["default_target"] = target

        if not any(t["name"] == target for t in self.app.store.state["battle"]["targets"]):
            self.app.store.state["battle"]["targets"].append({"name": target, "avatar": ""})

        self.avatar_path = self._find_avatar_for_target(target)

        self.current_hp_max = random.randint(40, 90)
        self.current_hp = self.current_hp_max

        self.app.store.save()
        self.refresh()

    def upload_avatar(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")]
        )
        if not path:
            return

        try:
            saved = safe_copy_image(path, AVATAR_DIR)
        except (OSError, ValueError):
            Messagebox.ok("无法读取图片，请选择有效的图片文件。", "导入失败")
            return
        if not saved:
            return

        target = self.target_var.get().strip() or "Boss"

        found = False
        for item in self.app.store.state["battle"]["targets"]:
            if item["name"] == target:
                item["avatar"] = saved
                found = True
                break

        if not found:
            self.app.store.state["battle"]["targets"].append(
                {"name": target, "avatar": saved}
            )

        self.avatar_path = saved
        self.app.store.save()
        self.refresh()

    def _append_log(self, line: str):
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-5:]

        self.log_box.text.configure(state="normal")
        self.log_box.text.delete("1.0", END)
        self.log_box.text.insert(END, "\n".join(self.log_lines))
        self.log_box.text.configure(state="disabled")

    def attack(self):
        if self.current_hp <= 0:
            self.latest_label.configure(text="战斗已经结束。")
            return

        weapon_pool = self.app.battle_base_game_weapons + self.app.battle_real_weapons

        weapon = random.choice(weapon_pool)
        body = random.choice(self.app.battle_attack_points)
        dtype = random.choice(self.app.battle_damage_types)
        reaction = random.choice(self.app.battle_reactions)

        damage = random.randint(1, 20)
        crit = random.random() < 0.1
        if crit:
            damage *= random.choice([2, 3])

        self.current_hp = max(0, self.current_hp - damage)

        prefix = "暴击！" if crit else ""
        line = f"{prefix}你使用了{weapon}，命中了对方的{body}，造成了{damage}点{dtype}伤害。{reaction}"

        self.latest_label.configure(text=line)
        self.damage_label.configure(text=f"-{damage}" + ("  CRIT" if crit else ""))

        self._append_log(line)
        self.refresh()

        stats = self.app.store.state["battle"]["stats"]
        stats["total_hits"] += 1

        if self.current_hp == 0:
            stats["kills"] += 1
            warm = random.choice(self.app.battle_warm_messages)
            final_line = f"已击败 {self.target_var.get()}。\n{warm}"

            self.latest_label.configure(text=final_line)
            self._append_log(final_line)
            self.app.flash_status("战斗胜利。")

        self.app.store.save()
        self.app.increment_achievement_check()

        self.app.store.save()
