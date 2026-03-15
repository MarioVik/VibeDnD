"""Dialog for browsing the item database and adding inventory entries."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui.theme import COLORS, FONTS
from gui.widgets import (
    SectionedListbox,
    AlertDialog,
    configure_modal_dialog,
    center_dialog_over_parent,
)
from models.inventory_service import (
    add_item,
    cp_to_coins,
    current_wealth_cp,
    format_coins,
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

MAGIC_RARITY_ORDER = [
    "Common",
    "Uncommon",
    "Rare",
    "Very Rare",
    "Legendary",
    "Artifact",
    "Unknown",
]

ARMOR_SUBCATEGORY_ORDER = ["Light", "Medium", "Heavy", "Shields", "Other"]
WEAPON_SUBCATEGORY_ORDER = [
    "Simple Melee",
    "Simple Ranged",
    "Martial Melee",
    "Martial Ranged",
    "Other",
]

ADVENTURING_GEAR_SUBCATEGORY_ORDER = ["Packs", "Other"]

# Ordered by AC value (ascending).
LIGHT_ARMOR_ORDER = [
    "Padded Armor",
    "Leather Armor",
    "Studded Leather Armor",
]
MEDIUM_ARMOR_ORDER = [
    "Hide Armor",
    "Chain Shirt",
    "Scale Mail",
    "Breastplate",
    "Half Plate Armor",
]
HEAVY_ARMOR_ORDER = [
    "Ring Mail",
    "Chain Mail",
    "Splint Armor",
    "Plate Armor",
]
LIGHT_ARMOR_NAMES = set(LIGHT_ARMOR_ORDER)
MEDIUM_ARMOR_NAMES = set(MEDIUM_ARMOR_ORDER)
HEAVY_ARMOR_NAMES = set(HEAVY_ARMOR_ORDER)

ARMOR_AC_ORDER = LIGHT_ARMOR_ORDER + MEDIUM_ARMOR_ORDER + HEAVY_ARMOR_ORDER + ["Shield"]

SIMPLE_MELEE_WEAPONS = {
    "Club",
    "Dagger",
    "Greatclub",
    "Handaxe",
    "Javelin",
    "Light Hammer",
    "Mace",
    "Quarterstaff",
    "Sickle",
    "Spear",
}
SIMPLE_RANGED_WEAPONS = {
    "Dart",
    "Light Crossbow",
    "Shortbow",
    "Sling",
    "Arrows",
    "Bolts",
    "Bullets, Firearm",
    "Bullets, Sling",
    "Needles",
}
MARTIAL_MELEE_WEAPONS = {
    "Battleaxe",
    "Flail",
    "Glaive",
    "Greataxe",
    "Greatsword",
    "Halberd",
    "Lance",
    "Longsword",
    "Maul",
    "Morningstar",
    "Pike",
    "Rapier",
    "Scimitar",
    "Shortsword",
    "Trident",
    "Warhammer",
    "War Pick",
    "Whip",
}
MARTIAL_RANGED_WEAPONS = {
    "Blowgun",
    "Hand Crossbow",
    "Heavy Crossbow",
    "Longbow",
    "Musket",
    "Pistol",
}


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
        self.configure(bg=COLORS["bg"])
        configure_modal_dialog(self, parent)
        center_dialog_over_parent(self, parent)

        self.selected_item: dict | None = None
        self.items_by_name = {i.get("name", ""): i for i in self.data.items}
        self.category_filter_var = tk.StringVar(value="Any")
        self.min_cost_var = tk.StringVar(value="")
        self.max_cost_var = tk.StringVar(value="")
        self.include_magic_var = tk.BooleanVar(value=False)

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
        ttk.Checkbutton(
            filters,
            text="Include magic items",
            variable=self.include_magic_var,
            command=self._populate_list,
        ).pack(side=tk.LEFT, padx=(12, 0))

        ttk.Button(filters, text="Reset", width=7, command=self._reset_filters).pack(
            side=tk.LEFT, padx=(8, 0)
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
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
            spacing1=2,
            spacing3=2,
            padx=10,
            pady=8,
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
            height=5,
            wrap=tk.WORD,
            bg=COLORS["bg_light"],
            fg=COLORS["fg_dim"],
            font=FONTS["body_small"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.X, padx=8, pady=6)

        self._populate_list()
        self._refresh_meta()

    def _reset_filters(self):
        self.category_filter_var.set("Any")
        self.min_cost_var.set("")
        self.max_cost_var.set("")
        self.include_magic_var.set(False)
        self._populate_list()

    def _item_type(self, item: dict) -> str:
        t = str(item.get("type", "")).strip()
        return t or "Item"

    def _filtered_category_items(self, category: str) -> list[dict]:
        if category == "Magic Items" and not self.include_magic_var.get():
            return []

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
            if category == "Magic Items":
                by_rarity: dict[str, list[str]] = {}
                for item in items:
                    name = item.get("name", "")
                    if not name:
                        continue
                    rarity = str(item.get("rarity", "")).strip() or "Unknown"
                    by_rarity.setdefault(rarity, []).append(name)

                for rarity in MAGIC_RARITY_ORDER:
                    names = sorted(by_rarity.get(rarity, []))
                    if names:
                        sections.append((f"Magic Items • {rarity}", names))
            elif category == "Adventuring Gear":
                by_sub: dict[str, list[str]] = {}
                for item in items:
                    name = item.get("name", "")
                    if not name:
                        continue
                    by_sub.setdefault(
                        self._adventuring_gear_subcategory(item), []
                    ).append(name)
                for sub in ADVENTURING_GEAR_SUBCATEGORY_ORDER:
                    names = sorted(by_sub.get(sub, []))
                    if not names:
                        continue
                    if sub == "Other":
                        sections.append(("Adventuring Gear", names))
                    else:
                        sections.append((f"Adventuring Gear • {sub}", names))
            elif category == "Armor":
                by_sub: dict[str, list[str]] = {}
                item_names_in_data = {item.get("name", "") for item in items}
                for item in items:
                    name = item.get("name", "")
                    if not name:
                        continue
                    by_sub.setdefault(self._armor_subcategory(name), []).append(name)
                for sub in ARMOR_SUBCATEGORY_ORDER:
                    sub_names = by_sub.get(sub, [])
                    if not sub_names:
                        continue
                    sub_set = set(sub_names)
                    ordered = [n for n in ARMOR_AC_ORDER if n in sub_set]
                    remaining = [n for n in sub_names if n not in set(ordered)]
                    names = ordered + sorted(remaining)
                    if names:
                        sections.append((f"Armor • {sub}", names))
            elif category == "Weapons":
                by_sub: dict[str, list[str]] = {}
                for item in items:
                    name = item.get("name", "")
                    if not name:
                        continue
                    by_sub.setdefault(self._weapon_subcategory(name), []).append(name)
                for sub in WEAPON_SUBCATEGORY_ORDER:
                    names = sorted(by_sub.get(sub, []))
                    if names:
                        sections.append((f"Weapons • {sub}", names))
            else:
                names = [i.get("name", "") for i in items if i.get("name")]
                if names:
                    sections.append((category, names))
        self.item_list.set_sectioned_items(sections)

    def _adventuring_gear_subcategory(self, item: dict) -> str:
        # Only classify true bundled gear (items with listed sub-items) as packs.
        if item.get("sub_items"):
            return "Packs"
        return "Other"

    def _armor_subcategory(self, name: str) -> str:
        if name == "Shield":
            return "Shields"
        if name in LIGHT_ARMOR_NAMES:
            return "Light"
        if name in MEDIUM_ARMOR_NAMES:
            return "Medium"
        if name in HEAVY_ARMOR_NAMES:
            return "Heavy"
        return "Other"

    def _weapon_subcategory(self, name: str) -> str:
        if name in SIMPLE_MELEE_WEAPONS:
            return "Simple Melee"
        if name in SIMPLE_RANGED_WEAPONS:
            return "Simple Ranged"
        if name in MARTIAL_MELEE_WEAPONS:
            return "Martial Melee"
        if name in MARTIAL_RANGED_WEAPONS:
            return "Martial Ranged"
        return "Other"

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
                cost_text = format_coins(cost, compact=True)
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
        cost_line = (
            f"Cost: {format_coins(cost_cp, compact=True)}"
            if cost_cp > 0
            else "Cost: Varies/Unavailable"
        )
        body = [
            f"Category: {item.get('category', 'Unknown')}",
            f"Type: {self._item_type(item)}",
            (
                f"Rarity: {item.get('rarity', 'Unknown')}"
                if item.get("category") == "Magic Items"
                else ""
            ),
            cost_line,
            "",
        ]
        desc = item.get("full_description") or item.get(
            "description", "No description available."
        )
        cat = str(item.get("category", "")).lower()
        if desc and cat in ("weapons", "armor"):
            for part in desc.split(";"):
                part = part.strip()
                if part:
                    body.append(part)
        else:
            body.append(desc.replace("; Function:", "\nFunction:"))
        body = [line for line in body if line != ""]
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
