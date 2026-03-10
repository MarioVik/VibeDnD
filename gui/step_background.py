"""Step 3: Background selection."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import SectionedListbox, ScrollableFrame, WrappingLabel
from gui.theme import COLORS, FONTS
from gui.source_config import SECTION_ORDER, group_by_category, save_settings


class BackgroundStep(WizardStep):
    tab_title = "Background"

    def build_ui(self):
        self._edit_initialized = False
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Left: background list with source toggles
        left = ttk.Frame(self.frame, width=220)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_propagate(False)

        ttk.Label(left, text="Choose Background", style="Heading.TLabel").pack(anchor="w", pady=(0, 4))

        # Source filter toggles
        self.toggle_frame = ttk.Frame(left)
        self.toggle_frame.pack(fill=tk.X, pady=(0, 4))
        self.toggle_vars: dict[str, tk.BooleanVar] = {}
        self._build_toggles()

        self.bg_list = SectionedListbox(left, on_select=self._on_select)
        self.bg_list.pack(fill=tk.BOTH, expand=True)

        # Right: detail
        right = ScrollableFrame(self.frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.detail = right.inner

        self.detail_name = ttk.Label(self.detail, text="Select a background", style="Heading.TLabel")
        self.detail_name.pack(anchor="w", pady=(0, 4))

        self.detail_source = ttk.Label(self.detail, text="", style="Dim.TLabel")
        self.detail_source.pack(anchor="w")

        self.detail_desc = WrappingLabel(self.detail, text="")
        self.detail_desc.pack(fill=tk.X, anchor="w", pady=(8, 0))

        ttk.Separator(self.detail, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        self.info_frame = ttk.Frame(self.detail)
        self.info_frame.pack(fill=tk.X)

        # Ability bonus assignment
        self.bonus_frame = ttk.LabelFrame(self.detail, text="Ability Score Bonuses")
        self.bonus_frame.pack(fill=tk.X, pady=(8, 0))

        self._populate_list()

    def on_enter(self):
        """Pre-select background and bonus assignments when editing."""
        if not self._edit_initialized and self.character.background:
            self._edit_initialized = True
            name = self.character.background.get("name", "")
            # Snapshot bonus settings (_on_select will reset them)
            saved_mode = self.character.ability_bonus_mode
            saved_bonuses = dict(self.character.ability_scores.bonuses)
            # Select in list and populate detail panel
            self.bg_list.select_item(name)
            self._on_select(name)
            # Restore bonus mode and assignments
            if hasattr(self, 'bonus_mode'):
                self.bonus_mode.set(saved_mode)
                self._update_bonus_ui()
                if saved_mode == "2/1":
                    for ab, val in saved_bonuses.items():
                        if val == 2 and "+2" in self.bonus_combos:
                            self.bonus_combos["+2"].set(ab)
                        elif val == 1 and "+1" in self.bonus_combos:
                            self.bonus_combos["+1"].set(ab)

    def _build_toggles(self):
        """Build source filter checkboxes."""
        for w in self.toggle_frame.winfo_children():
            w.destroy()
        self.toggle_vars.clear()

        filters = self.data.source_filters.get("backgrounds", {})
        sections = SECTION_ORDER["backgrounds"]

        for cat in sections:
            var = tk.BooleanVar(value=filters.get(cat, True))
            cb = ttk.Checkbutton(self.toggle_frame, text=cat, variable=var,
                                 command=self._on_toggle_change)
            cb.pack(side=tk.LEFT, padx=(0, 6))
            self.toggle_vars[cat] = var

    def _on_toggle_change(self):
        """Update filters and rebuild list when a toggle changes."""
        filters = {cat: var.get() for cat, var in self.toggle_vars.items()}
        self.data.source_filters["backgrounds"] = filters
        save_settings(self.data.source_filters)
        self._populate_list()

    def _populate_list(self):
        filters = self.data.source_filters.get("backgrounds", {})
        enabled = {cat for cat, on in filters.items() if on}

        grouped = group_by_category(self.data.backgrounds, "backgrounds")
        sections = [(cat, [b["name"] for b in items])
                     for cat, items in grouped if cat in enabled]
        self.bg_list.set_sectioned_items(sections)

    def _on_select(self, name: str):
        bg = self.data.backgrounds_by_name.get(name)
        if not bg:
            return

        self.character.background = bg
        self.detail_name.configure(text=bg["name"])
        self.detail_source.configure(text=f"Source: {bg.get('source', 'Unknown')}")
        self.detail_desc.configure(text=bg.get("description", ""))

        # Info section
        for w in self.info_frame.winfo_children():
            w.destroy()

        info = [
            ("Feat", bg.get("feat", "None")),
            ("Skills", ", ".join(bg.get("skill_proficiencies", []))),
            ("Tool", bg.get("tool_proficiency", "None")),
        ]

        equip = bg.get("equipment", [])
        if equip:
            equip_text = " / ".join(f"({e['option']}) {e['items']}" for e in equip)
            info.append(("Equipment", equip_text))

        for label, value in info:
            row = ttk.Frame(self.info_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"{label}:", foreground=COLORS["accent"],
                      font=FONTS["body"], width=12, anchor="e").pack(side=tk.LEFT)
            WrappingLabel(row, text=f"  {value}").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # Ability bonus assignment
        for w in self.bonus_frame.winfo_children():
            w.destroy()

        abilities = bg.get("ability_scores", [])
        if abilities:
            ttk.Label(self.bonus_frame,
                      text=f"Distribute bonuses among: {', '.join(abilities)}",
                      style="Dim.TLabel").pack(anchor="w", padx=4, pady=(4, 2))

            # Mode selection
            mode_frame = ttk.Frame(self.bonus_frame)
            mode_frame.pack(fill=tk.X, padx=4)
            self.bonus_mode = tk.StringVar(value="2/1")
            ttk.Radiobutton(mode_frame, text="+2 / +1", variable=self.bonus_mode,
                            value="2/1", command=self._update_bonus_ui).pack(side=tk.LEFT, padx=8)
            ttk.Radiobutton(mode_frame, text="+1 / +1 / +1", variable=self.bonus_mode,
                            value="1/1/1", command=self._update_bonus_ui).pack(side=tk.LEFT, padx=8)

            # Assignment combos
            self.assign_frame = ttk.Frame(self.bonus_frame)
            self.assign_frame.pack(fill=tk.X, padx=4, pady=4)
            self.bonus_combos = {}
            self.current_abilities = abilities

            self._update_bonus_ui()

        # Set feat from background
        feat_name = bg.get("feat")
        if feat_name:
            feat = self.data.find_feat(feat_name)
            self.character.feat = feat

        self.notify_change()

    def _update_bonus_ui(self):
        for w in self.assign_frame.winfo_children():
            w.destroy()
        self.bonus_combos.clear()

        mode = self.bonus_mode.get()
        self.character.ability_bonus_mode = mode
        abilities = self.current_abilities

        if mode == "2/1":
            # Two dropdowns: one for +2, one for +1
            row1 = ttk.Frame(self.assign_frame)
            row1.pack(fill=tk.X, pady=2)
            ttk.Label(row1, text="+2 to:", width=8).pack(side=tk.LEFT)
            var2 = tk.StringVar(value=abilities[0] if abilities else "")
            combo2 = ttk.Combobox(row1, textvariable=var2, values=abilities, state="readonly", width=15)
            combo2.pack(side=tk.LEFT, padx=4)
            self.bonus_combos["+2"] = var2

            row2 = ttk.Frame(self.assign_frame)
            row2.pack(fill=tk.X, pady=2)
            ttk.Label(row2, text="+1 to:", width=8).pack(side=tk.LEFT)
            remaining = [a for a in abilities if a != abilities[0]] if abilities else []
            var1 = tk.StringVar(value=remaining[0] if remaining else "")
            combo1 = ttk.Combobox(row2, textvariable=var1, values=abilities, state="readonly", width=15)
            combo1.pack(side=tk.LEFT, padx=4)
            self.bonus_combos["+1"] = var1

            var2.trace_add("write", self._on_bonus_change)
            var1.trace_add("write", self._on_bonus_change)

        else:
            # Three abilities each get +1
            ttk.Label(self.assign_frame, text=f"Each gets +1: {', '.join(abilities)}",
                      style="Dim.TLabel").pack(anchor="w")

        self._on_bonus_change()

    def is_valid(self) -> bool:
        return self.character.background is not None

    def _on_bonus_change(self, *args):
        self.character.ability_scores.clear_bonuses()

        mode = self.bonus_mode.get()
        if mode == "2/1":
            plus2 = self.bonus_combos.get("+2")
            plus1 = self.bonus_combos.get("+1")
            if plus2:
                ab2 = plus2.get()
                if ab2:
                    self.character.ability_scores.set_bonus(ab2, 2)
            if plus1:
                ab1 = plus1.get()
                if ab1:
                    self.character.ability_scores.set_bonus(ab1, 1)
        else:
            for ab in self.current_abilities:
                self.character.ability_scores.set_bonus(ab, 1)

        self.character.ability_bonus_mode = mode
        self.notify_change()
