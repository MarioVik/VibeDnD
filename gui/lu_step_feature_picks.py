"""Level-up step: Feature picks (Blessed Strikes, Elemental Affinity, etc.)."""

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
    get_feature_picks_for_level,
    validate_feature_picks,
)


class LuFeaturePicksStep(LevelUpStep):
    tab_title = "Feature Picks"

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
            text="Feature Choices",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        self._scroll = ScrollableFrame(self.frame, auto_hide_scrollbar=True)
        self._scroll.grid(row=1, column=0, sticky="nsew")

        self._radio_vars: dict[str, tk.StringVar] = {}

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._scroll.inner.winfo_children():
            w.destroy()
        self._radio_vars.clear()

        inner = self._scroll.inner
        picks = get_feature_picks_for_level(self.ctx, self.character, self.data)

        for pick_cfg in picks:
            feature = pick_cfg["feature"]
            label = pick_cfg.get("label", f"Choose an option for {feature}:")
            options = pick_cfg["options"]

            SectionHeader(inner, text=feature).pack(
                fill=tk.X, padx=SPACING["lg"],
                pady=(SPACING["lg"], SPACING["sm"]),
            )

            card = CardFrame(inner, pad=SPACING["lg"])
            card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

            tk.Label(
                card.inner,
                text=label,
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w", pady=(0, SPACING["sm"]))

            current = self.ctx.feature_picks.get(feature, "")
            var = tk.StringVar(value=current)
            self._radio_vars[feature] = var

            for option in options:
                rb = ttk.Radiobutton(
                    card.inner,
                    text=option,
                    variable=var,
                    value=option,
                    style="Card.TRadiobutton",
                    command=lambda f=feature, v=var: self._on_pick(f, v),
                )
                rb.pack(anchor="w", pady=SPACING["xs"])

    def _on_pick(self, feature: str, var: tk.StringVar):
        value = var.get()
        if value:
            self.ctx.feature_picks[feature] = value
        else:
            self.ctx.feature_picks.pop(feature, None)
        self.notify_change()

    def is_valid(self) -> bool:
        ok, _, _ = validate_feature_picks(self.ctx, self.character, self.data)
        return ok
