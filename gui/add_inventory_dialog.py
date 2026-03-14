"""Dialog for browsing the item database and adding inventory entries."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui.theme import COLORS, FONTS
from gui.widgets import SectionedListbox, AlertDialog
from models.inventory_service import (
    add_item,
    cp_to_coins,
    current_wealth_cp,
)


CATEGORY_ORDER = [
    "Adventuring Gear",
    "Armor",
    "Weapons",
    "Mounts and Vehicles",
    "Poisons",
    "Tools",
    "Magic Items",
]


class AddInventoryDialog(tk.Toplevel):
    def __init__(self, parent, character, game_data, on_changed=None):
        super().__init__(parent)
        self.character = character
        self.data = game_data
        self.on_changed = on_changed

        style = ttk.Style(self)
        style.configure(
            "WealthValue.TLabel",
            font=FONTS["subheading"],
            foreground=COLORS["fg_bright"],
        )

        self.title("Add to Inventory")
        self.geometry("980x620")
        self.transient(parent)
        self.grab_set()

        self.selected_item: dict | None = None
        self.items_by_name = {i.get("name", ""): i for i in self.data.items}
        self.category_filter_var = tk.StringVar(value="Any")
        self.min_cost_var = tk.StringVar(value="")
        self.max_cost_var = tk.StringVar(value="")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Item Browser", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.wealth_label = ttk.Label(top, text="", style="WealthValue.TLabel")
        self.wealth_label.grid(row=0, column=1, sticky="e", padx=(0, 12))

        filters = ttk.Frame(self)
        filters.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        ttk.Label(filters, text="Category:").pack(side=tk.LEFT)

        self.type_combo = ttk.Combobox(
            filters,
            textvariable=self.category_filter_var,
            values=["Any"] + CATEGORY_ORDER,
            state="readonly",
            width=24,
        )
        self.type_combo.pack(side=tk.LEFT, padx=(4, 12))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_list())

        ttk.Label(filters, text="Min GP:").pack(side=tk.LEFT)
        ttk.Entry(filters, textvariable=self.min_cost_var, width=8).pack(
            side=tk.LEFT, padx=(4, 8)
        )
        ttk.Label(filters, text="Max GP:").pack(side=tk.LEFT)
        ttk.Entry(filters, textvariable=self.max_cost_var, width=8).pack(
            side=tk.LEFT, padx=(4, 8)
        )
        ttk.Button(filters, text="Reset", command=self._reset_filters).pack(
            side=tk.LEFT
        )

        self.min_cost_var.trace_add("write", lambda *_: self._populate_list())
        self.max_cost_var.trace_add("write", lambda *_: self._populate_list())

        body = ttk.Frame(self)
        body.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, width=260)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 6))
        left.grid_propagate(False)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.item_list = SectionedListbox(left, on_select=self._on_select_item)
        self.item_list.grid(row=0, column=0, sticky="nsew")

        right = ttk.LabelFrame(body, text="Item Details")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.detail_title = ttk.Label(
            right, text="Select an item", style="Subheading.TLabel"
        )
        self.detail_title.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        self.detail_text = tk.Text(
            right,
            wrap=tk.WORD,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            state=tk.DISABLED,
        )
        self.detail_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        actions = ttk.Frame(right)
        actions.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        ttk.Label(actions, text="Qty:").pack(side=tk.LEFT)
        self.qty_var = tk.IntVar(value=1)
        ttk.Spinbox(actions, from_=1, to=999, textvariable=self.qty_var, width=5).pack(
            side=tk.LEFT, padx=(4, 10)
        )
        ttk.Button(actions, text="Add Free", command=self._add_free).pack(side=tk.LEFT)
        ttk.Button(actions, text="Buy", command=self._buy).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Close", command=self.destroy).pack(side=tk.RIGHT)

        log = ttk.LabelFrame(self, text="Recent Transactions")
        log.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.log_text = tk.Text(
            log,
            height=7,
            wrap=tk.WORD,
            bg=COLORS["bg_light"],
            fg=COLORS["fg_dim"],
            font=FONTS["body_small"],
            borderwidth=0,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.X, padx=8, pady=6)

        self._populate_list()
        self._refresh_meta()

    def _reset_filters(self):
        self.category_filter_var.set("Any")
        self.min_cost_var.set("")
        self.max_cost_var.set("")
        self._populate_list()

    def _item_type(self, item: dict) -> str:
        t = str(item.get("type", "")).strip()
        return t or "Item"

    def _filtered_category_items(self, category: str) -> list[dict]:
        items = list(self.data.items_by_category.get(category, []))
        selected_category = self.category_filter_var.get().strip() or "Any"
        min_gp_text = self.min_cost_var.get().strip()
        max_gp_text = self.max_cost_var.get().strip()

        try:
            min_gp = float(min_gp_text) if min_gp_text else None
        except ValueError:
            min_gp = None
        try:
            max_gp = float(max_gp_text) if max_gp_text else None
        except ValueError:
            max_gp = None

        out = []
        for item in items:
            if selected_category != "Any" and item.get("category") != selected_category:
                continue
            gp = int(item.get("cost_cp", 0)) / 100.0
            if min_gp is not None and gp < min_gp:
                continue
            if max_gp is not None and gp > max_gp:
                continue
            out.append(item)
        return out

    def _populate_list(self):
        sections = []
        for category in CATEGORY_ORDER:
            items = sorted(
                self._filtered_category_items(category), key=lambda i: i.get("name", "")
            )
            names = [i.get("name", "") for i in items if i.get("name")]
            if names:
                sections.append((category, names))
        self.item_list.set_sectioned_items(sections)

    def _refresh_meta(self):
        gp, sp, cp = cp_to_coins(current_wealth_cp(self.character))
        self.wealth_label.configure(text=f"Wealth: {gp} gp, {sp} sp, {cp} cp")

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        txs = getattr(self.character, "inventory_transactions", []) or []
        if not txs:
            self.log_text.insert("1.0", "No transactions yet.")
        else:
            lines = []
            for tx in txs[:10]:
                mode = tx.get("mode", "free")
                sign = "-" if mode == "buy" else "+"
                cost = int(tx.get("total_cost_cp", 0))
                c_gp, c_sp, c_cp = cp_to_coins(cost)
                cost_text = f"{c_gp} gp {c_sp} sp {c_cp} cp"
                lines.append(
                    f"[{tx.get('timestamp', '')}] {mode.upper()} x{tx.get('qty', 1)} {tx.get('item', 'Item')} ({sign}{cost_text})"
                )
            self.log_text.insert("1.0", "\n".join(lines))
        self.log_text.configure(state=tk.DISABLED)

    def _on_select_item(self, name: str):
        item = self.items_by_name.get(name)
        self.selected_item = item
        if not item:
            return
        self.detail_title.configure(text=item.get("name", "Item"))

        cost_cp = int(item.get("cost_cp", 0))
        c_gp, c_sp, c_cp = cp_to_coins(cost_cp)
        cost_line = (
            f"Cost: {c_gp} gp, {c_sp} sp, {c_cp} cp"
            if cost_cp > 0
            else "Cost: Varies/Unavailable"
        )
        body = [
            f"Category: {item.get('category', 'Unknown')}",
            f"Type: {self._item_type(item)}",
            cost_line,
            "",
            item.get("full_description")
            or item.get("description", "No description available."),
        ]
        sub = item.get("sub_items") or []
        if sub:
            body.append("\nContains:")
            body.extend([f"- {s}" for s in sub])

        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", "\n".join(body))
        self.detail_text.configure(state=tk.DISABLED)

    def _add(self, mode: str):
        if not self.selected_item:
            AlertDialog(self, "Add to Inventory", "Select an item first.")
            return
        qty = max(1, int(self.qty_var.get() or 1))
        ok, msg = add_item(self.character, self.selected_item, qty, mode)
        if not ok:
            AlertDialog(self, "Add to Inventory", msg)
            return
        if callable(self.on_changed):
            self.on_changed()
        self._refresh_meta()

    def _add_free(self):
        self._add("free")

    def _buy(self):
        self._add("buy")
