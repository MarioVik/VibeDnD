"""Read-only character sheet viewer with export and edit buttons."""

import re
import tkinter as tk

from tkinter import ttk, filedialog

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, AlertDialog, SectionedListbox
from gui.sheet_builder import build_character_sheet, _container_contents
from models.character_store import save_character
from paths import characters_dir
from gui.add_inventory_dialog import AddInventoryDialog, ARMOR_AC_ORDER
from models.inventory_service import format_coins, normalize_item_key, remove_item
from models.standard_actions import (
    WEAPON_DATA,
    get_selected_armor_counts,
    get_selected_non_weapon_items,
    get_selected_weapon_counts,
)


class CharacterViewer(ttk.Frame):
    """Full-screen read-only character sheet with navigation and export."""

    def __init__(self, parent, character, save_path, game_data, app):
        super().__init__(parent)
        self.character = character
        self.save_path = save_path
        self.data = game_data
        self.app = app
        self._spell_index = {
            s.get("name", ""): s for s in (self.data.spells if self.data else [])
        }
        self._item_by_norm_name = {
            normalize_item_key(name): item
            for name, item in (
                (self.data.items_by_name or {}).items() if self.data else []
            )
        }
        self._inventory_entries_by_name = {}
        self._selected_inventory_name = ""
        self._tab_dirty = {"general": False, "inventory": False, "spells": False}
        self._build_ui()

    def _build_ui(self):
        # ── Top bar ─────────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=20, pady=(16, 6))

        ttk.Button(
            top,
            text="\u25c0  Back to Menu",
            command=self._on_back,
        ).pack(side=tk.LEFT)

        if self.character.level < 20:
            ttk.Button(
                top,
                text="Level Up",
                command=self._on_level_up,
            ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            top,
            text="Add to inventory",
            command=self._on_add_inventory,
        ).pack(side=tk.LEFT, padx=4)

        # Character name
        ttk.Label(
            top,
            text=self.character.name or "Unnamed",
            font=("Segoe UI", 18, "bold"),
            foreground=COLORS["accent"],
        ).pack(side=tk.LEFT, padx=8)

        # Export buttons (right side)
        ttk.Button(top, text="Export Character", command=self._export_json).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(top, text="Export PDF", command=self._export_pdf).pack(
            side=tk.RIGHT, padx=4
        )

        ttk.Button(
            top,
            text="Respec character",
            command=self._on_edit,
        ).pack(side=tk.RIGHT, padx=8)

        # ── Character tabs ──────────────────────────────────────
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=20, pady=(6, 16))

        self.general_tab = ttk.Frame(self.tabs)
        self.inventory_tab = ttk.Frame(self.tabs)
        self.spells_tab = ttk.Frame(self.tabs)

        self.tabs.add(self.general_tab, text="General")
        self.tabs.add(self.inventory_tab, text="Inventory")
        self.tabs.add(self.spells_tab, text="Spells")
        self._tab_widgets = {
            "general": self.general_tab,
            "inventory": self.inventory_tab,
            "spells": self.spells_tab,
        }
        self._tab_titles = {
            "general": "General",
            "inventory": "Inventory",
            "spells": "Spells",
        }
        self.tabs.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        general_scroll = ScrollableFrame(self.general_tab)
        general_scroll.pack(fill=tk.BOTH, expand=True)
        self._general_parent = general_scroll.inner

        inventory_scroll = ScrollableFrame(self.inventory_tab)
        inventory_scroll.pack(fill=tk.BOTH, expand=True)
        self._inventory_parent = inventory_scroll.inner

        self._build_spells_tab()
        self._refresh_tabs(force=True)

    def _build_spells_tab(self):
        self.spells_tab.columnconfigure(0, weight=0)
        self.spells_tab.columnconfigure(1, weight=1)
        self.spells_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.spells_tab, width=300)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(2, 2))
        left.grid_propagate(False)

        ttk.Label(left, text="Known Spells", style="Heading.TLabel").pack(
            anchor="w", pady=(0, 2)
        )
        self.spells_list = SectionedListbox(left, on_select=self._on_spell_select)
        self.spells_list.pack(fill=tk.BOTH, expand=True)
        self.spells_list.search_entry.configure(style="ViewerCompactSpells.TEntry")

        style = ttk.Style(self)
        style.configure("ViewerCompactSpells.TEntry", padding=(6, 2))

        right = ttk.LabelFrame(self.spells_tab, text="Spell Details")
        right.grid(row=0, column=1, sticky="nsew", pady=(2, 2))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.spell_title = ttk.Label(
            right,
            text="Select a spell",
            style="Subheading.TLabel",
        )
        self.spell_title.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        self.spell_detail_text = tk.Text(
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
        self.spell_detail_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.spell_detail_text.tag_configure(
            "label", font=(FONTS["body"][0], FONTS["body"][1], "bold")
        )

    def _refresh_tabs(self, force: bool = False):
        if force:
            self._tab_dirty = {"general": True, "inventory": True, "spells": True}
            self._apply_tab_labels()

        selected = self._selected_tab_key()
        if selected:
            self._refresh_tab(selected)

    def _apply_tab_labels(self):
        pass

    def _selected_tab_key(self) -> str:
        if not self.winfo_exists() or not self.tabs.winfo_exists():
            return ""
        current = self.tabs.select()
        if current == str(self.general_tab):
            return "general"
        if current == str(self.inventory_tab):
            return "inventory"
        if current == str(self.spells_tab):
            return "spells"
        return ""

    def _refresh_tab(self, key: str):
        if key == "general":
            build_character_sheet(
                self._general_parent,
                self.character,
                self.data,
                on_change=self._on_sheet_changed,
                compact=True,
                include_sections={
                    "header",
                    "combat",
                    "abilities",
                    "saving_throws",
                    "skills",
                    "standard_actions",
                    "species_traits",
                    "class_features",
                    "subclass",
                    "feats",
                },
            )
            self._tab_dirty["general"] = False
            self._apply_tab_labels()
            return

        if key == "inventory":
            build_character_sheet(
                self._inventory_parent,
                self.character,
                self.data,
                on_change=self._on_sheet_changed,
                compact=True,
                include_sections={"wealth"},
            )
            self._render_inventory_split_view()
            self._tab_dirty["inventory"] = False
            self._apply_tab_labels()
            return

        if key == "spells":
            self._refresh_spells_tab()
            self._tab_dirty["spells"] = False
            self._apply_tab_labels()

    def _mark_tabs_dirty(self, include_current: bool = False):
        current = self._selected_tab_key()
        for key in self._tab_dirty.keys():
            if include_current or key != current:
                self._tab_dirty[key] = True
        self._apply_tab_labels()

    def _on_tab_changed(self, _event=None):
        key = self._selected_tab_key()
        if not key:
            return
        if self._tab_dirty.get(key):
            self._refresh_tab(key)

    def _parse_item_qty(self, text: str) -> tuple[str, int]:
        raw = str(text or "").strip()
        parts = raw.split(" ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            return parts[1].strip(), max(1, int(parts[0]))
        return raw, 1

    def _effective_inventory_pools(self):
        c = self.character
        weapon_counts = dict(get_selected_weapon_counts(c))
        armor_counts = dict(get_selected_armor_counts(c))
        inventory_items = list(get_selected_non_weapon_items(c))

        for ent in getattr(c, "custom_inventory", []) or []:
            name = str(ent.get("name", "")).strip()
            if not name:
                continue
            qty = max(1, int(ent.get("qty", 1)))
            category = str(ent.get("category", "Adventuring Gear"))
            key = normalize_item_key(name)
            if category == "Weapons":
                weapon_counts[key] = weapon_counts.get(key, 0) + qty
            elif category == "Armor":
                armor_counts[key] = armor_counts.get(key, 0) + qty
            else:
                inventory_items.append(f"{qty} {name}" if qty > 1 else name)

        removed = {
            normalize_item_key(k): int(v)
            for k, v in (getattr(c, "removed_items", {}) or {}).items()
            if int(v) > 0
        }

        for key, rem in removed.items():
            if key in weapon_counts:
                weapon_counts[key] = max(0, weapon_counts[key] - rem)
                if weapon_counts[key] <= 0:
                    weapon_counts.pop(key, None)
            if key in armor_counts:
                armor_counts[key] = max(0, armor_counts[key] - rem)
                if armor_counts[key] <= 0:
                    armor_counts.pop(key, None)

        inv_map: dict[str, int] = {}
        inv_name: dict[str, str] = {}
        order: list[str] = []
        for line in inventory_items:
            base_name, qty = self._parse_item_qty(line)
            if not base_name:
                continue
            key = normalize_item_key(base_name)
            if key not in inv_map:
                order.append(key)
                inv_name[key] = base_name
            inv_map[key] = inv_map.get(key, 0) + qty

        for key, rem in removed.items():
            if key in inv_map:
                inv_map[key] = max(0, inv_map[key] - rem)

        inv_entries = []
        for key in order:
            qty = inv_map.get(key, 0)
            if qty <= 0:
                continue
            inv_entries.append({"name": inv_name[key], "key": key, "qty": qty})

        return weapon_counts, armor_counts, inv_entries

    # ── Armor proficiency helpers (mirrors sheet_builder logic) ──

    ARMOR_REQUIRED = {
        "padded armor": "light",
        "leather armor": "light",
        "studded leather armor": "light",
        "hide armor": "medium",
        "chain shirt": "medium",
        "scale mail": "medium",
        "breastplate": "medium",
        "half plate armor": "medium",
        "ring mail": "heavy",
        "chain mail": "heavy",
        "splint armor": "heavy",
        "plate armor": "heavy",
        "shield": "shield",
    }

    def _armor_profs(self) -> set[str]:
        out: set[str] = set()
        for p in (self.character.character_class or {}).get("armor_proficiencies", []):
            t = str(p).lower()
            for k in ("shield", "heavy", "medium", "light"):
                if k in t:
                    out.add(k)
        return out

    def _can_equip_armor(self, armor_key: str) -> tuple[bool, str]:
        req = self.ARMOR_REQUIRED.get(armor_key, "light")
        if req in self._armor_profs():
            return True, ""
        label = "Shields" if req == "shield" else f"{req.title()} armor"
        return False, f"{self.character.class_name} is not proficient with {label}."

    def _has_weapon_proficiency(self, weapon_key: str) -> bool:
        cls = self.character.character_class or {}
        profs = [str(p).lower() for p in cls.get("weapon_proficiencies", [])]
        if any(weapon_key in p for p in profs):
            return True
        meta = WEAPON_DATA.get(weapon_key, {})
        cat = meta.get("category", "")
        if cat == "simple" and any("simple" in p for p in profs):
            return True
        if cat == "martial" and any("martial" in p for p in profs):
            return True
        return False

    # ── Inventory split view ────────────────────────────────────

    def _render_inventory_split_view(self):
        split = ttk.LabelFrame(self._inventory_parent, text="Item Details")
        split.pack(fill=tk.BOTH, expand=True, pady=3)
        split.columnconfigure(0, weight=1)
        split.columnconfigure(1, weight=1)
        split.rowconfigure(0, weight=1)

        # ── Left: Treeview with Equip / Item / Qty columns ──
        left = ttk.Frame(split)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=(0, 8))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.inv_tree = ttk.Treeview(
            left,
            columns=("equip", "name", "qty"),
            show="tree headings",
            selectmode="browse",
        )
        self.inv_tree.heading("#0", text="", anchor="w")
        self.inv_tree.heading("equip", text="Equip", anchor="center")
        self.inv_tree.heading("name", text="Item", anchor="w")
        self.inv_tree.heading("qty", text="Qty", anchor="center")

        self.inv_tree.column("#0", width=20, minwidth=20, stretch=False)
        self.inv_tree.column(
            "equip", width=55, minwidth=55, stretch=False, anchor="center"
        )
        self.inv_tree.column("name", width=280, minwidth=120, stretch=True, anchor="w")
        self.inv_tree.column(
            "qty", width=45, minwidth=45, stretch=False, anchor="center"
        )

        tree_scroll = ttk.Scrollbar(
            left, orient=tk.VERTICAL, command=self.inv_tree.yview
        )
        self.inv_tree.configure(yscrollcommand=tree_scroll.set)
        self.inv_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll.grid(row=0, column=1, sticky="ns")

        self.inv_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.inv_tree.bind("<ButtonRelease-1>", self._on_tree_click)

        self._inv_tree_entries: dict[str, dict] = {}

        # ── Right: detail panel ──
        right = ttk.Frame(split)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=(0, 8))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.inventory_detail_title = ttk.Label(
            right, text="Select an item", style="Subheading.TLabel"
        )
        self.inventory_detail_title.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.inventory_detail_text = tk.Text(
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
        self.inventory_detail_text.grid(row=1, column=0, sticky="nsew")

        self.remove_item_btn = ttk.Button(
            right,
            text="Remove item",
            command=self._remove_selected_item,
            state=tk.DISABLED,
        )
        self.remove_item_btn.grid(row=2, column=0, sticky="e", pady=(6, 0))

        self._refresh_inventory_split_items()

    _EQUIP_CHECK = "\u2611"  # ☑
    _EQUIP_UNCHECK = "\u2610"  # ☐

    def _refresh_inventory_split_items(self):
        weapon_counts, armor_counts, inv_entries = self._effective_inventory_pools()
        equipped_weapons = set(self.character.equipped_weapons or [])
        equipped_armor = set(self.character.equipped_armor or [])

        self._inv_tree_entries = {}
        self.inv_tree.delete(*self.inv_tree.get_children())

        # ── Weapons section ──
        weapons_node = self.inv_tree.insert(
            "",
            tk.END,
            text="",
            values=("", "Equipment • Weapons", ""),
            tags=("section",),
        )
        for key in sorted(weapon_counts.keys()):
            qty = weapon_counts[key]
            name = key.title()
            equipped = key in equipped_weapons
            check = self._EQUIP_CHECK if equipped else self._EQUIP_UNCHECK
            iid = self.inv_tree.insert(
                "",
                tk.END,
                text="",
                values=(check, name, str(qty)),
            )
            self._inv_tree_entries[iid] = {
                "name": name,
                "key": key,
                "qty": qty,
                "category": "Weapons",
                "equippable": True,
                "equipped": equipped,
            }

        # ── Armor section ──
        self.inv_tree.insert(
            "",
            tk.END,
            text="",
            values=("", "Equipment • Armor & Shields", ""),
            tags=("section",),
        )
        ac_order_keys = [normalize_item_key(n) for n in ARMOR_AC_ORDER]
        ordered_armor_keys = [k for k in ac_order_keys if k in armor_counts]
        remaining_armor_keys = sorted(
            k for k in armor_counts if k not in set(ac_order_keys)
        )
        for key in ordered_armor_keys + remaining_armor_keys:
            qty = armor_counts[key]
            name = key.title()
            equipped = key in equipped_armor
            check = self._EQUIP_CHECK if equipped else self._EQUIP_UNCHECK
            iid = self.inv_tree.insert(
                "",
                tk.END,
                text="",
                values=(check, name, str(qty)),
            )
            self._inv_tree_entries[iid] = {
                "name": name,
                "key": key,
                "qty": qty,
                "category": "Armor",
                "equippable": True,
                "equipped": equipped,
            }

        # ── Inventory section ──
        if inv_entries:
            self.inv_tree.insert(
                "", tk.END, text="", values=("", "Inventory", ""), tags=("section",)
            )
            for e in inv_entries:
                iid = self.inv_tree.insert(
                    "",
                    tk.END,
                    text="",
                    values=("", e["name"], str(e["qty"])),
                )
                self._inv_tree_entries[iid] = {
                    "name": e["name"],
                    "key": e["key"],
                    "qty": e["qty"],
                    "category": "Inventory",
                    "equippable": False,
                    "equipped": False,
                }
                # Show pack/container sub-items as clickable children
                container = _container_contents(e["name"])
                if container:
                    _, contents = container
                    for sub in contents:
                        sub_name = sub.strip()
                        sub_iid = self.inv_tree.insert(
                            iid,
                            tk.END,
                            text="",
                            values=("", f"  {sub_name}", ""),
                            tags=("subitem",),
                        )
                        self._inv_tree_entries[sub_iid] = {
                            "name": sub_name,
                            "key": normalize_item_key(sub_name),
                            "qty": 1,
                            "category": "Inventory",
                            "equippable": False,
                            "equipped": False,
                            "is_subitem": True,
                            "parent_name": e["name"],
                        }
                    self.inv_tree.item(iid, open=True)

        # Style section header rows and sub-items
        self.inv_tree.tag_configure("section", foreground=COLORS["accent"])
        self.inv_tree.tag_configure("subitem", foreground=COLORS["fg_dim"])

        # Restore selection
        if self._selected_inventory_name:
            for iid, entry in self._inv_tree_entries.items():
                if entry.get("name") == self._selected_inventory_name:
                    self.inv_tree.selection_set(iid)
                    self.inv_tree.see(iid)
                    self._on_inventory_select_entry(entry)
                    return

        # Select first item
        for iid in self.inv_tree.get_children():
            if iid in self._inv_tree_entries:
                self.inv_tree.selection_set(iid)
                self.inv_tree.see(iid)
                self._on_inventory_select_entry(self._inv_tree_entries[iid])
                return

        self._selected_inventory_name = ""
        self.remove_item_btn.configure(state=tk.DISABLED)
        self.inventory_detail_title.configure(text="No items")
        self._set_inventory_detail_text("No inventory items available.")

    def _on_tree_select(self, event=None):
        sel = self.inv_tree.selection()
        if not sel:
            return
        iid = sel[0]
        entry = self._inv_tree_entries.get(iid)
        if not entry:
            return
        self._on_inventory_select_entry(entry)

    def _on_tree_click(self, event=None):
        region = self.inv_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.inv_tree.identify_column(event.x)
        if col != "#1":  # Equip column
            return
        iid = self.inv_tree.identify_row(event.y)
        if not iid:
            return
        entry = self._inv_tree_entries.get(iid)
        if not entry or not entry.get("equippable"):
            return
        self._toggle_equip(iid, entry)

    def _toggle_equip(self, iid: str, entry: dict):
        key = entry["key"]
        cat = entry["category"]
        currently_equipped = entry.get("equipped", False)
        new_state = not currently_equipped

        if cat == "Weapons":
            equipped = list(self.character.equipped_weapons or [])
            if new_state:
                if not self._has_weapon_proficiency(key):
                    AlertDialog(
                        self.winfo_toplevel(),
                        "Weapon Proficiency",
                        f"You are not proficient with {key.title()}. "
                        "You can still equip it, but your proficiency bonus "
                        "will not be added to attack rolls.",
                    )
                if key not in equipped:
                    equipped.append(key)
            else:
                equipped = [w for w in equipped if w != key]
            self.character.equipped_weapons = sorted(equipped)

        elif cat == "Armor":
            equipped = list(self.character.equipped_armor or [])
            if new_state:
                ok, reason = self._can_equip_armor(key)
                if not ok:
                    AlertDialog(
                        self.winfo_toplevel(),
                        "Armor Training Required",
                        reason,
                    )
                    return
                if key != "shield":
                    equipped = [a for a in equipped if a == "shield"]
                if key not in equipped:
                    equipped.append(key)
            else:
                equipped = [a for a in equipped if a != key]
            self.character.equipped_armor = self._normalize_equipped_armor(
                set(equipped)
            )

        self._on_sheet_changed()

        # Sync all equip visuals to match actual character state
        current_weapons = set(self.character.equipped_weapons or [])
        current_armor = set(self.character.equipped_armor or [])
        for tree_iid, tree_entry in self._inv_tree_entries.items():
            if not tree_entry.get("equippable"):
                continue
            ekey = tree_entry["key"]
            ecat = tree_entry["category"]
            if ecat == "Weapons":
                is_eq = ekey in current_weapons
            elif ecat == "Armor":
                is_eq = ekey in current_armor
            else:
                continue
            tree_entry["equipped"] = is_eq
            self.inv_tree.set(
                tree_iid,
                "equip",
                self._EQUIP_CHECK if is_eq else self._EQUIP_UNCHECK,
            )

        # Update detail panel for selected item
        self._on_inventory_select_entry(entry)

    def _on_inventory_select_entry(self, entry: dict):
        self._selected_inventory_name = entry.get("name", "")
        is_subitem = entry.get("is_subitem", False)
        self.remove_item_btn.configure(state=tk.DISABLED if is_subitem else tk.NORMAL)
        self._show_inventory_details(entry)

    def _find_item_record(self, entry: dict) -> dict | None:
        key = entry.get("key", "")
        for ent in getattr(self.character, "custom_inventory", []) or []:
            if normalize_item_key(ent.get("name", "")) != key:
                continue
            item_id = str(ent.get("item_id", ""))
            if (
                item_id
                and self.data
                and item_id in getattr(self.data, "items_by_id", {})
            ):
                return self.data.items_by_id[item_id]

        raw_name = str(entry.get("name", "")).strip()
        variants = {key, normalize_item_key(raw_name)}

        no_paren = re.sub(r"\s*\([^)]*\)", "", raw_name).strip()
        if no_paren:
            variants.add(normalize_item_key(no_paren))

        no_comma = raw_name.replace(",", " ")
        if no_comma:
            variants.add(normalize_item_key(no_comma))

        for var in list(variants):
            if var.endswith("s") and len(var) > 3:
                variants.add(var[:-1])

        for var in variants:
            if var in self._item_by_norm_name:
                return self._item_by_norm_name[var]

        for var in sorted(variants, key=len, reverse=True):
            if len(var) < 4:
                continue
            for item_key, item in self._item_by_norm_name.items():
                if var in item_key or item_key in var:
                    return item

        return None

    def _on_inventory_select(self, label: str):
        entry = self._inventory_entries_by_name.get(label)
        if not entry:
            self.remove_item_btn.configure(state=tk.DISABLED)
            return
        self._on_inventory_select_entry(entry)

    def _show_inventory_details(self, entry: dict):
        self.inventory_detail_title.configure(text=entry.get("name", "Item"))
        record = self._find_item_record(entry)

        lines = []
        if entry.get("is_subitem"):
            lines.append(f"Part of: {entry.get('parent_name', 'Unknown')}")
        else:
            lines.append(f"Category: {entry.get('category', 'Unknown')}")
            lines.append(f"Quantity: {entry.get('qty', 1)}")
        if entry.get("equippable"):
            lines.append(f"Equipped: {'Yes' if entry.get('equipped') else 'No'}")
        if record:
            item_type = str(record.get("type", "")).strip() or "Item"
            lines.append(f"Type: {item_type}")
            if record.get("category") == "Magic Items":
                lines.append(f"Rarity: {record.get('rarity', 'Unknown')}")
            cost_cp = int(record.get("cost_cp", 0))
            if cost_cp > 0:
                lines.append(f"Cost: {format_coins(cost_cp, compact=True)}")
            else:
                lines.append("Cost: Varies/Unavailable")
            lines.append("")
            desc = record.get("full_description") or record.get("description") or ""
            desc = desc.strip()
            cat = str(record.get("category", "")).lower()
            if desc and cat in ("weapons", "armor"):
                for part in desc.split(";"):
                    part = part.strip()
                    if part:
                        lines.append(part)
            else:
                lines.append(
                    desc.replace("; Function:", "\nFunction:")
                    if desc
                    else "No description available."
                )
            sub = record.get("sub_items") or []
            if sub:
                lines.append("")
                lines.append("Contains:")
                lines.extend([f"- {s}" for s in sub])
        else:
            weapon_meta = WEAPON_DATA.get(entry.get("key", ""), {})
            container = _container_contents(entry.get("name", ""))
            lines.append("")
            if weapon_meta:
                dmg = weapon_meta.get("damage", "-")
                props = ", ".join(weapon_meta.get("properties", []) or []) or "None"
                mastery = weapon_meta.get("mastery") or "-"
                lines.append(f"Damage: {dmg}")
                lines.append(f"Properties: {props}")
                lines.append(f"Mastery: {mastery}")
            elif container:
                _, contents = container
                lines.append("Contains:")
                lines.extend([f"- {c}" for c in contents])
            else:
                lines.append(
                    "No description available for this item in the current data set."
                )

        self._set_inventory_detail_text("\n".join(lines))

    def _set_inventory_detail_text(self, text: str):
        self.inventory_detail_text.configure(state=tk.NORMAL)
        self.inventory_detail_text.delete("1.0", tk.END)
        self.inventory_detail_text.insert("1.0", text)
        self.inventory_detail_text.configure(state=tk.DISABLED)

    def _normalize_equipped_armor(self, keys: set[str]) -> list[str]:
        has_shield = "shield" in keys
        body = sorted(k for k in keys if k != "shield")
        out = []
        if has_shield:
            out.append("shield")
        out.extend(body[:1])
        return out

    def _remove_selected_item(self):
        sel = self.inv_tree.selection()
        if not sel:
            return
        iid = sel[0]
        entry = self._inv_tree_entries.get(iid)
        if not entry:
            return

        ok, msg = remove_item(self.character, entry.get("name", ""), qty=1)
        if not ok:
            AlertDialog(self.winfo_toplevel(), "Remove Item", msg)
            return

        weapon_counts, armor_counts, _ = self._effective_inventory_pools()
        self.character.equipped_weapons = [
            w for w in (self.character.equipped_weapons or []) if w in weapon_counts
        ]
        self.character.equipped_armor = self._normalize_equipped_armor(
            {a for a in (self.character.equipped_armor or []) if a in armor_counts}
        )

        self._on_sheet_changed()
        self._refresh_tab("inventory")

    def _refresh_spells_tab(self):
        cantrips = list(dict.fromkeys(self.character.selected_cantrips or []))
        spells = list(dict.fromkeys(self.character.selected_spells or []))

        sections: list[tuple[str, list[str]]] = []
        if cantrips:
            sections.append(("Cantrips", sorted(cantrips)))

        by_level: dict[int, list[str]] = {}
        unknown_level: list[str] = []
        for name in spells:
            spell = self._spell_index.get(name)
            if spell is None:
                unknown_level.append(name)
                continue
            lvl = int(spell.get("level", 1))
            by_level.setdefault(lvl, []).append(name)

        for lvl in sorted(by_level.keys()):
            sections.append((f"Level {lvl}", sorted(by_level[lvl])))
        if unknown_level:
            sections.append(("Other", sorted(unknown_level)))

        self.spells_list.set_sectioned_items(sections)

        if sections and sections[0][1]:
            self.spells_list.select_item(sections[0][1][0])
            self._show_spell_details(sections[0][1][0])
        else:
            self._show_spell_details(None)

    def _on_spell_select(self, spell_name: str):
        self._show_spell_details(spell_name)

    def _show_spell_details(self, spell_name: str | None):
        if not spell_name:
            self.spell_title.configure(text="No spells known")
            self._set_spell_detail_text(
                "This character has no selected cantrips or spells."
            )
            return

        spell = self._spell_index.get(spell_name, {})
        if not spell:
            self.spell_title.configure(text=spell_name)
            self._set_spell_detail_text("No spell data found for this entry.")
            return

        level = spell.get("level", 0)
        level_text = "Cantrip" if level == 0 else f"Level {level}"
        school = spell.get("school", "Unknown")

        comps = spell.get("components", {}) or {}
        comp_text = []
        for k in ["V", "S", "M"]:
            val = comps.get(k)
            if not val:
                continue
            if k == "M" and isinstance(val, str):
                comp_text.append(f"M ({val})")
            else:
                comp_text.append(k)
        components = ", ".join(comp_text) if comp_text else "None"

        self.spell_title.configure(text=spell.get("name", spell_name))
        body = [
            f"Level: {level_text}",
            f"School: {school}",
            f"Casting Time: {spell.get('casting_time', 'Unknown')}",
            f"Range: {spell.get('range', 'Unknown')}",
            f"Duration: {spell.get('duration', 'Unknown')}",
            f"Components: {components}",
        ]
        source = spell.get("source")
        if source:
            body.append(f"Source: {source}")
        body.append("")
        body.append(spell.get("description", "No description available."))

        higher = (spell.get("higher_levels") or "").strip()
        if higher:
            body.extend(["", f"At Higher Levels: {higher}"])

        self._set_spell_detail_text("\n".join(body))

    def _set_spell_detail_text(self, text: str):
        if (
            not getattr(self, "spell_detail_text", None)
            or not self.spell_detail_text.winfo_exists()
        ):
            return
        label_prefixes = {
            "Level",
            "School",
            "Casting Time",
            "Range",
            "Duration",
            "Components",
            "Source",
            "At Higher Levels",
        }

        self.spell_detail_text.configure(state=tk.NORMAL)
        self.spell_detail_text.delete("1.0", tk.END)

        for raw_line in text.splitlines():
            if ":" in raw_line:
                key, rest = raw_line.split(":", 1)
                if key in label_prefixes:
                    self.spell_detail_text.insert(tk.END, f"{key}:", "label")
                    self.spell_detail_text.insert(tk.END, f"{rest}\n")
                    continue
            self.spell_detail_text.insert(tk.END, f"{raw_line}\n")

        self.spell_detail_text.configure(state=tk.DISABLED)

    def _on_sheet_changed(self):
        if self.save_path:
            save_character(
                self.character, characters_dir(), existing_filename=self.save_path
            )
        # Avoid rebuilding the active tab during interaction; refresh it only
        # when revisiting to prevent visible flicker.
        self._mark_tabs_dirty(include_current=False)

    # ── Navigation ──────────────────────────────────────────────

    def _on_back(self):
        self.app.show_home()

    def _on_edit(self):
        self.app.show_wizard(self.character, self.save_path)

    def _on_add_inventory(self):
        AddInventoryDialog(
            self,
            self.character,
            self.data,
            on_changed=lambda: (
                self._on_sheet_changed(),
                self._refresh_tabs(force=True),
            ),
        )

    def _on_level_up(self):
        from gui.level_up_wizard import LevelUpWizard

        def on_complete():
            # Save and refresh
            save_character(
                self.character, characters_dir(), existing_filename=self.save_path
            )
            self.app.show_viewer(self.character, self.save_path)

        LevelUpWizard(self, self.character, self.data, on_complete=on_complete)

    # ── Exports (same pattern as SummaryStep) ───────────────────

    def _export_json(self):
        from models.character_store import character_to_save_dict
        import json

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.character.name}.json",
        )
        if path:
            data = character_to_save_dict(self.character)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            AlertDialog(self.winfo_toplevel(), "Export", f"Character saved to {path}")

    def _export_pdf(self):
        from export.pdf_export import export_pdf

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{self.character.name}.pdf",
        )
        if path:
            try:
                export_pdf(self.character, path)
                AlertDialog(
                    self.winfo_toplevel(),
                    "Export",
                    f"PDF character sheet saved to {path}",
                )
            except Exception as e:
                AlertDialog(
                    self.winfo_toplevel(),
                    "Export Error",
                    f"Failed to generate PDF:\n{e}",
                )
