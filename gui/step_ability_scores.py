"""Step 6: Ability score assignment (standard array or point buy) + HP override."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import GradientHeader, SectionHeader, CardFrame, ScrollableFrame
from gui.theme import COLORS, FONTS, SPACING
from models.ability_scores import STANDARD_ARRAY, POINT_BUY_COSTS, POINT_BUY_BUDGET, POINT_BUY_MIN, POINT_BUY_MAX
from models.ability_bonus_utils import (
    apply_background_ability_bonuses,
    get_background_bonus_abilities,
)

ABILITIES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
ABILITY_SHORT = {"Strength": "STR", "Dexterity": "DEX", "Constitution": "CON",
                 "Intelligence": "INT", "Wisdom": "WIS", "Charisma": "CHA"}
CARD_RADIO_STYLE = "Card.TRadiobutton"


class AbilityScoresStep(WizardStep):
    tab_title = "Abilities"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # ── Hero header ─────────────────────────────────────────
        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        tk.Label(
            hero.inner,
            text="Ability Scores",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"]))

        # ── Scrollable content ──────────────────────────────────
        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew")
        inner = scroll.inner

        # HP override container (populated in on_enter once class is known)
        self._hp_outer = tk.Frame(inner, bg=COLORS["bg"])
        self._hp_outer.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], 0))

        # Background / origin bonuses
        self._bonus_outer = tk.Frame(inner, bg=COLORS["bg"])
        self._bonus_outer.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], 0))

        # Method toggle
        SectionHeader(inner, text="Method").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        method_card = CardFrame(inner, pad=SPACING["md"])
        method_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        method_frame = tk.Frame(method_card.inner, bg=COLORS["bg_surface"])
        method_frame.pack(fill=tk.X)
        self.method_var = tk.StringVar(value="standard_array")
        ttk.Radiobutton(method_frame, text="Standard Array (15, 14, 13, 12, 10, 8)",
                        variable=self.method_var, value="standard_array",
                        command=self._on_method_change,
                        style=CARD_RADIO_STYLE).pack(side=tk.LEFT, padx=(0, SPACING["lg"]))
        ttk.Radiobutton(method_frame, text="Point Buy (27 points)",
                        variable=self.method_var, value="point_buy",
                        command=self._on_method_change,
                        style=CARD_RADIO_STYLE).pack(side=tk.LEFT)

        # Main assignment area
        SectionHeader(inner, text="Scores").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        self.assign_card = CardFrame(inner, pad=SPACING["lg"])
        self.assign_card.pack(fill=tk.X, padx=SPACING["lg"])
        self.assign_frame = self.assign_card.inner

        # Point buy budget display
        self.budget_frame = tk.Frame(inner, bg=COLORS["bg"])
        self.budget_label = tk.Label(
            self.budget_frame, text="Points: 27 / 27",
            font=FONTS["subheading"], fg=COLORS["fg"], bg=COLORS["bg"],
        )
        self.budget_label.pack(side=tk.LEFT, padx=SPACING["sm"])
        self.budget_bar = ttk.Progressbar(self.budget_frame, maximum=POINT_BUY_BUDGET,
                                          value=0, length=200)
        self.budget_bar.pack(side=tk.LEFT, padx=SPACING["sm"])

        self._bottom_spacer = tk.Frame(inner, bg=COLORS["bg"], height=1)
        self._bottom_spacer.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["lg"]))

        # Snapshot loaded scores before defaults overwrite them (edit mode)
        self._loaded_scores = dict(self.character.ability_scores.scores)
        self._has_loaded_data = any(v != 10 for v in self._loaded_scores.values())
        self._edit_initialized = False

        # Use character's method (may differ from default for loaded characters)
        self.method_var.set(self.character.score_method)

        # Score widgets
        self.score_widgets = {}
        self.bonus_combos = {}
        self.bonus_widgets = {}
        self._current_bonus_abilities: list[str] = []
        self._build_assignment_ui()
        self._build_background_bonus_section()

        # Restore loaded scores to character model (_build_assignment_ui set defaults)
        if self._has_loaded_data:
            for ab, val in self._loaded_scores.items():
                self.character.ability_scores.set_base(ab, val)

    def on_enter(self):
        """Refresh when entering this tab. Pre-populate scores in edit mode."""
        self._build_background_bonus_section()
        if not self._edit_initialized and self._has_loaded_data:
            self._edit_initialized = True
            method = self.method_var.get()
            if method == "standard_array":
                self._swapping = True
                try:
                    for ab in ABILITIES:
                        val = self._loaded_scores.get(ab, 10)
                        if ab in self.score_widgets:
                            self.score_widgets[ab]["var"].set(str(val))
                        self.character.ability_scores.set_base(ab, val)
                finally:
                    self._swapping = False
            else:  # point_buy
                for ab in ABILITIES:
                    val = self._loaded_scores.get(ab, 8)
                    if ab in self.score_widgets:
                        self.score_widgets[ab]["var"].set(val)
        self._update_display()
        self._build_hp_override()

    def _build_background_bonus_section(self):
        for w in self._bonus_outer.winfo_children():
            w.destroy()

        background = self.character.background or {}
        self._current_bonus_abilities = get_background_bonus_abilities(self.character)
        if not background or not self._current_bonus_abilities:
            self.bonus_combos.clear()
            self.bonus_widgets.clear()
            if self._bonus_outer.winfo_manager():
                self._bonus_outer.pack_forget()
            return

        if not self._bonus_outer.winfo_manager():
            self._bonus_outer.pack(
                fill=tk.X,
                padx=SPACING["lg"],
                pady=(SPACING["sm"], 0),
                after=self._hp_outer,
            )

        apply_background_ability_bonuses(self.character)

        SectionHeader(self._bonus_outer, text="Ability Score Increases").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        bonus_card = CardFrame(self._bonus_outer, pad=SPACING["lg"])
        bonus_card.pack(fill=tk.X)
        bonus_inner = bonus_card.inner
        _bg = COLORS["bg_surface"]

        tk.Label(
            bonus_inner,
            text=f"From Background: {background.get('name', 'Unknown')}",
            font=FONTS["body_bold"],
            fg=COLORS["fg"],
            bg=_bg,
        ).pack(anchor="w")

        tk.Label(
            bonus_inner,
            text=(
                "These bonuses come from your background and are added on top "
                "of the base scores you assign below."
            ),
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=_bg,
            wraplength=780,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(SPACING["xs"], SPACING["xs"]))

        tk.Label(
            bonus_inner,
            text=f"Choose from: {', '.join(self._current_bonus_abilities)}",
            font=FONTS["body"],
            fg=COLORS["accent_text"],
            bg=_bg,
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        mode_frame = tk.Frame(bonus_inner, bg=_bg)
        mode_frame.pack(fill=tk.X)

        self.bonus_mode = tk.StringVar(value=self.character.ability_bonus_mode)
        ttk.Radiobutton(
            mode_frame,
            text="+2 / +1",
            variable=self.bonus_mode,
            value="2/1",
            command=self._update_bonus_ui,
            style=CARD_RADIO_STYLE,
        ).pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        ttk.Radiobutton(
            mode_frame,
            text="+1 / +1 / +1",
            variable=self.bonus_mode,
            value="1/1/1",
            command=self._update_bonus_ui,
            style=CARD_RADIO_STYLE,
        ).pack(side=tk.LEFT, padx=(0, SPACING["sm"]))

        self.assign_bonus_frame = tk.Frame(bonus_inner, bg=_bg)
        self.assign_bonus_frame.pack(fill=tk.X, pady=(SPACING["xs"], 0))

        self._update_bonus_ui()

    def _update_bonus_ui(self):
        if not hasattr(self, "assign_bonus_frame"):
            return

        for w in self.assign_bonus_frame.winfo_children():
            w.destroy()

        self.bonus_combos.clear()
        self.bonus_widgets.clear()
        self.character.ability_bonus_mode = self.bonus_mode.get()
        apply_background_ability_bonuses(self.character)

        abilities = list(self._current_bonus_abilities)
        _bg = COLORS["bg_surface"]

        if self.character.ability_bonus_mode == "2/1":
            assignments = dict(self.character.ability_bonus_assignments)
            plus2_value = assignments.get("+2", abilities[0] if abilities else "")
            plus1_choices = [ability for ability in abilities if ability != plus2_value]
            plus1_value = assignments.get("+1", plus1_choices[0] if plus1_choices else "")

            row1 = tk.Frame(self.assign_bonus_frame, bg=_bg)
            row1.pack(fill=tk.X, pady=2)
            tk.Label(
                row1,
                text="+2 to:",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=_bg,
                width=8,
            ).pack(side=tk.LEFT)
            plus2_var = tk.StringVar(value=plus2_value)
            plus2_combo = ttk.Combobox(
                row1,
                textvariable=plus2_var,
                values=abilities,
                state="readonly",
                width=15,
            )
            plus2_combo.pack(side=tk.LEFT, padx=4)
            self.bonus_combos["+2"] = plus2_var
            self.bonus_widgets["+2"] = plus2_combo

            row2 = tk.Frame(self.assign_bonus_frame, bg=_bg)
            row2.pack(fill=tk.X, pady=2)
            tk.Label(
                row2,
                text="+1 to:",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=_bg,
                width=8,
            ).pack(side=tk.LEFT)
            plus1_var = tk.StringVar(value=plus1_value)
            plus1_combo = ttk.Combobox(
                row2,
                textvariable=plus1_var,
                values=plus1_choices,
                state="readonly",
                width=15,
            )
            plus1_combo.pack(side=tk.LEFT, padx=4)
            self.bonus_combos["+1"] = plus1_var
            self.bonus_widgets["+1"] = plus1_combo

            plus2_var.trace_add("write", self._on_bonus_change)
            plus1_var.trace_add("write", self._on_bonus_change)
        else:
            for ability in abilities:
                row = tk.Frame(self.assign_bonus_frame, bg=_bg)
                row.pack(fill=tk.X, pady=2)
                tk.Label(
                    row,
                    text="+1 to:",
                    font=FONTS["body_bold"],
                    fg=COLORS["fg"],
                    bg=_bg,
                    width=8,
                ).pack(side=tk.LEFT)
                tk.Label(
                    row,
                    text=ability,
                    font=FONTS["body"],
                    fg=COLORS["accent_text"],
                    bg=_bg,
                ).pack(side=tk.LEFT, padx=4)

        self._on_bonus_change()

    def _on_bonus_change(self, *_args):
        if not self._current_bonus_abilities:
            return

        mode = self.bonus_mode.get()
        self.character.ability_bonus_mode = mode

        if mode == "2/1":
            plus2_var = self.bonus_combos.get("+2")
            plus1_var = self.bonus_combos.get("+1")
            plus2_value = plus2_var.get() if plus2_var else ""
            plus1_value = plus1_var.get() if plus1_var else ""

            plus2_widget = self.bonus_widgets.get("+2")
            plus1_widget = self.bonus_widgets.get("+1")

            if plus1_widget and plus2_value:
                plus1_choices = [
                    ability
                    for ability in self._current_bonus_abilities
                    if ability != plus2_value
                ]
                plus1_widget["values"] = plus1_choices
                if plus1_value == plus2_value and plus1_choices:
                    plus1_var.set(plus1_choices[0])
                    return
            elif plus1_widget:
                plus1_widget["values"] = self._current_bonus_abilities

            if plus2_widget and plus1_value:
                plus2_widget["values"] = [
                    ability
                    for ability in self._current_bonus_abilities
                    if ability != plus1_value
                ]
            elif plus2_widget:
                plus2_widget["values"] = self._current_bonus_abilities

            self.character.ability_bonus_assignments = {}
            if plus2_value:
                self.character.ability_bonus_assignments["+2"] = plus2_value
            if plus1_value and plus1_value != plus2_value:
                self.character.ability_bonus_assignments["+1"] = plus1_value
        else:
            self.character.ability_bonus_assignments = {
                ability: 1 for ability in self._current_bonus_abilities
            }

        apply_background_ability_bonuses(self.character)
        self._update_display()

    def _build_assignment_ui(self):
        for w in self.assign_frame.winfo_children():
            w.destroy()
        self.score_widgets.clear()

        method = self.method_var.get()
        _bg = COLORS["bg_surface"]

        # Header row
        header = tk.Frame(self.assign_frame, bg=_bg)
        header.pack(fill=tk.X, pady=(0, SPACING["xs"]))
        for text, width in [("Ability", 18), ("Base", 8), ("Bonus", 8), ("Total", 8), ("Mod", 8)]:
            tk.Label(header, text=text, font=FONTS["label_upper_bold"],
                     fg=COLORS["fg_dim"], bg=_bg, width=width, anchor="w").pack(side=tk.LEFT)

        # Accent line separator
        tk.Frame(self.assign_frame, bg="#4a2028", height=2).pack(fill=tk.X, pady=(0, SPACING["xs"]))

        for ability in ABILITIES:
            row = tk.Frame(self.assign_frame, bg=_bg)
            row.pack(fill=tk.X, pady=3)

            tk.Label(row, text=f"{ABILITY_SHORT[ability]}  ({ability})",
                     font=FONTS["body"], fg=COLORS["fg"], bg=_bg, width=18, anchor="w").pack(side=tk.LEFT)

            if method == "standard_array":
                initial_val = sorted(STANDARD_ARRAY, reverse=True)[ABILITIES.index(ability)]
                var = tk.StringVar(value=str(initial_val))
                self.character.ability_scores.set_base(ability, initial_val)
                combo = ttk.Combobox(row, textvariable=var,
                                     values=[str(v) for v in sorted(STANDARD_ARRAY, reverse=True)],
                                     state="readonly", width=5)
                combo.pack(side=tk.LEFT, padx=4)
                var.trace_add("write", lambda *a, ab=ability, v=var: self._on_score_change(ab, v))
                self.score_widgets[ability] = {"var": var, "widget": combo}
            else:
                var = tk.IntVar(value=8)
                spin = ttk.Spinbox(row, from_=POINT_BUY_MIN, to=POINT_BUY_MAX,
                                   textvariable=var, width=5, command=lambda ab=ability: self._on_pb_change(ab))
                spin.pack(side=tk.LEFT, padx=4)
                var.trace_add("write", lambda *a, ab=ability: self._on_pb_change(ab))
                self.score_widgets[ability] = {"var": var, "widget": spin}

            bonus_label = tk.Label(row, text="+0", font=FONTS["body"],
                                   fg=COLORS["fg_dim"], bg=_bg, width=6)
            bonus_label.pack(side=tk.LEFT, padx=4)

            total_label = tk.Label(row, text="10", font=FONTS["stat"],
                                   fg=COLORS["fg"], bg=_bg, width=6)
            total_label.pack(side=tk.LEFT, padx=4)

            mod_label = tk.Label(row, text="+0", font=FONTS["stat_mod"],
                                 fg=COLORS["fg_dim"], bg=_bg, width=6)
            mod_label.pack(side=tk.LEFT, padx=4)

            self.score_widgets[ability]["bonus_label"] = bonus_label
            self.score_widgets[ability]["total_label"] = total_label
            self.score_widgets[ability]["mod_label"] = mod_label

        # Show/hide budget
        if method == "point_buy":
            self.budget_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=SPACING["sm"])
        else:
            self.budget_frame.pack_forget()

        self._update_display()

    # ── HP Override (moved from Summary) ────────────────────────

    def _build_hp_override(self):
        """Build/rebuild the level-1 HP override section based on current class."""
        for w in self._hp_outer.winfo_children():
            w.destroy()

        if not self.character.class_levels:
            return

        cl0 = self.character.class_levels[0]
        char_class = self.character.character_class
        if not char_class:
            return

        hit_die = char_class.get("hit_die", 8)
        con_mod = self.character.ability_scores.modifier("Constitution")
        average = hit_die // 2 + 1

        SectionHeader(self._hp_outer, text="HP at Level 1").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        hp_card = CardFrame(self._hp_outer, pad=SPACING["lg"])
        hp_card.pack(fill=tk.X)
        hp_inner = hp_card.inner

        # Fresh StringVars each rebuild to avoid stale trace accumulation
        self._hp_mode = tk.StringVar()
        self._hp_manual_var = tk.StringVar()

        # Restore mode from existing hp_roll if any
        if cl0.hp_roll is None:
            self._hp_mode.set("max")
        elif cl0.hp_roll == hit_die:
            self._hp_mode.set("max")
        elif cl0.hp_roll == average:
            self._hp_mode.set("manual")
            self._hp_manual_var.set(str(cl0.hp_roll))
        else:
            self._hp_mode.set("manual")
            self._hp_manual_var.set(str(cl0.hp_roll))

        radio_row = tk.Frame(hp_inner, bg=COLORS["bg_surface"])
        radio_row.pack(fill=tk.X)

        ttk.Radiobutton(
            radio_row,
            text=f"Max ({hit_die} + {con_mod} CON = {hit_die + con_mod} HP)",
            variable=self._hp_mode,
            value="max",
            style=CARD_RADIO_STYLE,
        ).pack(side=tk.LEFT, padx=(0, SPACING["md"]))

        ttk.Radiobutton(
            radio_row,
            text="Manual:",
            variable=self._hp_mode,
            value="manual",
            style=CARD_RADIO_STYLE,
        ).pack(side=tk.LEFT)

        manual_entry = ttk.Entry(radio_row, textvariable=self._hp_manual_var, width=5)
        manual_entry.pack(side=tk.LEFT, padx=(4, 4))

        self._hp_hint_label = tk.Label(
            radio_row,
            text=f"+ {con_mod} CON = ? HP",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self._hp_hint_label.pack(side=tk.LEFT)

        def _update_state(*_):
            if self._hp_mode.get() == "manual":
                manual_entry.config(state="normal")
            else:
                manual_entry.config(state="disabled")
            _update_hint()
            self._apply_hp_override(hit_die, con_mod)

        def _update_hint(*_):
            if self._hp_mode.get() != "manual":
                return
            val = self._hp_manual_var.get().strip()
            try:
                roll = int(val)
                if roll >= 1:
                    self._hp_hint_label.config(text=f"+ {con_mod} CON = {roll + con_mod} HP")
                else:
                    self._hp_hint_label.config(text="(must be \u2265 1)")
            except ValueError:
                self._hp_hint_label.config(text=f"+ {con_mod} CON = ? HP")

        self._hp_mode.trace_add("write", _update_state)
        self._hp_manual_var.trace_add("write", lambda *_: (_update_hint(), self._apply_hp_override(hit_die, con_mod)))

        if self._hp_mode.get() != "manual":
            manual_entry.config(state="disabled")

    def _apply_hp_override(self, hit_die, con_mod):
        """Write the chosen HP value into character.class_levels[0].hp_roll."""
        if not self.character.class_levels:
            return
        cl0 = self.character.class_levels[0]
        mode = self._hp_mode.get()
        if mode == "max":
            cl0.hp_roll = None
        elif mode == "manual":
            val = self._hp_manual_var.get().strip()
            try:
                roll = int(val)
                if roll >= 1:
                    cl0.hp_roll = roll
            except ValueError:
                pass
        self.notify_change()

    # ── Method / score changes ──────────────────────────────────

    def _on_method_change(self):
        self.character.score_method = self.method_var.get()
        self._build_assignment_ui()

    def _on_score_change(self, ability: str, var: tk.StringVar):
        if getattr(self, '_swapping', False):
            return

        try:
            val = int(var.get())
        except (ValueError, tk.TclError):
            return

        self._swapping = True
        try:
            old_val = self.character.ability_scores.base(ability)

            swap_target = None
            for other_ab in ABILITIES:
                if other_ab != ability and other_ab in self.score_widgets:
                    other_val = self.character.ability_scores.base(other_ab)
                    if other_val == val:
                        swap_target = other_ab
                        break

            self.character.ability_scores.set_base(ability, val)

            if swap_target:
                self.score_widgets[swap_target]["var"].set(str(old_val))
                self.character.ability_scores.set_base(swap_target, old_val)
        finally:
            self._swapping = False

        self._update_display()

    def _on_pb_change(self, ability: str = None):
        for ab, widgets in self.score_widgets.items():
            try:
                val = int(widgets["var"].get())
            except (ValueError, tk.TclError):
                val = 8
            val = max(POINT_BUY_MIN, min(POINT_BUY_MAX, val))
            self.character.ability_scores.set_base(ab, val)
        self._update_display()

    def is_valid(self) -> bool:
        if self.method_var.get() == "point_buy":
            return self.character.ability_scores.point_buy_total() == POINT_BUY_BUDGET
        else:
            return True

    def _update_display(self):
        scores = self.character.ability_scores

        for ability in ABILITIES:
            if ability not in self.score_widgets:
                continue
            w = self.score_widgets[ability]

            base = scores.base(ability)
            bonus = scores.bonus(ability)
            total = scores.total(ability)
            mod = scores.modifier(ability)
            mod_str = scores.modifier_str(ability)

            w["bonus_label"].configure(text=f"+{bonus}" if bonus > 0 else str(bonus) if bonus else "\u2014")
            w["total_label"].configure(text=str(total))
            w["mod_label"].configure(text=mod_str)

            if mod > 0:
                w["mod_label"].configure(fg=COLORS["positive"])
            elif mod < 0:
                w["mod_label"].configure(fg=COLORS["negative"])
            else:
                w["mod_label"].configure(fg=COLORS["fg_dim"])

        # Update point buy budget
        if self.method_var.get() == "point_buy":
            spent = scores.point_buy_total()
            remaining = POINT_BUY_BUDGET - spent
            self.budget_label.configure(text=f"Points: {remaining} / {POINT_BUY_BUDGET}")
            self.budget_bar.configure(value=spent)
            if remaining < 0:
                self.budget_label.configure(fg=COLORS["negative"])
            elif remaining == 0:
                self.budget_label.configure(fg=COLORS["positive"])
            else:
                self.budget_label.configure(fg=COLORS["fg"])

        self.notify_change()
