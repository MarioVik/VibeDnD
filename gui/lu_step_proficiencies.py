"""Level-up step: Subclass proficiency/expertise grants."""

import tkinter as tk
from tkinter import ttk

from gui.lu_base_step import LevelUpStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    GradientHeader,
    SectionHeader,
    ScrollableFrame,
)
from models.level_up_logic import (
    get_subclass_grants,
    validate_proficiency_step,
)


class LuProficienciesStep(LevelUpStep):
    tab_title = "Proficiencies"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_row = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_row.pack(
            fill=tk.X,
            padx=SPACING["card_pad"],
            pady=(SPACING["xl"], SPACING["xl"]),
        )

        tk.Label(
            hero_row,
            text="Subclass Proficiencies",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        self._scroll = ScrollableFrame(self.frame, auto_hide_scrollbar=True)
        self._scroll.grid(row=1, column=0, sticky="nsew")

        self._prof_combos: list[tuple[tk.StringVar, ttk.Combobox]] = []
        self._exp_combos: list[tuple[tk.StringVar, ttk.Combobox]] = []

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._scroll.inner.winfo_children():
            w.destroy()
        self._prof_combos.clear()
        self._exp_combos.clear()

        inner = self._scroll.inner
        grants = get_subclass_grants(self.ctx, self.character, self.data)
        if not grants:
            return

        existing_profs = self.character.all_skill_proficiencies

        for grant in grants:
            gp = grant.get("grants_proficiency")
            ge = grant.get("grants_expertise")

            if gp and gp.get("automatic") and ge and ge.get("automatic"):
                card = CardFrame(inner, pad=SPACING["lg"])
                card.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], 0))
                tk.Label(
                    card.inner,
                    text=f"{grant['feature_name']}: automatically gained",
                    font=FONTS["body"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w")
                continue

            SectionHeader(inner, text=grant["feature_name"]).pack(
                fill=tk.X, padx=SPACING["lg"],
                pady=(SPACING["lg"], SPACING["sm"]),
            )

            if gp and not gp.get("automatic"):
                count = gp.get("count", 1)
                available = [s for s in gp["skills"] if s not in existing_profs]

                card = CardFrame(inner, pad=SPACING["lg"])
                card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

                tk.Label(
                    card.inner,
                    text=f"Choose {count} skill proficiency(s):",
                    font=FONTS["body"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w", pady=(0, SPACING["xs"]))

                for i in range(count):
                    prev_val = self.ctx.prof_picks[i] if i < len(self.ctx.prof_picks) else ""
                    var = tk.StringVar(value=prev_val)
                    combo = ttk.Combobox(
                        card.inner,
                        textvariable=var,
                        values=available,
                        state="readonly",
                        width=30,
                    )
                    combo.pack(anchor="w", padx=SPACING["lg"], pady=SPACING["xs"])
                    combo.bind("<<ComboboxSelected>>", lambda *_, v=var, idx=i: self._on_prof_change(idx, v))
                    self._prof_combos.append((var, combo))

                if ge and ge.get("from_granted"):
                    tk.Label(
                        card.inner,
                        text="(You also gain Expertise in the chosen skills.)",
                        font=FONTS["body_small"],
                        fg=COLORS["fg_dim"],
                        bg=COLORS["bg_surface"],
                    ).pack(anchor="w", pady=(SPACING["xs"], 0))

            if ge and not ge.get("automatic") and not ge.get("from_granted"):
                count = ge.get("count", 1)
                available = ge.get("skills", [])

                card = CardFrame(inner, pad=SPACING["lg"])
                card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

                tk.Label(
                    card.inner,
                    text=f"Choose {count} skill expertise(s):",
                    font=FONTS["body"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w", pady=(0, SPACING["xs"]))

                for i in range(count):
                    prev_val = self.ctx.expertise_picks[i] if i < len(self.ctx.expertise_picks) else ""
                    var = tk.StringVar(value=prev_val)
                    combo = ttk.Combobox(
                        card.inner,
                        textvariable=var,
                        values=available,
                        state="readonly",
                        width=30,
                    )
                    combo.pack(anchor="w", padx=SPACING["lg"], pady=SPACING["xs"])
                    combo.bind("<<ComboboxSelected>>", lambda *_, v=var, idx=i: self._on_exp_change(idx, v))
                    self._exp_combos.append((var, combo))

    def _on_prof_change(self, idx: int, var: tk.StringVar):
        while len(self.ctx.prof_picks) <= idx:
            self.ctx.prof_picks.append("")
        self.ctx.prof_picks[idx] = var.get()
        self.notify_change()

    def _on_exp_change(self, idx: int, var: tk.StringVar):
        while len(self.ctx.expertise_picks) <= idx:
            self.ctx.expertise_picks.append("")
        self.ctx.expertise_picks[idx] = var.get()
        self.notify_change()

    def is_valid(self) -> bool:
        ok, _, _ = validate_proficiency_step(self.ctx, self.character, self.data)
        return ok
