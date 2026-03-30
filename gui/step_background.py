"""Step 3: Background selection."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import (
    SectionedListbox,
    ScrollableFrame,
    WrappingLabel,
    GradientHeader,
    SectionHeader,
    CardFrame,
)
from gui.theme import COLORS, FONTS, SPACING
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
    handle_ua_toggle,
    save_settings,
)


class BackgroundStep(WizardStep):
    tab_title = "Background"

    def build_ui(self):
        self._edit_initialized = False
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Left: background list with source toggles
        left = tk.Frame(self.frame, bg=COLORS["bg"], width=220)
        left.grid(row=0, column=0, sticky="nsew", padx=(SPACING["sm"], SPACING["xs"]), pady=0)
        left.grid_propagate(False)

        SectionHeader(left, text="Choose Background").pack(
            fill=tk.X, pady=(SPACING["lg"], SPACING["sm"])
        )

        # Source filter toggles
        self.toggle_frame = tk.Frame(left, bg=COLORS["bg"])
        self.toggle_frame.pack(fill=tk.X, pady=(0, SPACING["xs"]))
        self.toggle_vars: dict[str, tk.BooleanVar] = {}
        self._ua_prev_enabled = False
        self._build_toggles()

        self.bg_list = SectionedListbox(left, on_select=self._on_select)
        self.bg_list.pack(fill=tk.BOTH, expand=True)

        # Right: detail
        right = ScrollableFrame(self.frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0), pady=0)
        self.detail = right.inner

        # Hero header
        self._hero = GradientHeader(self.detail, min_height=60)
        self._hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

        self.detail_name = tk.Label(
            self._hero.inner,
            text="Select a background",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        )
        self.detail_name.pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        self.detail_source = tk.Label(
            self._hero.inner,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        )
        self.detail_source.pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        self.detail_desc = WrappingLabel(
            self.detail, text="", foreground=COLORS["fg_dim"]
        )
        self.detail_desc.pack(fill=tk.X, anchor="w", padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        self.info_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.info_frame.pack(fill=tk.X, padx=SPACING["lg"])

        # Ability bonus assignment
        self.bonus_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.bonus_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], 0))

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
            if hasattr(self, "bonus_mode"):
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
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)

        for cat in sections:
            label = "UA" if cat == UA_CATEGORY else cat
            var = tk.BooleanVar(value=filters.get(cat, cat != UA_CATEGORY))
            cb = ttk.Checkbutton(
                self.toggle_frame,
                text=label,
                variable=var,
                command=self._on_toggle_change,
            )
            cb.pack(side=tk.LEFT, padx=(0, 6))
            self.toggle_vars[cat] = var

    def _on_toggle_change(self):
        """Update filters and rebuild list when a toggle changes."""
        ua_var = self.toggle_vars.get(UA_CATEGORY)
        proceed, _ = handle_ua_toggle(self.frame, ua_var, self._ua_prev_enabled)
        if not proceed:
            return

        filters = {cat: var.get() for cat, var in self.toggle_vars.items()}
        self.data.source_filters["backgrounds"] = filters
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)
        save_settings(self.data.source_filters)
        self._populate_list()

    def _populate_list(self):
        filters = self.data.source_filters.get("backgrounds", {})
        enabled = {cat for cat, on in filters.items() if on}

        grouped = group_by_category(self.data.backgrounds, "backgrounds")
        sections = [
            (cat, [b["name"] for b in items])
            for cat, items in grouped
            if cat in enabled
        ]
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

        SectionHeader(self.info_frame, text="Details").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        info_card = CardFrame(self.info_frame, pad=SPACING["lg"])
        info_card.pack(fill=tk.X)

        info = [
            ("Feat", bg.get("feat", "None")),
            ("Skills", ", ".join(bg.get("skill_proficiencies", []))),
            ("Tool", bg.get("tool_proficiency", "None")),
        ]

        equip = bg.get("equipment", [])
        if equip:
            equip_text = " / ".join(f"({e['option']}) {e['items']}" for e in equip)
            info.append(("Equipment", equip_text))

        _bg = COLORS["bg_surface"]
        for label, value in info:
            row = tk.Frame(info_card.inner, bg=_bg)
            row.pack(fill=tk.X, pady=1)
            tk.Label(
                row,
                text=f"{label}:",
                font=FONTS["body_bold"],
                fg=COLORS["accent_text"],
                bg=_bg,
                width=12,
                anchor="e",
            ).pack(side=tk.LEFT)
            WrappingLabel(
                row, text=f"  {value}", background=_bg
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # Ability bonus assignment
        for w in self.bonus_frame.winfo_children():
            w.destroy()

        abilities = bg.get("ability_scores", [])
        if abilities:
            SectionHeader(self.bonus_frame, text="Ability Score Bonuses").pack(
                fill=tk.X, pady=(SPACING["sm"], SPACING["sm"])
            )

            bonus_card = CardFrame(self.bonus_frame, pad=SPACING["lg"])
            bonus_card.pack(fill=tk.X)
            bonus_inner = bonus_card.inner

            tk.Label(
                bonus_inner,
                text=f"Distribute bonuses among: {', '.join(abilities)}",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w", pady=(0, SPACING["xs"]))

            # Mode selection
            mode_frame = tk.Frame(bonus_inner, bg=COLORS["bg_surface"])
            mode_frame.pack(fill=tk.X)
            self.bonus_mode = tk.StringVar(value="2/1")
            ttk.Radiobutton(
                mode_frame,
                text="+2 / +1",
                variable=self.bonus_mode,
                value="2/1",
                command=self._update_bonus_ui,
            ).pack(side=tk.LEFT, padx=SPACING["sm"])
            ttk.Radiobutton(
                mode_frame,
                text="+1 / +1 / +1",
                variable=self.bonus_mode,
                value="1/1/1",
                command=self._update_bonus_ui,
            ).pack(side=tk.LEFT, padx=SPACING["sm"])

            # Assignment combos
            self.assign_frame = tk.Frame(bonus_inner, bg=COLORS["bg_surface"])
            self.assign_frame.pack(fill=tk.X, pady=(SPACING["xs"], 0))
            self.bonus_combos = {}
            self.bonus_widgets = {}
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
        self.bonus_widgets.clear()

        mode = self.bonus_mode.get()
        self.character.ability_bonus_mode = mode
        abilities = self.current_abilities
        _bg = COLORS["bg_surface"]

        if mode == "2/1":
            row1 = tk.Frame(self.assign_frame, bg=_bg)
            row1.pack(fill=tk.X, pady=2)
            tk.Label(row1, text="+2 to:", font=FONTS["body_bold"], fg=COLORS["fg"], bg=_bg, width=8).pack(side=tk.LEFT)
            var2 = tk.StringVar(value=abilities[0] if abilities else "")
            combo2 = ttk.Combobox(
                row1, textvariable=var2, values=abilities, state="readonly", width=15
            )
            combo2.pack(side=tk.LEFT, padx=4)
            self.bonus_combos["+2"] = var2
            self.bonus_widgets["+2"] = combo2

            row2 = tk.Frame(self.assign_frame, bg=_bg)
            row2.pack(fill=tk.X, pady=2)
            tk.Label(row2, text="+1 to:", font=FONTS["body_bold"], fg=COLORS["fg"], bg=_bg, width=8).pack(side=tk.LEFT)
            remaining = [a for a in abilities if a != abilities[0]] if abilities else []
            var1 = tk.StringVar(value=remaining[0] if remaining else "")
            combo1 = ttk.Combobox(
                row2, textvariable=var1, values=[a for a in abilities if a != abilities[0]] if abilities else [], state="readonly", width=15
            )
            combo1.pack(side=tk.LEFT, padx=4)
            self.bonus_combos["+1"] = var1
            self.bonus_widgets["+1"] = combo1

            var2.trace_add("write", self._on_bonus_change)
            var1.trace_add("write", self._on_bonus_change)

        else:
            for ab in abilities:
                row = tk.Frame(self.assign_frame, bg=_bg)
                row.pack(fill=tk.X, pady=2)
                tk.Label(row, text="+1 to:", font=FONTS["body_bold"], fg=COLORS["fg"], bg=_bg, width=8).pack(side=tk.LEFT)
                tk.Label(
                    row, text=ab, font=FONTS["body"], fg=COLORS["accent_text"], bg=_bg,
                ).pack(side=tk.LEFT, padx=4)

        self._on_bonus_change()

    def is_valid(self) -> bool:
        return self.character.background is not None

    def _on_bonus_change(self, *args):
        self.character.ability_scores.clear_bonuses()

        mode = self.bonus_mode.get()
        if mode == "2/1":
            plus2_var = self.bonus_combos.get("+2")
            plus1_var = self.bonus_combos.get("+1")
            ab2 = plus2_var.get() if plus2_var else ""
            ab1 = plus1_var.get() if plus1_var else ""
            abilities = self.current_abilities

            combo2_w = self.bonus_widgets.get("+2")
            combo1_w = self.bonus_widgets.get("+1")

            if combo1_w and ab2:
                allowed = [a for a in abilities if a != ab2]
                combo1_w["values"] = allowed
                if ab1 == ab2 and allowed:
                    plus1_var.set(allowed[0])
                    return
            elif combo1_w:
                combo1_w["values"] = abilities

            if combo2_w and ab1:
                combo2_w["values"] = [a for a in abilities if a != ab1]
            elif combo2_w:
                combo2_w["values"] = abilities

            if ab2:
                self.character.ability_scores.set_bonus(ab2, 2)
            if ab1 and ab1 != ab2:
                self.character.ability_scores.set_bonus(ab1, 1)
        else:
            for ab in self.current_abilities:
                self.character.ability_scores.set_bonus(ab, 1)

        self.character.ability_bonus_mode = mode
        self.notify_change()
