import random
from urllib.parse import quote
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledText
from typing import Any, Dict, Optional

from utils import get_jinrishici_quote, format_now


class FavoritesWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("已收藏内容")
        self.geometry("760x520")
        self.transient(app.root)
        self.build_ui()
        self.refresh()

    def build_ui(self):
        main = tb.Frame(self, padding=12)
        main.pack(fill=BOTH, expand=True)

        self.listbox = tb.Treeview(main, columns=("source",), show="headings", height=14)
        self.listbox.heading("source", text="来源")
        self.listbox.pack(fill=BOTH, expand=True)

        btn_row = tb.Frame(main)
        btn_row.pack(fill=X, pady=(8, 0))

        tb.Button(btn_row, text="查看", command=self.view_selected).pack(side=LEFT, padx=(0, 8))
        tb.Button(btn_row, text="移除收藏", bootstyle="danger", command=self.remove_selected).pack(side=LEFT)

    def refresh(self):
        for item in self.listbox.get_children():
            self.listbox.delete(item)

        for i, fav in enumerate(self.app.store.state["quotes"]["favorites"]):
            short = fav["text"][:48] + ("…" if len(fav["text"]) > 48 else "")
            self.listbox.insert("", END, iid=str(i), values=(f"{short} — {fav['source']}",))

    def get_selected(self):
        sel = self.listbox.selection()
        if not sel:
            return None, None
        idx = int(sel[0])
        return idx, self.app.store.state["quotes"]["favorites"][idx]

    def view_selected(self):
        _, item = self.get_selected()
        if not item:
            return
        Messagebox.ok(f"{item['text']}\n\n—— {item['source']}", "收藏内容")

    def remove_selected(self):
        idx, _ = self.get_selected()
        if idx is None:
            return
        del self.app.store.state["quotes"]["favorites"][idx]
        self.app.store.save()
        self.refresh()


class CustomQuotesWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("我的记录")
        self.geometry("760x520")
        self.transient(app.root)
        self.build_ui()
        self.refresh()

    def build_ui(self):
        main = tb.Frame(self, padding=12)
        main.pack(fill=BOTH, expand=True)

        self.listbox = tb.Treeview(
            main,
            columns=("time", "source", "preview"),
            show="headings",
            height=16
        )
        self.listbox.heading("time", text="时间")
        self.listbox.heading("source", text="来源")
        self.listbox.heading("preview", text="内容预览")

        self.listbox.column("time", width=150, anchor=W)
        self.listbox.column("source", width=120, anchor=W)
        self.listbox.column("preview", width=420, anchor=W)

        self.listbox.pack(fill=BOTH, expand=True)

        btn_row = tb.Frame(main)
        btn_row.pack(fill=X, pady=(8, 0))

        tb.Button(btn_row, text="查看", command=self.view_selected).pack(side=LEFT, padx=(0, 8))
        tb.Button(btn_row, text="删除", bootstyle="danger", command=self.delete_selected).pack(side=LEFT)
        tb.Button(btn_row, text="刷新", command=self.refresh).pack(side=RIGHT)

    def _get_custom_quotes(self):
        return [
            item for item in self.app.store.state["quotes"]["all"]
            if item.get("type") == "custom"
        ]

    def refresh(self):
        for item in self.listbox.get_children():
            self.listbox.delete(item)

        custom_quotes = self._get_custom_quotes()
        for i, item in enumerate(custom_quotes):
            preview = item["text"][:50] + ("…" if len(item["text"]) > 50 else "")
            created_at = item.get("created_at", "无时间戳")
            source = item.get("source", "")
            self.listbox.insert(
                "",
                END,
                iid=str(i),
                values=(created_at, source, preview)
            )

    def get_selected(self):
        sel = self.listbox.selection()
        if not sel:
            return None, None

        idx = int(sel[0])
        custom_quotes = self._get_custom_quotes()
        if idx >= len(custom_quotes):
            return None, None

        return idx, custom_quotes[idx]

    def view_selected(self):
        _, item = self.get_selected()
        if not item:
            return

        lines = [
            f"时间：{item.get('created_at', '无时间戳')}",
            f"来源：{item.get('source', '')}",
            "",
            item["text"],
        ]
        Messagebox.ok("\n".join(lines), "我的记录")

    def delete_selected(self):
        _, item = self.get_selected()
        if not item:
            return

        confirmed = Messagebox.yesno(
            f"确定要删除这条记录吗？\n\n{item['text'][:40]}{'…' if len(item['text']) > 40 else ''}",
            "确认删除"
        )
        if confirmed != "Yes":
            return

        all_quotes = self.app.store.state["quotes"]["all"]
        try:
            all_quotes.remove(item)
        except ValueError:
            return

        favorites = self.app.store.state["quotes"]["favorites"]
        if item in favorites:
            favorites.remove(item)

        self.app.store.save()
        self.refresh()
        self.app.flash_status("已删除一条灵光一现。")


class QuoteWindow(tb.Toplevel):
    def __init__(self, app: "WESI"):
        super().__init__(app.root)
        self.app = app
        self.title("来一句")
        self.geometry("760x500")
        self.transient(app.root)

        self.current_quote: Optional[Dict[str, Any]] = None
        self.last_api_quote = None

        self.build_ui()
        self.after(50, self.next_quote)

    def build_ui(self):
        main = tb.Frame(self, padding=14)
        main.pack(fill=BOTH, expand=True)

        self.quote_label = tb.Label(
            main,
            text="正在获取一句话……",
            font=("Segoe UI", 14, "bold"),
            wraplength=680,
            justify=CENTER
        )
        self.quote_label.pack(anchor=CENTER, fill=X, pady=(20, 16))

        self.source_label = tb.Label(
            main,
            text="—— 请稍候",
            font=("Segoe UI", 10),
            bootstyle="secondary"
        )
        self.source_label.pack(anchor=CENTER)

        row = tb.Frame(main)
        row.pack(fill=X, pady=(24, 8))

        tb.Button(row, text="下一条", bootstyle="primary", command=self.next_quote).pack(side=LEFT, padx=(0, 8))
        tb.Button(row, text="收藏", bootstyle="success", command=self.favorite_current).pack(side=LEFT, padx=(0, 8))
        tb.Button(row, text="记录此刻", bootstyle="danger", command=self.add_custom_quote).pack(side=LEFT, padx=(0, 8))
        tb.Button(row, text="我的记录", command=self.open_custom_quotes).pack(side=LEFT, padx=(0, 8))
        tb.Button(row, text="收藏夹", bootstyle="primary-outline", command=self.open_favorites).pack(side=LEFT)

    def next_quote(self):
        quote = get_jinrishici_quote()

        if not quote:
            self.quote_label.configure(text="获取失败，请检查网络")
            self.source_label.configure(text="")
            return

        self.current_quote = quote

        self.quote_label.configure(text=self.current_quote["text"])
        self.source_label.configure(text=f"—— {self.current_quote['source']}")

    def favorite_current(self):
        if not self.current_quote:
            return

        favorites = self.app.store.state["quotes"]["favorites"]
        if self.current_quote not in favorites:
            favorites.append(self.current_quote)
            self.app.store.save()
            self.app.flash_status("已加入收藏。")

    def add_custom_quote(self):
        dialog = tb.Toplevel(self)
        dialog.title("新增内容")
        dialog.geometry("480x320")
        dialog.transient(self)
        dialog.grab_set()

        main = tb.Frame(dialog, padding=12)
        main.pack(fill=BOTH, expand=True)

        tb.Label(main, text="内容").pack(anchor=W)
        text_box = ScrolledText(main, height=6)
        text_box.pack(fill=BOTH, expand=True, pady=(6, 12))

        tb.Label(main, text="来源").pack(anchor=W)
        source_var = tb.StringVar(value="灵光一现")
        tb.Entry(main, textvariable=source_var).pack(fill=X, pady=(6, 12))

        def save_custom():
            text = text_box.text.get("1.0", END).strip()
            source = source_var.get().strip() or "灵光一现"
            if not text:
                return

            self.app.store.state["quotes"]["all"].append({
                "text": text,
                "source": source,
                "type": "custom",
                "created_at": format_now(),
            })

            self.app.store.save()
            self.app.flash_status("已加入内容库。")
            dialog.destroy()
            self.next_quote()

        tb.Button(main, text="保存", bootstyle="success", command=save_custom).pack(anchor=E)

    def open_favorites(self):
        FavoritesWindow(self.app)

    def open_custom_quotes(self):
        CustomQuotesWindow(self.app)