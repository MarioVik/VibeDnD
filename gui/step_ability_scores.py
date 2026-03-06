"""Step 4: Ability score assignment (standard array or point buy)."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.theme import COLORS, FONTS
from models.ability_scores import STANDARD_ARRAY, POINT_BUY_COSTS, POINT_BUY_BUDGET, POINT_BUY_MIN, POINT_BUY_MAX

ABILITIES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
ABILITY_SHORT = {"Strength": "STR", "Dexterity": "DEX", "Constitution": "CON",
                 "Intelligence": "INT", "Wisdom": "WIS", "Charisma": "CHA"}


class AbilityScoresStep(WizardStep):
    tab_title = "Abilities"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)

        # Title
        ttk.Label(self.frame, text="Assign Ability Scores", style="Heading.TLabel").pack(
            anchor="w", padx=12, pady=(12, 4))

        # Method toggle
        method_frame = ttk.Frame(self.frame)
        method_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        self.method_var = tk.StringVar(value="standard_array")
        ttk.Radiobutton(method_frame, text="Standard Array (15, 14, 13, 12, 10, 8)",
                        variable=self.method_var, value="standard_array",
                        command=self._on_method_change).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Radiobutton(method_frame, text="Point Buy (27 points)",
                        variable=self.method_var, value="point_buy",
                        command=self._on_method_change).pack(side=tk.LEFT)

        # Main assignment area
        self.assign_frame = ttk.Frame(self.frame)
        self.assign_frame.pack(fill=tk.BOTH, expand=True, padx=12)

        # Point buy budget display
        self.budget_frame = ttk.Frame(self.frame)
        self.budget_label = ttk.Label(self.budget_frame, text="Points: 27 / 27",
                                      style="Subheading.TLabel")
        self.budget_label.pack(side=tk.LEFT, padx=8)
        self.budget_bar = ttk.Progressbar(self.budget_frame, maximum=POINT_BUY_BUDGET,
                                          value=0, length=200)
        self.budget_bar.pack(side=tk.LEFT, padx=8)

        # Score widgets
        self.score_widgets = {}
        self._build_assignment_ui()

    def on_enter(self):
        """Refresh when entering this tab (background bonuses may have changed)."""
        self._update_display()

    def _build_assignment_ui(self):
        for w in self.assign_frame.winfo_children():
            w.destroy()
        self.score_widgets.clear()

        method = self.method_var.get()

        # Header row
        header = ttk.Frame(self.assign_frame)
        header.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(header, text="Ability", width=14, style="Subheading.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Base", width=8, style="Subheading.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Bonus", width=8, style="Subheading.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Total", width=8, style="Subheading.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Mod", width=8, style="Subheading.TLabel").pack(side=tk.LEFT)

        ttk.Separator(self.assign_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=2)

        for ability in ABILITIES:
            row = ttk.Frame(self.assign_frame)
            row.pack(fill=tk.X, pady=3)

            # Ability name
            ttk.Label(row, text=f"{ABILITY_SHORT[ability]}  ({ability})", width=18).pack(side=tk.LEFT)

            if method == "standard_array":
                # Pre-assign array values in order: STR=15, DEX=14, CON=13, INT=12, WIS=10, CHA=8
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
                # Spinbox for point buy (8-15)
                var = tk.IntVar(value=8)
                spin = ttk.Spinbox(row, from_=POINT_BUY_MIN, to=POINT_BUY_MAX,
                                   textvariable=var, width=5, command=lambda ab=ability: self._on_pb_change(ab))
                spin.pack(side=tk.LEFT, padx=4)
                var.trace_add("write", lambda *a, ab=ability: self._on_pb_change(ab))
                self.score_widgets[ability] = {"var": var, "widget": spin}

            # Bonus display
            bonus_label = ttk.Label(row, text="+0", width=6, style="Dim.TLabel")
            bonus_label.pack(side=tk.LEFT, padx=4)

            # Total display
            total_label = ttk.Label(row, text="10", width=6, style="Stat.TLabel")
            total_label.pack(side=tk.LEFT, padx=4)

            # Modifier display
            mod_label = ttk.Label(row, text="+0", width=6, style="StatMod.TLabel")
            mod_label.pack(side=tk.LEFT, padx=4)

            self.score_widgets[ability]["bonus_label"] = bonus_label
            self.score_widgets[ability]["total_label"] = total_label
            self.score_widgets[ability]["mod_label"] = mod_label

        # Show/hide budget
        if method == "point_buy":
            self.budget_frame.pack(fill=tk.X, padx=12, pady=8)
        else:
            self.budget_frame.pack_forget()

        self._update_display()

    def _on_method_change(self):
        self.character.score_method = self.method_var.get()
        self._build_assignment_ui()

    def _on_score_change(self, ability: str, var: tk.StringVar):
        # Guard against re-entrant calls from programmatic var.set()
        if getattr(self, '_swapping', False):
            return

        try:
            val = int(var.get())
        except (ValueError, tk.TclError):
            return

        self._swapping = True
        try:
            old_val = self.character.ability_scores.base(ability)

            # Find if another ability already has this value (swap needed)
            swap_target = None
            for other_ab in ABILITIES:
                if other_ab != ability and other_ab in self.score_widgets:
                    other_val = self.character.ability_scores.base(other_ab)
                    if other_val == val:
                        swap_target = other_ab
                        break

            # Set the new value on this ability
            self.character.ability_scores.set_base(ability, val)

            # If another ability had this value, give it our old value (swap)
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

            w["bonus_label"].configure(text=f"+{bonus}" if bonus > 0 else str(bonus) if bonus else "—")
            w["total_label"].configure(text=str(total))
            w["mod_label"].configure(text=mod_str)

            # Color code modifier
            if mod > 0:
                w["mod_label"].configure(foreground=COLORS["positive"])
            elif mod < 0:
                w["mod_label"].configure(foreground=COLORS["negative"])
            else:
                w["mod_label"].configure(foreground=COLORS["fg_dim"])

        # Update point buy budget
        if self.method_var.get() == "point_buy":
            spent = scores.point_buy_total()
            remaining = POINT_BUY_BUDGET - spent
            self.budget_label.configure(text=f"Points: {remaining} / {POINT_BUY_BUDGET}")
            self.budget_bar.configure(value=spent)
            if remaining < 0:
                self.budget_label.configure(foreground=COLORS["negative"])
            elif remaining == 0:
                self.budget_label.configure(foreground=COLORS["positive"])
            else:
                self.budget_label.configure(foreground=COLORS["fg"])

        self.notify_change()
