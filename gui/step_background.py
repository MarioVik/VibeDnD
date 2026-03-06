"""Step 3: Background selection."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import SearchableListbox, ScrollableFrame
from gui.theme import COLORS, FONTS


class BackgroundStep(WizardStep):
    tab_title = "Background"

    def build_ui(self):
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Left: background list
        left = ttk.Frame(self.frame, width=220)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_propagate(False)

        ttk.Label(left, text="Choose Background", style="Heading.TLabel").pack(anchor="w", pady=(0, 6))
        self.bg_list = SearchableListbox(left, on_select=self._on_select)
        self.bg_list.pack(fill=tk.BOTH, expand=True)

        # Right: detail
        right = ScrollableFrame(self.frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.detail = right.inner

        self.detail_name = ttk.Label(self.detail, text="Select a background", style="Heading.TLabel")
        self.detail_name.pack(anchor="w", pady=(0, 4))

        self.detail_source = ttk.Label(self.detail, text="", style="Dim.TLabel")
        self.detail_source.pack(anchor="w")

        self.detail_desc = ttk.Label(self.detail, text="", wraplength=500)
        self.detail_desc.pack(anchor="w", pady=(8, 0))

        ttk.Separator(self.detail, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        self.info_frame = ttk.Frame(self.detail)
        self.info_frame.pack(fill=tk.X)

        # Ability bonus assignment
        self.bonus_frame = ttk.LabelFrame(self.detail, text="Ability Score Bonuses")
        self.bonus_frame.pack(fill=tk.X, pady=(8, 0))

        self._populate_list()

    def _populate_list(self):
        names = sorted([b["name"] for b in self.data.backgrounds])
        self.bg_list.set_items(names)

    def _on_select(self, name: str):
        bg = self.data.backgrounds_by_name.get(name)
        if not bg:
            return

        self.character.background = bg
        self.detail_name.configure(text=bg["name"])
        self.detail_source.configure(text=f"Source: {bg.get('source', 'Unknown')}")
        self.detail_desc.configure(text=bg.get("description", "")[:400])

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
            equip_text = " / ".join(f"({e['option']}) {e['items'][:80]}" for e in equip)
            info.append(("Equipment", equip_text))

        for label, value in info:
            row = ttk.Frame(self.info_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"{label}:", foreground=COLORS["accent"],
                      font=FONTS["body"], width=12, anchor="e").pack(side=tk.LEFT)
            ttk.Label(row, text=f"  {value}", wraplength=400).pack(side=tk.LEFT, padx=(4, 0))

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
